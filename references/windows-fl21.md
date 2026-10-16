# Windows and FL21 setup

Use an existing working bridge before changing an installation. The project helpers support FL21 native mixer streams. Live control additionally depends on the installed FL MIDI API and the bridge's compatibility with its embedded Python.

## Dependencies and local configuration

- FL Studio and the plugins required by the project.
- Python and FFmpeg/ffprobe for audio operations.
- [FL Studio MCP Server](https://github.com/CryptoJones/FL-Studio-MCP-Server), with its isolated environment and live extra when needed.
- [Flapi](https://github.com/MaddyGuthridge/Flapi) for remote MIDI-controller scripting calls.
- A running virtual MIDI transport, such as [loopMIDI](https://www.tobias-erichsen.de/software/loopmidi.html).

Follow the upstream bridge installation instructions for your version. This skill does not install the transport or drivers. Store your installation paths in your local environment rather than adding them to this repository. `FL_MCP_ROOT` can point to the MCP wrapper checkout for the examples below.

```powershell
$flPython = Join-Path $env:FL_MCP_ROOT '.venv\Scripts\python.exe'
& $flPython -c 'import flapi; assert flapi.enable(); import general,mixer; print(general.getVersion(),mixer.getTrackName(0)); flapi.disable()'
```

Require an actual FL read to establish access. A port list or connection flag alone can report the wrong output device. Fresh Python clients avoid stale connection state after FL restarts. Import FL modules after enabling Flapi and disconnect when finished.

## MIDI ports and FL21 compatibility

Keep request and response ports distinct and follow the routing expected by your controller. For a controller adapted to send responses directly through `device.midiOutSysex`, an example is:

| FL device | Example assignment |
|---|---|
| Flapi Request input | Enabled, request controller, port 236 |
| Flapi Response output | Port 236 |
| Flapi Request output | Port 235 |
| Flapi Response input | Response controller, port 237 |

That arrangement applies to the direct-response adaptation, not every upstream installation. The request input and reply output share a number; the request output must not take the reply output's number. Preserve the values across restarts. Check the transport before repeating port changes or reinstalling the bridge.

FL21 API30 uses a restricted embedded Python 3.9 environment. A bridge may require an accessible standard library, explicit controller import paths, compatibility with the absence of `typing.Self`, and a logging implementation that avoids unavailable modules. Interscript dispatch support can also differ; a direct-response adaptation must preserve packet framing and mark reply origin correctly. These are bridge compatibility requirements, not functionality installed by this repository. Do not overwrite a working adapted controller with an unmodified installer.

## API constraints

Use APIs present in the installed FL version. `mixer.getRouteToLevel` is unavailable in API30; route-enabled queries can be used where supported. Channel Rack filtering can change the meaning of a channel index.

Capture parameter values before edits, wait briefly after a write, then verify the formatted display value. A mixer fader value of 0.8 is 0 dB. A loaded plugin can still be bypassed or blended at 0%, so inspect the actual slot state.

Exception serialization in older embedded Python can hide the original error behind an `__import__()` keyword-argument error. Check request syntax and API availability before treating that message as a reason to reinstall.

## Render and reopen

FL's [official export manual](https://www.image-line.com/fl-studio-learning/fl-studio-online-manual/html/fformats_save_export.htm#commandline_export) describes `/R /Ewav` and `/O`.

An existing FL instance can cause another command-line render request to exit without exporting. Preserve and close the current session before using the renderer. FL may remain running after export; a completed WAV and a non-rendering state are more useful completion signals than waiting only for exit.

Before any separately authorized restart, identify the saved project, confirm that playback/recording is stopped, and establish that there are no unsaved changes. Do not force-close an uncertain session. The helper refuses to close a pre-existing process. Reopen the intended project afterward and verify a fresh bridge connection if live control is needed.

Live plugin edits are separate from saved project data. Saving arbitrary live plugin states through an FL API is not provided by these helpers; use a supported persistence route or save the project before rendering its copy.
