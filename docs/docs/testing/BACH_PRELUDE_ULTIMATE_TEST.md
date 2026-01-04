# Bach Prelude Ultimate Test Suite

**Status:** Phase 1-2 Complete (2025-10-22)  
**Progress:** 60% (Fixture + E2E Framework Complete)  
**Remaining:** HTML Report Generator, Musical Validators, CI Integration

---

## Overview

The **Bach Prelude Ultimate Test** is the definitive stress test for the score layer system. It validates all 10 score layers across the complete 35-measure Bach Prelude in C Major (BWV 846), capturing screenshots at key measures to verify musical accuracy, PPQ alignment, and rendering integrity.

This test suite was chosen as THE foundational regression test because:
- ✅ **Historical significance**: Original test for the first platform/animations
- ✅ **Musical complexity**: Full harmonic progression with modulations
- ✅ **Technical rigor**: 35 measures × 10 layers × 9 sample points = 90 screenshots
- ✅ **Layer coverage**: Tests every layer type from Form to Fretboard
- ✅ **Long-term value**: Will be the constant baseline until release

---

## Implementation Status

### ✅ Phase 1: Full 35-Measure Bach Prelude Fixture (COMPLETE)

**File**: `src/lib/nvx1/bachPreludeScore.ts` (235 lines)

**Features**:
- Complete 35-measure score with authentic harmonic progression
- Form sections with proper boundaries:
  - **Enunciation** (M1-11)
  - **Development** (M12-19)
  - **Recapitulation** (M20-32)
  - **Coda** (M33-35)
- Exact chord progression: C → Dm7 → G7 → Am → D7 → G → ... → C
- Roman numeral analysis for all measures
- Right-hand fingering (p-i-m-a-m-i) on all note events
- PPQ-aligned timing (960 per quarter, 3840 per measure)
- Helper functions: `getBachMeasure()`, `getAllBachMeasures()`

**Unit Tests**: 11/11 passing ✓
- Complete score generation (35 measures across 4 parts)
- Form section structure validation
- PPQ timing alignment (all measures 3840 ticks)
- Chord progression accuracy (35 chords validated)
- Right-hand fingering patterns
- Bass notes on beat 1
- Measure line breaks every 4 measures

---

### ✅ Phase 2: Layer Screenshot Test System (COMPLETE)

**File**: `tests/e2e/helpers/layerIsolation.ts` (165 lines)

**Utilities**:
- `setActiveLayer(page, layer)`: Isolate single layer for capture
- `enableAllLayers(page)`: Composite view with all 10 layers
- `scrollToMeasure(page, measureNumber)`: Navigate to specific measure (1-35)
- `getMeasureClipRect(measureNumber)`: Calculate screenshot bounds
- `saveLayerScreenshot(page, measure, layer)`: Save with naming convention
- `getLayerVisibility(page)`: Query current layer states

**File**: `tests/e2e/theater8k.bach-prelude-layers.spec.ts` (220 lines)

**Test Suite**:
1. **Layer Screenshot Capture**: Captures 90 screenshots (9 measures × 10 layers)
   - Sample measures: 1, 5, 9, 13, 17, 21, 25, 29, 33
   - Naming: `bach-m{measure}-{layer}.png` (e.g., `bach-m01-form.png`)
   - Generates `capture-manifest.json` with results

2. **Layer Toggle Validation**: Validates all layers can be toggled simultaneously

3. **Layer Persistence Test**: Checks localStorage persistence across reloads

4. **Composite View Test**: Captures full composite at measure 1

5. **Form Section Labels**: Validates section boundaries (Enunciation, Development, etc.)

6. **Layer Ordering System**: Tests stack position persistence

7. **Musical Accuracy Suite**:
   - Chord progression validation
   - All 35 measures navigability

### ✅ Phase 2.1: Score Parity Metric Hooks (ADOPTED 2025-10-22)
- **Purpose:** Enforce the 20 official score parity metrics during Bach Prelude runs. See `docs/testing/SCORE_PARITY_METRICS.md` for the full matrix.
- **Playwright Integration:** Extend `tests/e2e/theater8k.bach-prelude-layers.spec.ts` to calculate metrics after each capture pass and emit `test-artifacts/score-parity/metrics.json`.
- **CI Expectations:** Pull requests fail when any metric reports a non-pass status; attach JSON + supporting screenshots for reviewers.
- **Command Stub:** `pnpm test:score-parity` (to be added) should execute the metric suite headlessly once the dedicated spec lands.

