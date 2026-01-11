# AI Plugin Configuration Guide

> **STORY:** SKOREQ-OBS-EPIC-001-STORY-002  
> **Status:** Implementation Complete  
> **Date:** 2026-01-09

## Overview

This guide covers the configuration of AI-powered OBS plugins for music education streaming:

- **LocalVocal** - Real-time speech-to-text transcription
- **Background Removal** - AI-powered green screen replacement
- **Advanced Scene Switcher** - Intelligent macro automation
- **CleanStream** (optional) - Verbal tic removal

## LocalVocal Configuration

### Location
`~/.config/obs-studio/plugin_config/obs-localvocal/config.json`

### Key Settings

| Setting | Value | Description |
|---------|-------|-------------|
| `model` | `medium.en` | English-optimized Whisper model |
| `useGPU` | `true` | Enable GPU acceleration |
| `vadEnabled` | `true` | Voice activity detection |
| `showCaptions` | `true` | Display captions in OBS |
| `captionDurationMs` | `3000` | How long captions stay visible |
| `initialPrompt` | Music theory context | Helps with technical terms |

### Music Education Optimization

The `initialPrompt` setting is configured with music theory context:
```
"Music theory lesson about guitar scales, chords, and harmony."
```

This helps the model correctly transcribe:
- Scale names (Dorian, Mixolydian, etc.)
- Chord symbols (Cmaj7, Dm7b5, etc.)
- Interval names (minor third, perfect fifth, etc.)

### Adding LocalVocal to OBS

1. **Add Audio Filter:**
   - Right-click your audio source (Mic/Aux)
   - Filters → Add → LocalVocal Transcription

2. **Add Text Source for Captions:**
   - Add Source → Text (GDI+)
   - Name: `🎤 LocalVocal Captions`
   - Read from file: `~/.roxy/obs-portable/captions/current.txt`

## Background Removal Configuration

### Location
`~/.config/obs-studio/plugin_config/obs-backgroundremoval/config.json`

### Key Settings

| Setting | Value | Description |
|---------|-------|-------------|
| `model` | `mediapipe` | Google's MediaPipe model |
| `useGPU` | `true` | GPU acceleration |
| `segmentationThreshold` | `0.5` | Detection sensitivity |
| `featherAmount` | `3` | Edge softness |
| `lightingProfile` | `studio` | Preset for studio lighting |
| `hairDetectionEnabled` | `true` | Better hair edge detection |

### Adding to Camera Source

1. Right-click camera source
2. Filters → Add → Background Removal
3. Configure:
   - Threshold: 0.5 (adjust for your lighting)
   - Blur: 5px (soften edges)
   - Enable "Hair Detection"

### Troubleshooting

**Guitar neck bleeding through:**
- Increase `segmentationThreshold` to 0.6
- Enable `temporalSmoothing` (0.8)

**Flickering edges:**
- Increase `featherAmount` to 5
- Enable `temporalSmoothing`

## Advanced Scene Switcher Macros

### Location
`~/.roxy/obs-portable/macros/advanced-scene-switcher.json`

### Pre-configured Macros (12 total)

| Macro | Hotkey | Action |
|-------|--------|--------|
| 🎬 Lesson Start | `Ctrl+Shift+1` | Full theory scene + enable all widgets |
| 🎸 Scale Focus | `Ctrl+Shift+2` | Fretboard-focused scene |
| 🎵 Chord Study | `Ctrl+Shift+3` | Braid + fretboard |
| ⭕ Circle Focus | `Ctrl+Shift+4` | Circle of fifths scene |
| 🎤 Performance | `Ctrl+Shift+5` | Clean camera, no overlays |
| 📝 Song Analysis | `Ctrl+Shift+6` | Score + fretboard |
| ☕ BRB Mode | `Ctrl+Shift+B` | Break screen + mute mic |
| ⬆️ Key Shift Up | `Ctrl+Up` | Transpose up semitone |
| ⬇️ Key Shift Down | `Ctrl+Down` | Transpose down semitone |
| 📊 Toggle Intervals | `Ctrl+I` | Show/hide interval overlay |
| 🎤 Toggle Captions | `Ctrl+C` | Show/hide captions |
| 🎹 MIDI Highlight | MIDI input | Auto-highlight chord function |

### Importing Macros

1. Open OBS → Tools → Advanced Scene Switcher
2. Click "Import" button
3. Select `~/.roxy/obs-portable/macros/advanced-scene-switcher.json`
4. Enable desired macros

## CleanStream Configuration (Optional)

CleanStream removes verbal tics (um, uh, like, etc.) from your audio stream.

### Installation
```bash
# If not already installed
flatpak install flathub com.obsproject.Studio.Plugin.CleanStream
```

### Configuration
Add as audio filter on Mic/Aux:
- Sensitivity: Medium (default)
- Words to filter: um, uh, like, you know
- Fade duration: 100ms

## Performance Considerations

### GPU Usage
With all AI plugins enabled:
- LocalVocal: ~10% GPU
- Background Removal: ~15% GPU
- Total overhead: ~25% GPU

### CPU Usage
- Whisper transcription: 1-2 CPU cores
- Scene switching: Negligible

### Memory
- LocalVocal models: 500MB-1.5GB (depending on model size)
- Background Removal: ~200MB

## Files

| File | Purpose |
|------|---------|
| `~/.config/obs-studio/basic/profiles/SKOREQ/basic.ini` | OBS profile settings |
| `~/.config/obs-studio/plugin_config/obs-localvocal/config.json` | LocalVocal settings |
| `~/.config/obs-studio/plugin_config/obs-backgroundremoval/config.json` | Background removal settings |
| `~/.roxy/obs-portable/macros/advanced-scene-switcher.json` | ASS macros |

## Acceptance Criteria

- [x] LocalVocal configured with music-optimized Whisper model
- [x] Background removal configured for studio lighting
- [x] 12 Advanced Scene Switcher macros created
- [x] CleanStream configuration documented
- [x] Documentation with troubleshooting guide complete
