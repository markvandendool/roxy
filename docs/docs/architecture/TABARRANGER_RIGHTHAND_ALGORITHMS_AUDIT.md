# TabArranger & RightHandArranger: Complete Algorithm Audit

**Date:** 2025-01-XX  
**Status:** PRODUCTION-READY (TabArranger Phase 1), ARCHITECTURE COMPLETE (RightHandArranger)  
**Purpose:** Standalone reference for fingering algorithm implementation and finger symbol generation

---

## Executive Summary

**TabArranger** and **RightHandArranger** are the two core algorithms that generate physically constrained fingering solutions for guitar tablature and bridge rail notation. They determine which finger symbols (1, 2, 3, 4, T for left hand; P, I, M, A for right hand) appear on the score display and drive 3D hand animations.

**Key Innovation:** These algorithms use optimization techniques (Dynamic Programming, Beam Search) with biomechanical constraint validation to generate **physically playable** fingerings, not just mathematically possible ones.

---

## Part 1: TabArranger - Left-Hand Fingering Algorithm

### 1.1 System Overview

**File:** `packages/nvx1-score/src/fingering/TabArranger.ts`  
**Lines:** 620  
**Status:** Phase 1 Complete ✅, Phase 2 In Progress  
**Complexity:** O(n × m²) where n=notes, m=candidates per note

**Purpose:** Generate optimal left-hand fingerings (string, fret, finger) for tablature display and 3D hand control.

### 1.2 Two-Phase Architecture

#### Phase 1: Rule-Based Algorithm (COMPLETE ✅)

**Components:**
1. **Candidate Generator** - Smart finger assignment with context awareness
2. **Constraint Filters** - 5 hard physical constraints
3. **Cost Function** - 10-component scoring system
4. **Dynamic Programming Optimizer** - Globally optimal path finding
5. **Beam Search** - K-best alternative solutions

#### Phase 2: Data-Driven Enhancement (IN PROGRESS)

**Components:**
1. **Common Voicing Database** - Pattern matching against known chord shapes
2. **Voice Leading Optimization** - Musical intelligence for smooth transitions
3. **ML Integration (Future)** - Fretting-Transformer model for learned patterns

### 1.3 Complete Algorithm Flow

```
Input: Note[] (musical notation - pitches, durations, timing)
  ↓
┌─────────────────────────────────────────────────────────┐
│ STEP 1: Candidate Generation                           │
│ generateCandidatesForNote(note: Note): Fingering[]     │
└─────────────────────────────────────────────────────────┘
  For each note, generate 2-4 possible string/fret combinations
  
  Example: C4 (MIDI 60)
  → Candidate 1: String 1 (high E), Fret 8
  → Candidate 2: String 2 (B), Fret 1
  → Candidate 3: String 3 (G), Fret 5
  → Candidate 4: String 5 (A), Fret 3
  
  Context-aware: Considers previous note for position consistency
  ↓
┌─────────────────────────────────────────────────────────┐
│ STEP 2: Physical Constraint Filtering                  │
│ isPlayable(solution: FingeringSolution): boolean       │
└─────────────────────────────────────────────────────────┘
  Filter by 5 hard constraints:
  
  1. Hand Span Check
     - Maximum span: 4-6 frets (skill-dependent)
     - Formula: max(fret) - min(fret) ≤ skillThreshold
     - Example: Fret 3 to Fret 7 = 4 frets ✅ (acceptable)
     - Example: Fret 1 to Fret 8 = 7 frets ❌ (rejected)
  
  2. Finger Stretch Check
     - Maximum distance between adjacent fingers: 4 frets
     - Example: Index on Fret 3, Middle on Fret 7 = 4 frets ✅
     - Example: Index on Fret 3, Middle on Fret 8 = 5 frets ❌
  
  3. Finger Ordering Validation (CRITICAL)
     - Lower-numbered fingers can't be on higher frets than higher-numbered fingers
     - Index (1) must be ≤ Middle (2) ≤ Ring (3) ≤ Pinky (4)
     - Example: Index on Fret 5, Ring on Fret 3 ❌ (anatomically impossible)
     - Example: Index on Fret 3, Ring on Fret 5 ✅ (valid)
  
  4. Barré Chord Detection
     - Detects impossible barré chords
     - Filters solutions requiring multiple strings with same finger
  
  5. String Skipping Penalty
     - Calculates penalty (doesn't filter, just penalizes)
     - Prefers adjacent strings over large skips
  
  ↓
┌─────────────────────────────────────────────────────────┐
│ STEP 3: Cost Function Scoring                          │
│ calculateCost(solution: FingeringSolution): number     │
└─────────────────────────────────────────────────────────┘
  10-component cost function:
  
  1. Hand Span Penalty
     cost += (span > 4) ? (span - 4)² × 10 : 0
     Exponential penalty beyond comfortable range
  
  2. Finger Stretch Penalty
     cost += (stretch > 3) ? (stretch - 3)² × 8 : 0
     Exponential penalty beyond 3 frets
  
  3. String Skipping Penalty
     cost += stringSkipCount × 5
     Penalizes non-adjacent string usage
  
  4. Awkward Finger Combination Detection
     cost += awkwardCombinations × 3
     Detects uncomfortable finger patterns
  
  5. Position Shift Penalty
     cost += Math.abs(newPosition - previousPosition) × 2
     Penalizes large position changes
  
  6. Barré Chord Penalty
     cost += (hasBarre) ? 15 : 0
     Barré chords are harder
  
  7. High Fret Penalty
     cost += (maxFret > 12) ? (maxFret - 12) × 3 : 0
     Higher frets are harder to reach
  
  8. Voice Leading Cost
     cost += pitchMovementCost
     Prefers smooth pitch transitions
  
  9. Open String Bonus
     cost -= (hasOpenString) ? 5 : 0
     Open strings are easier
  
  10. Common Shape Bonus
      cost -= (matchesCommonShape) ? 10 : 0
      Recognized chord shapes are easier
  
  ↓
┌─────────────────────────────────────────────────────────┐
│ STEP 4: Optimization (Best Guessing)                   │
│ optimizeSequence(candidates: Fingering[][]):            │
│   FingeringSolution                                      │
└─────────────────────────────────────────────────────────┘
  Two optimization algorithms:
  
  A. Dynamic Programming (Single Best Solution)
     - Builds DP table: dp[i][j] = best cost ending at note i, candidate j
     - Transition: dp[i][j] = min(dp[i-1][k] + transitionCost(k, j))
     - Backtrack: Reconstruct optimal path from endpoint
     - Complexity: O(n × m²)
     - Returns: Single optimal FingeringSolution
  
  B. Beam Search (K-Best Alternatives)
     - Maintains top-k paths at each step
     - Expands all paths, keeps best k
     - Returns: K best solutions ranked by cost
     - Use case: Show user multiple options
  
  ↓
┌─────────────────────────────────────────────────────────┐
│ STEP 5: Difficulty Estimation                          │
│ estimateDifficulty(solution: FingeringSolution):       │
│   number (0-10)                                          │
└─────────────────────────────────────────────────────────┘
  Calculate physical difficulty:
  - Hand span contribution
  - Finger stretch contribution
  - Position shifts per second
  - Barré usage
  - High fret usage
  
  Returns: 0-10 difficulty rating
  
  ↓
Output: FingeringSolution {
  fingerings: Fingering[],      // Array of {string, fret, finger}
  cost: number,                 // Total optimization cost
  difficulty: number,           // 0-10 physical difficulty
  handSpan: number,             // Maximum fret span
  position: number,             // Starting fret position
  isPlayable: boolean           // Physical validation result
}
```

