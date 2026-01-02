# Mindsong Juke Hub - Existing API Integrations

This document catalogs all existing API integrations found in the mindsong-juke-hub repository that can be leveraged for the CITADEL epic.

## Current API Integrations

### 1. **Supabase Integration**
- **Location**: `src/integrations/supabase/`
- **Files**: 
  - `client.ts` - Client-side Supabase client
  - `server-client.ts` - Server-side Supabase client
  - `types.ts` - TypeScript types (comprehensive database schema)
- **Usage**: Database operations, authentication, real-time subscriptions
- **Key Tables Found**:
  - `ai_response_cache` - AI response caching
  - `ai_usage_logs` - AI usage tracking
  - `automation_logs` - Automation execution logs
  - `automation_workflows` - Workflow definitions
  - `automation_workflows_crm` - CRM-specific workflows
  - `campaign_sends` - Campaign tracking
  - `teacher_settings` - Teacher configuration (includes Calendly usernames)
  - Many more tables for CRM, student management, etc.
- **Relevant for CITADEL**: 
  - Can be used for storing CRM data, social media posts, business automation records
  - Existing automation tables can be leveraged for Phase 7 (Business Automation)
  - AI usage logs can inform Phase 8 (AI Excellence)

### 2. **Calendly Integration**
- **Location**: `src/lib/calendly.ts`
- **Component**: `src/components/dashboard/CalendlyEmbed.tsx`
- **Features**:
  - Calendly URL generation
  - Embed URL generation
  - Teacher-specific Calendly URLs from database
- **Relevant for CITADEL**: Business automation (Phase 7) - scheduling integration

### 3. **YouTube Integration**
- **Location**: 
  - `src/services/TransportYouTubeSyncService.ts`
  - `src/services/YouTubeService.ts` (referenced)
  - `src/pages/NovaxeTheater.tsx`
  - `src/components/media/` (YouTubePlayer, YouTubeUrlInput)
- **Features**:
  - YouTube video playback
  - Transport synchronization with YouTube playback
  - YouTube URL input component
- **Relevant for CITADEL**: Social Integration (Phase 6) - YouTube Data API v3 integration

### 4. **VCO (Virtual Contract Office) API**
- **Location**: `src/services/vco/api.ts`
- **Features**:
  - Query requests/responses
  - Chat with Claude API
  - Document ingestion
  - Report generation
  - Health checks
  - Streaming support
  - Claude API fallback
- **Relevant for CITADEL**: AI Excellence (Phase 8) - LLM integration patterns

### 5. **MuseScore API**
- **Location**: `src/services/musescore/MuseScoreAPIClient.ts`
- **Features**: MuseScore integration for music notation
- **Relevant for CITADEL**: Content pipeline (Phase 5) - potential for music content processing

### 6. **CRM Components with API Integration Points**
- **Location**: `src/components/crm/`
- **Key Components**:
  - `ContactsManager.tsx` - Contact management
  - `DealsManager.tsx` - Deal pipeline management
  - `WorkflowsManager.tsx` - Workflow automation
  - `CRMAnalytics.tsx` - Analytics dashboard
  - `analytics/ReportingDashboard.tsx` - Reporting
  - `ai/PredictiveLeadScoring.tsx` - AI-powered lead scoring
  - `ai/AIChatbotSupport.tsx` - AI chatbot
  - `ai/SentimentAnalysis.tsx` - Sentiment analysis
  - `ai/SalesForecasting.tsx` - Sales forecasting
  - `ai/AIInsightsDashboard.tsx` - AI insights
  - `integrations/CalendarScheduler.tsx` - Calendar integration
  - `integrations/AITaskManager.tsx` - AI task management
  - `integrations/EmailSync.tsx` - Email synchronization
  - `integrations/DocumentManager.tsx` - Document management
  - `integrations/MultiChannelComms.tsx` - Multi-channel communications
  - `webhooks/WebhookManager.tsx` - Webhook management
  - `quotes/QuoteProposalGenerator.tsx` - Quote generation
  - `forms/LeadCaptureFormBuilder.tsx` - Lead capture forms
  - `segments/ContactSegmentsManager.tsx` - Contact segmentation
  - `segments/AdvancedSegmentBuilder.tsx` - Advanced segmentation
  - `reports/CustomReportBuilder.tsx` - Custom reporting
  - `activities/ActivityTimeline.tsx` - Activity tracking
  - `import/ImportExportTools.tsx` - Data import/export
  - `fields/CustomFieldsManager.tsx` - Custom field management
- **Relevant for CITADEL**: 
  - Business Automation (Phase 7) - Twenty CRM integration can leverage these patterns
  - Social Integration (Phase 6) - Multi-channel communications component

### 7. **Dashboard Components**
- **Location**: `src/components/dashboard/`
- **Components**:
  - `CalendlyEmbed.tsx` - Calendly scheduling
  - `QuickPracticeSection.tsx` - Practice tracking
  - `SkillTreeWidget.tsx` - Skill progression
  - `UpcomingLessons.tsx` - Lesson scheduling
- **Relevant for CITADEL**: Student dashboard APIs can inform social integration patterns

### 8. **API Routes**
- **Location**: `src/pages/api/`
- **Routes**:
  - `rocky/search-scores.ts` - Score search API
  - `rocky/load-score.ts` - Score loading API
- **Relevant for CITADEL**: API route patterns for MCP server implementations

### 9. **Architecture API**
- **Location**: `src/components/ArchitectureMap/api/architectureApi.ts`
- **Features**: Architecture mapping API
- **Relevant for CITADEL**: Can inform API design patterns

## Integration Patterns Found

### 1. **Supabase Pattern**
- Client/server separation
- Type-safe queries
- Real-time subscriptions
- **Can be used for**: Storing all CITADEL data (CRM, social posts, business records)

### 2. **External API Pattern (VCO)**
- Environment variable configuration
- Fallback mechanisms
- Streaming support
- Error handling
- **Can be used for**: Social media APIs, business tool APIs

### 3. **Component-Based API Usage**
- React hooks for data fetching
- Component-level API integration
- **Can be used for**: MCP server tool implementations

### 4. **Service Layer Pattern**
- Service classes for API interactions
- Separation of concerns
- **Can be used for**: All CITADEL MCP servers

## Recommendations for CITADEL Integration

### Phase 6: Social Integration
1. **YouTube**: Already has YouTube integration - can extend with YouTube Data API v3 for posting, analytics
2. **Discord/Telegram**: Use similar patterns to YouTube integration
3. **Postiz**: Can leverage CRM integration patterns for social media scheduling

### Phase 7: Business Automation
1. **Twenty CRM**: Use existing CRM component patterns (`src/components/crm/`)
2. **Plane**: Can use similar patterns to CRM task management
3. **Chatwoot**: Use MultiChannelComms component as reference

### Phase 8: AI Excellence
1. **LangGraph**: Use VCO API patterns for orchestration
2. **Mem0**: Can use Supabase for persistent storage
3. **MCP Gateway**: Use existing service layer patterns

## Next Steps

1. **Examine specific CRM components** to understand API call patterns
2. **Review Supabase schema** to understand data models
3. **Check for environment variables** in `.env` files for API keys
4. **Document API endpoints** used by CRM components
5. **Create integration mapping** between existing APIs and CITADEL requirements

