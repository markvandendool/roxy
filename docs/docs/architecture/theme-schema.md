# Global Theme Schema Blueprint

*Status: Draft*  
*Owner: Frontend Platform / Rocky AI Enablement*

## Goals

- Provide a single source of truth for every visual token in the app so Rocky AI (and humans) can generate, preview, and apply complete experiences on demand.
- Support per-teacher "skins" with full coverage across core product surfaces (practice studio, marketing dashboards, onboarding flows) and especially music-specific widgets (fretboards, chord cubes, typography tests).
- Enable deterministic serialization (JSON) so themes can round-trip between the AI pipeline, Supabase persistence, and the runtime theme engine.
- Preserve accessibility (contrast, font sizing, motion sensitivity) through schema validation.

## High-Level Structure

```mermaid
graph TD
    Prompt[Rocky prompt]
    Generator[Theme Generator LLM]
    Schema[Theme JSON (this doc)]
    Validator[Schema & Accessibility Guard]
    Runtime[Theme Runtime (Context + CSS vars)]
    Widgets[UI & Musical Widgets]

    Prompt --> Generator --> Schema --> Validator --> Runtime --> Widgets
    Schema -->|Persist| Supabase
```

The **Theme JSON** is the contract between:
- Rockys generative stack
- The Supabase persistence layer
- The runtime theme context that emits CSS variables & component overrides

## Schema Overview

Top-level shape:

```ts
interface ThemeDefinition {
  id: string;                // UUID or slug generated on save
  name: string;              // Human-friendly label ("Mediterranean Sunrise")
  description?: string;      // Optional meta / Rocky notes
  version: number;           // Schema version for migrations (start at 1)
  createdBy: string;         // Teacher ID or "rocky"
  createdAt: string;         // ISO timestamp
  tags?: string[];           // e.g. ["mediterranean", "acoustic", "warm"]
  palette: PaletteTokens;
  typography: TypographyTokens;
  surfaces: SurfaceTokens;
  widgets: WidgetTokens;
  motion: MotionTokens;
  music: MusicTokens;        // Fretboards, chord cubes, notation glyphs
  assets?: AssetTokens;      // Textures, imagery, audio-reactive overlays
  accessibility: AccessibilitySettings;
  metadata?: Record<string, unknown>; // Free-form data (Rocky prompt, mood board refs)
}
```

### Palette Tokens

```ts
interface PaletteTokens {
  primary: ColorRole;
  secondary: ColorRole;
  accent: ColorRole;
  neutral: NeutralScale;
  success: ColorRole;
  warning: ColorRole;
  danger: ColorRole;
  background: {
    base: string;        // e.g. "#0f1412"
    elevated: string;
    overlay: string;
  };
  foreground: {
    base: string;
    muted: string;
    inverse: string;
  };
  gradient?: {
    hero?: GradientStop[];
    widget?: GradientStop[];
  };
}

type ColorRole = {
  base: string;
  hover: string;
  pressed: string;
  outline?: string;
  shadow?: string;
  emphasis?: string; // accent highlight, glow
};

type NeutralScale = {
  "50": string;
  "100": string;
  "200": string;
  "300": string;
  "400": string;
  "500": string;
  "600": string;
  "700": string;
  "800": string;
  "900": string;
};

interface GradientStop {
  position: number; // 0-100
  color: string;
}
```

### Typography Tokens

```ts
interface TypographyTokens {
  body: FontStack;
  display: FontStack;
  monospace: FontStack;
  musicalNotation: FontStack; // Vexflow glyphs / special ligatures
  scale: {
    xs: TypeScale;
    sm: TypeScale;
    md: TypeScale;
    lg: TypeScale;
    xl: TypeScale;
    display: TypeScale;
  };
  letterSpacing: Record<'tight' | 'normal' | 'wide', string>;
  lineHeights: Record<'compact' | 'standard' | 'comfortable', number>;
}

type FontStack = {
  family: string;   // CSS font-family string
  fallback?: string[];
  weight?: number | string; // default weight
  featureSettings?: string; // e.g. "kern" on, stylistic sets
};

type TypeScale = {
  fontSize: string;   // rem
  fontWeight: number;
  lineHeight: string; // unitless or rem
};
```

### Surface Tokens

