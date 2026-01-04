# Detailed Release Action Plan - MindSong JukeHub
**Generated:** 2025-11-30  
**Status:** Phase F Freeze → Phase G → Production  
**Based on:** Full Production Release Plan

---

## Overview

This document provides a detailed, task-by-task breakdown of the release plan. Each task is actionable, with clear acceptance criteria and dependencies.

**Total Timeline:** 15 weeks (3.75 months)  
**Current Phase:** Phase F Freeze  
**Next Phase:** Phase G Unfreeze

---

## Phase G: Unfreeze & Verification (Week 1)

### Day 1-2: Runtime Verification

#### Task G1.1: AudioWorklet Clock Test
**Status:** Pending  
**Priority:** P0 (Critical)  
**Estimated Time:** 2 hours

**Steps:**
1. Start dev server: `npm run dev`
2. Navigate to `/theater-8k` or `/score`
3. Open browser DevTools → Console
4. Check for AudioWorklet errors
5. Verify `khronos-clock.js` loads successfully
6. Check console logs for clock initialization
7. Verify beat calculation accuracy in telemetry

**Acceptance Criteria:**
- ✅ No AudioWorklet errors in console
- ✅ Clock loads without errors
- ✅ Beat calculation is accurate (verify against expected tempo)
- ✅ Clock ticks are consistent

**Dependencies:** None  
**Blockers:** None  
**Notes:** Reference: `docs/architecture/PHASE_G_RUNTIME_VERIFICATION_CHECKLIST.md`

---

#### Task G1.2: KhronosBus Tick Verification
**Status:** Pending  
**Priority:** P0 (Critical)  
**Estimated Time:** 3 hours

**Steps:**
1. Start dev server
2. Navigate to a page with transport (e.g., `/theater-8k`)
3. Open DevTools → Console
4. Subscribe to KhronosBus ticks: `KhronosBus.subscribe('tick', console.log)`
5. Press play
6. Monitor tick frequency (should be ~60Hz)
7. Check telemetry for jitter, drift, positional integrity
8. Verify no tick gaps or regressions

**Acceptance Criteria:**
- ✅ Ticks publish at ~60Hz during playback
- ✅ No tick gaps or missing ticks
- ✅ Telemetry shows acceptable jitter (<5ms)
- ✅ Position updates correctly
- ✅ No regressions from previous behavior

**Dependencies:** G1.1 (AudioWorklet clock must work)  
**Blockers:** None  
**Notes:** Use `useKhronosPosition` hook for testing

---

#### Task G1.3: Basic Audio Playback
**Status:** Pending  
**Priority:** P0 (Critical)  
**Estimated Time:** 2 hours

**Steps:**
1. Start dev server
2. Navigate to `/score` or `/nvx1-score`
3. Load a test score
4. Press play button
5. Verify audio actually plays
6. Listen for clicks, pops, timing issues
7. Test stop, pause, resume
8. Test tempo changes

**Acceptance Criteria:**
- ✅ Audio plays when play is pressed
- ✅ No clicks, pops, or artifacts
- ✅ Stop, pause, resume work correctly
- ✅ Tempo changes work smoothly
- ✅ Timing is accurate

**Dependencies:** G1.1, G1.2 (Clock and ticks must work)  
**Blockers:** None  
**Notes:** Test with multiple score types

---

#### Task G1.4: Metronome Click
**Status:** Pending  
**Priority:** P0 (Critical)  
**Estimated Time:** 1 hour

**Steps:**
1. Start dev server
2. Navigate to a page with metronome
3. Enable metronome
4. Press play
5. Verify metronome clicks on beat
6. Check sync to transport position
7. Test tempo changes
8. Verify metronome stops when transport stops

**Acceptance Criteria:**
- ✅ Metronome clicks on beat
- ✅ Syncs to transport position
- ✅ Tempo changes work correctly
- ✅ Stops when transport stops

**Dependencies:** G1.1, G1.2, G1.3  
**Blockers:** None  
**Notes:** Test with various tempos (60, 120, 180 BPM)

---

### Day 2-3: Core System Fixes

