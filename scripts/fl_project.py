"""Inspect FL21 mixer state, export native FSTs, or patch mixer parameters in a copy."""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile

from fl_studio_mcp import _compat
_compat.install()
import pyflp
from pyflp.mixer import MixerID


def check(condition, message):
    if not condition:
        raise ValueError(message)


def load(path):
    path = Path(path).resolve(strict=True)
    project = pyflp.parse(path)
    check(str(project.version).split('.')[0] == '21', 'Only observed FL21 streams are supported.')
    return path, project


def track_values(project, index):
    tracks = list(project.mixer)
    check(0 <= index < len(tracks), 'Mixer track is outside the project.')
    values = [deepcopy(v) for v in project.events.first(MixerID.Params).value
              if v['channel_data'] >> 6 == 128 + index]
    check(bool(values), 'The observed FL21 parameter addressing does not match this file.')
    return tracks[index], values


def slot_blocks(track):
    result, block = [], {}
    for event in track.events:
        ident = int(event.id)
        if ident == 201:
            block['plugin'] = event.value
        elif ident == 203:
            block['display_name'] = event.value
        elif ident == 213:
            block['state_sha256'] = hashlib.sha256(bytes(event)).hexdigest()
        elif ident == 98:
            result.append({'slot': event.value, **block})
            block = {}
    return result


def inspect(project, selected):
    output = []
    for index, track in enumerate(project.mixer):
        if selected and index not in selected:
            continue
        _, values = track_values(project, index)
        slots = slot_blocks(track)
        lookup = {(int(v['id']), v['channel_data'] & 63): v['msg'] for v in values}
        if not selected and not track.name and not any('plugin' in s for s in slots) and index:
            continue
        for slot in slots:
            slot['enabled'] = bool(lookup.get((0, slot['slot']), 0))
            slot['mix'] = lookup.get((1, slot['slot']), 0) / 12800
        flags = next((int(e.value['flags']) for e in track.events if int(e.id) == 236), None)
        output.append({'track': index, 'name': track.name, 'flags': flags,
                       'effects_enabled': bool(flags & 4) if flags is not None else None,
                       'fader_raw': lookup.get((192, 0)), 'slots': slots})
    return {'fl_version': str(project.version), 'tracks': output}


def validate_and_write(output, data, validate):
    output = Path(output).resolve()
    check(not output.exists(), f'Refusing to overwrite {output}')
    with tempfile.TemporaryDirectory(prefix='fl-preset-check-') as folder:
        staged = Path(folder) / output.name
        staged.write_bytes(data)
        validate(pyflp.parse(staged))
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('xb') as file:
        file.write(data)
    return {'output': str(output), 'sha256': hashlib.sha256(data).hexdigest(),
            'parsed_and_verified': True, 'runtime_reload_tested': False}


def export(args, source, project):
    template_path, template = load(args.template)
    check(int(template.format) == 64, 'Template must be a native mixer-state FST.')
    track, values = track_values(project, args.track)
    check([s['slot'] for s in slot_blocks(track)] == list(range(10)), 'Expected 10 FL21 slots.')
    name = deepcopy(next(e for e in template.events if int(e.id) == 204))
    name.value = args.name
    prefix = {199, 159, 28, 37, 42}
    body = {95, 149, 236, 201, 203, 212, 155, 128, 41, 213, 98}
    events = [deepcopy(e) for e in template.events if int(e.id) in prefix] + [name]
    events += [deepcopy(e) for e in track.events if int(e.id) in body]
    params = deepcopy(project.events.first(MixerID.Params))
    params.value = [v for v in values if not 64 <= int(v['id']) <= 191]
    for value in params.value:
        value['channel_data'] = (130 << 6) | (value['channel_data'] & 63)
    events.append(params)
    payload = b''.join(bytes(e) for e in events)
    raw = template_path.read_bytes()[:18] + len(payload).to_bytes(4, 'little') + payload

    def validate(parsed):
        check(int(parsed.format) == 64, 'Wrong preset format.')
        state_ids = (201, 203, 212, 213)
        check([bytes(e) for e in parsed.events if int(e.id) in state_ids] ==
              [bytes(e) for e in track.events if int(e.id) in state_ids], 'Plugin states changed.')
        check(bytes(parsed.events.first(MixerID.Params)) == bytes(params), 'Mixer state changed.')
        check(not any(int(e.id) in (235, 154, 147) for e in parsed.events), 'Song routing leaked.')
    return validate_and_write(args.output, raw, validate)


