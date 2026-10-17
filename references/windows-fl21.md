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

## Save an identified working project

On FL21/API30, an already-named working project was saved successfully through the MIDI-controller command below, with saved bytes and reopened parameters checked. First confirm the active project is the intended separate working copy. Save writes that current project; the command does not take a destination path.

```python
# Inside an enabled Flapi client; after identifying the working project.
import general, transport, midi
assert not transport.isRecording()
if transport.isPlaying():
    transport.stop()
if transport.getLoopMode() != 1:  # 0 = Pattern, 1 = Song
    transport.setLoopMode()
transport.globalTransport(midi.FPT_Save, 1)
```

Wait briefly, verify `general.getChangedFlag()==0`, compare the intended file's bytes/hash, then reopen and read representative parameters, bypass/mix values, faders and routes. An uncompleted Save with a blocked load/dialog does not establish that the command is unsupported. If persistence remains uncertain, preserve the session and request the user's save/close rather than discarding changes. No generic arbitrary-plugin offline writer is supplied here.

Saving Song mode matters: `/R` can render an empty pattern into a valid short WAV. On the observed FL21 stream, Song mode persisted as `ProjectID.LoopActive=true`; that property name/library description is not reliable evidence of a selected Playlist loop. Verify the live mode and save it before exporting. Pass the expected full arrangement duration to the renderer.

## Offline template and preset compatibility

The external sample loader's bundled template and 80-byte Playlist writer can target newer FL releases. For FL21, use a compatible installed factory template and the observed 60-byte Playlist records, then verify the live arrangement. Referenced audio must remain available with the project.

Offline grafting of preset plugin events is different from loading an FST normally in FL. Native wrapper state can retain a source insert/slot destination; in the observed FL21 `WrapperEvent._u1` prefix, the first eight bytes are two little-endian uint32 values for insert and slot. Assign the intended destination before grafting and confirm live locations. Older ASCII plugin-name events also need conversion to the destination stream's UTF-16 strings. Do not generalize these observed fields to other versions without verification. The supplied helper exports presets; it does not import or graft them.

Formatted readback is essential when adapting controls: EQ2 and Maximus frequency knobs do not use the same normalized frequency scale. Record actual displayed Hz, dB and times instead of assuming the requested raw value produced a particular setting.