#### Task G2.1: AudioScheduler Timing Review
**Status:** Pending  
**Priority:** P0 (Critical if drift detected)  
**Estimated Time:** 4 hours

**Steps:**
1. Review `src/services/audio/AudioScheduler.ts`
2. Check for `requestAnimationFrame` usage
3. Compare timing accuracy vs AudioWorklet clock
4. If drift detected:
   - Migrate to AudioWorklet-based scheduling
   - Remove rAF timing loop
   - Use KhronosBus ticks for scheduling
5. Test with complex scores
6. Verify scheduling accuracy

**Acceptance Criteria:**
- ✅ No rAF drift detected OR migration complete
- ✅ Scheduling accuracy within 5ms
- ✅ Works with complex scores (1000+ events)
- ✅ No performance regressions

**Dependencies:** G1.1, G1.2 (Must verify clock first)  
**Blockers:** None  
**Notes:** Reference: `docs/architecture/PHASE_F_FREEZE_ARCHITECTURAL_DIAGNOSTIC.md`

---

#### Task G2.2: UI Widget Sync Verification
**Status:** Pending  
**Priority:** P0 (Critical)  
**Estimated Time:** 3 hours

**Steps:**
1. Start dev server
2. Navigate to `/theater-8k`
3. Load a score and press play
4. Observe Theater widgets (playhead, notes, etc.)
5. Check for visual lag or jitter
6. Test playhead movement accuracy
7. Verify widgets sync to transport position
8. Test with tempo changes

**Acceptance Criteria:**
- ✅ Theater widgets sync to transport
- ✅ No visual lag or jitter
- ✅ Playhead movement is accurate
- ✅ Works with tempo changes

**Dependencies:** G1.1, G1.2, G1.3  
**Blockers:** None  
**Notes:** Test with various widget configurations

---

#### Task G2.3: ChordCubes Playback Sync Integration
**Status:** Pending  
**Priority:** P1 (High)  
**Estimated Time:** 4 hours

**Steps:**
1. Review `src/plugins/chordcubes-v2/rendering/CubeAnimator.ts`
2. Check for rAF-only timing
3. Integrate KhronosBus for playback-synced animations
4. Remove rAF-only timing from CubeAnimator
5. Test cube animations during playback
6. Verify animations sync to transport

**Acceptance Criteria:**
- ✅ Cube animations sync to transport
- ✅ No rAF-only timing in CubeAnimator
- ✅ Animations work during playback
- ✅ No performance regressions

**Dependencies:** G1.1, G1.2  
**Blockers:** None  
**Notes:** Reference: `docs/architecture/PHASE_F_FREEZE_ARCHITECTURAL_DIAGNOSTIC.md`

---

### Day 3-5: Test Suite Restoration

#### Task G3.1: Review Skipped Tests
**Status:** Pending  
**Priority:** P1 (High)  
**Estimated Time:** 4 hours

**Steps:**
1. Find all skipped tests: `grep -r "\.skip\(" src/ tests/`
2. Review each skipped test
3. Categorize by reason (transport-related, broken, etc.)
4. Create list of tests to re-enable
5. Document tests that should remain skipped

**Acceptance Criteria:**
- ✅ All skipped tests reviewed
- ✅ List of tests to re-enable created
- ✅ Tests categorized by priority
- ✅ Documentation updated

**Dependencies:** None  
**Blockers:** None  
**Notes:** ~191 skipped tests found

---

#### Task G3.2: Re-enable Transport Tests
**Status:** Pending  
**Priority:** P0 (Critical)  
**Estimated Time:** 6 hours

**Steps:**
1. Find transport-related skipped tests
2. Update tests to use KhronosBus instead of legacy transport
3. Re-enable tests
4. Fix any broken tests
5. Run test suite
6. Verify tests pass

**Acceptance Criteria:**
- ✅ Transport tests re-enabled
- ✅ Tests use KhronosBus
- ✅ All tests pass
- ✅ No regressions

**Dependencies:** G1.1, G1.2, G3.1  
**Blockers:** None  
**Notes:** Reference: `docs/architecture/TRANSPORT_SERVICE_MIGRATION_GUIDE.md`