---

### ⏳ Phase 3: Musical Accuracy Validators (PENDING)

**Files to Create**:
- `tests/validation/chordVoicingValidator.ts`
- `tests/validation/ppqTimingValidator.ts`
- `tests/validation/arpeggioPatternValidator.ts`

**Validations**:
1. **Chord Voicing**: Verify chord notes match expected pitches (C = C-E-G)
2. **PPQ Timing**: Check 160-tick alignment (sextuplet grid: 960 ÷ 6)
3. **Arpeggio Pattern**: Validate ascending/descending patterns

---

### ⏳ Phase 4: HTML Report Generator (PENDING)

**File to Create**: `tests/e2e/helpers/bachPreludeReport.ts`

**Features**:
- Grid view: measures (rows) × layers (columns)
- Traffic light indicators (✓ green, ⚠ yellow, ✗ red)
- Click to enlarge screenshots
- Filterable by layer or measure
- Export capability

**Layout**:
```
┌─────────────────────────────────────────────────────────┐
│ Bach Prelude Ultimate Layer Test - 2025-10-22          │
│ 90/90 tests passed (100%)                              │
├─────────────────────────────────────────────────────────┤
│        Form  Pos  Fret  Bridge  Chords  Bass ...       │
├─────────────────────────────────────────────────────────┤
│ M1     ✓     ✓    ✓     ✓       ✓       ✓    ...       │
│ M5     ✓     ✓    ✓     ⚠       ✓       ✓    ...       │
│ M9     ✓     ✓    ✓     ✓       ✓       ✗    ...       │
│ ...                                                     │
└─────────────────────────────────────────────────────────┘
```

---

### ⏳ Phase 5: CI Integration (PENDING)

**File to Create**: `.github/workflows/bach-prelude-validation.yml`

**Features**:
- Runs on every push to main or feature branches
- Uploads screenshots as artifacts
- Generates HTML report
- Posts results to PR comments

---

## Usage

### Run Full Test Suite

```bash
# Capture all 90 screenshots
pnpm test:bach-prelude

# View results
open test-artifacts/bach-prelude-screenshots/capture-manifest.json
```

### Run Specific Test

```bash
# Just layer capture
pnpm playwright test tests/e2e/theater8k.bach-prelude-layers.spec.ts -g "captures individual layers"

# Just validation tests
pnpm playwright test tests/e2e/theater8k.bach-prelude-layers.spec.ts -g "Musical Accuracy"
```

### Run Unit Tests

```bash
# Test Bach Prelude fixture
pnpm test src/lib/nvx1/__tests__/bachPreludeScore.test.ts

# All tests
pnpm test
```

---

## Test Output Structure

```
test-artifacts/bach-prelude-screenshots/
├── bach-m01-form.png
├── bach-m01-position.png
├── bach-m01-fret.png
├── bach-m01-bridge.png
├── bach-m01-chords.png
├── bach-m01-bass.png
├── bach-m01-diagrams.png
├── bach-m01-scale.png
├── bach-m01-notation.png
├── bach-m01-fretboard.png
├── bach-m01-composite.png
├── bach-m05-form.png
├── ... (90 total screenshots)
└── capture-manifest.json
```

**Capture Manifest** (JSON):
```json
{
  "testDate": "2025-10-22T11:34:00.000Z",
  "totalMeasures": 35,
  "sampledMeasures": [1, 5, 9, 13, 17, 21, 25, 29, 33],
  "layers": ["form", "position", "fret", ...],
  "results": [
    {
      "measure": 1,
      "layer": "form",
      "captured": true,
      "filepath": "test-artifacts/bach-prelude-screenshots/bach-m01-form.png"
    },
    ...
  ],
  "summary": {
    "total": 90,
    "captured": 90,
    "failed": 0
  }
}
```

---

## Layer Validation Checklist

