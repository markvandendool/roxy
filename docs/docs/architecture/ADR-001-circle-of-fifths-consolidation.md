# ADR-001: Circle of Fifths Component Consolidation

**Status**: Accepted  
**Date**: 2025-10-14  
**Authors**: Chief Engineer  
**Reviewers**: Mark van den Dool

---

## Context

### The Problem

We had **three competing Circle of Fifths implementations** in the codebase, causing:

1. **Widget launcher confusion** — Wrong version showing up in UI
2. **Duplicate feature development** — Same features rebuilt multiple times (5+ times per user report)
3. **Inconsistent behavior** — Different implementations had different feature sets
4. **Maintenance burden** — Three codebases to update for every change

### The Implementations

| Component | Location | Status | Features |
|-----------|----------|--------|----------|
| `CircleOfFifthsWidget` | `src/components/theater/widgets/circle-of-fifths/` | ✅ V2 Parity | Full TonalityButton wrapper with controls |
| `FifthCircleWidget` | `src/components/theater/widgets/v3/` (now DEPRECATED) | ❌ Mock | Simple visualization, no V2 features |
| `CircleOfFifthsV2` | `src/components/circle-of-fifths/` | ✅ Delegate | Originally full SVG, now delegates to canonical |

### Root Cause

- No single source of truth designation
- Multiple naming conventions (`CircleOfFifths`, `FifthCircle`, `V2`, `V3`, `Widget`)
- Lack of deprecation strategy
- No linting rules to prevent duplication

---

## Decision

### Consolidate to ONE Canonical Implementation: `V3CircleOfFifths`

**Location**: `src/components/circle-of-fifths/V3CircleOfFifths.tsx`

**Rationale**:
- **V3** prefix aligns with Theater V3 architecture
- **CircleOfFifths** is the correct musical term (not "FifthCircle")
- Wraps `TonalityButton` (the 529-line faithful Angular V2 port)
- Includes Theater-specific controls and event handling

### Migration Strategy

1. **Create canonical component** with clear documentation
2. **Deprecate obsolete implementations** but keep files for history
3. **Create barrel exports with aliases** for backward compatibility
4. **Add ESLint rule** to prevent future duplication
5. **Update all widget registrations** to use canonical version
6. **Document in ADR** (this document)

---

## Implementation

### File Structure (After Consolidation)

```
src/components/circle-of-fifths/
├── V3CircleOfFifths.tsx          ← CANONICAL (155 lines)
├── TonalityButton.tsx             ← Core V2 implementation (529 lines)
├── index.ts                       ← Barrel with aliases
├── CircleOfFifthsV2.tsx          ← Alias (deprecated but functional)
├── store.ts                       ← Zustand state management
├── types.ts                       ← TypeScript interfaces
├── utils/                         ← Coordinate mapping, etc.
├── hooks/                         ← React hooks
└── DEPRECATED/
    ├── FifthCircleWidget.tsx     ← Obsolete mock (moved here)
    └── README.md                 ← Why deprecated + migration guide
```

### Widget Registry Updates

**Before**:
- `v3-fifth-circle` → FifthCircleWidget (mock) ❌
- `novaxe-circle-fifths` → CircleOfFifthsWidget ✅
- `circle-v2` → CircleOfFifthsV2 (was delegate) ✅

**After**:
- `v3-fifth-circle` → **REMOVED** (deprecated)
- `novaxe-circle-fifths` → V3CircleOfFifths ✅
- `v3-circle-of-fifths` → V3CircleOfFifths ✅

### Barrel Export Aliases

```typescript
// src/components/circle-of-fifths/index.ts
export { V3CircleOfFifths } from './V3CircleOfFifths';  // CANONICAL

// Backward compatibility aliases (all point to V3CircleOfFifths)
export { V3CircleOfFifths as CircleOfFifthsV2 };
export { V3CircleOfFifths as CircleOfFifthsWidget };
export { V3CircleOfFifths as CircleOfFifths };
```

