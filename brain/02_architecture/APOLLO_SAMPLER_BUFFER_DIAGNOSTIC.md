# Apollo Sampler Buffer Loading Diagnostic
**Issue:** "No available buffers for note: 36" error - zero audio output  
**Date:** 2025-12-02  
**Status:** 🔍 DIAGNOSING

---

## Problem Summary

**Error:** `Error: No available buffers for note: 36`  
**Location:** `Apollo.js: Sampler._findClosest()`  
**Impact:** Zero audio output across all browsers (Cursor, Edge, Chrome, Incognito)  
**Note:** C2 (MIDI note 36) - bass note, contrabass instrument

---

## Root Cause Analysis

### Hypothesis 1: Samples Not Loaded
**Evidence:**
- Apollo `isReady = true` but samplers have no buffers
- Browser-specific behavior suggests timing/loading race condition
- Error occurs when trying to play C2 on contrabass instrument

**Diagnostic Steps:**
1. Check `window.apollo.isReady` → Should be `true`
2. Check `window.apollo.getVoiceSampler('melody')` → Should return sampler
3. Check `sampler.hasBuffers` → **LIKELY FALSE**
4. Check `sampler.loaded` → **LIKELY FALSE**

### Hypothesis 2: Wrong Instrument/Sample Range
**Evidence:**
- Switching to "contrabass" instrument
- C2 (note 36) is a low bass note
- Contrabass samples might not include C2 range

**Diagnostic Steps:**
1. Check what samples are actually loaded: `sampler._buffers` or `sampler.buffers`
2. Check sample range: What notes are available?
3. Verify instrument mapping: Is "contrabass" mapped correctly?

### Hypothesis 3: Browser-Specific Sample Loading
**Evidence:**
- Different behavior in Cursor browser vs Edge vs Chrome vs Incognito
- Suggests browser security/caching/loading differences

**Diagnostic Steps:**
1. Check browser console for sample loading errors
2. Check Network tab for failed sample requests
3. Check if samples are cached/blocked

---

## Diagnostic Script

Run this in browser console to diagnose:

```javascript
// Comprehensive Apollo sampler diagnostic
(async function() {
  console.log("🔬 APOLLO SAMPLER DIAGNOSTIC");
  console.log("════════════════════════════════════════");
  
  // 1. Check Apollo instance
  const apollo = window.apollo;
  if (!apollo) {
    console.error("❌ window.apollo not found");
    return;
  }
  console.log("✅ Apollo instance found");
  console.log("   isReady:", apollo.isReady);
  
  // 2. Check all voice samplers
  const voices = ['chord', 'melody', 'bass'];
  for (const voice of voices) {
    console.log(`\n📊 Voice: ${voice}`);
    const sampler = apollo.getVoiceSampler?.(voice);
    if (!sampler) {
      console.error(`   ❌ Sampler not found for ${voice}`);
      continue;
    }
    
    console.log("   ✅ Sampler found");
    console.log("   loaded:", sampler.loaded);
    console.log("   hasBuffers:", sampler.hasBuffers);
    
    // Check buffers directly
    if (sampler._buffers) {
      const bufferKeys = Object.keys(sampler._buffers);
      console.log("   bufferCount:", bufferKeys.length);
      console.log("   bufferKeys (first 10):", bufferKeys.slice(0, 10));
      
      // Check if C2 (note 36) is available
      const note36 = sampler._buffers['36'] || sampler._buffers['C2'] || sampler._buffers['c2'];
      console.log("   C2 (note 36) available:", !!note36);
    } else if (sampler.buffers) {
      const bufferKeys = Object.keys(sampler.buffers);
      console.log("   bufferCount:", bufferKeys.length);
      console.log("   bufferKeys (first 10):", bufferKeys.slice(0, 10));
    } else {
      console.warn("   ⚠️ Cannot access buffers (private property)");
    }
    
    // Check current instrument
    if (apollo.getCurrentInstrument) {
      const currentInst = await apollo.getCurrentInstrument(voice);
      console.log("   currentInstrument:", currentInst);
    }
  }
  
  // 3. Check SampleLibrary
  console.log("\n📚 SampleLibrary:");
  if (window.SampleLibrary) {
    console.log("   ✅ SampleLibrary available");
    console.log("   instruments:", Object.keys(window.SampleLibrary).slice(0, 10));
  } else {
    console.error("   ❌ SampleLibrary not found");
  }
  
  // 4. Try nuclear diagnostic
  if (window.__NVX1_TEST_AUDIO) {
    console.log("\n🔬 Running nuclear diagnostic...");
    const result = await window.__NVX1_TEST_AUDIO();
    console.log("   Result:", result);
  }
  
  console.log("\n════════════════════════════════════════");
})();
```

---

## Fixes Applied

### Fix 1: Metronome Hook Initialization ✅
**File:** `src/utils/novaxe-figma/metronome.ts`  
**Change:** Initialize `window.__TEST_METRONOME_DRIFT__()` at module load (not waiting for first click)  
**Status:** ✅ COMPLETE

### Fix 2: Buffer Check Before Play ✅
**File:** `src/services/audio/backends/ApolloBackend.ts`  
**Change:** Added buffer verification before `playMelody()` call  
**Status:** ✅ COMPLETE  
**Logic:**
- Check `sampler.hasBuffers` or `sampler.loaded`
- If false, wait 100ms and re-check (browser timing issue)
- If still false, throw error with clear message

---

## Next Steps

1. **Run Diagnostic Script:** Execute in browser console to identify root cause
2. **Check Sample Loading:** Verify samples are actually loading in Network tab
3. **Verify Instrument Mapping:** Check if "contrabass" maps to correct Apollo instrument
4. **Browser Testing:** Test in each browser to identify browser-specific issues

---

## Browser-Specific Issues

### Cursor Browser
- May have different security policies
- Check if samples are blocked by CORS/content policy

### Edge/Chrome
- Standard browser behavior
- Check Network tab for failed requests

### Incognito Mode
- No cache - samples must load fresh
- May reveal loading race conditions

---

## Expected Fix

Once root cause identified, likely fixes:
1. **If samples not loading:** Ensure `Apollo.init()` completes before marking `isReady = true`
2. **If wrong instrument:** Fix instrument mapping for "contrabass"
3. **If browser-specific:** Add browser-specific sample loading logic
4. **If timing issue:** Add retry logic with exponential backoff

---

**Status:** 🔍 AWAITING DIAGNOSTIC RESULTS