### 1.4 Finger Symbol Assignment

**Fingering Object Structure:**
```typescript
interface Fingering {
  string: number;        // 1-6 (1=high E, 6=low E)
  fret: number;          // 0-24 (0=open string)
  finger: '1' | '2' | '3' | '4' | 'T';  // Finger assignment
  pitch: number;         // MIDI note number
}
```

**Finger Symbol Mapping:**
- **"1"** = Index finger → Displayed on tablature above/below fret
- **"2"** = Middle finger → Displayed on tablature above/below fret
- **"3"** = Ring finger → Displayed on tablature above/below fret
- **"4"** = Pinky finger → Displayed on tablature above/below fret
- **"T"** = Thumb → Displayed on tablature (rare, for thumb-over technique)

**Finger Assignment Logic:**
```typescript
function assignFinger(fret: number, position: number): string {
  // Position = lowest fret in current hand position
  const relativeFret = fret - position;
  
  if (relativeFret === 0) return '1';      // Index on lowest fret
  if (relativeFret === 1) return '2';      // Middle on next fret
  if (relativeFret === 2) return '3';       // Ring on next fret
  if (relativeFret === 3) return '4';      // Pinky on next fret
  if (relativeFret === 4) return '4';      // Pinky stretch (max)
  
  // Special cases
  if (fret === 0) return null;             // Open string, no finger
  if (relativeFret > 4) return 'T';         // Thumb-over (advanced)
  
  return '1'; // Default to index
}
```

### 1.5 Physical Constraint Enforcement (Critical Bugfix)

**Problem:** TabArranger was generating physically impossible fingerings where lower-numbered fingers were on higher frets than higher-numbered fingers.

**Example of Invalid Fingering (Now Caught):**
```
String 3, Fret 5, Finger 1 (index)  ❌
String 2, Fret 5, Finger 1 (index)  ❌
String 1, Fret 3, Finger 3 (ring)   ❌
```
This requires index finger on Fret 5 while ring finger is on Fret 3 - anatomically impossible.

**Solution:** Constraint validation **during DP optimization**, not just after:
```typescript
// Inside DP loop (lines 618-679 in TabArranger.ts)
for (let i = 0; i < candidates.length; i++) {
  for (let j = 0; j < candidates[i].length; j++) {
    const currCandidate = candidates[i][j];
    
    // Build accumulated path so far
    const pathSoFar: Fingering[] = [];
    // ... backtrack to build path ...
    pathSoFar.push(currCandidate);
    
    // Check if accumulated solution violates physical constraints
    const testSolution: FingeringSolution = {
      fingerings: pathSoFar,
      cost: 0,
      difficulty: 0,
      position: Math.min(...pathSoFar.map(f => f.fret)),
    };
    
    // CRITICAL: Validate during optimization, not after
    if (!this.isPlayable(testSolution)) {
      continue; // Skip this candidate
    }
    
    // Continue DP calculation...
  }
}
```

### 1.6 Willing Sacrifice: Complexity Reduction

**File:** `packages/nvx1-score/src/fingering/WillingSacrifice.ts`  
**Lines:** 380  
**Purpose:** Handle physically impossible passages by simplifying them

**6 Simplification Layers:**
```
Layer 0: Original (may be unplayable)
  ↓
Layer 1: removeOctaveDoubling()
  Remove pitch duplicates (e.g., C4 + C5 → C4 only)
  ↓
Layer 2: keepMelodyAndBass()
  Strip inner voices, keep only melody and bass
  ↓
Layer 3: arpeggiateChords()
  Spread simultaneous notes over time
  ↓
Layer 4: simplifyRhythm()
  Reduce note density (remove subdivisions)
  ↓
Layer 5: transposeToEasierKey()
  Move to easier register (fewer sharps/flats, lower frets)
  ↓
Output: SimplificationResult {
  layers: FingeringSolution[],  // One solution per layer
  recommended: number,          // Best layer index
  playability: boolean[]        // Which layers are playable
}
```

**Playability Detection:**
```typescript
isPassagePlayable(notes: Note[], tempo: number): boolean {
  // Check 1: Max simultaneity (≤ 6 notes for 6-string guitar)
  if (maxSimultaneous > 6) return false;
  
  // Check 2: Generate fingering successfully
  const fingering = tabArranger.generateFingerings(notes);
  if (!fingering.success) return false;
  
  // Check 3: Hand span not extreme (≤ 8 frets)
  if (fingering.handSpan > 8) return false;
  
  // Check 4: Position shifts per second (≤ 4 shifts/sec)
  if (shiftsPerSecond > 4) return false;
  
  return true;
}
```

---

## Part 2: RightHandArranger - Right-Hand Fingering Algorithm

### 2.1 System Overview

**File:** `packages/nvx1-score/src/fingering/rightHand/RightHandArranger.ts`  
**Status:** Architecture Complete, Implementation In Progress  
**Purpose:** Generate right-hand patterns (P-I-M-A or strumming) for bridge rail display

### 2.2 Technique Selection

**File:** `packages/nvx1-score/src/fingering/rightHand/TechniqueSelector.ts`

```typescript
function selectTechnique(context: MusicalContext): Technique {
  // Classical: Arpeggios, single-note melodies
  if (hasArpeggios || style === 'classical') {
    return 'fingerpicking';
  }
  
  // Rock/Metal: Power chords, fast runs
  if (tempo > 140 || hasPowerChords) {
    return 'flatpicking';
  }
  
  // Folk/Acoustic: Chord progressions
  if (hasChords && tempo < 120) {
    return 'strumming';
  }
  
  // Hybrid: Complex pieces
  return 'hybrid';
}
```

### 2.3 Fingerpicking (Classical - P-I-M-A)

**Finger Assignments:**
- **P (Pulgar/Thumb):** Bass strings (E6, A5, D4)
- **I (Índice/Index):** G string (G3)
- **M (Medio/Middle):** B string (B2)
- **A (Anular/Ring):** High E string (E1)

**Pattern Generation:**
```typescript
interface FingerpickingPattern {
  pattern: string;        // "P-I-M-A" or "P-A-M-I"
  repetitions: number;
  thumbAlternation: boolean; // Alternating bass
}

function generateFingerpickingPattern(
  notes: Note[],
  leftHandFingering: Fingering[]
): FingerpickingPattern {
  // Analyze note timing and string assignments
  // Match to common patterns (P-I-M-A arpeggio, etc.)
  // Optimize for minimal finger movement
}
```

