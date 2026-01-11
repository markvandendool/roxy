# 📱 Vertical Streaming Guide

> **Version:** 1.0.0  
> **EPIC:** SKOREQ-OBS-DREAM  
> **Story:** STORY-006  
> **Canvas:** 1080×1920 @ 60fps (9:16)

---

## Overview

The SKOREQ Vertical Collection provides **5 master scenes** optimized for mobile-first platforms: TikTok, YouTube Shorts, and Instagram Reels.

---

## Platform Specifications

| Platform | Max Duration | Safe Zone (Top) | Safe Zone (Bottom) | Recommended |
|----------|-------------|-----------------|--------------------| ------------|
| **TikTok** | 3 min | 150px | 200px | V1, V4 |
| **YouTube Shorts** | 60s | 100px | 150px | V2, V4 |
| **Instagram Reels** | 90s | 120px | 180px | V3, V4 |

### Safe Zones

Each platform overlays UI elements on videos. Avoid placing text/watermarks in these areas:

```
┌────────────────────┐ ← Top 100-150px unsafe
│   Platform UI      │
├────────────────────┤
│                    │
│   SAFE ZONE        │
│   (Place content   │
│    here)           │
│                    │
├────────────────────┤
│   Platform UI      │ ← Bottom 150-200px unsafe
│   + Right edge     │ ← Right 60-80px unsafe
└────────────────────┘
```

---

## Master Scene Reference

### 📱 V1: TikTok Piano (F9)

**Vertical piano focus** - Center piano widget with face cam and hands.

```
┌──────────────────┐
│                  │
│    Face Cam      │
│   (Elgato Pro)   │
├──────────────────┤
│                  │
│                  │
│  Piano Widget    │
│   (Full Width)   │
│                  │
│                  │
├──────────────────┤
│  Overhead Cam    │
│    (Hands)       │
└──────────────────┘
```

**Sources:**
- Top: Face cam (1080×480)
- Middle: Piano widget (1080×960)
- Bottom: Overhead hands (1080×480)

**Best For:** Quick piano tips, chord breakdowns, "How to play X"

---

### 📱 V2: YouTube Shorts Guitar (F10)

**Vertical fretboard** - Large fretboard with face reaction.

```
┌──────────────────┐
│                  │
│                  │
│   Fretboard      │
│   Widget         │
│   (Rotated 90°)  │
│                  │
│                  │
│                  │
├──────────────────┤
│                  │
│    Face Cam      │
└──────────────────┘
```

**Sources:**
- Top: Fretboard widget rotated (1080×1440)
- Bottom: Face cam (1080×480)

**Best For:** Scale patterns, chord shapes, quick guitar tips

**Special Feature:** Key transposition works vertically (120px per semitone)

---

### 📱 V3: Instagram Reels Theory (Ctrl+F9)

**Circle of Fifths focus** - Theory explanation with visual.

```
┌──────────────────┐
│                  │
│   Circle of      │
│    Fifths        │
│   (Square)       │
│                  │
├──────────────────┤
│                  │
│    Face Cam      │
│         ┌───────┐│
│         │Harmnic││
│         └───────┘│
└──────────────────┘
```

**Sources:**
- Top: COF widget (1080×1080, square)
- Bottom: Face cam with Harmonic Profile overlay

**Best For:** Theory explainers, "Did you know" content, key relationships

---

### 📱 V4: Mobile Full Teaching (Ctrl+F10)

**Complete vertical teaching** - All elements stacked.

```
┌──────────────────┐
│                  │
│   Main Camera    │
│                  │
├──────────────────┤
│   Piano Widget   │
├──────────────────┤
│ Fretboard Widget │
├─────────┬────────┤
│   COF   │Harmnic │
└─────────┴────────┘
```

**Sources:**
- Camera: 1080×720
- Piano: 1080×400
- Fretboard: 1080×400
- COF + Harmonic: 540×400 each

**Best For:** Full lessons, multi-concept explanations

---

### 📱 V5: Vertical Multi-Cam (Ctrl+F11)

**3-way camera split** - Multi-angle performance.

```
┌──────────────────┐
│    Face Cam      │
│                  │
├──────────────────┤
│   Main Camera    │
│                  │
├──────────────────┤
│  Overhead Cam    │
│    (Hands)       │
└──────────────────┘
```

