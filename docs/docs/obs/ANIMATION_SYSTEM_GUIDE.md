# 🎬 Animation System Guide

> **Version:** 1.0.0  
> **EPIC:** SKOREQ-OBS-DREAM  
> **Story:** STORY-008  
> **Plugin:** move-transition (2.9.0+)

---

## Overview

The SKOREQ Animation System uses the **move-transition** OBS plugin (move_source_filter) to create smooth, professional animations for sources and scene transitions.

---

## Core Concepts

### Move Source Filter

The `move_source_filter` allows animating source properties over time:

- **Position** (pos_x, pos_y)
- **Scale** (scale_x, scale_y)
- **Rotation** (degrees)
- **Opacity** (0-100)
- **Bounds** (bounds_x, bounds_y)

### Easing Functions

| ID | Name | Description | Best For |
|----|------|-------------|----------|
| 0 | None | Instant | N/A |
| 1 | Linear | Constant speed | Mechanical |
| 2 | Quad In | Slow start | Dramatic entry |
| 3 | Quad Out | Slow end | Natural stop |
| 4 | Quad In/Out | Slow both | Smooth overall |
| 5 | Cubic In | Slower start | Strong entry |
| 6 | Cubic Out | Slower end | Gentle stop |
| **7** | **Cubic In/Out** | **Smooth** | **RECOMMENDED** |
| 8 | Bounce | Bouncy | Playful |
| 9 | Elastic | Springy | Energetic |

---

## Animation Categories

### Entrance Animations

| Animation | Duration | Use Case |
|-----------|----------|----------|
| `fade_in` | 300ms | Subtle appearance |
| `slide_in_left` | 500ms | Side panel entry |
| `slide_in_right` | 500ms | Widget reveal |
| `slide_in_top` | 500ms | Header/title |
| `slide_in_bottom` | 500ms | Lower third |
| `zoom_in` | 400ms | Focus attention |
| `bounce_in` | 500ms | Playful entry |
| `rotate_in` | 600ms | Dramatic reveal |

### Exit Animations

| Animation | Duration | Use Case |
|-----------|----------|----------|
| `fade_out` | 300ms | Clean disappear |
| `slide_out_left` | 500ms | Panel close |
| `slide_out_right` | 500ms | Widget dismiss |
| `zoom_out` | 400ms | Shrink away |
| `pop_out` | 300ms | Quick dismiss |

### Emphasis Animations

| Animation | Duration | Use Case |
|-----------|----------|----------|
| `pulse` | 300ms | Attention grab |
| `shake` | 400ms | Alert/error |
| `wiggle` | 500ms | Playful highlight |
| `glow` | 400ms | Subtle emphasis |
| `highlight_flash` | 200ms | Quick attention |

### Transformation Animations

| Animation | Duration | Use Case |
|-----------|----------|----------|
| `move_smooth` | 800ms | Layout change |
| `resize_smooth` | 600ms | Size change |
| `key_transpose` | 1300ms | **Music key shift** |
| `flip_horizontal` | 400ms | Reveal/compare |
| `flip_vertical` | 400ms | Card flip |

---

## Key Transposition Animation

The signature SKOREQ animation for music education:

### Mechanics

```
Direction: Horizontal slide
Distance: 160px per semitone (fretboard)
Duration: 1300ms
Easing: Cubic In/Out (7)
```

### Hotkeys

| Hotkey | Action |
|--------|--------|
| Ctrl+Up | Transpose up 1 semitone |
| Ctrl+Down | Transpose down 1 semitone |
| Ctrl+Shift+C | Reset to C |
| Ctrl+Shift+G | Jump to G |

### Example: Moving from C to G

```
Semitones: 7 (C→G)
Distance: 7 × 160px = 1120px left
Duration: 1300ms
All widgets move simultaneously
```

---

## Simultaneous Move Chains

Coordinate multiple sources animating together:

### Available Chains

| Chain ID | Name | Description |
|----------|------|-------------|
| `key_shift_all` | Full Key Shift | Transpose all instruments |
| `stagger_entrance` | Staggered Entry | Sequential widget appearance |
| `focus_swap` | Focus Swap | One grows, one shrinks |
| `layout_morph` | Layout Morph | Smoothly change layouts |
| `emphasis_cascade` | Cascading Pulse | Wave of attention |
| `scene_reset` | Reset All | Return to defaults |

### Implementation Example

**Full Key Shift Chain:**