**Common Patterns:**
- **P-I-M-A:** Standard arpeggio (thumb → index → middle → ring)
- **P-A-M-I:** Reverse arpeggio
- **P-I-M-I-A-M-I:** Extended pattern
- **Travis Picking:** Alternating bass (P) with treble (I-M)

**Finger Independence Constraint:**
- **80ms minimum** between same-finger reuse (Sung 2013 research)
- Prevents physically impossible rapid finger repetition

### 2.4 Flatpicking (Plectrum)

**Pattern Types:**
```typescript
interface PickingPattern {
  type: 'alternate' | 'economy' | 'sweep' | 'hybrid';
  directions: ('down' | 'up')[]; // For each note
  stringSkips: number[];          // Track string jumps
}
```

**Alternate Picking:**
- Down-up-down-up (minimizes hand movement)
- Always alternates direction regardless of string changes

**Economy Picking:**
- Combines alternate + sweep
- Continues same direction when moving to adjacent string
- Fewer strokes than alternate picking

**Sweep Picking:**
- Continuous motion across strings (one direction)
- Used for fast arpeggios

**String Skipping:**
- Non-adjacent strings (complex coordination)
- Higher cost in optimization

### 2.5 Strumming Patterns

**Pattern Structure:**
```typescript
interface StrummingPattern {
  pattern: ('D' | 'U' | 'M' | '-')[]; // Down, Up, Mute, Rest
  accents: boolean[];                   // Which beats are accented
  timing: number[];                     // Exact timing in ms
}
```

**Common Patterns:**
- **Folk Basic:** D-D-U-U (down-down-up-up)
- **Rock Classic:** D-DU-UDU (down-down-up-up-down-up-down-up)
- **Waltz:** D-U-U (down-up-up)

**Arrow Display Mapping:**
- **D (Down)** → ▼ (strong) or ⇓ (weak)
- **U (Up)** → ▲ (strong) or ⇑ (weak)
- **M (Mute)** → ▽ or △ (60% opacity)
- **- (Rest)** → No arrow

### 2.6 Complete RightHandArranger Flow

```
Input: Notes[] + Left-Hand Fingering (from TabArranger)
  ↓
┌─────────────────────────────────────────────────────────┐
│ STEP 1: Technique Selection                             │
│ selectTechnique(context: MusicalContext): Technique     │
└─────────────────────────────────────────────────────────┘
  Analyze musical context:
  - Has arpeggios? → Fingerpicking
  - Has chords + slow tempo? → Strumming
  - Fast tempo + power chords? → Flatpicking
  ↓
┌─────────────────────────────────────────────────────────┐
│ STEP 2: Pattern Generation                              │
│ generatePattern(technique: Technique): Pattern          │
└─────────────────────────────────────────────────────────┘
  Based on technique:
  
  Fingerpicking:
    - Analyze note timing
    - Match to common arpeggio patterns
    - Generate P-I-M-A sequence
  
  Flatpicking:
    - Determine alternate vs. economy vs. sweep
    - Assign down/up directions
    - Optimize for minimal hand movement
  
  Strumming:
    - Analyze rhythm pattern
    - Assign down/up based on beat positions
    - Add accents and mutes
  ↓
┌─────────────────────────────────────────────────────────┐
│ STEP 3: Finger Assignment (Fingerpicking)              │
│ assignFingers(notes: Note[]): RightHandFingering[]      │
└─────────────────────────────────────────────────────────┘
  For each note:
  
  Bass notes (E6, A5, D4) → P (thumb)
  G string → I (index)
  B string → M (middle)
  E1 string → A (ring)
  
  Check finger independence:
  - Minimum 80ms between same-finger reuse
  - If too fast, reassign to different finger
  ↓
┌─────────────────────────────────────────────────────────┐
│ STEP 4: Timing Optimization                            │
│ optimizeTiming(pattern: Pattern): Pattern              │
└─────────────────────────────────────────────────────────┘
  Extract timing from MIDI/notation
  Apply velocity curves (accents, dynamics)
  Smooth transitions between patterns
  ↓
┌─────────────────────────────────────────────────────────┐
│ STEP 5: Physical Validation                            │
│ validatePhysical(solution: RightHandSolution): boolean │
└─────────────────────────────────────────────────────────┘
  Validate:
  - Finger reach to strings
  - Finger independence timing (80ms minimum)
  - Wrist angle limits
  ↓
Output: RightHandSolution {
  fingerings: RightHandFingering[],  // Each with finger (P-I-M-A) or direction (↓↑)
  pattern: FingerpickingPattern | PickingPattern | StrummingPattern,
  technique: 'fingerpicking' | 'flatpicking' | 'strumming',
  totalCost: number,
  performance: PerformanceMetrics
}
```

---

## Part 3: Integration with Score Display

### 3.1 Tablature Rail Display

**Source:** TabArranger `FingeringSolution`  
**Location:** `src/components/NVX1/TablatureRail/` (or similar)

**Display Format:**
```
E │──0━━──1━━──3━━──5━━──│
B │──1━━──1━━──3━━──5━━──│
G │──0━━──2━━──4━━──5━━──│
D │──2━━──3━━──5━━──7━━──│
A │──3━━──3━━──5━━──7━━──│
E │──────1━━──3━━──5━━──│
   1     2     3     4      (finger symbols above/below)
```

**Finger Symbol Rendering:**
```typescript
// For each Fingering in FingeringSolution
fingering.fingerings.forEach(fingering => {
  const x = calculateXPosition(fingering.string, fingering.fret);
  const y = calculateYPosition(fingering.string);
  
  // Render finger symbol
  renderFingerSymbol(x, y, fingering.finger); // "1", "2", "3", "4", "T"
});
```

### 3.2 Bridge Rail Display

**Source:** RightHandArranger `RightHandSolution`  
**Location:** `src/components/NVX1/BridgeRail/` (or similar)

**Display Mode 1: Strumming (Arrows)**
```
  ▼  ⇓  ⇑  ⇑  ▼  ⇑
(D)(d)(u)(u)(D)(u)
```

**Arrow Rendering:**
```typescript
// For each StrumEvent in RightHandSolution
solution.pattern.strums.forEach(strum => {
  const arrowType = strum.isWeak ? 'strumWeak' : 'strum';
  const rotation = strum.isUp ? 180 : 0;
  const opacity = strum.isMiss ? 0.6 : 1.0;
  
  renderArrow(strum.position, arrowType, rotation, opacity);
});
```

**Display Mode 2: Fingerstyle (P-I-M-A Letters)**
```
  p  i  m  a  p  i
```

**Letter Rendering:**
```typescript
// For each RHFingerEvent in RightHandSolution
solution.fingerings.forEach(fingering => {
  const x = calculateXPosition(fingering.timing);
  const y = calculateYPosition(fingering.string);
  
  renderFingerLetter(x, y, fingering.finger); // "p", "i", "m", "a"
});
```

### 3.3 Complete Data Flow: Score → Algorithms → Display → 3D Hands