---

#### Task G3.3: Add KhronosBus Integration Tests
**Status:** Pending  
**Priority:** P0 (Critical)  
**Estimated Time:** 4 hours

**Steps:**
1. Create `src/khronos/__tests__/khronos.integration.test.ts` if not exists
2. Add tests for:
   - Subscribe/unsubscribe
   - Tick events
   - Command events
   - Telemetry updates
   - Multiple subscribers
3. Run tests
4. Verify all tests pass

**Acceptance Criteria:**
- ✅ Integration tests created
- ✅ All tests pass
- ✅ Coverage for key scenarios
- ✅ No regressions

**Dependencies:** G1.1, G1.2  
**Blockers:** None  
**Notes:** Reference: `docs/architecture/PHASE_G_TEST_PLANS.md`

---

#### Task G3.4: Fix Broken Tests
**Status:** Pending  
**Priority:** P1 (High)  
**Estimated Time:** 8 hours

**Steps:**
1. Run full test suite: `npm test`
2. Identify broken tests
3. Fix broken tests
4. Re-run test suite
5. Verify all tests pass

**Acceptance Criteria:**
- ✅ All tests pass
- ✅ No broken tests
- ✅ Test coverage maintained
- ✅ No regressions

**Dependencies:** G3.1, G3.2, G3.3  
**Blockers:** None  
**Notes:** May require multiple iterations

---

## Phase H: Core Feature Stabilization (Weeks 2-3)

### Week 2: Production-Ready Pages Testing

#### Task H1.1: Test 32 Production-Ready Pages
**Status:** Pending  
**Priority:** P0 (Critical)  
**Estimated Time:** 16 hours (2 days)

**Pages to Test:**
1. `/` - Index page
2. `/auth` - Authentication
3. `/profile` - User profile
4. `/dashboard` - Main dashboard
5. `/lessons` - Lessons list
6. `/lessons/:lessonId` - Lesson player
7. `/score` - Score editor
8. `/nvx1-score` - NVX1 score editor
9. `/theater-8k` - 8K Theater
10. `/chordcubes` - ChordCubes V2
11. `/myst-cube-room` - Myst Cube Room
12. `/olympus` - Olympus hub
13. `/olympus/piano` - Piano widget
14. `/olympus/fretboard` - Fretboard widget
15. `/olympus/circle` - Circle of fifths
16. `/olympus/braid` - Braid widget
17. `/olympus/score` - Score widget
18. `/fretboard` - Fretboard page
19. `/pricing` - Pricing page
20. `/terms` - Terms of service
21. `/privacy` - Privacy policy
22. `/resources` - Resources
23. `/skills` - Skills tracker
24. `/discover` - Song discovery
25. `/progress` - Progress dashboard
26. `/calendar` - Calendar
27. `/community` - Community
28. `/practice` - Practice studio
29. `/songvault` - Song vault
30. `/livehub` - Live hub
31. `/guitartube` - GuitarTube
32. `/payment-success` - Payment success

**Steps for Each Page:**
1. Navigate to page
2. Verify page loads without errors
3. Test core functionality
4. Check for console errors
5. Verify responsive design
6. Test user interactions
7. Document any issues

**Acceptance Criteria:**
- ✅ All 32 pages load without errors
- ✅ Core functionality works
- ✅ No console errors
- ✅ Responsive design works
- ✅ User interactions work correctly

**Dependencies:** Phase G complete  
**Blockers:** None  
**Notes:** Create test checklist for each page

---

#### Task H1.2: Fix Bugs in Core Services
**Status:** Pending  
**Priority:** P0 (Critical)  
**Estimated Time:** 12 hours (1.5 days)

**Services to Test:**
1. KhronosEngine
2. KhronosBus
3. AudioPlaybackService
4. EventSpineTransportSync
5. EventSpine
6. ChordEngine
7. VGMEngine
8. ScoreLoadingService
9. AudioScheduler
10. GlobalAudioContext
11. ... (all 45 core services)

