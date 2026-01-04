# Pre-Release To-Do List
**Status:** Phase F Freeze → Phase G → Release  
**Last Updated:** 2025-11-30

---

## 🎯 Phase G Unfreeze (Critical Path)

### 1. Runtime Verification
- [ ] **AudioWorklet Clock Test**
  - Start dev server, verify clock loads
  - Check console for AudioWorklet errors
  - Verify beat calculation accuracy

- [ ] **KhronosBus Tick Verification**
  - Confirm ticks publish at ~60Hz during playback
  - Check telemetry (jitter, drift, positional integrity)
  - Verify no tick gaps or regressions

- [ ] **Basic Audio Playback**
  - Load a score, press play
  - Verify audio actually plays
  - Check for clicks, pops, timing issues

- [ ] **Metronome Click**
  - Verify metronome clicks on beat
  - Check sync to transport position
  - Test tempo changes

### 2. Core System Fixes (If Needed)

- [ ] **AudioScheduler Timing**
  - If rAF drift detected, migrate to AudioWorklet-based scheduling
  - Verify scheduling accuracy vs AudioWorklet clock
  - Test with complex scores

- [ ] **UI Widget Sync**
  - Verify Theater widgets sync to transport
  - Check for visual lag or jitter
  - Test playhead movement

- [ ] **ChordCubes Playback Sync**
  - Integrate KhronosBus for playback-synced animations
  - Remove rAF-only timing from CubeAnimator
  - Test cube animations during playback

### 3. Legacy Cleanup

- [ ] **TransportService Migration**
  - Migrate 9 files from TransportService to KhronosBus hooks
  - Remove TransportService proxy (or mark deprecated)
  - Update imports

- [ ] **UnifiedKernelEngine Cleanup**
  - Verify all 25 references are safe (stub only)
  - Document stub purpose
  - Consider removing if unused

- [ ] **Tone.js Audit**
  - Verify no Tone.Transport usage (synthesis only)
  - Document Tone.js usage (55 files)
  - Consider WebAudio migration (long-term)

---

## 🧪 Testing & Validation

### 4. Test Suite Restoration

- [ ] **Re-enable Skipped Tests**
  - Review ~191 skip-stubbed tests
  - Re-enable transport tests (now KhronosBus-based)
  - Fix any broken tests

- [ ] **New Test Coverage**
  - AudioWorklet clock tests
  - KhronosBus integration tests
  - EventSpineTransportSync tests
  - VGMEngine latency tests

- [ ] **E2E Tests**
  - Full playback flow (load → play → stop)
  - Tempo changes
  - Loop regions
  - Seek operations

### 5. Performance Validation

- [ ] **EventSpine Query Performance**
  - Test with large scores (1000+ measures)
  - Verify query latency <100ms
  - Check memory usage

- [ ] **VGMEngine Latency**
  - Verify <15ms latency target
  - Test live MIDI input
  - Check scheduling accuracy

- [ ] **Audio Playback Quality**
  - No clicks, pops, or artifacts
  - Smooth tempo changes
  - Accurate timing

---

## 🐛 Bug Fixes (As Discovered)

### 6. Runtime Issues

- [ ] **Audio Context Issues**
  - Browser autoplay policy handling
  - AudioContext resume/suspend
  - Multiple tab handling

- [ ] **Timing Issues**
  - Tick frequency stability
  - Position accuracy
  - Loop region behavior

- [ ] **UI Sync Issues**
  - Widget lag
  - Playhead jitter
  - Visual stuttering

---

## 📚 Documentation

### 7. Architecture Documentation

- [ ] **Update Architecture Docs**
  - Document KhronosBus API
  - Document AudioWorklet clock
  - Update transport migration guide

- [ ] **Developer Guide**
  - How to subscribe to KhronosBus
  - How to schedule audio events
  - How to sync UI to transport

- [ ] **Release Notes**
  - Phase F → Phase G changes
  - Breaking changes (if any)
  - Migration guide

---

## 🚀 Release Preparation

### 8. Pre-Release Checklist

- [ ] **Code Quality**
  - All tests passing
  - No linter errors
  - No TypeScript errors
  - No console warnings

- [ ] **Performance**
  - No memory leaks
  - Acceptable load times
  - Smooth playback

- [ ] **Compatibility**
  - Test on Chrome, Firefox, Safari
  - Test on mobile (if applicable)
  - Test with various audio devices

- [ ] **Security**
  - No exposed secrets
  - Secure audio context handling
  - Safe event handling

### 9. Release Artifacts

- [ ] **Build Verification**
  - Production build succeeds
  - No build warnings
  - Asset optimization

- [ ] **Deployment**
  - Staging deployment
  - Production deployment
  - Rollback plan

---

## 📊 Priority Levels

### 🔴 Critical (Block Release)
- Runtime verification (audio plays, ticks work)
- Core system fixes (if broken)
- Critical bug fixes

### 🟡 High (Should Fix)
- Test suite restoration
- Legacy cleanup
- Performance validation

### 🟢 Medium (Nice to Have)
- Documentation updates
- Tone.js audit
- Advanced features

---

## 🎯 Success Criteria

**Release is ready when:**
- ✅ Audio plays correctly
- ✅ Transport timing is accurate
- ✅ UI syncs to transport
- ✅ All critical tests pass
- ✅ No critical bugs
- ✅ Performance is acceptable
- ✅ Documentation is updated

---

## 📝 Notes

- **Phase F Freeze:** No transport/audio/Khronos edits during freeze
- **Phase G Unfreeze:** Runtime verification and fixes
- **Release:** When all critical items are complete

**Estimated Timeline:**
- Phase G Unfreeze: 1-2 days
- Testing & Fixes: 3-5 days
- Documentation: 1 day
- Release Prep: 1 day
- **Total: ~1-2 weeks** (depending on issues found)

---

**Last Updated:** 2025-11-30  
**Status:** Phase F Freeze → Awaiting Phase G Unfreeze








