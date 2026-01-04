# 🕐 TIMING PILLAR SPECIFICATION v1.0

**Document ID:** TIMING-PILLAR-SPEC-v1.0  
**Status:** DRAFT  
**Created:** December 8, 2025  
**Sprint:** TIME LATTICE RECAPTURE (Phase 0)  
**Owner:** Core Architecture Team

---

## Executive Summary

This document defines the **Universal Time Lattice** - a music-theory-aware timing subsystem that serves as the single source of truth for all time-related operations in the MindSong Juke Hub. The Time Lattice provides accurate timing for ALL time signatures, including simple meters (4/4, 3/4, 2/4), compound meters (6/8, 9/8, 12/8), and asymmetric meters (5/4, 7/8, 11/8).

### Why This Matters

The original Angular system (`music_project`) had this intelligence:
- Per-measure `timeSigNum`, `timeSigDenom` arrays
- Dynamic `tabSignatureDivider[]` for compound meters
- `getActualDivider()` returning correct subdivision counts
- `incrementMetro()` respecting measure boundaries

**We lost this during migration.** The current React system:
- Uses hardcoded `BEATS_PER_MEASURE = 4`
- Ignores `timeSigDenom` entirely
- Shows "1 2 3 4" for ALL meters
- Cannot play 6/8 correctly

---

## 1. CANONICAL TYPES

### 1.1 TimeSignature

The foundational type for meter representation:

```typescript
/**
 * Represents a musical time signature.
 * 
 * INVARIANTS:
 * - numerator ∈ [1, 32] (practical limit for music)
 * - denominator ∈ {1, 2, 4, 8, 16, 32}
 * - denominator = 2^n for some n ∈ [0, 5]
 */
export interface TimeSignature {
  readonly numerator: number;   // Top number (beats per measure)
  readonly denominator: number; // Bottom number (beat unit, must be power of 2)
}

// Pre-defined constants for common time signatures
export const TIME_SIGNATURES = {
  COMMON_TIME: { numerator: 4, denominator: 4 } as const,
  CUT_TIME:    { numerator: 2, denominator: 2 } as const,
  WALTZ:       { numerator: 3, denominator: 4 } as const,
  SIX_EIGHT:   { numerator: 6, denominator: 8 } as const,
  NINE_EIGHT:  { numerator: 9, denominator: 8 } as const,
  TWELVE_EIGHT:{ numerator: 12, denominator: 8 } as const,
  FIVE_FOUR:   { numerator: 5, denominator: 4 } as const,
  SEVEN_EIGHT: { numerator: 7, denominator: 8 } as const,
} as const;
```

### 1.2 MeterClassification

Categorizes meters for rendering and metronome behavior:

```typescript
/**
 * Classification of a meter based on beat grouping.
 * 
 * SIMPLE:    Each beat divides into 2 (duple subdivision)
 *            Examples: 4/4, 3/4, 2/4
 * 
 * COMPOUND:  Each beat divides into 3 (triple subdivision)
 *            Examples: 6/8, 9/8, 12/8
 *            Compound meters have denominator=8 and numerator divisible by 3
 * 
 * ASYMMETRIC: Irregular beat groupings
 *             Examples: 5/4 (2+3 or 3+2), 7/8 (2+2+3 or other)
 */
export type MeterType = 'SIMPLE' | 'COMPOUND' | 'ASYMMETRIC';

export interface MeterClassification {
  readonly type: MeterType;
  readonly beatsPerMeasure: number;        // Felt beats (2 in 6/8, 4 in 4/4)
  readonly subdivisionsPerBeat: number;    // 2 for simple, 3 for compound
  readonly totalSubdivisions: number;      // Total per measure
  readonly beatGrouping: readonly number[];// How to group beats [2,2] or [3,3] etc.
  readonly isCompound: boolean;            // Quick check for compound
  readonly divider: number;                // From V1: 1 for /4, 2 for /8
}
```

### 1.3 MeasureTimingInfo (Enhanced from existing type)

Per-measure timing data with full time signature support:

```typescript
/**
 * Complete timing information for a single measure.
 * This is the PRIMARY interface adapters use.
 * 
 * EXISTING: Type exists in novaxe-score.ts but is UNUSED.
 * ACTION:   Wire this into KhronosEngine and all consumers.
 */
export interface MeasureTimingInfo {
  // Identity
  readonly measureIndex: number;           // 0-based global index
  
  // Time Signature (THE CRITICAL ADDITION)
  readonly timeSignature: TimeSignature;
  readonly meterClass: MeterClassification;
  
  // Tempo
  readonly bpm: number;                    // Tempo at this measure
  
  // Computed Timing (milliseconds from song start)
  readonly millisStart: number;            // When measure starts
  readonly millisEnd: number;              // When measure ends
  readonly millisDuration: number;         // = millisEnd - millisStart
  
  // Beat Calculations (V1 COMPATIBILITY)
  readonly beatsInMeasure: number;         // = timeSignature.numerator for simple
  readonly ticksPerMeasure: number;        // = beatsInMeasure * PPQ
  readonly tickStart: number;              // Absolute tick at measure start
  readonly tickEnd: number;                // Absolute tick at measure end
  
  // V1 Compatibility Arrays
  readonly divider: number;                // 1 for /4, 2 for /8 (V1: tabSignatureDivider)
  
  // Position helpers
  readonly cumulativeBeats: number;        // Beats from song start to this measure
}
```

### 1.4 SubdivisionLabel

How to display count labels based on meter:

```typescript
/**
 * Labels for beat subdivisions based on meter type.
 * 
 * SIMPLE (4/4): "1", "i", "&", "a", "2", "i", "&", "a", ...
 *   - 16 labels per measure (4 beats × 4 subdivisions)
 * 
 * COMPOUND (6/8): "1", "&", "a", "2", "&", "a"
 *   - 6 labels per measure (2 beats × 3 subdivisions)
 * 
 * V1 REFERENCE: measure.js:getBarText()
 */
export interface SubdivisionLabels {
  readonly measureIndex: number;
  readonly labels: readonly string[];
  readonly emphasisPattern: readonly number[]; // Weight 0-2 for each position
}
```

---

## 2. TIME LATTICE ENGINE

### 2.1 Interface Definition

```typescript
/**
 * UNIVERSAL TIME LATTICE
 * 
 * The single source of truth for all musical time operations.
 * Replaces scattered timing logic across the codebase.
 * 
 * DESIGN PRINCIPLES:
 * 1. Immutable: All returned data is readonly
 * 2. Pure: No side effects, deterministic outputs
 * 3. Cached: Expensive computations memoized
 * 4. Compatible: Matches V1 algorithm behavior exactly
 */
export interface TimeLattice {
  // ========================================================================
  // CORE: Measure Timing Array
  // ========================================================================
  
  /**
   * Build complete timing info for all measures.
   * This is the FOUNDATION - all other methods use this data.
   * 
   * @param measures - Array of measures with time signature info
   * @param defaultBpm - Fallback BPM if not specified per-measure
   * @returns Immutable array of MeasureTimingInfo
   * 
   * V1 EQUIVALENT: curSongModel.initTabMeasures()
   */
  buildMeasureTimingArray(
    measures: readonly MeasureInput[],
    defaultBpm: number
  ): readonly MeasureTimingInfo[];
  
  // ========================================================================
  // METER CLASSIFICATION
  // ========================================================================
  
  /**
   * Classify a time signature into its meter type.
   * 
   * @param timeSig - Time signature to classify
   * @returns Full meter classification with beat groupings
   * 
   * V1 EQUIVALENT: tabSignatureDivider[] logic in initTabMeasures()
   */
  classifyMeter(timeSig: TimeSignature): MeterClassification;
  
  /**
   * Get subdivision labels for a specific measure.
   * 
   * @param measureIdx - Measure index
   * @returns Array of labels ("1", "i", "&", "a" etc.)
   * 
   * V1 EQUIVALENT: measure.js:getBarText()
   */
  getSubdivisionLabels(measureIdx: number): SubdivisionLabels;
  
  // ========================================================================
  // POSITION CONVERSIONS
  // ========================================================================
  
  /**
   * Convert absolute tick to position (measure, beat, tick).
   * METER-AWARE: Uses correct beatsPerMeasure for each measure.
   * 
   * V1 EQUIVALENT: curPosModel position tracking
   */
  tickToPosition(absoluteTick: number): KhronosPosition;
  
  /**
   * Convert position to absolute tick.
   * METER-AWARE: Accounts for variable time signatures.
   */
  positionToTick(position: KhronosPosition): number;
  
  /**
   * Convert milliseconds to position.
   * TEMPO-AWARE: Handles tempo changes per measure.
   */
  millisToPosition(millis: number): KhronosPosition;
  
  /**
   * Convert position to milliseconds.
   */
  positionToMillis(position: KhronosPosition): number;
  
  // ========================================================================
  // NAVIGATION
  // ========================================================================
  
  /**
   * Move position by one beat, respecting meter.
   * Handles measure boundaries correctly for all time signatures.
   * 
   * V1 EQUIVALENT: curPosModel.incrementMetro()
   */
  incrementBeat(position: KhronosPosition, direction: 1 | -1): KhronosPosition;
  
  /**
   * Move position by one subdivision.
   * Respects compound vs simple subdivision counts.
   */
  incrementSubdivision(position: KhronosPosition, direction: 1 | -1): KhronosPosition;
  
  /**
   * Move to next/previous measure.
   */
  incrementMeasure(position: KhronosPosition, direction: 1 | -1): KhronosPosition;
  
  // ========================================================================
  // QUERIES
  // ========================================================================
  
  /**
   * Get time signature at a given position.
   * 
   * V1 EQUIVALENT: curPosModel.getActualMetroTimeSig()
   */
  getTimeSignatureAt(position: KhronosPosition): TimeSignature;
  
  /**
   * Get divider (1 or 2) for a measure.
   * 
   * V1 EQUIVALENT: curPosModel.getActualDivider()
   */
  getDividerAt(measureIdx: number): number;
  
  /**
   * Check if position is at a measure boundary.
   */
  isAtMeasureBoundary(position: KhronosPosition): boolean;
  
  /**
   * Check if position is at a beat boundary.
   */
  isAtBeatBoundary(position: KhronosPosition): boolean;
  
  // ========================================================================
  // V1 COMPATIBILITY GETTERS
  // ========================================================================
  
  /**
   * Get tabSignature array (numerators per measure).
   * COMPATIBILITY: Direct match to csm.tabSignature[]
   */
  getTabSignature(): readonly number[];
  
  /**
   * Get tabSignatureDivider array.
   * COMPATIBILITY: Direct match to csm.tabSignatureDivider[]
   */
  getTabSignatureDivider(): readonly number[];
  
  /**
   * Get tabBeats array (beats per measure, V1 style calculation).
   * COMPATIBILITY: Direct match to csm.tabBeats[]
   */
  getTabBeats(): readonly number[];
  
  /**
   * Get total beat count.
   * COMPATIBILITY: Direct match to csm.totalBeatNumber
   */
  getTotalBeatNumber(): number;
}

// Input type for building timing array
export interface MeasureInput {
  timeSigNum?: number;       // Default: 4
  timeSigDenom?: number;     // Default: 4
  bpm?: number;              // Inherit from previous or default
}
```

