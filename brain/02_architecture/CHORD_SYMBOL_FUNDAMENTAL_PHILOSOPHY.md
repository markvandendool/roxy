# 🎵 Chord Symbol as Fundamental Unit - Architecture Philosophy

## Overview

**Fundamental Principle**: Chord symbols (letter names like `C`, `Am`, `Bdim`, `F#maj7`) are the **primary identifier** for chords throughout the system. Roman numerals (`I`, `ii`, `V7`, `viiø`) are **derived metadata** used for display, theory analysis, and context-dependent operations.

## Why This Shift?

### Problems with "Roman Numeral First" Approach (Legacy Chord Cubes)

1. **Context Dependency**: Roman numerals require a key context (`I` in C major ≠ `I` in G major)
2. **Incomplete Mapping**: Not all chords map cleanly to Roman numerals (e.g., `B` major in C key = `bVII`, not a standard diatonic chord)
3. **Widget Mismatch**: The braid has MORE chords than cubes, so forcing 1:1 Roman numeral mapping causes incorrect cube triggers
4. **Conversion Overhead**: Constant conversion between Roman numerals and chord symbols adds complexity and potential errors

### Benefits of "Chord Symbol First" Approach

1. **Absolute Identity**: `C` is always `C`, regardless of key context
2. **Universal Compatibility**: Works across all widgets without conversion
3. **Flexible Mapping**: Can handle any chord type without forcing it into Roman numeral constraints
4. **Simpler Event Flow**: Events carry chord symbols as primary data, Roman numerals as optional metadata

## Architecture Implementation

### Event Structure

```typescript
interface ChordDetectedEvent {
  type: 'chord:detected';
  chord: {
    symbol: string;        // PRIMARY: Absolute chord symbol (e.g., "C", "Am", "Bdim")
    notes: string[];       // Derived from symbol
    midiNotes: number[];   // Derived from symbol
    root: string;          // Derived from symbol
    type: string;          // Derived from symbol
    bass?: string;         // Optional bass note
    confidence?: number;   // Detection confidence
  };
  source: 'real-time' | 'bulk' | 'braid-widget' | 'chordcubes';
  timestamp: number;
}

interface ChordDetectedEventWithRoman extends ChordDetectedEvent {
  romanNumeral?: string | null;  // DERIVED: Optional Roman numeral for display/theory
  key?: string;                  // Context needed for Roman numeral conversion
}
```

### Key Principles

1. **Chord Symbol is Primary**: All events, storage, and communication use chord symbols as the fundamental identifier
2. **Roman Numeral is Derived**: Roman numerals are computed on-demand from chord symbols + key context
3. **Optional Roman Numerals**: Not all chords need Roman numerals (e.g., braid has chords that don't map to standard Roman numerals)
4. **Source-Aware Filtering**: Different sources (braid, cubes, MIDI) can have different behaviors based on their chord sets

## Widget Behavior

### Braid Widget
- **Has MORE chords than cubes** (major, minor, 7th, diminished, half-diminished, etc.)
- Emits `chord:detected` with `chord.symbol` as primary
- Includes `romanNumeral` as optional metadata (may be null for non-diatonic chords)
- **Does NOT trigger cubes** (braid has more chords than cubes, so forcing 1:1 mapping causes errors)

### Chord Cubes Widget
- **Has LIMITED chord set** (standard diatonic chords: I, ii, iii, IV, V, vi, viiø, etc.)
- Receives `play-roman` messages for cubes that exist
- Converts Roman numerals to chord symbols internally for audio playback
- **Only triggered by sources that guarantee valid Roman numeral mapping**

### MIDI Input / Audio Detection
- Detects chord symbols directly from MIDI notes
- Converts to Roman numerals for display/theory analysis
- Can trigger cubes if Roman numeral exists in cube set

## Conversion Flow

```
MIDI Notes → Chord Symbol (via detection)
                ↓
         Chord Symbol (FUNDAMENTAL)
                ↓
         ┌──────┴──────┐
         ↓             ↓
    Audio Play    Roman Numeral (DERIVED)
         ↓             ↓
    Apollo API    Display/Theory
```

## Migration Notes

### Legacy Code (Chord Cubes App)
- Originally built around Roman numerals as primary identifier
- Required constant conversion between Roman numerals and chord symbols
- Caused issues when braid chords didn't map to cube Roman numerals

### Current Code (Olympus Integration)
- Chord symbols are primary in all events
- Roman numerals computed on-demand for display/theory
- Braid clicks don't trigger cubes (prevents incorrect mappings)
- MIDI/cube clicks still trigger cubes (guaranteed valid mapping)

## Best Practices

1. **Always use chord symbols** for storage, events, and cross-widget communication
2. **Compute Roman numerals** only when needed for display or theory analysis
3. **Don't force 1:1 mapping** between widgets with different chord sets
4. **Use source filtering** to prevent incorrect widget triggers
5. **Handle null Roman numerals** gracefully (not all chords have Roman numeral equivalents)

## Example: Braid Click Flow

```
User clicks "B" on braid
    ↓
Braid builds chord symbol: "BM" (B major)
    ↓
Converts to MIDI notes: [71, 75, 78]
    ↓
Emits chord:detected event:
  {
    chord: { symbol: "BM", ... },
    romanNumeral: "bVII" (in C major),
    source: "braid-widget"
  }
    ↓
ChordCubesEmbed receives event
    ↓
Checks source: "braid-widget"
    ↓
SKIPS play-roman (braid has more chords than cubes)
    ↓
Braid plays audio via Apollo
Braid highlights itself
Cubes remain unchanged ✅
```

## Example: Cube Click Flow

```
User clicks "I" cube
    ↓
Cube emits cubes:chord-click:
  {
    roman: "I",
    letter: "C",
    ...
  }
    ↓
ChordCubesEmbed receives message
    ↓
Builds chord symbol: "C" (from letter or roman conversion)
    ↓
Emits chord:detected event:
  {
    chord: { symbol: "C", ... },
    romanNumeral: "I",
    source: "cubes:chord-click"
  }
    ↓
ChordCubesEmbed receives its own event
    ↓
Checks source: "cubes:chord-click"
    ↓
SKIPS play-roman (already from cubes, avoid echo)
    ↓
Other widgets (braid, piano, etc.) receive event
    ↓
Braid highlights "I" position
Piano highlights C major notes
All widgets synchronized ✅
```

## Conclusion

**Chord symbols are the fundamental unit** because they are:
- Absolute (no key context needed)
- Universal (work across all widgets)
- Flexible (handle any chord type)
- Simple (no conversion overhead)

**Roman numerals are derived metadata** used for:
- Display/theory analysis
- Context-dependent operations
- Educational purposes
- Widget-specific features (like cube highlighting)

This architecture prevents the "one click, multiple cubes" problem and the "braid B triggers Bdim cube" issue by recognizing that **not all chords map to cubes**, and that's okay - the braid can exist independently with its richer chord set.



