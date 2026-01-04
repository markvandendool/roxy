# Phase 3.1 Architecture Decision: RSC for Vite/React Router

**Date:** 2025-12-09  
**Phase:** 3.1 - RSC Integration  
**Status:** ✅ Implementation Complete

---

## Context

The SongVault Upgrade Plan v2.1.0 specifies React Server Components (RSC) for Phase 3.1, which is a Next.js 14+ feature. However, the current codebase uses:

- **Vite** for bundling
- **React Router** for routing
- **SPA architecture** (client-side routing)

## Decision

**Adapt RSC patterns to work with the current Vite/React Router setup** while preparing for future Next.js migration.

### Approach

1. **Server-Side Data Fetching Layer**
   - Created `src/integrations/supabase/server-client.ts`
   - Server-safe Supabase client (no session persistence)
   - Reusable across SSR, API routes, and future Next.js migration

2. **RSC-Like Components**
   - Created `src/app/songvault/components/RSC_SongRows.tsx`
   - Created `src/app/songvault/components/RSC_Hero.tsx`
   - Async server components that fetch data server-side
   - Compatible with both Vite SSR and Next.js App Router

3. **Streaming SSR via Suspense**
   - Components use React Suspense for streaming
   - Client-side wrapper `RSC_SongRowsWithSuspense` enables progressive rendering
   - Fallback UI during data fetching

4. **Selective Hydration**
   - Server components render static HTML
   - Only interactive components (PreviewCard, CarouselRow arrows) hydrate
   - Reduces client-side JavaScript bundle

## Benefits

✅ **Works with current architecture** (Vite/React Router)  
✅ **Prepares for Next.js migration** (components can be marked 'use server')  
✅ **Performance improvements** (server-side data fetching, streaming SSR)  
✅ **Selective hydration** (reduces client bundle size)  
✅ **No breaking changes** (backward compatible with existing components)

## Migration Path to Next.js

When migrating to Next.js App Router:

1. Move `src/app/songvault/components/` to `app/songvault/components/`
2. Add `'use server'` directive to async components
3. Update imports to use Next.js `cookies()` for auth
4. Enable Next.js streaming SSR

## Files Created

- `src/integrations/supabase/server-client.ts` - Server-side Supabase client
- `src/app/songvault/components/RSC_SongRows.tsx` - Server component for song rows
- `src/app/songvault/components/RSC_Hero.tsx` - Server component for hero banner

## Next Steps

- **Phase 3.2:** Edge Search Service (Bun + Supabase Edge)
- **Phase 3.3:** CDN/Image Optimization

---

**Phase 3.1: RSC Integration — ✅ COMPLETE (Adapted for Vite)**