---

## 3. METER CLASSIFICATION ALGORITHM

### 3.1 Decision Tree

```
classifyMeter(num, denom):
  │
  ├─ denom = 8 AND num % 3 = 0?
  │   └─ YES → COMPOUND
  │       beatsPerMeasure = num / 3
  │       subdivisionsPerBeat = 3
  │       divider = 2
  │
  ├─ num % 2 ≠ 0 AND num ≠ 3?  (5, 7, 11, 13...)
  │   └─ YES → ASYMMETRIC
  │       beatsPerMeasure = depends on grouping
  │       subdivisionsPerBeat = varies
  │       divider = 1 (usually)
  │
  └─ DEFAULT → SIMPLE
      beatsPerMeasure = num
      subdivisionsPerBeat = 2
      divider = 1
```

### 3.2 Implementation Reference

```typescript
// CANONICAL IMPLEMENTATION
function classifyMeter(timeSig: TimeSignature): MeterClassification {
  const { numerator, denominator } = timeSig;
  
  // COMPOUND: x/8 where x is divisible by 3
  if (denominator === 8 && numerator % 3 === 0 && numerator >= 6) {
    const groups = numerator / 3;
    return {
      type: 'COMPOUND',
      beatsPerMeasure: groups,                  // 6/8 = 2, 9/8 = 3, 12/8 = 4
      subdivisionsPerBeat: 3,                   // Compound = triplet feel
      totalSubdivisions: numerator,             // 6, 9, or 12
      beatGrouping: Array(groups).fill(3),      // [3,3] for 6/8
      isCompound: true,
      divider: 2                                // V1: tabSignatureDivider = 2
    };
  }
  
  // ASYMMETRIC: Odd meters not divisible by 2 (except 3)
  if (numerator > 4 && numerator % 2 !== 0) {
    // 5/4 = [3,2] or [2,3], 7/8 = [2,2,3] or [3,2,2], etc.
    const grouping = getAsymmetricGrouping(numerator);
    return {
      type: 'ASYMMETRIC',
      beatsPerMeasure: grouping.length,
      subdivisionsPerBeat: 2,                   // Simplified
      totalSubdivisions: numerator * (4 / denominator) * 4,
      beatGrouping: grouping,
      isCompound: false,
      divider: denominator === 8 ? 2 : 1
    };
  }
  
  // SIMPLE: Everything else (4/4, 3/4, 2/4, etc.)
  return {
    type: 'SIMPLE',
    beatsPerMeasure: numerator,
    subdivisionsPerBeat: 2,                     // Duple subdivision
    totalSubdivisions: numerator * 4,           // 16 for 4/4
    beatGrouping: Array(numerator).fill(1),     // Each beat is one unit
    isCompound: false,
    divider: 1                                  // V1: tabSignatureDivider = 1
  };
}

// Helper for asymmetric groupings
function getAsymmetricGrouping(numerator: number): readonly number[] {
  switch (numerator) {
    case 5: return [3, 2];     // Most common 5/4 grouping
    case 7: return [2, 2, 3];  // Most common 7/8 grouping
    case 11: return [3, 3, 3, 2];
    case 13: return [3, 3, 3, 2, 2];
    default: {
      // Generate grouping algorithmically
      const groups: number[] = [];
      let remaining = numerator;
      while (remaining > 0) {
        if (remaining >= 3) {
          groups.push(3);
          remaining -= 3;
        } else {
          groups.push(remaining);
          remaining = 0;
        }
      }
      return groups;
    }
  }
}
```

