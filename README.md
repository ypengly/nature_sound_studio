# NatureSound Studio (Phase 1)

Create long-form ambient / nature soundtracks (rain, ocean, forest, fireplace…)
with a mixer, seamless randomized looping, and MP3 / WAV / FLAC export.

This is the **Phase 1** build: sound library + import, mixer with
volume/pan/mute/solo, seamless crossfaded looping, and export. Built-in
procedural sound generators, Auto Mix, and the YouTube/video tools described
in the full spec are Phase 2 / Phase 3 and are not in this build yet.

> ⚠️ Only use audio you have permission to use. This app does not download
> audio for you — bring your own recordings, public-domain sounds, or
> properly licensed sound effects.

## 1. Install Python dependencies

Requires Python 3.11+.

```bash
cd nature_sound_studio
python -m venv .venv
# Windows: .venv\Scripts\activate      macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
```

## 2. Install FFmpeg (required for MP3/FLAC export and importing MP3 files)

- **Windows:** download a build from https://www.gyan.dev/ffmpeg/builds/
  (get the "essentials" zip), extract it somewhere like `C:\ffmpeg`, then add
  `C:\ffmpeg\bin` to your PATH (Settings → search "Environment Variables" →
  edit the `Path` variable → add the folder → restart your terminal).
  Alternatively, just drop `ffmpeg.exe` into the `nature_sound_studio` folder
  next to `app.py` — the app looks there too.
- **macOS:** `brew install ffmpeg`
- **Linux:** `sudo apt install ffmpeg` (Debian/Ubuntu) or your distro's
  equivalent.

Verify it worked:

```bash
ffmpeg -version
```

## 3. Run the app

```bash
python app.py
```

## 4. Using it

1. **Library tab** — import your WAV/MP3/FLAC source sounds, tag each with a
   category (Rain, Ocean, Forest…), preview or delete them.
2. **Mixer tab** — sounds you add from the Library appear here as layers with
   volume, pan, mute, solo and on/off controls. Add the same sound more than
   once for a thicker layer.
3. **Export tab** — pick a filename, duration (presets or a custom number of
   minutes), format and quality, then hit **Preview Mix** for a quick 3-minute
   sample or **Generate Audio** for the full-length render. Rendering happens
   in 30-second chunks in a background thread, so the app stays responsive
   and memory use stays low even for an 8-hour track.

The preset buttons above the tabs apply a starting mix (e.g. "Cozy Rain",
"Deep Sleep") using whatever matching sounds are already in your library —
import at least one sound per category you want to use.

All your files live in `~/NatureSoundStudio/` (Projects, Generated, Presets,
SourceSounds, Exports, Previews). Set the `NATURESOUND_HOME` environment
variable before launching to use a different folder.

## 5. Package as a Windows .exe

```bash
pip install pyinstaller
pyinstaller --noconfirm --windowed --name "NatureSoundStudio" ^
    --add-data "presets;presets" app.py
```

Then copy `ffmpeg.exe` into the resulting `dist/NatureSoundStudio/` folder
(next to the generated `.exe`) so exporting works on a machine without
FFmpeg installed. Run the build from that folder to confirm it launches
before distributing it.

## Project structure

```
nature_sound_studio/
├── app.py                 entry point
├── config.py               where user data/files live
├── requirements.txt
├── audio/
│   ├── loader.py            reads/validates/normalizes source files
│   ├── effects.py           pan, edge fades
│   ├── crossfade.py         equal-power crossfade
│   ├── generator.py         LayerStream: endless randomized non-repeating stream
│   ├── mixer.py              combines layers, chunked rendering
│   ├── exporter.py           FFmpeg export + WAV preview, progress/cancel
│   └── errors.py
├── ui/
│   ├── main_window.py
│   ├── library_panel.py / library_model.py
│   ├── mixer_panel.py
│   ├── export_panel.py
│   ├── render_worker.py      background QThread for rendering
│   └── style.py               dark theme
└── presets/presets.json
```

## Troubleshooting

- **"FFmpeg was not found"** — see step 2 above; make sure `ffmpeg -version`
  works in the same terminal you launch the app from.
- **A sound won't import** — check it's actually a WAV/MP3/FLAC file and
  longer than half a second; the app will tell you which file and why.
- **Export says "not enough disk space"** — free up space or export to a
  different drive; the estimate is shown in the error message.