```
NVX1Score (Musical Notation)
  │
  ├─→ TabArranger.generateFingerings(notes)
  │     ↓
  │   FingeringSolution {
  │     fingerings: [
  │       { string: 2, fret: 5, finger: "1" },  // Index finger
  │       { string: 1, fret: 3, finger: "3" }   // Ring finger
  │     ]
  │   }
  │     ↓
  │   Tablature Rail Display:
  │     E │──0━━──5━━──│
  │     B │──1━━──3━━──│
  │         1     3        (finger symbols)
  │
  └─→ RightHandArranger.generateRightHand(notes, leftHandFingering)
        ↓
      RightHandSolution {
        fingerings: [
          { finger: "p", string: 6 },  // Thumb on low E
          { finger: "i", string: 3 }   // Index on G
        ]
      }
        ↓
      Bridge Rail Display:
        p  i              (P-I-M-A letters)
        OR
        ▼  ⇓              (strumming arrows)
        ↓
      ScorePlaybackConductor extracts technique data:
        technique: {
          string: 2, fret: 5, finger: "1",      // Left hand
          rhFinger: "p"                          // Right hand
        }
        ↓
      HandModel3D.updatePose(technique)
        ↓
      IK Solver calculates joint angles
        ↓
      3D Hand Animation (60 FPS)
```

---

## Part 4: Implementation Details

### 4.1 TabArranger File Structure

```
packages/nvx1-score/src/fingering/
├── TabArranger.ts              (620 lines) - Main algorithm
├── WillingSacrifice.ts         (380 lines) - Complexity reducer
├── UserRulesParser.ts          (280 lines) - Customization
├── types.ts                    - FingeringSolution, Fingering interfaces
└── data/
    ├── tunings.json            - 13 guitar tunings
    └── common-voicings-expanded.json  - 50+ chord shapes
```

### 4.2 RightHandArranger File Structure

```
packages/nvx1-score/src/fingering/rightHand/
├── RightHandArranger.ts        - Main algorithm
├── TechniqueSelector.ts        - Technique selection logic
├── PatternGenerator.ts         - Pattern generation
├── FingerAssigner.ts          - P-I-M-A assignments
├── TimingOptimizer.ts         - Timing/velocity optimization
├── PhysicalValidator.ts       - Right-hand validation
└── types.ts                   - RightHandSolution, RightHandFingering
```

### 4.3 Key Interfaces

**FingeringSolution (Left Hand):**
```typescript
interface FingeringSolution {
  fingerings: Fingering[];
  cost: number;
  difficulty: number;        // 0-10
  handSpan: number;          // Maximum fret span
  position: number;          // Starting fret position
  isPlayable: boolean;
}

interface Fingering {
  string: number;            // 1-6
  fret: number;              // 0-24
  finger: '1' | '2' | '3' | '4' | 'T';
  pitch: number;            // MIDI note number
}
```

**RightHandSolution (Right Hand):**
```typescript
interface RightHandSolution {
  fingerings: RightHandFingering[];
  pattern: FingerpickingPattern | PickingPattern | StrummingPattern;
  technique: 'fingerpicking' | 'flatpicking' | 'strumming';
  totalCost: number;
  performance: PerformanceMetrics;
}

interface RightHandFingering {
  technique: Technique;
  finger?: 'P' | 'I' | 'M' | 'A';      // For fingerpicking
  direction?: 'down' | 'up';           // For flatpicking
  string: number;                      // 1-6
  timing: number;                      // ms from start
  velocity: number;                    // 0-127
}
```

### 4.4 Performance Characteristics

**TabArranger:**
- **Time Complexity:** O(n × m²) where n=notes, m=candidates
- **Typical Performance:** < 50ms for 100-note passage
- **Memory:** O(n × m) for DP table

**RightHandArranger:**
- **Time Complexity:** O(n × p) where n=notes, p=patterns
- **Typical Performance:** < 30ms for 100-note passage
- **Memory:** O(n) for pattern storage

---

## Part 5: Physical Constraint Reference

### 5.1 Left-Hand Constraints

| Constraint | Limit | Formula | Example |
|------------|-------|---------|---------|
| Hand Span | 4-6 frets (skill-dependent) | max(fret) - min(fret) ≤ threshold | Fret 3-7 = 4 frets ✅ |
| Finger Stretch | 4 frets max | |fret₁ - fret₂| ≤ 4 | Index Fret 3, Middle Fret 7 = 4 ✅ |
| Finger Ordering | Index ≤ Middle ≤ Ring ≤ Pinky | finger₁.fret ≤ finger₂.fret | Index Fret 5, Ring Fret 3 ❌ |
| Barré Detection | Filter impossible | Check finger overlap | Multiple strings, same finger |
| String Skipping | Penalty only | cost += skipCount × 5 | Prefer adjacent strings |

### 5.2 Right-Hand Constraints

| Constraint | Limit | Formula | Example |
|------------|-------|---------|---------|
| Finger Independence | 80ms minimum | timeBetween(finger₁, finger₂) ≥ 80ms | Same finger reuse < 80ms ❌ |
| Finger Reach | String-dependent | P: E6-A5-D4, I: G3, M: B2, A: E1 | P on E1 string ❌ |
| Wrist Angle | ±80° flexion | |wristAngle| ≤ 80° | Extreme wrist bend ❌ |
| Strumming Arc | Physics-based | Calculate strumming motion | Validate arm movement |

---

## Part 6: Usage Examples

### 6.1 Basic TabArranger Usage

```typescript
import { TabArranger } from 'packages/nvx1-score/src/fingering/TabArranger';

const tabArranger = new TabArranger({
  skillLevel: 'intermediate',
  tuning: 'standard',
});

const notes = [
  { pitch: 60, duration: 1, timestamp: 0 }, // C4
  { pitch: 64, duration: 1, timestamp: 0 }, // E4
  { pitch: 67, duration: 1, timestamp: 0 }, // G4
];

// Generate single best solution
const solution = tabArranger.generateFingerings(notes);

console.log(solution.fingerings);
// [
//   { string: 2, fret: 1, finger: "1" },  // C4
//   { string: 1, fret: 0, finger: null }, // E4 (open)
//   { string: 3, fret: 0, finger: null }  // G4 (open)
// ]

// Generate K-best alternatives
const alternatives = tabArranger.generateAlternatives(notes, 5);
// Returns 5 best solutions ranked by cost
```

### 6.2 RightHandArranger Usage

```typescript
import { RightHandArranger } from 'packages/nvx1-score/src/fingering/rightHand/RightHandArranger';

const rightHandArranger = new RightHandArranger({
  technique: 'auto', // or 'fingerpicking', 'flatpicking', 'strumming'
});

const notes = [/* ... */];
const leftHandFingering = tabArranger.generateFingerings(notes);

// Generate right-hand solution
const solution = rightHandArranger.generateRightHand(notes, leftHandFingering);

console.log(solution.fingerings);
// [
//   { finger: "p", string: 6, timing: 0 },   // Thumb on low E
//   { finger: "i", string: 3, timing: 100 }, // Index on G
//   { finger: "m", string: 2, timing: 200 }, // Middle on B
//   { finger: "a", string: 1, timing: 300 }  // Ring on high E
// ]
```

