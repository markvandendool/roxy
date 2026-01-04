# Vision #1 Architecture

## Overview

Vision #1 implements OBS → Website NDI compositing with multi-camera support, timeline capture, and internal recording.

## System Architecture

```
┌─────────────┐
│     OBS     │──NDI──┐
│  (Cameras)  │       │
└─────────────┘       │
                      ▼
┌─────────────────────────────────────────┐
│         Browser (MindSong Hub)          │
│                                          │
│  ┌────────────────────────────────────┐ │
│  │  NDIReceiverService (libndi WASM)  │ │
│  │  - Discovery                       │ │
│  │  - Connection                      │ │
│  │  - Frame Decoding                  │ │
│  └────────────────────────────────────┘ │
│                    │                     │
│                    ▼                     │
│  ┌────────────────────────────────────┐ │
│  │   CameraInputService               │ │
│  │  - Multi-camera management         │ │
│  │  - Active/paused state             │ │
│  │  - LRU eviction                   │ │
│  └────────────────────────────────────┘ │
│                    │                     │
│                    ▼                     │
│  ┌────────────────────────────────────┐ │
│  │      CameraLayer (WebGPU)          │ │
│  │  - Layer 0 (background)           │ │
│  │  - Texture upload                 │ │
│  │  - Multi-camera compositing        │ │
│  └────────────────────────────────────┘ │
│                    │                     │
│                    ▼                     │
│  ┌────────────────────────────────────┐ │
│  │   RecordingService                 │ │
│  │  - Canvas capture                 │ │
│  │  - WebCodecs encoding             │ │
│  │  - Timeline capture                │ │
│  └────────────────────────────────────┘ │
└─────────────────────────────────────────┘
```

## Component Details

### NDI Layer

**NDIReceiverService:**
- Wraps libndi WASM module
- Handles NDI discovery (mDNS or manual IP)
- Connects to NDI sources
- Decodes SpeedHQ frames to raw video

**CameraInputService:**
- Manages multiple camera sources
- Limits simultaneous decodes (2-3 max for 4K)
- Implements LRU eviction
- Tracks camera state (active/paused/connected)

### Rendering Layer

**CameraLayer Widget:**
- Rust/WASM WebGPU widget
- Renders as Layer 0 (background)
- Supports single camera (full-screen)
- Supports multi-camera (split-screen, PiP, grid)
- Efficient texture upload from ImageBitmap

### Recording Layer

**RecordingService:**
- Captures canvas via `captureStream()`
- Encodes with WebCodecs (H.264 hardware-accelerated)
- Captures audio from microphone
- Integrates with TimelineCaptureService

**TimelineCaptureService:**
- Captures all widget/KRONOS/HERMES events
- Timestamps with 960 PPQ precision
- Exports Vision #2 JSON format
- Includes camera/widget metadata

## Data Flow

### Camera Feed Flow

```
OBS (NDI) → libndi WASM → YUV frames → RGB conversion → ImageBitmap → WebGPU Texture → CameraLayer
```

### Recording Flow

```
Canvas → captureStream() → VideoFrame → VideoEncoder → Encoded Chunks → MP4 Blob
```

### Timeline Flow

```
Widget Events → TimelineCaptureService → Buffer → JSON Export
```

## Performance Characteristics

### Decode Performance (Target)

- **1080p @ 60fps:** < 16ms per frame
- **4K @ 60fps:** < 33ms per frame
- **CPU Usage:** < 80% total for 2-3 cameras

### Recording Performance

- **Canvas Capture:** ~5-10ms GPU→CPU transfer
- **Encoding:** ~2-5ms per frame (hardware-accelerated)
- **File Output:** Minimal overhead

### Memory Usage

- **Per 4K Frame:** ~24MB RGB
- **10 Streams:** ~240MB frames + overhead
- **Timeline Buffer:** ~50MB max (100k events)

## Multi-Camera Compositing

### Supported Arrangements

- **FullScreen:** Single camera full-screen
- **SplitScreen:** Two cameras side-by-side
- **PictureInPicture:** Main camera + overlay
- **Grid:** 2x2, 3x3, etc.

### Layout Calculation

Camera positions/scales calculated in NDC space:
- Full-screen: `[0, 0]` position, `[2, 2]` scale
- Split-screen: `[-1, 0]` and `[0, 0]` positions
- Grid: Calculated based on columns/rows

## Error Handling

### Graceful Degradation

- **NDI Connection Failure:** Show error, allow manual IP entry
- **Decoder Failure:** Fallback to lower resolution
- **Encoding Failure:** Fallback to software encoding
- **Out of Memory:** Reduce active cameras

### Error Reporting

- Centralized ErrorHandlingService
- User-friendly error messages
- Console logging for debugging
- Error callback system

## Browser Requirements

### Minimum

- Chrome 113+ or Edge 113+
- WebGPU support
- WebCodecs API support
- Canvas captureStream() support

### Recommended

- Chrome 120+ (latest)
- Discrete GPU
- 16GB+ RAM
- Gigabit Ethernet

## Security Considerations

- NDI uses local network only (no internet exposure)
- User media requires explicit permission
- File downloads require user interaction
- No data sent to external servers

## Future Enhancements

- FFmpeg.wasm integration for MP4 muxing
- Audio + video synchronization
- Real-time streaming (WebRTC)
- Cloud storage integration
- Advanced timeline editing