**Steps:**
1. Test each service individually
2. Test service interactions
3. Identify bugs
4. Fix bugs
5. Re-test
6. Document fixes

**Acceptance Criteria:**
- ✅ All core services work correctly
- ✅ Service interactions work
- ✅ No critical bugs
- ✅ Performance acceptable

**Dependencies:** Phase G complete  
**Blockers:** None  
**Notes:** Prioritize critical bugs first

---

### Week 3: Performance & Browser Compatibility

#### Task H2.1: Performance Optimization
**Status:** Pending  
**Priority:** P1 (High)  
**Estimated Time:** 8 hours

**Steps:**
1. Run performance profiling
2. Identify performance bottlenecks
3. Optimize critical paths
4. Test performance improvements
5. Verify no regressions

**Acceptance Criteria:**
- ✅ Performance targets met
- ✅ No performance regressions
- ✅ Load times acceptable
- ✅ Smooth playback

**Dependencies:** H1.1, H1.2  
**Blockers:** None  
**Notes:** Use Chrome DevTools Performance tab

---

#### Task H2.2: Browser Compatibility Testing
**Status:** Pending  
**Priority:** P0 (Critical)  
**Estimated Time:** 8 hours

**Browsers to Test:**
- Chrome (latest)
- Firefox (latest)
- Safari (latest)
- Edge (latest)

**Steps:**
1. Test on each browser
2. Verify core functionality
3. Check for browser-specific issues
4. Fix any issues
5. Document browser compatibility

**Acceptance Criteria:**
- ✅ Works on all target browsers
- ✅ No browser-specific issues
- ✅ Consistent behavior across browsers
- ✅ Documentation updated

**Dependencies:** H1.1, H1.2  
**Blockers:** None  
**Notes:** Test on desktop and mobile if applicable

---

## Phase I: Staging Features (Weeks 4-6)

### Week 4: Staging Pages Testing

#### Task I1.1: Test 28 Staging Pages
**Status:** Pending  
**Priority:** P1 (High)  
**Estimated Time:** 20 hours (2.5 days)

**Pages to Test:**
1. `/teacher` - Teacher hub
2. `/teacher/lessons` - Teacher lessons
3. `/teacher/lessons/:lessonId/edit` - Lesson editor
4. `/teacher/settings` - Teacher settings
5. `/admin` - Admin dashboard
6. `/booking` - Booking hub
7. `/sessions` - Sessions
8. `/songs` - Song explorer
9. `/music_project/*` - Music project routes (7 sub-routes)
10. `/rocky/builder` - Rocky score builder
11. `/alpha-lucid` - Alpha Lucid
12. `/magic18` - Magic 18
13. `/chord-block-demo` - Chord block demo
14. `/fretboard-demo` - Fretboard demo
15. `/style-lab` - Style lab
16. `/experiments/roman-dial` - Roman dial lab
17. `/vision1-test` - Vision1 test
18. `/vision1-mock-test` - Vision1 mock test
19. `/vision1-wasm-test` - Vision1 WASM test
20. `/vision1-recording-test` - Vision1 recording test
21. `/obs-websocket-test` - OBS WebSocket test
22. `/ghost-protocol` - Ghost protocol
23. `/architecture` - Architecture map
24. `/typography-test` - Typography test
25. `/tims-tools` - Tim's Tools
26. `/crm` - CRM dashboard
27. `/crm-crawler` - CRM crawler
28. `/crm/templates` - Email templates
29. `/marketing` - Marketing dashboard
30. `/sales` - Sales page
31. `/education` - Music education

**Steps:** (Same as H1.1)

**Acceptance Criteria:**
- ✅ All staging pages load without errors
- ✅ Core functionality works
- ✅ No critical bugs
- ✅ Ready for production

**Dependencies:** Phase H complete  
**Blockers:** None

---

### Week 5: Staging Services Testing

#### Task I2.1: Test 120 Staging Services
**Status:** Pending  
**Priority:** P1 (High)  
**Estimated Time:** 24 hours (3 days)