### 6.3 Integration with Score Display

```typescript
// In tablature rail component
const fingeringSolution = tabArranger.generateFingerings(notes);

fingeringSolution.fingerings.forEach(fingering => {
  // Render fret number
  renderFret(fingering.string, fingering.fret);
  
  // Render finger symbol
  if (fingering.finger) {
    renderFingerSymbol(fingering.string, fingering.fret, fingering.finger);
  }
});

// In bridge rail component
const rightHandSolution = rightHandArranger.generateRightHand(notes, fingeringSolution);

if (rightHandSolution.technique === 'fingerpicking') {
  rightHandSolution.fingerings.forEach(fingering => {
    renderFingerLetter(fingering.timing, fingering.finger); // "p", "i", "m", "a"
  });
} else if (rightHandSolution.technique === 'strumming') {
  rightHandSolution.pattern.strums.forEach(strum => {
    renderStrumArrow(strum.position, strum.isUp, strum.isWeak, strum.isMiss);
  });
}
```

---

## Part 7: Research Foundation

### 7.1 Academic Papers

- **Sung et al. (2013):** Finger force and biomechanics in guitar playing
  - **Key Finding:** 80ms minimum between same-finger reuse
  - **Used In:** RightHandArranger finger independence constraint

- **Trajano et al. (2004):** Right-hand finger optimization algorithms
  - **Key Finding:** P-I-M-A assignment rules for classical guitar
  - **Used In:** RightHandArranger finger assignment logic

- **OpenSim Hand Model (Mirakhorlo et al. 2018):** Biomechanical hand model
  - **Used In:** 3D hand validation and physical constraints

### 7.2 Open Source References

- **Gtrsnipe (Python):** MIDI → Guitar Tab converter
  - **Used For:** Candidate generation inspiration

- **Chorderator (C/C++):** Chord fingering generator
  - **Used For:** Common voicing database

---

## Conclusion

**TabArranger** and **RightHandArranger** are the core algorithms that:

1. **Generate physically playable fingerings** using optimization (DP, Beam Search)
2. **Enforce biomechanical constraints** (hand span, finger stretch, ordering)
3. **Determine finger symbols** (1,2,3,4,T for left hand; P,I,M,A for right hand)
4. **Drive score display** (tablature rail, bridge rail)
5. **Control 3D hand animations** (via technique metadata)

**Key Innovation:** These algorithms don't just find mathematically possible fingerings - they find **physically playable** ones by validating against biomechanical constraints during optimization, not just after.

**Result:** The score displays correct finger symbols on tablature and bridge rails, and these symbols drive real-time 3D hand animations with biomechanically accurate joint movements.

---

---

## Part 8: Complete System Inventory

### 8.1 Complete File Structure

**TabArranger (Left-Hand) Core:**
```
packages/nvx1-score/src/fingering/
├── TabArranger.ts                    (955 lines) - Main algorithm
├── WillingSacrifice.ts               (380 lines) - Complexity reducer
├── UserRulesParser.ts                (280 lines) - Customization
├── VoiceLeadingOptimizer.ts          (288 lines) - Voice leading optimization
├── types.ts                          (406 lines) - Core type definitions
├── __tests__/
│   ├── TabArranger.test.ts           - Vitest test suite
│   └── TabArranger.basic.test.ts     - Basic tests
├── datasets/
│   ├── tunings.json                  - 13 guitar tunings
│   ├── common-voicings.json          - 50+ chord shapes
│   ├── common-voicings-expanded.json - Extended voicings
│   └── user-rules.md                 - User customization rules
└── 3d/
    ├── HandModel3D.ts                - 3D hand model bridge
    ├── BimanualIntegration.ts        - Bimanual coordination
    └── PhysicalValidator.ts          (531 lines) - Biomechanical validation
```

**RightHandArranger (Right-Hand) Core:**
```
packages/nvx1-score/src/fingering/rightHand/
├── RightHandArranger.ts              (761 lines) - Main algorithm
├── TechniqueSelector.ts              (478 lines) - Technique selection
├── FingerpickingGenerator.ts         (504 lines) - P-I-M-A patterns
├── FlatpickingGenerator.ts           (468 lines) - Pick direction
├── StrummingGenerator.ts             (495 lines) - Strumming patterns
├── CostCalculator.ts                 (421 lines) - Cost function
├── types.ts                          (445 lines) - Type definitions
└── index.ts                          - Package exports
```

**UI Components & Integration:**
```
packages/nvx1-score/src/
├── components/
│   ├── RefingeringModal.tsx          (302 lines) - Alternative fingering selector
│   ├── FretboardVisualization.tsx    - Visual fretboard display
│   └── WillingSacrificeModal.tsx     - Simplification UI
├── examples/
│   └── TabArrangerDemo.tsx           (318 lines) - Complete integration demo
└── pages/
    └── TABATestPage.tsx               (1614 lines) - Comprehensive test page
```

**Frontend Integration Components:**
```
src/components/
├── NVX1/
│   ├── TabEditor/
│   │   ├── TabEditorPanel.tsx        (191 lines) - Main editing controls
│   │   └── LHFingerSelector.tsx      (61 lines) - Left-hand finger selector
│   ├── RHFingerSelector/
│   │   └── index.tsx                 (107 lines) - Right-hand finger selector
│   └── ChordStrip/
│       ├── TablatureLayer.tsx        - Tablature rendering
│       └── StrumsLayer.tsx           (105 lines) - Strums layer
├── novaxe-figma/
│   ├── TablatureLayer.tsx            (620 lines) - Dual-mode tablature
│   └── BridgeLayer.tsx               (395 lines) - Bridge rail rendering
└── theater/widgets/fretboard/components/
    ├── FingeringIndicator.tsx        (48 lines) - Finger indicator
    └── FingeringHints.tsx            (139 lines) - Fretboard hints
```

**Bridge System (Right-Hand Display):**
```
src/utils/novaxe-figma/
├── bridgePatterns.ts                 (407 lines) - 15+ preset patterns
├── bridgeAutoGeneration.ts           (306 lines) - Auto-generation algorithm
└── (used by BridgeLayer.tsx)
```

**Services & Stores:**
```
src/services/
├── input/
│   └── RightHandMenuService.ts       (295 lines) - Pattern entry service
└── (ScorePlaybackConductor.ts integrates technique data)

src/store/
└── righthand.ts                      (52 lines) - Zustand store for RH state
```

**Test Infrastructure:**
```
test-tabarranger.mjs                  (297 lines) - Standalone test script
test-tabarranger-progressions.mjs     (416 lines) - Progression tests
```

### 8.2 UI Components & User Interaction

#### 8.2.1 RefingeringModal Component

**File:** `packages/nvx1-score/src/components/RefingeringModal.tsx`

**Purpose:** Interactive modal for selecting alternative fingerings for selected passages.

