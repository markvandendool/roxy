# RockyAI Testing Gym - Comprehensive Guide

**Date:** 2025-01-24  
**Status:** Production Ready

## Overview

The RockyAI Testing Gym is a comprehensive testing suite page (`/rocky-test-gym`) that exercises all RockyAI orchestration workflows with real audio analysis, visual feedback, and automated test execution using Cursor's internal browser tools.

## Features

- **Real Audio Analysis**: Uses Web Audio API AnalyserNode to detect actual audio output
- **Full Quality Metrics**: Timing, latency, spectrum analysis, duration verification
- **Visual Feedback**: Real-time progress bars, waveform visualizers, test results
- **Service Health Monitoring**: Tracks health of all services (Rocky, NotaGen, MusicGen)
- **Cursor Browser Integration**: Automated test execution via Cursor's internal browser tools
- **Comprehensive Reporting**: Detailed test reports with pass/fail summaries

## Test Suites

### Instant Jam Workflow Tests (Primary Focus)

#### Skeleton Generation Tests
1. **skeleton-generation**: Verify skeleton score generates in <100ms
2. **skeleton-audio-detection**: Verify audio is detected via AnalyserNode
3. **skeleton-frequency-verification**: Verify correct chord frequencies are present

#### NotaGen Integration Tests
4. **notagen-trigger**: Trigger NotaGen orchestration and verify it starts
5. **notagen-background-generation**: Verify background generation doesn't interrupt playback
6. **notagen-score-merge**: Verify score merge completes successfully
7. **notagen-part-addition**: Verify new orchestral parts appear in transport
8. **notagen-frequency-verification**: Verify orchestral frequencies appear in audio spectrum

#### MusicGen Integration Tests
9. **musicgen-trigger**: Trigger MusicGen audio generation and verify it starts
10. **musicgen-audio-generation**: Verify audio file is generated successfully
11. **musicgen-audio-playback**: Verify generated audio plays correctly
12. **musicgen-audio-merge**: Verify audio merges with skeleton score correctly
13. **musicgen-quality-verification**: Verify no audio glitches/clicks (THD analysis)

#### Full Workflow Tests
14. **full-workflow-execution**: Execute complete workflow end-to-end
15. **full-workflow-phase-completion**: Verify all phases complete successfully
16. **full-workflow-score-verification**: Verify final score has all parts
17. **full-workflow-transport-playback**: Verify transport plays complete score correctly
18. **full-workflow-timing-synchronization**: Verify all layers are synchronized
19. **full-workflow-spectrum-analysis**: Complete spectrum analysis across all layers
20. **full-workflow-quality-assessment**: Final audio quality assessment with all metrics

### Service Health Tests
- **skeleton-service-health**: Check skeleton generator service health
- **notagen-service-health**: Check NotaGen service health
- **musicgen-service-health**: Check MusicGen service health

## Usage

### Via UI Page

1. Navigate to `/rocky-test-gym`
2. Select test suite from dropdown
3. Select tests to run (checkboxes)
4. Click "Run Tests" button
5. Monitor progress in real-time
6. View results and metrics

### Via Cursor Browser Tools

1. **Navigate to test gym:**
   ```typescript
   await browser_navigate({ url: 'http://localhost:9135/rocky-test-gym' });
   ```

2. **Wait for page load:**
   ```typescript
   await browser_wait_for({ time: 3 });
   ```

3. **Take initial screenshot:**
   ```typescript
   await browser_take_screenshot({ filename: 'test-gym-initial.png' });
   ```

4. **Execute tests via UI interaction:**
   ```typescript
   // Select test suite
   await browser_click({ element: 'Test suite dropdown', ref: 'suite-selector' });
   await browser_select_option({ element: 'Instant Jam Workflow', ref: 'suite-option' });
   
   // Click Run Tests button
   await browser_click({ element: 'Run Tests button', ref: 'run-tests-button' });
   ```

5. **Monitor execution:**
   ```typescript
   await browser_wait_for({ text: 'Test Suite Complete' });
   ```

6. **Capture console logs:**
   ```typescript
   const consoleMessages = await browser_console_messages();
   ```

7. **Take final screenshot:**
   ```typescript
   await browser_take_screenshot({ filename: 'test-gym-results.png', fullPage: true });
   ```

8. **Analyze results:**
   ```typescript
   const snapshot = await browser_snapshot();
   // Extract test results from page
   ```

### Via Execution Script