---

## 4. V1 ALGORITHM RESTORATION

### 4.1 tabSignatureDivider[] Recreation

**Original V1 Code** (curSongModel.js:351-366):
```javascript
switch (csm.scoreMeasures[i-1].timeSigDenom){
  case 4:
    csm.tabSignatureDivider.push(1);
    break;
  case 8:
    csm.tabSignatureDivider.push(2);
    break;
}
```

**Time Lattice Implementation**:
```typescript
// Build tabSignatureDivider from measure timing array
function getTabSignatureDivider(measures: MeasureTimingInfo[]): number[] {
  return measures.map(m => m.divider);
}
```

### 4.2 tabBeats[] Recreation

**Original V1 Code** (curSongModel.js:347-349):
```javascript
csm.tabBeats.push((csm.scoreMeasures[i-1].timeSigNum || 0) * 4 
  / ((csm.scoreMeasures[i-1].timeSigDenom || 4) / 4));
```

**Time Lattice Implementation**:
```typescript
// Build tabBeats (V1 formula exact)
function getTabBeats(measures: MeasureTimingInfo[]): number[] {
  return measures.map(m => {
    const { numerator, denominator } = m.timeSignature;
    return (numerator * 4) / (denominator / 4);
  });
}
// For 4/4: (4 * 4) / (4/4) = 16 / 1 = 16
// For 6/8: (6 * 4) / (8/4) = 24 / 2 = 12
// For 3/4: (3 * 4) / (4/4) = 12 / 1 = 12
```

### 4.3 Subdivision Labels Recreation

**Original V1 Code** (measure.js:31-48):
```javascript
measure.getBarText = function(nb){
  switch(nb % 4){
    case 0: return nb/4+1;  // Downbeat: "1", "2", "3", "4"
    case 1: return 'i';     // E subdivision
    case 2: return '&';     // And
    case 3: return 'a';     // A subdivision
  }
}
```

**Time Lattice Implementation**:
```typescript
function getSubdivisionLabel(
  subdivisionIndex: number,
  meterClass: MeterClassification
): string {
  if (meterClass.isCompound) {
    // COMPOUND: "1", "&", "a", "2", "&", "a"
    const posInBeat = subdivisionIndex % 3;
    const beatNum = Math.floor(subdivisionIndex / 3) + 1;
    switch (posInBeat) {
      case 0: return String(beatNum);
      case 1: return '&';
      case 2: return 'a';
    }
  }
  
  // SIMPLE: "1", "i", "&", "a", "2", "i", "&", "a"
  const posInBeat = subdivisionIndex % 4;
  const beatNum = Math.floor(subdivisionIndex / 4) + 1;
  switch (posInBeat) {
    case 0: return String(beatNum);
    case 1: return 'i';
    case 2: return '&';
    case 3: return 'a';
  }
  return '';
}
```

---

## 5. INTEGRATION POINTS

### 5.1 KhronosEngine Integration