### Form Layer
- ✓ Section labels render at correct boundaries
- ✓ "Enunciation" appears at M1
- ✓ "Development" appears at M12
- ✓ "Recapitulation" appears at M20
- ✓ "Coda" appears at M33

### Position Layer
- ✓ Beat grid visible at 160-tick intervals
- ✓ Measure numbers at start of each measure
- ✓ Barlines aligned vertically
- ✓ No grid drift across 35 measures

### Fret Layer
- ✓ Diamond noteheads for all notes
- ⏳ Finger notches color-coded (1=yellow, 2=green, 3=blue, 4=red)
- ⏳ Sustain rails connect held notes
- ✓ All fret numbers 0-12 (within range)

### Bridge Layer
- ✓ p-i-m-a-m-i pattern on notes
- ⏳ Strum arrows (when implemented)
- ⏳ Technique overlays (when implemented)

### Chords Layer
- ✓ Chord symbol at start of chord change
- ✓ All 35 chords present (C, Dm7, G7, Am, etc.)
- ⏳ Roman numerals (optional, not yet displayed)

### Bass Layer
- ✓ Bass anchor at root note of each chord
- ⏳ Slash bass indicators for inversions (C/G, G/B, etc.)
- ⏳ Ledger lines (when implemented)

### Diagrams Layer (Not Yet Implemented)
- ⏳ Two chord diagrams per measure
- ⏳ Finger labels match left-hand fingering
- ⏳ Open/muted string markers

### Scale Layer (Not Yet Implemented)
- ⏳ Scale map shows C major
- ⏳ Chord tones highlighted within scale
- ⏳ Fretboard range (first 5-7 frets)

### Notation Layer (Foundation Complete)
- ✓ Placeholder 5-line staff renders
- ⏳ Full VexFlow integration (Phase 3B)
- ⏳ Notes aligned to PPQ grid (±1px)

### Fretboard Layer (Not Yet Implemented)
- ⏳ Interactive neck renders 24 frets
- ⏳ String colors match physical guitar
- ⏳ Fret markers at 3, 5, 7, 9, 12, etc.

---

## Success Criteria

### Quantitative Metrics
- ✅ All 35 measures generated
- ✅ 4 form sections with correct boundaries
- ✅ PPQ timing: 0 alignment errors (all measures 3840 ticks)
- ✅ Chord progression: 100% accurate (35/35 validated)
- ✅ Right-hand fingering: Present on all notes
- ⏳ 90/90 layer screenshots captured
- ⏳ Visual regression: <0.01 diff ratio vs. baseline

### Qualitative Metrics
- ✅ Musicians can confirm chord progression
- ✅ Form sections visually distinct
- ✅ Harmonic progression clearly visible (C → Dm → G → C)
- ⏳ Playback sounds correct at 74 BPM
- ⏳ All layers toggle smoothly during playback (60 FPS)

---

## Bach Prelude Specification

### Metadata
- **Title**: Prelude in C Major (BWV 846)
- **Composer**: J.S. Bach
- **Source**: Well-Tempered Clavier, Book I
- **Key**: C Major
- **Time Signature**: 4/4
- **Tempo**: 74 BPM
- **Total Measures**: 35
- **Structure**: Continuous arpeggios with harmonic progression

### Harmonic Analysis

**Enunciation (M1-11)**: Establishing C major tonality
```
M1-2:  C    (I)
M3-4:  Dm7  (ii7)
M5:    G7   (V7)
M6:    C    (I)
M7-8:  Am   (vi)
M9-10: D7   (V7/V - secondary dominant)
M11:   G    (V)
```

**Development (M12-19)**: Chromatic exploration
```
M12-13: C    (I)
M14:    G/B  (V6 - first inversion)
M15:    Am   (vi)
M16:    G/B  (V6)
M17:    C    (I)
M18:    C7   (V7/IV - secondary dominant)
M19:    F    (IV)
```