```bash
# Run all tests in instant-jam-workflow suite
node scripts/testing/run-rocky-test-gym.mjs instant-jam-workflow

# Run specific tests
node scripts/testing/run-rocky-test-gym.mjs instant-jam-workflow skeleton-generation skeleton-audio-detection
```

## Audio Analysis Details

### Frequency Detection
- Uses FFT to detect expected note frequencies
- Compares detected frequencies to expected chord notes
- Tolerance: ±10 Hz for frequency matching
- Frequency match score: percentage of expected frequencies detected

### Amplitude Analysis
- Measures peak amplitude during playback
- Verifies audio is above noise floor (>1% threshold)
- Calculates dynamic range

### Timing Analysis
- Measures latency from trigger to audio detection
- Verifies playback timing matches score
- Measures jitter in playback

### Quality Metrics
- **SNR (Signal-to-Noise Ratio)**: Estimates signal quality
- **THD (Total Harmonic Distortion)**: Detects audio artifacts
- **Overall Quality Score**: Weighted combination of all metrics (0-1)

## Test Result Interpretation

### Pass Criteria
- Test status: `passed`
- Audio detected: `true`
- Latency: <100ms (generation), <50ms (audio onset)
- Quality score: >0.7
- No console errors

### Fail Criteria
- Test status: `failed`
- Audio not detected
- Latency exceeds thresholds
- Quality score <0.7
- Console errors present

## Architecture

### Components
- **RockyTestGym.tsx**: Main test gym page UI
- **AudioAnalysisEngine.ts**: Web Audio API analysis engine
- **TestRunner.ts**: Test execution engine
- **CursorBrowserTestRunner.ts**: Cursor browser integration layer
- **testScenarios.ts**: Test scenario definitions
- **types.ts**: Type definitions

### Audio Analysis Flow
1. Initialize AudioAnalysisEngine with AudioContext
2. Connect to audio source (Tone.js or AudioContext)
3. Capture audio stream via AnalyserNode
4. Analyze time-domain (amplitude) and frequency-domain (spectrum)
5. Compare detected vs expected frequencies
6. Calculate quality metrics (SNR, THD, latency)
7. Generate pass/fail verdict

## Integration Points

### RockyService Integration
Tests exercise `rockyService.createProgression()` with `useInstantJam: true` flag.

### Workflow Engine Integration
Tests execute workflows via `WorkflowEngine.execute()` and verify results.

### Transport Integration
Tests verify scores are loaded into transport and playback works correctly.

## Success Criteria

- All test scenarios execute successfully
- Audio analysis detects expected audio output
- Console errors are captured and reported
- Screenshots captured at key points
- Test reports generated automatically
- Real-time visual feedback works
- Performance metrics within acceptable ranges

## Troubleshooting

### Audio Not Detected
- Verify AudioContext is initialized
- Check that audio source is connected
- Ensure user gesture has triggered audio context resume
- Verify audio is actually playing (check transport state)

### High Latency
- Check network connectivity (for remote services)
- Verify local services are running
- Check browser performance (close other tabs)
- Verify audio context latency settings

### Test Failures
- Check console logs for errors
- Verify service health status
- Check test timeout settings
- Review audio analysis thresholds

## Future Enhancements

- CI/CD integration (run tests on commit)
- Performance benchmarking suite
- Visual regression testing
- Load testing (multiple concurrent requests)
- Test result history/dashboard
- Automated bug reporting
- Export test reports (JSON/HTML)

## Files Created

- `src/pages/RockyTestGym.tsx` - Main test gym page
- `src/services/testing/types.ts` - Type definitions
- `src/services/testing/AudioAnalysisEngine.ts` - Audio analysis engine
- `src/services/testing/testScenarios.ts` - Test scenario definitions
- `src/services/testing/TestRunner.ts` - Test execution engine
- `src/services/testing/CursorBrowserTestRunner.ts` - Cursor browser integration
- `src/components/testing/AudioVisualizer.tsx` - Audio visualization component
- `scripts/testing/run-rocky-test-gym.mjs` - Execution script
- `docs/testing/ROCKYAI_TESTING_GYM_GUIDE.md` - This guide

## Summary

The RockyAI Testing Gym provides comprehensive testing capabilities for all RockyAI orchestration workflows, with a focus on the Instant Jam workflow (skeleton → NotaGen → MusicGen). It uses real audio analysis to verify audio output, measures quality metrics, and integrates with Cursor's browser tools for automated execution.

All core components are implemented and ready for use. The test gym can be accessed at `/rocky-test-gym` and provides real-time feedback on test execution with comprehensive audio analysis.












