# Live Listener Audio Architecture – Systems Map

This is the high-signal, at-a-glance map for the entire live audio/MIDI detection stack used across Olympus/Apollo. It is designed to be both AI- and human-readable.

## Mermaid schematic (copy into any Markdown viewer that supports Mermaid)

```mermaid
flowchart LR
  %% Inputs
  subgraph Inputs
    A[MIDI Device<br/>WebMIDI]:::in
    B[Mic / Line-In<br/>getUserMedia]:::in
    C[Tab/System Audio<br/>getDisplayMedia / Loopback]:::in
    D[Audio File (MP3/WAV)]:::in
  end

  %% Ingest + Engines
  subgraph Ingest_and_Engines
    MS[MidiService]:::svc
    ARB[AudioRecognitionBridge]:::svc
    P0[P0 DSP Fast-Lane<br/>HPCP→Chord (Essentia/custom WASM)]:::engine
    P1[P1 ML (Basic Pitch TS)<br/>Streaming notes→Chord]:::engine
    ORC[(P2 Oracle on RunPod<br/>MT3/Onsets & Frames + Demucs)]:::engine
  end

  %% Fusion + Theory
  subgraph Fusion_and_Theory
    SWARM[Swarm/Fusion in GlobalMidiIngestService<br/>majority + hysteresis + corrections]:::coord
    CHORDS[ChordDetectionService / Tonal.js]:::svc
    KEY[canonicalKeyStore + KeyNormalization]:::svc
    ROMAN[ChordToRomanService]:::svc
  end

  %% Bus and Consumers
  EB[GlobalMidiEventBus<br/>'midi:*', 'chord:detected', 'braid:highlight']:::bus
  KRONOS[Kronos Transport<br/>Audio clock]:::svc
  HERMES[HERMES / NVX1 Score<br/>Key / "truth"]:::svc
  ROCKY[Rocky AI<br/>Real-time feedback]:::svc
  APOLLO[Apollo Engine<br/>Playback feedback]:::svc

  subgraph Widgets
    W1[Piano]
    W2[Fretboard]
    W3[Braid]
    W4[Circle of Fifths]
    W5[Chord Cubes]
  end

  %% Monitor
  MON[Olympus - Monitor Tab<br/>Tuner • Detector toggles • Metrics]:::ui

  %% Wiring
  A --> MS --> SWARM
  B --> ARB --> P0 --> SWARM
  C --> ARB
  D --> P1 --> SWARM
  C --> P1
  ORC -. WebSocket .-> SWARM

  SWARM --> CHORDS --> ROMAN
  HERMES --> KEY --> ROMAN
  KEY --> ROMAN
  SWARM --> EB
  EB --> W1 & W2 & W3 & W4 & W5
  EB --> ROCKY
  SWARM --> APOLLO
  KRONOS --> SWARM
  KRONOS --> Widgets
  MON --> EB
  MON --> SWARM

  classDef in fill:#eef,stroke:#88f,stroke-width:1px
  classDef svc fill:#efe,stroke:#4a4,stroke-width:1px
  classDef engine fill:#ffe,stroke:#cc8,stroke-width:1px
  classDef coord fill:#fef,stroke:#c8c,stroke-width:1px
  classDef bus fill:#eef,stroke:#66a,stroke-width:2px,stroke-dasharray: 4 2
  classDef ui fill:#f5f5f5,stroke:#999,stroke-width:1px
```

## Mental model (one-liners)
- Inputs (MIDI / Mic / Tab/System / Files) → Ingest → Engines (P0/P1/P2) → Fusion → Theory (Key/Roman) → Bus → Widgets/Feedback; Kronos clocks everything.
- “3 Ears”: MIDI Ear, Audio Ear (P0 fast + P1 ML correction), Score Ear (HERMES truth).
- Olympus Monitor is the cockpit: choose ear(s), view tuner, see status and latency.

## Where to plug in
- New detectors: implement analyzer adapter (see SWARM spec) → feed votes to fusion in `GlobalMidiIngestService`.
- New widgets: subscribe to `GlobalMidiEventBus` (‘chord:detected’, ‘braid:highlight’).
- Oracle backends: expose WebSocket/gRPC streaming endpoint returning analyzer votes.

## Observability (minimum)
- Emit per-chord: origin engine, confidence, windowMs, producedAt, total latency buckets.
- Olympus → show P0/P1/P2 status, last correction source, P50/P95 latency.