**Features:**
- Generates K-best alternatives using `TabArranger.generateAlternatives()`
- Visual fretboard preview for each alternative
- Keyboard navigation (Arrow keys, Enter, Escape)
- Difficulty and cost display
- Real-time preview updates

**Usage:**
```typescript
<RefingeringModal
  notes={selectedNotes}
  skillLevel="intermediate"
  onApply={(solution) => applyFingering(solution)}
  onCancel={() => closeModal()}
  isOpen={isModalOpen}
/>
```

#### 8.2.2 TABATestPage Component

**File:** `packages/nvx1-score/src/pages/TABATestPage.tsx`

**Purpose:** Comprehensive test page for both TabArranger and RightHandArranger with live score integration.

**Features:**
- Live score integration (reads from `useNVX1Store`)
- Real-time fingering generation
- 3D hand visualization (left and right hands)
- Technique selection (auto, fingerpicking, flatpicking, strumming)
- Skill level adjustment
- Visual tablature and bridge rail display
- Performance metrics display
- Bimanual coordination preview

**Key Integration Points:**
- Extracts notes from `NVX1Score` via `normalizeTabNoteEvent()`
- Renders `TablatureLayer` and `BridgeLayer` components
- Initializes `HandModel3D` for 3D visualization
- Syncs with Hermes state (currentMeasure, currentBeat)

#### 8.2.3 TabEditorPanel Component

**File:** `src/components/NVX1/TabEditor/TabEditorPanel.tsx`

**Purpose:** Main editing controls for tablature entry.

**Features:**
- Duration selector
- Left-hand finger selector (`LHFingerSelector`)
- Articulation selector
- Auto-notation panel
- Measure/beat navigation
- Undo/redo controls

#### 8.2.4 LHFingerSelector Component

**File:** `src/components/NVX1/TabEditor/LHFingerSelector.tsx`

**Purpose:** UI for selecting left-hand finger (1, 2, 3, 4).

**Visual:** Circular buttons with finger numbers, color-coded.

#### 8.2.5 RHFingerSelector Component

**File:** `src/components/NVX1/RHFingerSelector/index.tsx`

**Purpose:** UI for selecting right-hand finger (p, i, m, a) or strum direction (↓, ↑).

**Features:**
- Finger buttons (p, i, m, a) with color coding
- Strum arrow buttons (down/up)
- Rotation toggle for arrow direction

### 8.3 Bridge Layer System (Right-Hand Display)

#### 8.3.1 BridgeLayer Component

**File:** `src/components/novaxe-figma/BridgeLayer.tsx` (395 lines)

**Purpose:** Renders right-hand notation (strumming arrows or P-I-M-A letters) on the bridge rail.

**Features:**
- Dual-mode rendering:
  - **Strumming Mode:** Directional arrows (▼, ⇓, ⇑, ▲) with emphasis encoding
  - **Fingerstyle Mode:** Letter notation (p, i, m, a) above strings
- Click-to-play integration (plays corresponding tab notes)
- Playhead synchronization
- Measure-based positioning
- Visual state (past/active/future) for animations

**Event Types:**
```typescript
interface BridgeStrumEvent {
  eventType: 'strum';
  eventId: number;
  posInMeasure: number;    // 0-3840 (960 PPQ × 4 beats)
  isUp: boolean;           // false=down, true=up
  isWeak: boolean;         // false=strong, true=weak
  isMiss: boolean;         // false=hit, true=muted
  emphasis?: 'strong' | 'weak' | 'accent';
  measureIdx?: number;
}

interface BridgeFingerEvent {
  eventType: 'rh';
  eventId: number;
  posInMeasure: number;
  rh: { finger: 'p' | 'i' | 'm' | 'a' };
  string?: number;         // 1-6
  measureIdx?: number;
}
```

#### 8.3.2 Bridge Pattern Library

**File:** `src/utils/novaxe-figma/bridgePatterns.ts` (407 lines)

**Purpose:** 15+ preset strumming and fingerpicking patterns.

**Pattern Categories:**
- **Basic:** Whole note, half notes, quarter notes, eighth notes
- **Folk:** Folk basic (D-D-U-U), waltz, country strum
- **Rock:** Rock classic (D-DU-UDU), power, alt rock
- **Fingerstyle:** Travis picking, arpeggio, classical
- **Jazz:** Jazz swing, jazz comp
- **Latin:** Bossa nova, reggae

**Pattern Structure:**
```typescript
interface BridgePattern {
  id: string;
  name: string;
  category: 'basic' | 'folk' | 'rock' | 'jazz' | 'latin' | 'fingerstyle';
  beatsPerMeasure: number;
  pattern: StrumBeat[];
  visual: string;          // Visual preview
  description: string;
  icon: string;
}
```

**Functions:**
- `patternToEvents()` - Converts pattern to RH events
- `getPatternsByCategory()` - Filters by category
- `applyPatternToAllMeasures()` - Applies pattern to entire score
- `applyPatternToMeasure()` - Applies to single measure

#### 8.3.3 Bridge Auto-Generation Algorithm

**File:** `src/utils/novaxe-figma/bridgeAutoGeneration.ts` (306 lines)

**Purpose:** Automatically generates right-hand notation from left-hand tablature.

**Algorithm:**
1. **Analyze Tablature:**
   - Detect pattern type (strumming vs fingerstyle)
   - Calculate rhythm resolution (whole, half, quarter, eighth, sixteenth)
   - Count average notes per position (chords vs single notes)

2. **Generate Pattern:**
   - **Strumming:** Creates strum events at regular intervals based on rhythm
   - **Fingerstyle:** Maps strings to fingers (P→bass, I→G, M→B, A→E1)

3. **Pattern Matching:**
   - Matches detected rhythm to preset patterns
   - Suggests best pattern ID (e.g., 'folk-basic', 'rock-classic')

**Functions:**
- `analyzeTabNotes()` - Analyzes tablature structure
- `autoGenerateRH()` - Main auto-generation function
- `generateStrummingPattern()` - Creates strum events
- `generateFingerstylePattern()` - Creates finger events

#### 8.3.4 RightHandMenuService

**File:** `src/services/input/RightHandMenuService.ts` (295 lines)

**Purpose:** Service for entering and editing right-hand patterns.

**Features:**
- Enter strum patterns (p/i/m/a)
- Toggle barre chords
- Auto-generate patterns from left-hand tablature
- Pattern entry at specific measure/beat positions

**Methods:**
- `enterStrumPattern()` - Enter pattern at position
- `toggleBarre()` - Toggle barre chord
- `autoGeneratePattern()` - Auto-generate from measures
- `getEntriesForMeasure()` - Get entries for measure

#### 8.3.5 RightHand Store

**File:** `src/store/righthand.ts` (52 lines)

**Purpose:** Zustand store for managing right-hand fingering state.

**State:**
```typescript
interface RightHandStore {
  currentFingering: string[];              // Current selection
  fingerings: Record<string, string[]>;     // "measureIdx-beatIdx" → fingers
  setCurrentFingering: (fingers: string[]) => void;
  setFingeringForBeat: (m: number, b: number, f: string[]) => void;
  getFingeringForBeat: (m: number, b: number) => string[];
  clearFingering: (m: number, b: number) => void;
}
```

