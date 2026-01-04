# Score Parity Metric Matrix

**Status:** Adopted October 22, 2025  
**Owners:** Theater 8K Score Team (Mark V. • Copilot)

## Purpose
- Codifies the 20-point inspection used to certify NVX1 chord strip, bass ledger, and supporting layers against the Glass Moon reference template.  
- Provides explicit measurement guidance so QA, automation, and design reviews share a single source of truth.  
- Serves as the acceptance gate for score-related parity tests (Playwright, screenshot diffs, and visual spot checks).

## Integration Checklist
- ✅ **Bach Prelude Ultimate Suite** (`tests/e2e/theater8k.bach-prelude-layers.spec.ts`) must emit metric snapshots alongside screenshots.  
- ✅ **Score Parity Metrics Spec** (new Playwright entry point `tests/e2e/theater.score-parity-metrics.spec.ts`) records pass/fail for all rows below and uploads `test-artifacts/score-parity/metrics.json`.  
- ✅ CI must block merges when any metric reports `status !== "pass"`.  
- ✅ Manual reviews (design, pedagogy) reference this matrix before sign-off.

> **Command Stub (pending script wiring):** `pnpm test:score-parity` → alias for the Playwright metric suite once landed.

## 20-Point Metric Table
| # | Metric | Description | Measurement Strategy | Pass Criteria |
|---|--------|-------------|----------------------|---------------|
| 1 | Chord Card Fill Parity | Chord strip cards must retain the white NVX1 reference background. | Capture `getComputedStyle` for the active chord card or compare to baseline PNG. | Hex `#ffffff` ± 1% luminance delta or pixel diff < 0.5%. |
| 2 | Chord Text Alignment | Chord names must align to the left edge within template tolerance. | Measure text bounding box vs. card inset (`CanvasRenderingContext2D.measureText`). | ≤ 4 px deviation from template inset. |
| 3 | Bass Lane Order | Bass ledger must render directly beneath chord strip before diagrams. | Compare `layout.layerOffsets` ordering to expected stack. | Bass offset equals chords offset + chords height (±2 px). |
| 4 | Diagram Alignment | Diagram rack stays vertically centered on its layer without overlapping bass. | Inspect diagram Y positions vs. layer midpoint. | |Δy| ≤ 6 px relative to layer midpoint. |
| 5 | Layer Toggle Sequence | Default stack order matches NVX1: Form → Timeline → Chords → Bass → Diagrams → Fret → Bridge → Notation. | Assert `tokens.layerOrder`. | Exact order match; no extraneous layers. |
| 6 | Timeline Contrast | Timeline typography stays legible on neutral background. | Calculate contrast ratio using WCAG formula from sampled colors. | ≥ 4.5:1 contrast ratio. |
| 7 | Form Rail Placement | Form rail anchors to top margin with consistent padding. | Measure distance from canvas top to rail center. | 64 px ± 4 px spacing. |
| 8 | Bass Diamond Palette | NVX tone colors (root/third/fifth/seventh) map correctly to diamonds. | Sample fill colors per tone from rendered diamonds. | Color matches palette within ΔE ≤ 3. |
| 9 | Analysis Label Proximity | Roman numerals stay tethered to chord names. | Compute vertical gap between chord and analysis baselines. | Gap between 12–18 px inclusive. |
| 10 | Lane Badge Sequence | Lane badges mirror visual stack for quick scanning. | Read badge list in DOM order. | Matches `form, timeline, chords, analysis, bass, diagrams, fret, technique, bridge, scale`. |
| 11 | Technique Clearance | Technique overlay avoids colliding with fret diamonds. | Measure minimum distance between overlay rect and highest fret diamond. | ≥ 8 px clearance. |
| 12 | String Midline Balance | Strings stay evenly distributed within the fret layer. | Validate spacing variance across `layout.stringY`. | Standard deviation ≤ 0.75 px. |
| 13 | Bridge Separation | Bridge strokes sit below fret layer without overlap. | Compare bridge top to lowest string Y. | ≥ 20 px gap, consistent across strokes. |
| 14 | Diagram Rack Height | Diagram layer reserves full vertical budget for legibility. | Inspect `layerStyles.diagrams.height`. | Height between 120–140 px. |
| 15 | Canvas Background | Paper backdrop stays at NVX1 neutral gray. | Sample `tokens.canvasBackground`. | Exact `#EFEFEF`. |
| 16 | Measure Divider Legibility | Major/minor grid lines remain visible but unobtrusive. | Measure stroke width & opacity via `getComputedStyle`. | Width 1–1.5 px; opacity 0.55–0.75. |
| 17 | Sustain Bar Visibility | Sustain rails stay gold and distinct from strings. | Compare color to `tokens.sustainBarColor`. | RGB difference ≤ 5 units per channel. |
| 18 | Theme Override Safety | Chord card fill remains correct even when fret label tokens change. | Toggle theme overrides during test and re-sample fill. | Chord card still passes Metric #1 after override. |
| 19 | Accessibility Contrast | Text within chord/bass cards passes WCAG AA. | Run contrast check for text color vs. background. | ≥ 7:1 for critical instructional text. |
| 20 | Performance Baseline | Layer render passes complete within frame budget. | Measure average frame time during layer toggle loop (Playwright `page.metrics`). | ≤ 16 ms average over 120 toggles. |

## Data Capture & Reporting
- Persist raw readings to `test-artifacts/score-parity/metrics.json`:
  ```json
  {
    "timestamp": "2025-10-22T18:41:03.251Z",
    "metrics": [
      { "id": 1, "name": "Chord Card Fill Parity", "status": "pass", "value": "#ffffff", "threshold": "hex #ffffff" },
      { "id": 2, "name": "Chord Text Alignment", "status": "pass", "value": 2.5, "threshold": "≤ 4 px" }
      // ... remaining metrics
    ]
  }
  ```
- Upload the JSON (and any supporting screenshots) as Playwright attachments so CI pipelines can surface regressions.
- When a metric fails, annotate pull requests with the offending IDs and include before/after imagery for design review.

## References
- **Template Source:** `docs/reference/nvx1-chord-strip-reference.md` (Glass Moon capture).  
- **Implementation Blueprint:** `src/components/theater8k/widgets/score/tabRenderer.ts` and `src/components/theater8k/theme/scoreTokens.ts`.  
- **Test Harness:** `tests/e2e/helpers/layerIsolation.ts`, `tests/e2e/theater8k.bach-prelude-layers.spec.ts`.  
- **Future Work Items:**
  1. Wire `pnpm test:score-parity` script after Playwright spec lands.  
  2. Add visual regression baseline overlaying captured metrics.  
  3. Integrate metric results into `docs/theater-widget-parity-tracker.md` composite scorecards.
