---
name: fl-studio-mastering
description: Improve vocals, harshness, dynamics and final loudness in FL Studio using command-based control, saved project edits, native presets and measured audio comparisons. Use for FL Studio mixing or mastering work and adapting an existing vocal preset to a recording.
---

# FL Studio mastering

Deliver an audible revision and a recoverable project, then follow the user's listening preference. A louder or more processed version is not automatically better.

## Start with the actual song

Use commands and the FL bridge. Use command-based control; use GUI automation only when explicitly requested. Read [the Windows setup](references/windows-fl21.md) when connecting or rendering on Windows; it covers bridge requirements, MIDI wiring and restart constraints. Do not repeat installation when the working bridge already exists.

Locate the saved project and source audio. Preserve the original and any already-approved WAV/project. Work on a separately named revision; leave source recordings intact. A FLP is not a self-contained sample archive.

Establish which clips are instrumental, vocals or alternate full mixes before removing or rerouting them. Inspect channel-to-insert routing and the path to Master. Confirm actual effect bypass states, slot mix amounts, faders and mixer EQ; a loaded plugin's parameter values do not establish that it affects the sound.

## Diagnose before adding processing

Measure a baseline and inspect the active chain. Separate input gain, compressor makeup gain, bus gain, saturation and master limiting. Excessive gain at several stages can drive later processing harder. A threshold near the noise floor can compress almost the whole vocal. Identify the actual contributor before applying broad cuts or adding another compressor.

Treat isolated resonances or sibilance at the vocal/source level when possible. Use small, audible changes, including appropriate dynamic EQ or de-essing if tools support them; do not dull the entire mix to solve one vocal frequency. Check noise between phrases rather than assuming every piercing sound is noise. Preserve desired body, vocal balance and transient shape.

For smoothness on already-processed vocal exports, read [vocal smoothing](references/vocal-smoothing.md). Establish what processing is baked into the recording; adapt useful preset components and compare restrained EQ/de-essing before adding more broadband compression. Keep instrumental processing within the agreed scope; vocal harshness alone does not justify EQ on the beat.

Adapt an existing preset's active stages rather than automatically duplicating the entire chain on another insert. When the user requests serial or parallel processing, inspect its routing, gain and purpose and compare the result. Preserve disabled effects unless enabling one is a deliberate experiment. Auto-Tune key/scale and intensity belong to the particular song.

Choose settings for the recording instead of applying fixed thresholds blindly. Do not flatten all dynamics merely to make the level consistent. Set loudness for the song and requested use; a comparison preview at -14 LUFS does not mean the final master must target -14 LUFS.

## Edit and persist

The native MCP's `fl_connect` and `fl_eval_expr` or the installed Flapi Python client can operate mixer/effect parameters. Prefer verified APIs for the installed FL version. Snapshot values before changing them, wait briefly after a write, and verify the formatted readback. The bridge's default fader value 0.8 is 0 dB, not linear amplitude.

Live plugin writes are not automatically saved. On the verified FL21 route, the MIDI-controller Save command can persist an already-named working project; read the Windows reference and verify changed flag, saved bytes and reopened parameter values. Ask the user to save only if that command cannot complete or preservation is uncertain. Offline helpers below support inspection, mixer-parameter patches and FST export; they do not implement arbitrary native/VST plugin parameter editing or preset import.

For offline FL21 edits, use `scripts/fl_project.py` with the wrapper's Python environment. It preserves unrelated project bytes and refuses overwrites. For FST export, use an existing native mixer-preset template, retaining exact plugin states, bypasses and mix values. The helper omits song-specific routing and verifies the generated container; distinguish that from loading the FST in FL. Read [helper usage](references/commands.md) when performing these operations.

## Render, compare, deliver

Render with FL's command-line `/R /Ewav`; `scripts/render_project.ps1` tracks only its own process. Read the Windows reference before any restart: render commands can silently do nothing while another FL instance is running. Never discard unsaved changes to make rendering work. Do not declare completion from process exit or file existence alone; verify that the WAV is complete and decodable.

Select Song mode and save it before rendering a complete arrangement. Supply the known arrangement duration to the renderer; an empty Pattern-mode export can be a valid, decodable two-second WAV. Supply the project title when FL uses title metadata instead of the filename for its finished window caption.

Use `scripts/audio.py` for loudness/true-peak measurements, constant output attenuation and matched-volume excerpts. Match the same passage in both files. Keep comparison files distinct from the full master; present the full output as well. A constant trim preserves dynamics; it does not repair distortion or remove noise.

Check final duration, format, loudness and true peak, and compare vocal balance, harshness, noise and dynamics. Measurements are evidence, not a substitute for listening. Never claim to have heard a file from numerical analysis alone. Ask for the user's judgment on a bounded comparison when listening is unavailable.

Deliver the full WAV, edited project and requested native presets. Explain the audible changes and any difference between the project render and file-only finishing trim. Record the preferred full file, remaining uncertainty and command route in the song's own notes so a future session can resume without inferring preference from filenames. Improve this skill from demonstrated outcomes; retain successful versions when experimenting.