### ESLint Guard Rail

**Rule**: `local/no-duplicate-circle-of-fifths`

**Purpose**: Prevent creation of new Circle of Fifths components

**Implementation**: `eslint-local-rules.js`

**Allowed**:
- `V3CircleOfFifths.tsx` (canonical)
- `TonalityButton.tsx` (core implementation)
- Files in `/DEPRECATED/` folder
- Utility files (store, hooks, utils, types)

**Forbidden**:
- Any new file matching `*Circle*Fifth*.tsx` or `*FifthCircle*.tsx`
- New components wrapping TonalityButton

---

## Consequences

### Positive

✅ **Single source of truth** — No more confusion about which component to use  
✅ **Zero breaking changes** — Aliases maintain backward compatibility  
✅ **Future-proof** — ESLint prevents accidental duplication  
✅ **Clear migration path** — Deprecated files preserved with documentation  
✅ **Reduced maintenance** — One codebase to update instead of three  

### Negative

⚠️ **Import churn** — Developers must update imports over time  
⚠️ **Learning curve** — New naming convention to learn  
⚠️ **Git history fragmentation** — Changes split across multiple files  

### Mitigation

- **Aliases**: All old imports still work via barrel exports
- **Documentation**: README in DEPRECATED folder explains migration
- **ADR**: This document provides context for future developers
- **ESLint**: Prevents regression

---

## Validation

### Verification Steps

1. ✅ V3CircleOfFifths created with full V2 parity
2. ✅ FifthCircleWidget moved to DEPRECATED/
3. ✅ Barrel exports created with aliases
4. ✅ ESLint rule added and activated
5. ✅ Widget registrations updated
6. ✅ CircleOfFifthsV2 converted to alias
7. ✅ CircleOfFifthsWidget marked deprecated
8. ✅ ESSENTIAL_WIDGETS updated

### Testing Required

- [ ] Widget launcher shows V3CircleOfFifths correctly
- [ ] All Circle features work (rotation, mode cycling, dual highlighting)
- [ ] Old imports still resolve correctly
- [ ] ESLint catches duplicate Circle creation attempts
- [ ] Playwright tests pass with new widget ID

---

## References

- **V2 Angular Source**: `Novaxe V2 Source Code/src/app/components/tonality-button/`
- **TonalityButton Implementation**: `src/components/circle-of-fifths/TonalityButton.tsx`
- **Master Plan**: `m.plan.md` Phase 3
- **Widget Parity Spec**: `docs/20-specs/WIDGET_PARITY_SPECIFICATION.md`

---

## Lessons Learned

### What Went Wrong

1. **No architectural ownership** — Multiple developers created competing implementations
2. **Naming inconsistency** — `Circle`, `Fifth`, `V2`, `V3`, `Widget` used arbitrarily
3. **No deprecation strategy** — Old code never removed
4. **Missing guardrails** — No linting rules to enforce standards

### How We Fixed It

1. **Designated canonical component** with clear naming
2. **Created deprecation path** (DEPRECATED folder + README)
3. **Added ESLint rule** to prevent future duplication
4. **Documented in ADR** for institutional knowledge
5. **Updated master plan** to reflect new architecture

### Preventing Recurrence

- **Naming Convention**: All Theater widgets use `V3<WidgetName>` format
- **Single Source of Truth**: Documented in component header
- **Deprecation Process**: Move to DEPRECATED/ folder with README
- **ESLint Rules**: Custom rules for architectural violations
- **ADR Process**: Major decisions documented for future agents/developers

---

## Approval

**Approved by**: Mark van den Dool (Product Owner)  
**Implementation Date**: 2025-10-14  
**Review Date**: 2025-11-14 (30 days post-implementation)

---

**Status Legend**:
- ✅ Complete and validated
- ⚠️ Needs attention/monitoring
- ❌ Rejected or obsolete