**Current Problem** (KhronosEngine.ts:12):
```typescript
const BEATS_PER_MEASURE = 4; // Fallback until per-measure meter is available
```

**Solution**:
```typescript
// KhronosEngine will receive TimeLattice as a dependency
class KhronosEngine {
  private timeLattice: TimeLattice;
  private measureTimingArray: readonly MeasureTimingInfo[] = [];
  
  setTimeLattice(timeLattice: TimeLattice): void {
    this.timeLattice = timeLattice;
  }
  
  loadScore(measures: MeasureInput[], defaultBpm: number): void {
    this.measureTimingArray = this.timeLattice.buildMeasureTimingArray(
      measures, 
      defaultBpm
    );
  }
  
  // NOW METER-AWARE:
  private positionToAbsoluteTick(position: KhronosPosition): number {
    return this.timeLattice.positionToTick(position);
  }
  
  private absoluteTickToPosition(tick: number): KhronosPosition {
    return this.timeLattice.tickToPosition(tick);
  }
}
```

### 5.2 Metronome Integration

**Current Problem**: Metronome clicks assume 4/4 timing.

**Solution**:
```typescript
// Metronome uses TimeLattice for click scheduling
function scheduleMetronomeClicks(
  measureIdx: number,
  timeLattice: TimeLattice
): MetronomeClick[] {
  const timing = timeLattice.getMeasureTimingInfo(measureIdx);
  const meterClass = timing.meterClass;
  
  const clicks: MetronomeClick[] = [];
  
  for (let beat = 0; beat < meterClass.beatsPerMeasure; beat++) {
    const isDownbeat = beat === 0;
    const position = { measureIndex: measureIdx, beatInMeasure: beat, ticks: 0 };
    const millis = timeLattice.positionToMillis(position);
    
    clicks.push({
      time: millis / 1000,  // AudioContext time
      type: isDownbeat ? 'strong' : 'beat',
      emphasis: meterClass.beatGrouping[beat] // For asymmetric
    });
    
    // Add subdivisions for compound meters
    if (meterClass.isCompound) {
      // Add "&" and "a" clicks
      const ticksPerSub = KHRONOS_PPQ / 3;
      for (let sub = 1; sub < 3; sub++) {
        const subPos = { ...position, ticks: sub * ticksPerSub };
        const subMillis = timeLattice.positionToMillis(subPos);
        clicks.push({
          time: subMillis / 1000,
          type: 'subdivision'
        });
      }
    }
  }
  
  return clicks;
}
```

### 5.3 Score Store Integration

**Current**: `useScoreStore` has `buildMeasureTimingInfo()` that's basic.

**Enhancement**:
```typescript
// In score.ts store
buildMeasureTimingInfo: () => {
  const { score } = get();
  if (!score) return;
  
  // Use TimeLattice instead of manual calculation
  const timeLattice = getTimeLattice(); // Singleton or injected
  const measures = extractMeasuresFromScore(score);
  const timingArray = timeLattice.buildMeasureTimingArray(
    measures,
    score.info.bpm
  );
  
  set({ measureTimingInfo: timingArray });
}
```

---

## 6. FILE LOCATIONS

### 6.1 New Files to Create

```
src/
└── lib/
    └── timing/
        ├── index.ts                    # Public exports
        ├── TimeLattice.ts              # Main implementation
        ├── types.ts                    # TimeSignature, MeterClassification, etc.
        ├── meterClassifier.ts          # classifyMeter() logic
        ├── subdivisionLabels.ts        # Label generation
        ├── positionConversions.ts      # Tick/millis/position converters
        └── __tests__/
            ├── TimeLattice.test.ts
            ├── meterClassifier.test.ts
            └── fixtures/
                ├── 4-4-score.json
                ├── 6-8-score.json
                └── mixed-meter-score.json
```

### 6.2 Files to Modify

| File | Change |
|------|--------|
| `src/khronos/KhronosEngine.ts` | Remove hardcoded `BEATS_PER_MEASURE = 4`, inject TimeLattice |
| `src/khronos/types/index.ts` | Add TimeSignature re-export |
| `src/store/score.ts` | Wire `MeasureTimingInfo` from TimeLattice |
| `src/types/novaxe-score.ts` | Ensure `MeasureTimingInfo` matches spec |
| `src/components/nvx1/` | Use TimeLattice for subdivision display |

---

## 7. TESTING REQUIREMENTS

### 7.1 Unit Tests (Phase 1)