def patch(args, source, project):
    changes = json.loads(Path(args.changes).read_text(encoding='utf-8-sig'))
    check(isinstance(changes, list) and bool(changes), 'Changes must be a nonempty JSON array.')
    old = project.events.first(MixerID.Params)
    updated = deepcopy(old)
    seen, receipt = set(), []
    for change in changes:
        track, slot, parameter = change['track'], change.get('slot', 0), change['parameter']
        check(isinstance(track, int) and not isinstance(track, bool), 'Track must be an integer.')
        track_values(project, track)
        check(isinstance(slot, int) and 0 <= slot <= 9, 'Slot must be an integer from 0 to 9.')
        check(parameter in ('mix', 'enabled', 'fader'), 'Unsupported mixer parameter.')
        check(parameter != 'fader' or slot == 0, 'Fader changes do not take a slot.')
        value = change['value']
        if parameter == 'enabled':
            check(isinstance(value, bool), 'Enabled value must be boolean.')
            raw, ident = int(value), 0
        else:
            check(isinstance(value, (int, float)) and not isinstance(value, bool) and 0 <= value <= 1,
                  'Mix/fader value must be a finite number in [0,1].')
            raw, ident = round(value * (12800 if parameter == 'mix' else 16000)), 1 if parameter == 'mix' else 192
        key = (track, slot, ident)
        check(key not in seen, 'A parameter was specified twice.')
        seen.add(key)
        found = [v for v in updated.value if v['channel_data'] >> 6 == 128 + track and
                 v['channel_data'] & 63 == slot and int(v['id']) == ident]
        check(len(found) == 1, 'Could not identify exactly one mixer parameter.')
        receipt.append({**change, 'before_raw': found[0]['msg'], 'after_raw': raw})
        found[0]['msg'] = raw
    original, serialized = source.read_bytes(), bytes(old)
    check(original.count(serialized) == 1, 'Mixer event is not uniquely locatable.')
    replacement = bytes(updated)
    raw = original.replace(serialized, replacement, 1)
    raw = raw[:18] + (len(raw)-22).to_bytes(4, 'little') + raw[22:]

    def validate(parsed):
        check(bytes(parsed.events.first(MixerID.Params)) == replacement, 'Mixer patch did not persist.')
        check([bytes(e) for e in parsed.events if int(e.id) != 225] ==
              [bytes(e) for e in project.events if int(e.id) != 225], 'Unrelated project state changed.')
    return {**validate_and_write(args.output, raw, validate), 'changes': receipt}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    inspect_parser = sub.add_parser('inspect')
    inspect_parser.add_argument('--project', required=True)
    inspect_parser.add_argument('--track', type=int, action='append')
    preset = sub.add_parser('export-preset')
    preset.add_argument('--project', required=True)
    preset.add_argument('--track', type=int, required=True)
    preset.add_argument('--template', required=True)
    preset.add_argument('--name', required=True)
    preset.add_argument('--output', required=True)
    mixer = sub.add_parser('patch-mixer')
    mixer.add_argument('--project', required=True)
    mixer.add_argument('--changes', required=True)
    mixer.add_argument('--output', required=True)
    args = parser.parse_args()
    try:
        source, project = load(args.project)
        if args.command == 'inspect':
            result = inspect(project, args.track)
        elif args.command == 'export-preset':
            result = export(args, source, project)
        else:
            result = patch(args, source, project)
        print(json.dumps(result, indent=2))
    except (ValueError, OSError, KeyError, StopIteration) as error:
        parser.exit(1, f'{error}\n')


if __name__ == '__main__':
    main()