**Service Categories:**
- Apollo services (15 services)
- Audio services (25 services)
- Collaboration services (8 services)
- Education services (12 services)
- Import/export services (15 services)
- MIDI services (8 services)
- Notation services (10 services)
- Orchestration services (8 services)
- Playback services (10 services)
- Progression services (9 services)
- Score services (12 services)
- Social services (8 services)
- Voice leading services (8 services)
- Widget services (10 services)

**Steps:**
1. Test each service individually
2. Test service interactions
3. Identify bugs
4. Fix bugs
5. Re-test
6. Document fixes

**Acceptance Criteria:**
- ✅ All staging services work correctly
- ✅ Service interactions work
- ✅ No critical bugs
- ✅ Performance acceptable

**Dependencies:** I1.1  
**Blockers:** None

---

### Week 6: Integration Testing

#### Task I3.1: Integration Testing
**Status:** Pending  
**Priority:** P1 (High)  
**Estimated Time:** 16 hours (2 days)

**Test Scenarios:**
1. Full user flow (sign up → create score → play → export)
2. Teacher flow (create lesson → assign → track progress)
3. Admin flow (manage users → view analytics)
4. CRM flow (manage leads → send emails)
5. Multi-page workflows

**Steps:**
1. Create test scenarios
2. Execute test scenarios
3. Document issues
4. Fix issues
5. Re-test
6. Document results

**Acceptance Criteria:**
- ✅ All integration tests pass
- ✅ No critical bugs
- ✅ User flows work end-to-end
- ✅ Performance acceptable

**Dependencies:** I1.1, I2.1  
**Blockers:** None

---

## Phase J: Development Features (Weeks 7-12)

### Weeks 7-9: Development Pages Completion

#### Task J1.1: Complete 25 Development Pages
**Status:** Pending  
**Priority:** P2 (Medium)  
**Estimated Time:** 40 hours (5 days)

**Pages to Complete:**
1. `/msm` - MSM Complete
2. `/theater` - Legacy theater
3. `/braid` - Legacy braid
4. `/myst-theater` - Legacy myst theater
5. `/novaxe-theater` - Legacy novaxe theater
6. `/fretboard-test` - Fretboard test
7. `/piano-test` - Piano test
8. `/chord-strip-demo` - Chord strip demo
9. `/dev/ingest` - Dev ingest
10. `/dev/event-spine-trax` - Dev EventSpine Trax
11. `/olympus-safe` - Olympus safe mode
12. `/harmonic-profile-backup` - Harmonic profile backup
13. `/curriculum` - Curriculum
14. `/ear-training` - Ear training
15. `/stem-splitter` - Stem splitter
16. `/notagen` - NotaGen page
17. `/song-explorer` - Song explorer
18. `/progress-dashboard` - Progress dashboard
19. `/rocky-test-gym` - Rocky test gym
20. `/__nvx_trunc` - Truncated NVX
21. ... (5 more)

**Steps:**
1. Review each page
2. Identify incomplete features
3. Complete features
4. Test functionality
5. Fix bugs
6. Document completion

**Acceptance Criteria:**
- ✅ All development pages complete
- ✅ Core functionality works
- ✅ No critical bugs
- ✅ Ready for staging

**Dependencies:** Phase I complete  
**Blockers:** None

---

### Weeks 10-12: Development Services Completion

#### Task J2.1: Complete 200+ Development Services
**Status:** Pending  
**Priority:** P2 (Medium)  
**Estimated Time:** 80 hours (10 days)

**Service Categories:**
- AI services (25 services)
- Stem splitter services (8 services)
- Multiplayer services (12 services)
- Advanced features (155+ services)

**Steps:**
1. Review each service
2. Identify incomplete features
3. Complete features
4. Test functionality
5. Fix bugs
6. Document completion

**Acceptance Criteria:**
- ✅ All development services complete
- ✅ Service interactions work
- ✅ No critical bugs
- ✅ Performance acceptable

**Dependencies:** J1.1  
**Blockers:** None

---

## Phase K: Cleanup & Optimization (Weeks 13-14)

### Week 13: Abandoned Code Cleanup