**Recapitulation (M20-32)**: Return with modal mixture
```
M20:    Fm   (iv - modal mixture, borrowed from C minor)
M21:    C/G  (I6/4 - second inversion)
M22:    G7   (V7)
M23-24: C    (I)
M25:    Am7  (vi7)
M26:    Dm7  (ii7)
M27:    G7   (V7)
M28-29: C    (I)
M30:    G7/B (V6/5 - third inversion)
M31:    Am7  (vi7)
M32:    D7   (V7/V)
```

**Coda (M33-35)**: Final cadence
```
M33:    G7   (V7)
M34-35: C    (I - authentic cadence)
```

### Arpeggio Pattern

Each measure contains **24 notes** (6 notes per beat × 4 beats):
- **Rhythm**: Sextuplets (16th note feel, but 6 per beat)
- **PPQ Timing**: Notes at 0, 160, 320, 480, 640, 800, 960, ... (every 160 ticks)
- **Voicing**: Standard guitar chord shapes using ChordToTabService
- **Right Hand**: p-i-m-a-m-i pattern repeating
- **Left Hand**: Finger numbers from chord shapes (0-4)

---

## Integration with Existing Tests

The Bach Prelude test integrates with:

1. **Existing E2E Infrastructure**
   - Uses same Playwright configuration
   - Shares test utilities (layer isolation, screenshot helpers)
   - Outputs to same `test-artifacts/` directory

2. **Visual Regression Pipeline**
   - Compatible with existing snapshot comparison tools
   - Uses same diff threshold (<0.01 ratio)
   - Can be added to CI workflow alongside other visual tests

3. **Performance Benchmarks**
   - Validates 60 FPS target during layer toggling
   - Measures render overhead for all 10 layers
   - Tracks memory usage over 35-measure navigation

4. **Musical Accuracy Validators**
   - Chord voicing checks compatible with Theory Atlas
   - PPQ timing validation aligns with transport system
   - Arpeggio pattern recognition useful for auto-generation features

---

## Development Workflow

### Adding New Layers

When implementing a new layer (e.g., diagrams):

1. **Implement Layer Renderer**: Add to `tabRenderer.ts`
2. **Add to Score Fixtures**: Update `bachPreludeScore.ts` with test data
3. **Update Test**: Screenshot suite automatically captures new layer
4. **Validate**: Run `pnpm test:bach-prelude` to generate screenshots
5. **Review**: Visual inspection of generated PNGs
6. **Baseline**: Accept screenshots as baseline for future comparisons

### Debugging Layer Issues

```bash
# 1. Run full suite to identify failing layers
pnpm test:bach-prelude

# 2. Inspect manifest for failures
cat test-artifacts/bach-prelude-screenshots/capture-manifest.json | jq '.results[] | select(.captured == false)'

# 3. Run specific layer test in headed mode
pnpm playwright test tests/e2e/theater8k.bach-prelude-layers.spec.ts --headed --debug

# 4. Examine specific measure screenshot
open test-artifacts/bach-prelude-screenshots/bach-m01-{layer}.png
```

---

## Future Enhancements

### Phase 3: Musical Validators
- Implement chord voicing validator (C = C-E-G)
- Implement PPQ timing validator (160-tick alignment)
- Implement arpeggio pattern validator (ascending/descending)

### Phase 4: HTML Report
- Build interactive grid view with traffic lights
- Add screenshot zoom/comparison functionality
- Export to PDF for documentation

### Phase 5: CI Integration
- Auto-run on every PR
- Post results as PR comment
- Upload artifacts to GitHub Actions
- Fail PR if visual regression detected

### Phase 6: Extended Coverage
- Add more classical pieces (Für Elise, Moonlight Sonata)
- Test alternate tunings (Drop D, DADGAD)
- Test different time signatures (3/4, 6/8)
- Test key changes and modulations

---

## References

- [Layer System Architecture](../theater/8k-theater/LAYER_SYSTEM_ARCHITECTURE.md)
- [NVX1 Score Parity Plan](../theater/8k-theater/NVX1_SCORE_PARITY_PLAN.md)
- [Bach Prelude Plan](/score-parity-sprint-2-3.plan.md)
- [Playwright E2E Tests](../../tests/e2e/)

---

**Last Updated**: 2025-10-22  
**Author**: Engineering Team  
**Status**: Phase 1-2 Complete, Ready for Visual Regression Baseline