```json
{
  "targets": [
    {"source": "🎸 FretboardWidget", "px_per_semitone": 160},
    {"source": "🎹 PianoWidget", "px_per_semitone": 50},
    {"source": "🔵 CircleOfFifths", "degrees_per_step": 30}
  ],
  "duration": 1300,
  "easing": 7,
  "synchronized": true
}
```

---

## Setting Up Animations in OBS

### Step 1: Add Move Source Filter

1. Right-click source → Filters
2. Click "+" → Add "Move Source"
3. Name filter (e.g., "entrance_animation")

### Step 2: Configure Filter

```
Start Settings:
- Position: Off-screen or starting point
- Scale: Starting scale (e.g., 0.5 for zoom)
- Opacity: Starting opacity (e.g., 0)

End Settings (Get Transform):
- Click "Get Transform" to capture current position
- Adjust values as needed

Transition:
- Duration: 500 (ms)
- Easing: Cubic In/Out (7)
- Start Trigger: Show
- End Trigger: Hide
```

### Step 3: Test Animation

1. Toggle source visibility
2. Animation plays automatically on show/hide
3. Adjust duration/easing as needed

---

## Advanced Scene Switcher Integration

Use macros to trigger animations:

```json
{
  "name": "Key Shift Up Macro",
  "triggers": [
    {"type": "hotkey", "key": "Ctrl+Up"}
  ],
  "actions": [
    {
      "type": "filter",
      "source": "🎸 FretboardWidget",
      "filter": "key_shift",
      "settings": {"pos_x": "-=160"}
    },
    {
      "type": "filter",
      "source": "🎹 PianoWidget", 
      "filter": "key_shift",
      "settings": {"pos_x": "-=50"}
    }
  ]
}
```

---

## OBS WebSocket Batch Requests

For programmatic control via obs-mcp:

```python
# Simultaneous move via batch request
batch_requests = [
    {
        "requestType": "SetSourceFilterSettings",
        "requestData": {
            "sourceName": "🎸 FretboardWidget",
            "filterName": "move",
            "filterSettings": {
                "pos_x": current_x - 160,
                "duration": 1300,
                "easing": 7
            }
        }
    },
    {
        "requestType": "SetSourceFilterSettings",
        "requestData": {
            "sourceName": "🎹 PianoWidget",
            "filterName": "move",
            "filterSettings": {
                "pos_x": current_x - 50,
                "duration": 1300,
                "easing": 7
            }
        }
    }
]

client.call_batch(batch_requests)
```

---

## Voice Commands

ROXY can trigger animations via voice:

| Command | Animation |
|---------|-----------|
| "shift key up" | Key transpose +1 |
| "shift key down" | Key transpose -1 |
| "shift to G" | Transpose to G |
| "reset positions" | Reset all sources |
| "bring in widgets" | Staggered entrance |
| "focus on piano" | Focus swap to piano |
| "hide widgets" | Staggered exit |

---

## Performance Tips

### Optimization

1. **Limit concurrent animations** - Max 4-5 animating sources
2. **Use shorter durations** - Under 1000ms for most
3. **Avoid rotation on large sources** - Performance intensive
4. **Pre-position sources** - Move off-screen before animating in

### Debugging

1. **Test in Preview** - Use Studio Mode
2. **Check Filter Order** - Move filter should be last
3. **Verify Easing** - Wrong easing causes jank
4. **Monitor GPU** - High usage = reduce complexity

---

## Common Animation Recipes

### Lower Third Entry

```
Animation: slide_in_bottom + fade_in
Duration: 400ms
Easing: Cubic Out (6)
Position: Start 100px below final
```

### Widget Focus

```
Animation: zoom_in + brightness_pulse
Duration: 300ms + 200ms
Easing: Cubic In/Out (7)
Scale: 1.0 → 1.1 → 1.0
```

### Scene Change Preparation

```
Step 1: fade_out all widgets (200ms)
Step 2: switch scene
Step 3: stagger_entrance widgets (400ms + 100ms delays)
```

---

## Related Documentation

- [HORIZONTAL_LAYOUT_GUIDE.md](HORIZONTAL_LAYOUT_GUIDE.md) - Scene layouts
- [SCENE_ARCHITECTURE_GUIDE.md](SCENE_ARCHITECTURE_GUIDE.md) - Source organization
- [ROXY_OBS_VOICE_CONTROL.md](ROXY_OBS_VOICE_CONTROL.md) - Voice commands

---

*Part of the SKOREQ OBS Dream Collection*