#### Task K1.1: Remove/Archive Abandoned Code
**Status:** Pending  
**Priority:** P2 (Medium)  
**Estimated Time:** 16 hours (2 days)

**Items to Remove/Archive:**
- 15 abandoned pages (redirects, deprecated routes)
- 154+ abandoned services (legacy, deprecated)
- 234 abandoned components (legacy, deprecated)
- Archive projects (already in archive/)

**Steps:**
1. Review abandoned items
2. Verify they're not used
3. Remove or archive
4. Update imports
5. Run tests
6. Verify no regressions

**Acceptance Criteria:**
- ✅ Abandoned code removed/archived
- ✅ No broken imports
- ✅ Tests pass
- ✅ No regressions

**Dependencies:** Phase J complete  
**Blockers:** None

---

### Week 14: Final Optimization

#### Task K2.1: Performance Optimization
**Status:** Pending  
**Priority:** P1 (High)  
**Estimated Time:** 16 hours (2 days)

**Steps:**
1. Run comprehensive performance profiling
2. Identify optimization opportunities
3. Implement optimizations
4. Test performance improvements
5. Verify no regressions

**Acceptance Criteria:**
- ✅ Performance targets met
- ✅ No performance regressions
- ✅ Load times optimized
- ✅ Smooth playback

**Dependencies:** K1.1  
**Blockers:** None

---

#### Task K2.2: Documentation Completion
**Status:** Pending  
**Priority:** P1 (High)  
**Estimated Time:** 8 hours (1 day)

**Steps:**
1. Review all documentation
2. Update outdated documentation
3. Add missing documentation
4. Verify accuracy
5. Create release notes

**Acceptance Criteria:**
- ✅ All documentation complete
- ✅ Documentation accurate
- ✅ Release notes created
- ✅ Migration guides updated

**Dependencies:** K1.1  
**Blockers:** None

---

## Phase L: Production Launch (Week 15)

### Week 15: Final Verification & Launch

#### Task L1.1: Final Verification
**Status:** Pending  
**Priority:** P0 (Critical)  
**Estimated Time:** 8 hours (1 day)

**Steps:**
1. Run full test suite
2. Verify all critical features
3. Check performance
4. Verify browser compatibility
5. Review documentation
6. Create deployment checklist

**Acceptance Criteria:**
- ✅ All tests pass
- ✅ All critical features work
- ✅ Performance acceptable
- ✅ Browser compatibility verified
- ✅ Documentation complete

**Dependencies:** Phase K complete  
**Blockers:** None

---

#### Task L1.2: Deployment
**Status:** Pending  
**Priority:** P0 (Critical)  
**Estimated Time:** 4 hours

**Steps:**
1. Create production build
2. Deploy to staging
3. Verify staging deployment
4. Deploy to production
5. Verify production deployment
6. Monitor for issues

**Acceptance Criteria:**
- ✅ Production build succeeds
- ✅ Staging deployment successful
- ✅ Production deployment successful
- ✅ No deployment issues
- ✅ Monitoring active

**Dependencies:** L1.1  
**Blockers:** None

---

#### Task L1.3: Launch
**Status:** Pending  
**Priority:** P0 (Critical)  
**Estimated Time:** 2 hours

**Steps:**
1. Final verification
2. Announce launch
3. Monitor for issues
4. Address any issues
5. Document launch

**Acceptance Criteria:**
- ✅ Launch successful
- ✅ No critical issues
- ✅ Monitoring active
- ✅ Documentation updated

**Dependencies:** L1.2  
**Blockers:** None

---

## Summary

**Total Estimated Time:** ~300 hours (15 weeks)  
**Critical Path:** Phase G → Phase H → Phase I → Phase J → Phase K → Phase L

**Key Milestones:**
- Week 1: Phase G complete (runtime verification)
- Week 3: Phase H complete (core features stable)
- Week 6: Phase I complete (staging features ready)
- Week 12: Phase J complete (development features complete)
- Week 14: Phase K complete (cleanup done)
- Week 15: Phase L complete (production launch)

---

**Last Updated:** 2025-11-30  
**Status:** Phase F Freeze → Ready for Phase G








