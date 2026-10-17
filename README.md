# FL Studio Mastering

A command-based workflow and Codex skill for adapting vocal chains, managing gain and dynamics, exporting native presets, and comparing finished mixes.

The workflow starts with the recording and the existing project. It checks routing, bypass states and effect mix amounts before adding processing, preserves approved versions, and uses matched-volume comparisons to judge changes. It does not apply one compressor threshold or loudness target to every song.

## Included

- [SKILL.md](SKILL.md): instructions for vocal mixing and mastering with an agent.
- [Audio helper](scripts/audio.py): loudness and true-peak analysis, constant-gain comparisons and 24-bit output attenuation.
- [Project helper](scripts/fl_project.py): FL21 mixer inspection, native mixer-preset export and mixer-parameter changes in a new project copy.
- [Render helper](scripts/render_project.ps1): native FL command-line export while protecting existing sessions.
- [Commands](references/commands.md) and [Windows setup](references/windows-fl21.md).
- [Vocal smoothing](references/vocal-smoothing.md): adapt preset components to processed stems while preserving clarity and vocal/beat balance.

## Requirements

Audio commands need Python 3.10+ and FFmpeg/ffprobe on PATH. Project commands need the [FL Studio MCP Server](https://github.com/CryptoJones/FL-Studio-MCP-Server) Python environment, which provides PyFLP and its Python compatibility shim. Live control additionally requires a working [Flapi](https://github.com/MaddyGuthridge/Flapi) connection to FL Studio and a virtual MIDI transport such as loopMIDI on Windows.

FL21 project operations assume a native FL21 stream with ten mixer slots. The render helper targets Windows and defaults to the standard FL Studio 21 installation; override `-FlExe` for another location. See the Windows reference for API30 and embedded-Python compatibility constraints. This repository does not include FL Studio, a driver, a bridge installer or third-party plugins.

## Use the helpers

Run these from the repository root, replacing the example file paths with your own:

```powershell
python scripts/audio.py measure .\music\song.wav
python scripts/audio.py compare --before .\music\before.wav --after .\music\after.wav --out-dir .\comparisons\revision-2 --start 30 --duration 20
python scripts/audio.py trim --input .\music\render-float.wav --output .\music\final-24.wav --ceiling -1.5
```

For project operations, run `scripts/fl_project.py` with the MCP wrapper's Python executable. Close and preserve an existing FL session before using the renderer. Helpers refuse to overwrite their outputs.

## Install the skill

Clone this repository, then copy only the skill files into your Codex skills directory:

```powershell
git clone https://github.com/soin8293/fl-studio-mastering.git
Set-Location fl-studio-mastering
$skillDestination = Join-Path $HOME '.codex\skills\fl-studio-mastering'
if (Test-Path -LiteralPath $skillDestination) { throw 'Skill directory already exists.' }
New-Item -ItemType Directory -Path $skillDestination | Out-Null
Copy-Item -LiteralPath .\SKILL.md -Destination $skillDestination
Copy-Item -LiteralPath .\agents, .\references, .\scripts -Destination $skillDestination -Recurse
```

Then invoke `$fl-studio-mastering` for an FL Studio mixing or mastering request. Configure your own bridge and file paths; the skill does not infer permission to change an unrelated session.

## Operating limits

Plugin presence is different from audible processing: a bypassed slot or a zero mix amount can make its parameter settings irrelevant. Numerical measurements also do not establish that harshness is gone; listen to the full result.

Preset export preserves saved plugin state and mixer settings, while omitting song routing. Structural checks do not establish that a preset has been loaded successfully into FL. Offline mixer edits cover mix, bypass and fader values, not arbitrary native/VST parameter blocks. Live parameter changes need a separate persistence step before they exist in the saved FLP.

The renderer refuses to close pre-existing FL processes. A stalled render leaves its own process available for diagnosis. Final audio conversion and comparison files are separate from the saved project state.

Save Song mode before full-song export, and supply the known arrangement duration to `-ExpectedDurationSeconds`. A decodable short pattern is not a full-song export. Use `-ProjectTitle` when FL's finished caption uses metadata instead of the filename. See the Windows reference for the verified MIDI-controller Save route and offline preset destination/encoding concerns.

## Upstream tools

This workflow builds on [FL Studio](https://www.image-line.com/), [FL Studio MCP Server](https://github.com/CryptoJones/FL-Studio-MCP-Server), [Flapi](https://github.com/MaddyGuthridge/Flapi), [PyFLP](https://github.com/demberto/PyFLP), [FFmpeg](https://ffmpeg.org/) and [loopMIDI](https://www.tobias-erichsen.de/software/loopmidi.html). Their software, authorship and licenses remain with their respective projects; their binaries and source distributions are not bundled here.