### 8.4 Supporting Services & Generators

#### 8.4.1 TechniqueSelector

**File:** `packages/nvx1-score/src/fingering/rightHand/TechniqueSelector.ts` (478 lines)

**Purpose:** Automatically selects appropriate right-hand technique based on musical context.

**Selection Logic:**
- **Fingerpicking:** Arpeggios, classical, slow/medium tempo (< 120 BPM)
- **Flatpicking:** Power chords, fast passages, rock/metal (> 140 BPM)
- **Strumming:** Chord progressions, rhythm patterns
- **Hybrid:** Complex pieces requiring multiple techniques

**Features:**
- Context analysis (tempo, note density, hasArpeggios, hasPowerChords)
- Confidence scoring (0-1)
- Reasoning generation (explains why technique was selected)

#### 8.4.2 FingerpickingGenerator

**File:** `packages/nvx1-score/src/fingering/rightHand/FingerpickingGenerator.ts` (504 lines)

**Purpose:** Generates P-I-M-A fingerpicking patterns.

**Features:**
- String assignment rules (P→bass, I→G, M→B, A→E1)
- Common pattern matching (P-I-M-A, P-A-M-I, Travis picking)
- Pattern detection from generated fingerings
- Rule-based fallback if no pattern matches

#### 8.4.3 FlatpickingGenerator

**File:** `packages/nvx1-score/src/fingering/rightHand/FlatpickingGenerator.ts` (468 lines)

**Purpose:** Generates pick direction patterns (alternate, economy, sweep).

**Features:**
- **Alternate Picking:** Down-up-down-up (minimizes hand movement)
- **Economy Picking:** Same direction on string changes
- **Sweep Picking:** Continuous motion for fast arpeggios
- String skipping detection and optimization

#### 8.4.4 StrummingGenerator

**File:** `packages/nvx1-score/src/fingering/rightHand/StrummingGenerator.ts` (495 lines)

**Purpose:** Generates strumming patterns (D-U-M patterns).

**Features:**
- Rhythm extraction from MIDI/timing
- Pattern classification (D-D-U-D-U, D-U-D-U, etc.)
- Accent detection (strong beats)
- Muted strum detection (palm mutes)
- Flamenco rasgueado patterns

#### 8.4.5 CostCalculator

**File:** `packages/nvx1-score/src/fingering/rightHand/CostCalculator.ts` (421 lines)

**Purpose:** Calculates cost for right-hand fingering solutions.

**8-Component Cost Function:**
1. Finger movement cost (penalize large jumps)
2. Pattern consistency bonus (reward common patterns)
3. Timing accuracy penalty
4. Finger independence penalty (80ms minimum)
5. String reach penalty (finger-to-string mismatches)
6. Technique appropriateness bonus
7. Hand position penalty (awkward wrist angles)
8. Fatigue penalty (rapid repetition)

#### 8.4.6 VoiceLeadingOptimizer

**File:** `packages/nvx1-score/src/fingering/VoiceLeadingOptimizer.ts` (288 lines)

**Purpose:** Optimizes voice leading for smooth chord progressions.

**Features:**
- Analyzes pitch movement between chords
- Calculates physical movement (fret distance)
- Counts position shifts
- Generates quality score (0-100)

**Methods:**
- `analyzeVoiceLeading()` - Analyzes two solutions
- `analyzeProgression()` - Analyzes entire progression
- `optimizeProgression()` - Optimizes for minimal movement

### 8.5 Data & Configuration Files

#### 8.5.1 Tunings Database

**File:** `packages/nvx1-score/src/fingering/datasets/tunings.json`

**Contents:** 13 guitar tunings:
- Standard (E2-A2-D3-G3-B3-E4)
- Drop D, Drop C
- DADGAD, Open G, Open D, Open C
- And more...

**Structure:**
```json
{
  "tunings": {
    "standard": {
      "name": "Standard Tuning",
      "strings": [40, 45, 50, 55, 59, 64],
      "notes": ["E2", "A2", "D3", "G3", "B3", "E4"],
      "description": "...",
      "tags": ["beginner", "common", "standard"]
    }
  }
}
```

#### 8.5.2 Common Voicings Database

**File:** `packages/nvx1-score/src/fingering/datasets/common-voicings.json`

**Contents:** 50+ chord shapes with fingerings:
- Open chords (C, G, D, Am, Em, etc.)
- Barre chords (F, B, etc.)
- Jazz voicings (Cmaj7, Dm7, G7, etc.)

**Structure:**
```json
{
  "chords": {
    "C": [{
      "name": "Open C",
      "fingering": [
        { "string": 5, "fret": 3, "finger": 3 },
        { "string": 4, "fret": 2, "finger": 2 },
        ...
      ],
      "position": 0,
      "difficulty": 2,
      "tags": ["open", "beginner", "common"]
    }]
  }
}
```

#### 8.5.3 User Rules

**File:** `packages/nvx1-score/src/fingering/datasets/user-rules.md`

**Purpose:** User customization rules for fingering algorithm.

**Sections:**
- Custom constraints (preferred positions, injury avoidance)
- Chord overrides (custom voicings)
- Style preferences (jazz, blues, classical, rock)
- Complexity thresholds (when to simplify)
- Custom weights (override cost function)
- Position preferences (open, low, mid, high)

### 8.6 Integration Points

#### 8.6.1 TablatureLayer Integration

**File:** `src/components/novaxe-figma/TablatureLayer.tsx` (620 lines)

**Finger Symbol Rendering:**
- **Beginner Mode:** Colored finger dots (1=blue, 2=green, 3=orange, 4=red)
- **Advanced Mode:** Triangular notches (spatial encoding)

**Code:**
```typescript
// Lines 554-578: Beginner mode finger dots
{displayMode === 'beginner' && note.finger > 0 && (
  <g transform="translate(0, 28)">
    <circle r="12" fill={`url(#finger-${note.finger}-gradient)`} />
    <text>{note.finger}</text>
  </g>
)}

