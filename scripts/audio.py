"""Measure audio, make constant-gain comparisons, and attenuate final WAVs."""
import argparse
import json
import math
import os
from pathlib import Path
import re
import subprocess


def run(args):
    process = subprocess.run(args, capture_output=True, text=True)
    if process.returncode:
        raise ValueError(process.stderr[-2500:])
    return process


def finite(value):
    number = float(value)
    return number if math.isfinite(number) else None


def probe(path):
    return json.loads(run(['ffprobe', '-v', 'error', '-show_entries',
                          'format=duration:stream=codec_type,codec_name,sample_rate,channels,bits_per_raw_sample',
                          '-of', 'json', str(path)]).stdout)


def measure(path, start=None, duration=None):
    path = Path(path).resolve(strict=True)
    selection = []
    if start is not None:
        selection += ['-ss', str(start)]
    if duration is not None:
        selection += ['-t', str(duration)]
    result = run(['ffmpeg', '-hide_banner', '-nostats', *selection, '-i', str(path),
                  '-af', 'loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json',
                  '-f', 'null', os.devnull])
    blocks = re.findall(r'\{[^{}]*"input_i"[^{}]*\}', result.stderr)
    if not blocks:
        raise ValueError('No loudness measurement returned; check the audio/selection.')
    stats = json.loads(blocks[-1])
    return {'path': str(path), 'integrated_lufs': finite(stats['input_i']),
            'true_peak_dbfs': finite(stats['input_tp']), 'lra_lu': finite(stats['input_lra']),
            'media': probe(path)}


def preflight_outputs(paths):
    resolved = [Path(p).resolve() for p in paths]
    if len(set(resolved)) != len(resolved):
        raise ValueError('Output paths must be distinct.')
    for path in resolved:
        if path.exists():
            raise FileExistsError(f'Refusing to overwrite {path}')
    return resolved


def report_file(path, data):
    if path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('x', encoding='utf-8') as file:
            json.dump(data, file, indent=2, allow_nan=False)


def require_signal(stats):
    if stats['integrated_lufs'] is None or stats['true_peak_dbfs'] is None:
        raise ValueError('Audio is silent or cannot be measured; refusing gain calculation.')


def encode(source, target, gain, start=None, duration=None, bits=24):
    target.parent.mkdir(parents=True, exist_ok=True)
    selection = [] if start is None else ['-ss', str(start), '-t', str(duration)]
    run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-n', *selection,
         '-i', str(source), '-map', '0:a:0', '-af',
         f'volume={gain:.6f}dB,aresample=dither_method=triangular',
         '-c:a', f'pcm_s{bits}le', str(target)])


def execute(args):
    if args.command == 'measure':
        if args.report:
            preflight_outputs([args.report])
        result = measure(args.input)
        report_file(args.report, result)
        return result
    if args.command == 'trim':
        outputs = [args.output] + ([args.report] if args.report else [])
        preflight_outputs(outputs)
        before = measure(args.input)
        require_signal(before)
        gain = min(0.0, args.ceiling - before['true_peak_dbfs'] - 0.02)
        gain = math.floor(gain * 100) / 100
        output = Path(args.output).resolve()
        if output.suffix.lower() != '.wav':
            raise ValueError('Finishing output must be a WAV.')
        encode(before['path'], output, gain)
        after = measure(output)
        require_signal(after)
        if after['true_peak_dbfs'] > args.ceiling + 0.02:
            raise ValueError('Output true peak exceeded the requested ceiling.')
        result = {'gain_db': gain, 'before': before, 'after': after}
        report_file(args.report, result)
        return result
    if args.start < 0 or args.duration <= 0:
        raise ValueError('Comparison start must be nonnegative and duration positive.')
    output_dir = Path(args.out_dir).resolve()
    outputs = [output_dir / 'A-before.wav', output_dir / 'B-after.wav', output_dir / 'comparison.json']
    preflight_outputs(outputs)
    sources = [Path(args.before).resolve(strict=True), Path(args.after).resolve(strict=True)]
    for source in sources:
        total = float(probe(source)['format']['duration'])
        if args.start + args.duration > total + 0.01:
            raise ValueError('The selected passage must fit inside both recordings.')
    stats = [measure(source, args.start, args.duration) for source in sources]
    for item in stats:
        require_signal(item)
    target = min(args.target, *(item['integrated_lufs'] + args.ceiling -
                               item['true_peak_dbfs'] - 0.05 for item in stats))
    result = {'start_seconds': args.start, 'duration_seconds': args.duration,
              'requested_lufs': args.target, 'effective_lufs': target, 'files': []}
    for source, output, before in zip(sources, outputs, stats):
        gain = target - before['integrated_lufs']
        encode(source, output, gain, args.start, args.duration, bits=16)
        after = measure(output)
        require_signal(after)
        if abs(after['integrated_lufs'] - target) > 0.15:
            raise ValueError('The preview loudness did not match the target.')
        if after['true_peak_dbfs'] > args.ceiling + 0.02:
            raise ValueError('Preview true peak exceeded the ceiling.')
        result['files'].append({'gain_db': gain, 'before': before, 'after': after})
    report_file(outputs[-1], result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    measurement = commands.add_parser('measure')
    measurement.add_argument('input')
    measurement.add_argument('--report')
    trim = commands.add_parser('trim')
    trim.add_argument('--input', required=True)
    trim.add_argument('--output', required=True)
    trim.add_argument('--ceiling', type=float, default=-1.5)
    trim.add_argument('--report')
    compare = commands.add_parser('compare')
    compare.add_argument('--before', required=True)
    compare.add_argument('--after', required=True)
    compare.add_argument('--out-dir', required=True)
    compare.add_argument('--start', type=float, default=0)
    compare.add_argument('--duration', type=float, default=20)
    compare.add_argument('--target', type=float, default=-14)
    compare.add_argument('--ceiling', type=float, default=-1.5)
    args = parser.parse_args()
    if hasattr(args, 'ceiling') and (not math.isfinite(args.ceiling) or args.ceiling > 0):
        parser.error('Use a finite true-peak ceiling at or below 0 dBFS.')
    try:
        print(json.dumps(execute(args), indent=2, allow_nan=False))
    except (ValueError, OSError, KeyError) as error:
        parser.exit(1, f'{error}\n')


if __name__ == '__main__':
    main()