```ts
interface SurfaceTokens {
  card: SurfaceRole;
  panel: SurfaceRole;
  modal: SurfaceRole;
  tooltip: SurfaceRole;
  borderRadius: {
    sm: string;
    md: string;
    lg: string;
    full: string;
  };
  borderWidth: {
    hairline: string;
    thin: string;
    thick: string;
  };
  shadow: {
    low: string;
    medium: string;
    high: string;
  };
}

type SurfaceRole = {
  background: string;
  border: string;
  foreground: string;
  mutedForeground?: string;
};
```

### Widget Tokens

Widget tokens provide per-component affordances while still sourcing from the global palette.

```ts
interface WidgetTokens {
  fretboard: FretboardTokens;
  sequencer: SequencerTokens;
  chordCubes: ChordCubeTokens;
  marketingDashboard: MarketingTokens;
  forms?: FormTokens;
  audioMeters?: AudioMeterTokens;
}

interface FretboardTokens {
  woodTexture?: string;            // URL or asset key
  fretWire: string;
  stringColor: string;
  inlayColor: string;
  noteFillRoot: string;
  noteFillThird: string;
  noteFillFifth: string;
  noteFillSeventh: string;
  noteStroke: string;
  octaveHighlight: string;
  pentatonicOverlay: string;
  font: string;                    // overrides for fret labels
}

interface SequencerTokens {
  gridBackground: string;
  activeStep: string;
  inactiveStep: string;
  cursor: string;
  velocityHigh: string;
  velocityLow: string;
}

interface ChordCubeTokens {
  cubePrimary: string;
  cubeSecondary: string;
  wireframe: string;
  ambientLight: string;
  specularHighlight: string;
  labelColor: string;
}

interface MarketingTokens {
  heroBackground: string;
  chartPrimary: string;
  chartSecondary: string;
  tooltipBackground: string;
}
```

### Motion Tokens

```ts
interface MotionTokens {
  easing: {
    standard: string;   // e.g. "cubic-bezier(0.4, 0, 0.2, 1)"
    emphasized: string;
    exit: string;
  };
  durations: {
    fast: number;  // ms
    medium: number;
    slow: number;
  };
  transforms: {
    hoverScale: number;
    pressScale: number;
  };
  prefersReducedMotion: boolean; // allow Rocky to honor accessibility prompts
}
```

### Music Tokens

```ts
interface MusicTokens {
  glyphSet: {
    name: string;                      // "Solfege DoMiSol"
    root: string;
    third: string;
    fifth: string;
    seventh: string;
    sharp: string;
    flat: string;
    octave?: string;
  };
  noteheads: {
    fill: string;
    stroke: string;
    glow: string;
  };
  chordDiagrams: {
    dotFill: string;
    dotStroke: string;
    stringColor: string;
    fretMarker: string;
  };
  staff: {
    lineColor: string;
    ledgerLineColor: string;
    barlineColor: string;
  };
  audioReactivity?: {
    spectrumGradient: GradientStop[];
    tempoPulseColor: string;
  };
}
```

### Asset Tokens (Optional)

```ts
interface AssetTokens {
  textures?: Array<{
    id: string;
    type: 'image' | 'video';
    url: string;
    usage: Array<'background' | 'fretboard' | 'panel'>;
    blendMode?: string;
    opacity?: number;
  }>;
  illustrations?: Array<{
    id: string;
    url: string;
    description?: string;
  }>;
}
```

### Accessibility Settings

```ts
interface AccessibilitySettings {
  minimumContrast: number; // WCAG ratio target (e.g. 4.5)
  scaleMultiplier: number; // base font scaling multiplier (1 = default)
  highContrastMode?: boolean;
  reduceMotion?: boolean;
}
```

## Serialization & Storage

- Each saved skin is represented by a row in `teacher_theme_variants` keyed to the owning profile (`profile_id`). Variants carry human labels, status (`draft` | `preview` | `published`), schema version, optional metadata, and pointer to the active version.
- Concrete theme JSON lives in `teacher_theme_versions`. Every mutation creates a new version row containing the serialized `ThemeDefinition`, lineage metadata (author, change summary), and publication timestamp when elevated.
- Trigger `enforce_published_variant_has_version` ensures a published variant always references at least one version, and `promote_active_theme_version` flips the `active_version_id` when a version’s status becomes `published`.
- Local caching (browser `localStorage`) stores the most recently applied theme per user under `msm/theme/active`. Runtime hydrate falls back to the cache when Supabase is offline and backfills once the network recovers.
- Rocky still stamps prompt metadata into the version `metadata` column for explainability and regenerations.

