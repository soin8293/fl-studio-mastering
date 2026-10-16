# Helper commands

Run commands from the repository root and replace example paths with your files. All helpers refuse to overwrite outputs. Use `--help` or PowerShell `Get-Help` for options.

## Audio

```powershell
python scripts/audio.py measure .\music\song.wav --report .\working\measurement.json
python scripts/audio.py compare --before .\music\before.wav --after .\music\after.wav --out-dir .\comparisons\revision-2 --start 30 --duration 20
python scripts/audio.py trim --input .\music\render-float.wav --output .\music\final-24.wav --ceiling -1.5 --report .\working\final-check.json
```

`measure` uses FFmpeg loudnorm for analysis and ffprobe for media properties. It does not process the source file. `compare` applies constant gain to the same passage from both inputs. Its common target defaults to -14 LUFS, and is reduced if necessary to keep both files below the peak ceiling. That preview target is independent of the final master's intended loudness.

`trim` only attenuates when needed, includes a small true-peak margin, converts to 24-bit with dither, and checks the final peak. It does not normalize upward or change compression. Silent input is reported by `measure` and rejected for gain calculations.

## Projects and presets

Set `FL_MCP_ROOT` in your local environment to your FL Studio MCP Server checkout, with its Python environment already installed:

```powershell
$flPython = Join-Path $env:FL_MCP_ROOT '.venv\Scripts\python.exe'
& $flPython scripts/fl_project.py inspect --project .\music\song.flp --track 0 --track 3
& $flPython scripts/fl_project.py export-preset --project .\music\song.flp --track 3 --template .\presets\existing-mixer-state.fst --name 'Song - Vocals' --output .\presets\song-vocals.fst
& $flPython scripts/fl_project.py patch-mixer --project .\music\song.flp --changes .\working\changes.json --output .\music\song-alternative.flp
```

The preset template must be an existing native mixer-state FST. It supplies the container format, while the selected saved project insert supplies plugin states and mixer settings. No preset or licensed plugin is included in this repository.

An explicit mixer patch file can contain:

```json
[
  {"track": 3, "slot": 5, "parameter": "mix", "value": 0.32},
  {"track": 3, "slot": 4, "parameter": "enabled", "value": true}
]
```

Supported parameters are `mix` (0-1), `enabled` (boolean), and `fader` (0-1, with 0.8 representing 0 dB; omit slot). The helper changes only the native mixer-parameter event in a new file and checks that unrelated event bytes are preserved. It does not edit arbitrary plugin parameters.

Check the reported track index against the live track name and plugin lineup before editing. The helper uses stream order because a library insert identifier can be offset from FL's displayed number. FST export requires the observed FL21 addressing and ten slots, preserves bypass/mix/fader/mixer-EQ state, and omits song routing. Loading a mixer preset replaces the destination insert's chain.

## Render

```powershell
& scripts/render_project.ps1 -Project .\music\song-alternative.flp -OutputDirectory .\renders\alternative -RestoreProject .\music\song-approved.flp
```

Use `-FlExe` to supply a different installation path. Existing FL sessions must be closed first; the helper does not terminate them. It runs FL's native `/R /Ewav /O` command and accepts completion after a stable, decodable WAV and a finished render state. It stops only its own completed process and can reopen a supplied project.

Output inherits FL's current render-quality and bit-depth settings; inspect it before final conversion. If a timeout or dialog blocks the export, the helper leaves its process intact and reports its PID. Diagnose that process before starting another render.
