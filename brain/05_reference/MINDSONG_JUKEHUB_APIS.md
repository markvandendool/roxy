# 🎵 Mindsong Juke Hub - API Integration Reference

**Date**: January 2, 2026  
**Purpose**: Document existing APIs in mindsong-juke-hub for CITADEL integration

---

## 🔍 Discovered APIs & Integrations

### 1. Supabase CRM Integration ✅
**Location**: `src/integrations/supabase/`  
**Used By**: All CRM components

**Tables Used**:
- `crm_contacts` - Contact management
- `crm_deals` - Deal management (likely)
- Other CRM tables (workflows, activities, etc.)

**Components Using Supabase**:
- `src/components/crm/ContactsManager.tsx`
- `src/components/crm/DealsManager.tsx`
- `src/components/crm/CRMAnalytics.tsx`
- `src/components/crm/WorkflowsManager.tsx`
- And many more CRM components

**Configuration**:
```typescript
// src/integrations/supabase/client.ts
SUPABASE_URL = 'https://rlbltiuswhlzjvszhvsc.supabase.co'
SUPABASE_ANON_KEY = (from env or fallback)
```

**Usage Pattern**:
```typescript
import { supabase } from "@/integrations/supabase/client";

const { data, error } = await supabase
  .from("crm_contacts")
  .select("*")
  .order("created_at", { ascending: false });
```

---

### 2. Rocky Score Search API ✅
**Location**: `src/pages/api/rocky/search-scores.ts`  
**Endpoint**: `POST /api/rocky/search-scores`

**Purpose**: Search scores from FolkRNN database

**Request Body**:
```json
{
  "key": "D major",
  "meter": "6/8",
  "rhythm": "...",
  "title": "...",
  "limit": 10
}
```

**Response**:
```json
{
  "success": true,
  "results": [...],
  "message": "..."
}
```

---

### 3. Rocky Load Score API ✅
**Location**: `src/pages/api/rocky/load-score.ts`  
**Endpoint**: `POST /api/rocky/load-score`

**Purpose**: Load a specific score

---

### 4. Score Loader API ✅
**Location**: `src/api/score-loader.ts`

**Purpose**: Score loading functionality

---

## 📊 Pages & Components

### CRM Pages
- `src/pages/CRMCrawlerPage.tsx` - CRM crawler interface
- `src/components/crm/` - Full CRM component suite

### Dashboard Pages
- `src/pages/Dashboard.tsx` - Main dashboard
- `src/pages/ProgressDashboard.tsx` - Progress tracking
- `src/components/dashboard/` - Dashboard components
  - `QuickPracticeSection.tsx`
  - `SkillTreeWidget.tsx`
  - `UpcomingLessons.tsx`
  - `CalendlyEmbed.tsx`

### Student/Education Pages
- `src/pages/Lessons.tsx` - Lesson management
- `src/pages/TeacherLessons.tsx` - Teacher lesson view
- `src/pages/TeacherHub.tsx` - Teacher hub
- `src/pages/ProgressDashboard.tsx` - Student progress

### Other Pages
- `src/pages/Profile.tsx` - User profile
- `src/pages/Calendar.tsx` - Calendar view
- `src/pages/SongVault.tsx` - Song vault
- `src/pages/Auth.tsx` - Authentication

---

## 🔧 Services

**Location**: `src/services/`

**Key Services**:
- `src/services/APES/dashboard/` - Dashboard sync service
- `src/services/orchestration/` - Workflow orchestration
- `src/services/education/` - Education services
- `src/services/tutor/` - Tutor services
- `src/services/telemetry/` - Telemetry
- And many more...

---

## 🔗 Integration Points for CITADEL

### Business MCP Server ✅
**Updated**: Now uses Supabase (same as mindsong-juke-hub)

**Tools Available**:
- `crm_create_contact` - Create contact in Supabase CRM
- `business_get_contacts` - Get contacts from Supabase CRM
- `plane_create_issue` - Create Plane project issue
- `chatwoot_send_message` - Send Chatwoot message

**Configuration**:
```bash
# Use same Supabase credentials as mindsong-juke-hub
SUPABASE_URL=https://rlbltiuswhlzjvszhvsc.supabase.co
SUPABASE_ANON_KEY=your-key-here
```

---

## 📝 Notes

1. **Supabase is the primary CRM backend** - Not Twenty CRM
2. **All CRM components use Supabase** - Direct database access
3. **API routes exist** - Rocky score search/load APIs
4. **Dashboard uses Supabase** - Progress tracking, lessons, etc.
5. **Student dashboard** - Uses Supabase for data

---

## 🚀 Next Steps

1. **Test Supabase Integration**
   - Verify business MCP server can connect
   - Test contact creation/retrieval
   - Verify same credentials work

2. **Explore More APIs**
   - Check for other API routes
   - Look for external service integrations
   - Document authentication flows

3. **Integration Testing**
   - Test CRM operations via MCP
   - Verify data consistency
   - Test cross-service workflows

---

**Last Updated**: January 2, 2026  
**Status**: ✅ APIs documented, Business MCP updated