## CSS Variable Naming

At runtime, the theme context emits CSS custom properties scoped to `:root` or a `.theme-[id]` wrapper. Suggested naming convention:

```
--ms-theme-color-primary-base
--ms-theme-color-primary-hover
--ms-theme-typography-body-font-family
--ms-theme-widget-fretboard-note-root
--ms-theme-music-glyph-root
--ms-theme-motion-duration-fast
```

Components read these through a helper hook `useThemeToken('widget.fretboard.noteFillRoot')` or Tailwind plugin mapping.

## Runtime Integration

- `src/styles/theme-persistence.ts` exposes the contract for loading the active variant (`loadActiveThemeForUser`), listing available variants, and saving new ones. It normalizes IDs, maintains the cache, and guarantees a `ThemeDefinition` payload regardless of source (remote, cache, default).
- `useThemeSkinStore` (Zustand) sits at the boundary between auth and theming. On sign-in the store hydrates the active variant, tracks loading/error state, and exposes actions the Aesthetics Studio will call when teachers publish new skins.
- `ThemeProvider` consumes the store: once auth resolves, it fetches the user’s active skin, applies CSS custom properties, and resets to the default theme when the session ends. Hydration guards ensure SSR-provided `initialTheme` values are not clobbered before the remote load completes.
- On network failures the provider falls back to cached themes and records the source (`default`, `cache`, `remote`) for debugging.

## Validation & Guardrails

1. **Schema validation**: Zod/TypeScript types ensure generated JSON matches the contract.
2. **Color contrast checks**: Automatic evaluation of critical pairs (foreground/background, note fill vs. fretboard) using WCAG algorithms.
3. **Fallbacks**: If a token is missing/invalid, fall back to base theme or nearest neutral.
4. **Asset sanitization**: Ensure assets meet size/format constraints; CDN-signed URLs only.

## Sample Theme JSON (excerpt)

```json
{
  "id": "theme_mediterranean_sunrise",
  "name": "Mediterranean Sunrise",
  "version": 1,
  "createdBy": "teacher_123",
  "palette": {
    "primary": {
      "base": "#d97706",
      "hover": "#ea580c",
      "pressed": "#c2410c",
      "shadow": "rgba(217, 119, 6, 0.4)"
    },
    "secondary": {
      "base": "#0e7490",
      "hover": "#0f766e",
      "pressed": "#115e59"
    },
    "neutral": {
      "50": "#f8fafc",
      "100": "#f1f5f9",
      "200": "#e2e8f0",
      "300": "#cbd5f5",
      "400": "#94a3b8",
      "500": "#64748b",
      "600": "#475569",
      "700": "#334155",
      "800": "#1e293b",
      "900": "#0f172a"
    },
    "background": {
      "base": "#fdf6ec",
      "elevated": "#f6e8d5",
      "overlay": "rgba(15, 23, 42, 0.5)"
    },
    "foreground": {
      "base": "#1f2937",
      "muted": "#475569",
      "inverse": "#f8fafc"
    }
  },
  "music": {
    "glyphSet": {
      "name": "Solfege Terra",
      "root": "Do",
      "third": "Mi",
      "fifth": "Sol",
      "seventh": "Ti",
      "sharp": "♯",
      "flat": "♭"
    },
    "noteheads": {
      "fill": "#f97316",
      "stroke": "#b45309",
      "glow": "rgba(249, 115, 22, 0.55)"
    },
    "chordDiagrams": {
      "dotFill": "#0ea5e9",
      "dotStroke": "#0369a1",
      "stringColor": "#115e59",
      "fretMarker": "#f59e0b"
    },
    "staff": {
      "lineColor": "#0f172a",
      "ledgerLineColor": "#0e7490",
      "barlineColor": "#1e293b"
    }
  }
}
```

## Next Steps

1. **Finalize schema review** with frontend + design + Rocky AI teams.
2. **Generate TypeScript types** (`theme-schema.ts`) + Zod validator from this blueprint.
3. **Implement theme context** exposing `ThemeDefinition` to React components.
4. **Instrument Rocky AI prompts** to produce compliant JSON plus metadata.
5. **Define Supabase migrations** for `themes` and linkage tables.

---

*Document maintained by the Theming Platform working group. Propose changes via PRs or design reviews.*