```typescript
describe('classifyMeter', () => {
  it('classifies 4/4 as SIMPLE with 4 beats', () => {
    const result = classifyMeter({ numerator: 4, denominator: 4 });
    expect(result.type).toBe('SIMPLE');
    expect(result.beatsPerMeasure).toBe(4);
    expect(result.divider).toBe(1);
  });
  
  it('classifies 6/8 as COMPOUND with 2 beats', () => {
    const result = classifyMeter({ numerator: 6, denominator: 8 });
    expect(result.type).toBe('COMPOUND');
    expect(result.beatsPerMeasure).toBe(2);
    expect(result.divider).toBe(2);
  });
  
  it('classifies 5/4 as ASYMMETRIC', () => {
    const result = classifyMeter({ numerator: 5, denominator: 4 });
    expect(result.type).toBe('ASYMMETRIC');
    expect(result.beatGrouping).toEqual([3, 2]);
  });
});

describe('subdivision labels', () => {
  it('generates "1 i & a 2 i & a..." for 4/4', () => {
    const labels = getSubdivisionLabelsForMeasure(0, simpleMetric);
    expect(labels.labels).toEqual([
      '1', 'i', '&', 'a',
      '2', 'i', '&', 'a',
      '3', 'i', '&', 'a',
      '4', 'i', '&', 'a'
    ]);
  });
  
  it('generates "1 & a 2 & a" for 6/8', () => {
    const labels = getSubdivisionLabelsForMeasure(0, compoundMetric);
    expect(labels.labels).toEqual(['1', '&', 'a', '2', '&', 'a']);
  });
});

describe('V1 compatibility arrays', () => {
  it('tabSignatureDivider matches V1 for mixed meter', () => {
    const timeLattice = buildTimeLattice([
      { timeSigNum: 4, timeSigDenom: 4 },
      { timeSigNum: 6, timeSigDenom: 8 },
      { timeSigNum: 4, timeSigDenom: 4 }
    ]);
    expect(timeLattice.getTabSignatureDivider()).toEqual([1, 2, 1]);
  });
});
```

### 7.2 Integration Tests (Phase 3)

- Hallelujah (6/8) displays correctly
- Waltz (3/4) displays correctly
- Take Five (5/4) displays correctly
- Mixed meter scores navigate correctly
- Metronome clicks on correct beats

### 7.3 Visual Regression Tests (Phase 7)

- Screenshot comparison for each meter type
- Count label rendering verification
- Beat emphasis highlighting

---

## 8. SUCCESS CRITERIA

### 8.1 Phase 0 Complete When:

- [ ] This spec document approved
- [ ] 740_METRIC_BASELINE.md created
- [ ] Risk assessment complete
- [ ] Team alignment on approach

### 8.2 Time Lattice Complete When:

- [ ] All unit tests pass
- [ ] Hallelujah plays with correct 6/8 feel
- [ ] Count labels show "1 & a 2 & a" for compound meters
- [ ] Metronome clicks on dotted-quarter beats for 6/8
- [ ] V1 compatibility arrays match original implementation
- [ ] Zero regressions in 4/4 functionality

---

## 9. RISKS & MITIGATIONS

| Risk | Impact | Mitigation |
|------|--------|------------|
| KhronosEngine refactor breaks playback | HIGH | Feature flag, parallel implementation |
| Performance regression from new calculations | MEDIUM | Memoization, lazy evaluation |
| Edge cases in asymmetric meters | LOW | Comprehensive test fixtures |
| Store integration complexity | MEDIUM | Incremental rollout per component |

---

## 10. APPENDIX: V1 CODE REFERENCES

### A.1 Key Files in music_project

| File | Purpose | Key Functions |
|------|---------|---------------|
| `curSongModel.js` | Song model | `initTabMeasures()`, arrays |
| `curPosModel.js` | Position tracking | `getActualDivider()`, `incrementMetro()` |
| `measure.js` | Beat display | `getBarText()`, `getWidth()` |
| `musicUtil.js` | Timing math | `getMeasuresFromBeats()`, `getMillisFromBeats()` |
| `playerService.js` | Audio scheduling | `scheduleAheadTime`, metronome |

### A.2 Key Constants

```javascript
// From V1
BEAT_DIVISIONS = 960          // PPQ - matches our KHRONOS_PPQ
scheduleAheadTime = 0.05      // 50ms lookahead
metroResolution = 0/1/2       // Off, quarter, eighth
```

---

**Document End**

*Next: Create 740_METRIC_BASELINE.md*