// Lines 580-615: Advanced mode triangular notches
{displayMode === 'advanced' && note.finger === 1 && (
  <use href="#finger1lh" fill="#ffffff" />
)}
```

#### 8.6.2 ScorePlaybackConductor Integration

**File:** `src/services/ScorePlaybackConductor.ts`

**Purpose:** Extracts technique metadata from score for playback and 3D hand control.

**Technique Data Extraction:**
```typescript
interface ScoreNote {
  pitch: number;
  string: number;
  fret: number;
  finger: string;        // "1", "2", "3", "4", "T"
  technique?: {
    string: number;
    fret: number;
    finger: string;
    rhFinger?: string;   // "p", "i", "m", "a"
  };
}
```

**Event Emission:**
- Emits `midi:noteon` events with `technique` field
- `GlobalMidiEventBus` receives events
- 3D hand models subscribe to events

#### 8.6.3 HandModel3D Integration

**File:** `packages/nvx1-score/src/fingering/3d/HandModel3D.ts`

**Purpose:** TypeScript bridge to Rust WASM 3D hand renderer.

**Methods:**
- `initialize()` - Loads WASM module
- `applyLeftHandFingering()` - Converts fingering to joint angles
- `applyRightHandFingering()` - Converts RH fingering to joint angles
- `render()` - Calls WASM renderer
- `getJointPositions()` - Retrieves current joint positions

**Integration Flow:**
```
TabArranger → FingeringSolution → HandModel3D.applyLeftHandFingering() → IK Solver → 3D Animation
RightHandArranger → RightHandSolution → HandModel3D.applyRightHandFingering() → IK Solver → 3D Animation
```

#### 8.6.4 PhysicalValidator Integration

**File:** `packages/nvx1-score/src/fingering/3d/PhysicalValidator.ts` (531 lines)

**Purpose:** Validates fingering solutions against 3D biomechanical model.

**Validation Checks:**
- Finger span (3D distance between furthest fingers)
- Finger reach (can finger reach fret position?)
- Thumb position (behind neck)
- Joint angle limits
- Bimanual coordination (hands don't collide)
- String reach (right-hand fingers can reach strings?)

**Returns:**
```typescript
interface PhysicalValidationResult {
  isValid: boolean;
  errors: string[];
  warnings: string[];
  difficulty: number; // 0-10 (biomechanically validated)
  details: {
    leftHandValid: boolean;
    rightHandValid: boolean;
    noCollisions: boolean;
    withinJointLimits: boolean;
    reachable: boolean;
  };
}
```

### 8.7 Test Infrastructure

#### 8.7.1 Standalone Test Scripts

**Files:**
- `test-tabarranger.mjs` (297 lines)
- `test-tabarranger-progressions.mjs` (416 lines)

**Purpose:** Bypass Vitest to directly test algorithms.

**Test Coverage:**
- Single note fingering
- Two-note sequences
- C major triad
- C major scale
- Chord progressions (I-V-vi-IV, 12-bar blues, jazz ii-V-I)
- Skill level adaptation
- Constraint validation

#### 8.7.2 Vitest Test Suite

**File:** `packages/nvx1-score/src/fingering/__tests__/TabArranger.test.ts`

**Test Categories:**
- Basic functionality
- Skill level adaptation
- Constraint validation
- Performance metrics

### 8.8 Complete API Surface

#### 8.8.1 TabArranger API

```typescript
class TabArranger {
  constructor(config?: Partial<Constraints>);
  
  // Main methods
  generateFingerings(notes: Note[]): FingeringResult;
  generateAlternatives(notes: Note[], k: number): FingeringSolution[];
  generateChordFingering(chord: Chord): FingeringResult;
  
  // Configuration
  loadUserRules(rulesPath: string): Promise<void>;
  setConstraints(constraints: Partial<Constraints>): void;
  setWeights(weights: Partial<CostWeights>): void;
}
```

#### 8.8.2 RightHandArranger API

```typescript
class RightHandArranger {
  constructor(config?: Partial<RightHandConstraints>);
  
  // Main methods
  arrange(notes: Note[], leftHandFingering?: Fingering[], tempo?: number): RightHandFingeringResult;
  
  // Pattern generation (internal, but accessible)
  generateFingerpicking(notes: Note[], leftHand?: Fingering[]): RightHandFingering[];
  generateFlatpicking(notes: Note[], leftHand?: Fingering[]): RightHandFingering[];
  generateStrumming(notes: Note[], leftHand?: Fingering[], timeSignature?: [number, number]): RightHandFingering[];
}
```

#### 8.8.3 Bridge System API

```typescript
// Pattern library
export const BRIDGE_PATTERNS: BridgePattern[];
export function patternToEvents(pattern: BridgePattern, measureIdx: number, startEventId: number): RHEvent[];
export function getPatternsByCategory(category: string): BridgePattern[];

// Auto-generation
export function autoGenerateRH(tabNotes: TabNote[], measureCount: number): { events: BridgeRenderableEvent[], analysis: AnalysisResult };
export function applyPatternToAllMeasures(patternId: string, measureCount: number): BridgeRenderableEvent[];
export function applyPatternToMeasure(patternId: string, measureIdx: number): BridgeRenderableEvent[];
```

---

## Related Files

### Core Algorithms
- `packages/nvx1-score/src/fingering/TabArranger.ts` - Main left-hand algorithm (955 lines)
- `packages/nvx1-score/src/fingering/WillingSacrifice.ts` - Complexity reducer (380 lines)
- `packages/nvx1-score/src/fingering/rightHand/RightHandArranger.ts` - Main right-hand algorithm (761 lines)
- `packages/nvx1-score/src/fingering/rightHand/TechniqueSelector.ts` - Technique selection (478 lines)
- `packages/nvx1-score/src/fingering/rightHand/FingerpickingGenerator.ts` - P-I-M-A patterns (504 lines)
- `packages/nvx1-score/src/fingering/rightHand/FlatpickingGenerator.ts` - Pick direction (468 lines)
- `packages/nvx1-score/src/fingering/rightHand/StrummingGenerator.ts` - Strumming patterns (495 lines)
- `packages/nvx1-score/src/fingering/rightHand/CostCalculator.ts` - Cost function (421 lines)
- `packages/nvx1-score/src/fingering/VoiceLeadingOptimizer.ts` - Voice leading (288 lines)
- `packages/nvx1-score/src/fingering/3d/PhysicalValidator.ts` - Biomechanical validation (531 lines)

### UI Components
- `packages/nvx1-score/src/components/RefingeringModal.tsx` - Alternative fingering selector (302 lines)
- `packages/nvx1-score/src/pages/TABATestPage.tsx` - Comprehensive test page (1614 lines)
- `src/components/NVX1/TabEditor/TabEditorPanel.tsx` - Main editing controls (191 lines)
- `src/components/NVX1/TabEditor/LHFingerSelector.tsx` - Left-hand finger selector (61 lines)
- `src/components/NVX1/RHFingerSelector/index.tsx` - Right-hand finger selector (107 lines)
- `src/components/novaxe-figma/TablatureLayer.tsx` - Tablature rendering (620 lines)
- `src/components/novaxe-figma/BridgeLayer.tsx` - Bridge rail rendering (395 lines)

### Bridge System
- `src/utils/novaxe-figma/bridgePatterns.ts` - Pattern library (407 lines)
- `src/utils/novaxe-figma/bridgeAutoGeneration.ts` - Auto-generation (306 lines)
- `src/services/input/RightHandMenuService.ts` - Pattern entry service (295 lines)
- `src/store/righthand.ts` - Zustand store (52 lines)

### Documentation
- `docs/brain/10-architecture/TABARRANGER_ARCHITECTURE.md` - Detailed architecture
- `docs/brain/10-architecture/RIGHTHAND_AND_3D_MODEL_RESEARCH.md` - Research foundation
- `docs/reports/status/BRIDGE_RIGHT_HAND_SYSTEM_RESEARCH.md` - Bridge system analysis