**Sources:**
- Top: Face cam (1080×640)
- Middle: Main camera (1080×640)
- Bottom: Overhead hands (1080×640)

**Best For:** Performance videos, technique demonstrations

---

## Quick Reference

| Hotkey | Scene | Platform |
|--------|-------|----------|
| **F9** | TikTok Piano | TikTok |
| **F10** | Shorts Guitar | YouTube |
| **Ctrl+F9** | Reels Theory | Instagram |
| **Ctrl+F10** | Full Teaching | All |
| **Ctrl+F11** | Multi-Cam | All |

---

## Switching Between Horizontal & Vertical

### Method 1: Scene Collections

1. OBS → Scene Collection → SKOREQ-Horizontal
2. OBS → Scene Collection → SKOREQ-Vertical

### Method 2: Profile Switching (Preserves Scenes)

1. Ctrl+H → Switch to horizontal profile
2. Ctrl+V → Switch to vertical profile

### Method 3: Virtual Camera + Crop

For quick tests, use a horizontal scene with 9:16 crop:
1. Apply crop filter: Left 740, Right 740 (for 2560→1080)
2. Start virtual camera
3. Record/stream cropped output

---

## Recording Settings

### Vertical Profile (SKOREQ-Vertical)

| Setting | Value |
|---------|-------|
| Resolution | 1080×1920 |
| FPS | 60 |
| Encoder | NVENC H.264 |
| Bitrate | 8 Mbps |
| Keyframe | 2s |
| Profile | High |
| Output | ~/Videos/SKOREQ/vertical/ |

### File Naming

Default: `%CCYY-%MM-%DD %hh-%mm-%ss`

Example: `2026-01-10 14-30-45.mkv`

---

## Widget Rotation for Vertical

Some widgets need rotation/cropping for vertical display:

### Fretboard Widget
```json
{
  "rotation": 90,
  "notes": "Rotated 90° clockwise for vertical display"
}
```

### Piano Widget
```json
{
  "crop": {"left": 200, "right": 200},
  "notes": "Cropped to fit 9:16 while showing key range"
}
```

### Circle of Fifths
```json
{
  "natural_fit": true,
  "notes": "COF is circular, naturally fits any orientation"
}
```

---

## Platform-Specific Tips

### TikTok
- Keep text in center 70% of screen
- Hook in first 1-2 seconds
- Use trending sounds when relevant
- Vertical piano content performs well

### YouTube Shorts
- Front-load the value (60s max)
- Clear titles/text
- End with call-to-action
- Guitar content very popular

### Instagram Reels
- Aesthetic matters more
- Theory content does well
- Use covers/trending topics
- Caption important (often watched muted)

---

## Performance Considerations

Vertical recording uses fewer resources than horizontal:

| Canvas | Pixels | Relative Load |
|--------|--------|---------------|
| 2560×1440 | 3.7M | 100% |
| 1080×1920 | 2.1M | 56% |

**Tip:** For multi-platform, record horizontal and crop to vertical in post.

---

## Export for Multiple Platforms

### From MKV to Platform-Ready

```bash
# TikTok (up to 3 min)
ffmpeg -i input.mkv -c:v libx264 -preset slow -crf 18 \
       -c:a aac -b:a 192k tiktok_output.mp4

# YouTube Shorts (up to 60s)
ffmpeg -i input.mkv -t 60 -c:v libx264 -preset slow -crf 18 \
       -c:a aac -b:a 192k shorts_output.mp4

# Instagram Reels (up to 90s)
ffmpeg -i input.mkv -t 90 -c:v libx264 -preset slow -crf 18 \
       -c:a aac -b:a 192k reels_output.mp4
```

---

## Related Documentation

- [HORIZONTAL_LAYOUT_GUIDE.md](HORIZONTAL_LAYOUT_GUIDE.md) - 16:9 scenes
- [SCENE_ARCHITECTURE_GUIDE.md](SCENE_ARCHITECTURE_GUIDE.md) - Full architecture
- [ANIMATION_SYSTEM_GUIDE.md](ANIMATION_SYSTEM_GUIDE.md) - Transitions

---

*Part of the SKOREQ OBS Dream Collection*
