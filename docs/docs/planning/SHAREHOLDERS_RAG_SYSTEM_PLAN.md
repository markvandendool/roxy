# Shareholders Agreement RAG System - Premium UI/UX Implementation Plan

> **Status:** Planning Phase  
> **Target User:** 75-year-old non-technical user  
> **Quality Standard:** AAA Premium, Fully HIG-Compliant  
> **Last Updated:** 2025-01-XX

---

## Executive Summary

This document outlines the complete implementation plan for a premium-grade RAG (Retrieval-Augmented Generation) system for analyzing a 60-page shareholders agreement. The system will feature industry-leading UI/UX, full accessibility compliance, and seamless Cursor integration.

---

## Part 1: Industry Standard Setup & Default UI Analysis

### 1.1 Existing RAG System Default UIs

#### **Streamlit Default Interface**
**What it includes out-of-the-box:**
- **Chat Input Field**: Text area with submit button
- **Chat Display Area**: Scrollable conversation history
- **File Upload Widget**: Drag-and-drop document uploader
- **Sidebar Navigation**: Collapsible sidebar for settings
- **Response Display**: Markdown-formatted responses
- **Status Indicators**: Loading spinners, progress bars
- **Basic Styling**: Clean, minimal, but utilitarian

**Limitations:**
- Limited customization without CSS injection
- No built-in PDF viewer
- Basic chat interface only
- No citation highlighting
- No report generation UI

#### **Gradio Default Interface**
**What it includes out-of-the-box:**
- **Input Components**: Text boxes, file uploaders, sliders
- **Output Components**: Text, markdown, HTML, JSON
- **Example Inputs**: Pre-filled example queries
- **Interface Builder**: Declarative component layout
- **Theme Support**: Light/dark mode toggle
- **Sharing**: Built-in shareable links

**Limitations:**
- Less polished than Streamlit for document Q&A
- No native PDF viewer
- Basic chat patterns
- Limited accessibility features

#### **LlamaIndex + Streamlit (RAGIndex Example)**
**Default Components:**
- Document upload section
- Chat interface with history
- Citation display (basic)
- Document list sidebar
- Settings panel (chunk size, model selection)

**What's Missing for Premium:**
- PDF viewer with highlights
- Advanced citation visualization
- Report builder interface
- Accessibility features
- Professional typography
- Smooth animations

### 1.2 Industry-Leading Reference Interfaces

#### **ChatPDF (Premium Pattern)**
**UI Layout:**
```
┌─────────────────────────────────────────────────────────┐
│  Header: Logo | Document Name | Settings | Export      │
├──────────────┬──────────────────────────────────────────┤
│              │  Chat Interface                         │
│  PDF Viewer  │  ┌────────────────────────────────────┐ │
│  (Left 50%)  │  │  Conversation History              │ │
│              │  │  • User questions                  │ │
│  • Scroll    │  │  • AI responses with citations     │ │
│  • Zoom      │  │  • Highlighted source references   │ │
│  • Search    │  │                                    │ │
│  • Highlights│  └────────────────────────────────────┘ │
│              │  ┌────────────────────────────────────┐ │
│              │  │  [Ask a question...]        [Send] │ │
│              │  └────────────────────────────────────┘ │
└──────────────┴──────────────────────────────────────────┘
```

**Key Features:**
- Side-by-side layout (PDF + Chat)
- Click citations → jump to PDF location
- Text highlighting in PDF
- Mobile-responsive
- Clean, professional design

#### **Perplexity AI (Premium Pattern)**
**UI Characteristics:**
- Dark theme with cyan accents
- Search-focused input (prominent, centered)
- Card-based results with clear hierarchy
- Source attribution visible
- Follow-up question suggestions
- Smooth animations

#### **Claude Desktop (Premium Pattern)**
**UI Characteristics:**
- Conversation-focused layout
- Code editor view for prompts
- Folder organization (drag-and-drop)
- Dark mode optimized
- Syntax highlighting
- Context-aware suggestions

---

## Part 2: Premium UI/UX Specifications

### 2.1 Design System Foundation

#### **Color Palette (AAA WCAG Compliant)**
```css
/* Light Theme */
--bg-primary: #FFFFFF
--bg-secondary: #F8F9FA
--bg-tertiary: #E9ECEF
--text-primary: #212529
--text-secondary: #6C757D
--accent-primary: #0D6EFD (Blue)
--accent-secondary: #198754 (Green)
--accent-warning: #FFC107 (Amber)
--accent-error: #DC3545 (Red)
--border-color: #DEE2E6

/* Dark Theme */
--bg-primary: #1A1A1A
--bg-secondary: #2D2D2D
--bg-tertiary: #3D3D3D
--text-primary: #FFFFFF
--text-secondary: #B0B0B0
--accent-primary: #4A9EFF
--accent-secondary: #52C41A
--accent-warning: #FAAD14
--accent-error: #FF4D4F
--border-color: #404040
```

#### **Typography (Accessibility-First)**
```css
/* Base Font Sizes (Scalable) */
--font-size-xs: 0.75rem (12px)
--font-size-sm: 0.875rem (14px)
--font-size-base: 1rem (16px)      /* Minimum readable */
--font-size-lg: 1.125rem (18px)
--font-size-xl: 1.25rem (20px)
--font-size-2xl: 1.5rem (24px)
--font-size-3xl: 1.875rem (30px)

/* Font Families */
--font-sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif
--font-mono: "SF Mono", Monaco, "Cascadia Code", "Roboto Mono", monospace

/* Line Heights */
--line-height-tight: 1.25
--line-height-normal: 1.5
--line-height-relaxed: 1.75

/* Font Weights */
--font-weight-normal: 400
--font-weight-medium: 500
--font-weight-semibold: 600
--font-weight-bold: 700
```

#### **Spacing System (8px Grid)**
```css
--space-1: 0.25rem (4px)
--space-2: 0.5rem (8px)
--space-3: 0.75rem (12px)
--space-4: 1rem (16px)
--space-6: 1.5rem (24px)
--space-8: 2rem (32px)
--space-12: 3rem (48px)
--space-16: 4rem (64px)
```

### 2.2 Component Specifications

#### **A. Document Viewer Component**
**Requirements:**
- PDF.js-based renderer
- Text selection and highlighting
- Zoom controls (50% - 400%)
- Page navigation (prev/next, jump to page)
- Search within document
- Citation highlighting (auto-highlight cited sections)
- Annotation support (user notes)
- Keyboard navigation (arrow keys, page up/down)
- Screen reader support (ARIA labels)

**UI Layout:**
```
┌─────────────────────────────────────────┐
│  [← Prev]  Page 1 of 60  [Next →]      │
│  [Zoom Out] [100%] [Zoom In] [Fit]      │
│  [Search: ___________] [🔍]              │
├─────────────────────────────────────────┤
│                                         │
│         PDF Content Area                │
│         (Scrollable)                     │
│                                         │
│  • Highlighted citations (yellow)       │
│  • User annotations (blue)              │
│                                         │
└─────────────────────────────────────────┘
```

#### **B. Chat Interface Component**
**Requirements:**
- Message bubbles (user/AI distinct styling)
- Streaming response display
- Citation chips (clickable, numbered)
- Markdown rendering (code blocks, lists, links)
- Copy response button
- Regenerate response button
- Message timestamps
- Loading indicators
- Error states with retry
- Keyboard shortcuts (Cmd+Enter to send)

**UI Layout:**
```
┌─────────────────────────────────────────┐
│  Conversation History                    │
│  ┌─────────────────────────────────────┐ │
│  │ 👤 User: What are the key clauses?  │ │
│  │                                     │ │
│  │ 🤖 AI: Based on the shareholders    │ │
│  │     agreement, the key clauses     │ │
│  │     include:                        │ │
│  │     • [1] Section 3.2 (p.12)       │ │
│  │     • [2] Section 5.1 (p.18)       │ │
│  │                                     │ │
│  │     [Copy] [Regenerate]             │ │
│  └─────────────────────────────────────┘ │
│                                         │
│  ┌─────────────────────────────────────┐ │
│  │ [Ask a question...]        [Send →] │ │
│  │ 💡 Suggested: "What are the        │ │
│  │    termination conditions?"        │ │
│  └─────────────────────────────────────┘ │
└─────────────────────────────────────────┘
```

#### **C. Question Templates Component**
**Requirements:**
- Pre-built question templates
- Categorized (Overview, Rights, Obligations, etc.)
- One-click insertion
- Custom question builder
- Recent questions history

**UI Layout:**
```
┌─────────────────────────────────────────┐
│  Quick Questions                         │
│  ┌─────────────────────────────────────┐ │
│  │ 📋 Overview                          │ │
│  │   • What is this agreement about?    │ │
│  │   • Who are the parties?             │ │
│  │                                       │ │
│  │ 💼 Rights & Obligations              │ │
│  │   • What are my voting rights?       │ │
│  │   • What are the key obligations?    │ │
│  │                                       │ │
│  │ ⚖️ Legal Terms                      │ │
│  │   • What are the termination         │ │
│  │     conditions?                      │ │
│  └─────────────────────────────────────┘ │
└─────────────────────────────────────────┘
```

#### **D. Report Builder Component**
**Requirements:**
- Section builder (drag-and-drop)
- Template selection
- Export options (PDF, DOCX, Markdown)
- Custom formatting
- Table of contents generation
- Citation formatting (legal style)

**UI Layout:**
```
┌─────────────────────────────────────────┐
│  Report Builder                          │
│  ┌─────────────────────────────────────┐ │
│  │  Report Sections                     │ │
│  │  ┌─────────────────────────────────┐ │ │
│  │  │ 1. Executive Summary    [Edit]  │ │ │
│  │  │ 2. Key Findings         [Edit]  │ │ │
│  │  │ 3. Critical Clauses     [Edit]  │ │ │
│  │  │ 4. Recommendations      [Edit]  │ │ │
│  │  └─────────────────────────────────┘ │ │
│  │                                       │ │
│  │  [Add Section] [Preview] [Export]    │ │
│  └─────────────────────────────────────┘ │
└─────────────────────────────────────────┘
```

### 2.3 Accessibility Requirements (WCAG 2.1 AAA)

#### **Visual Accessibility**
- ✅ Minimum contrast ratio: 7:1 (normal text), 4.5:1 (large text)
- ✅ Text resizable up to 200% without loss of functionality
- ✅ Color not sole indicator (icons + text)
- ✅ Focus indicators visible (2px solid outline)
- ✅ Reduced motion option (respects `prefers-reduced-motion`)

#### **Keyboard Navigation**
- ✅ All interactive elements keyboard accessible
- ✅ Logical tab order
- ✅ Skip links for main content
- ✅ Keyboard shortcuts documented
- ✅ Escape key closes modals/dropdowns

#### **Screen Reader Support**
- ✅ Semantic HTML5 elements
- ✅ ARIA labels for all interactive elements
- ✅ ARIA live regions for dynamic content
- ✅ Alt text for images/icons
- ✅ Form labels associated with inputs
- ✅ Error messages announced

#### **Cognitive Accessibility**
- ✅ Clear, simple language
- ✅ Consistent navigation
- ✅ Error prevention (confirm destructive actions)
- ✅ Help text and tooltips
- ✅ Progress indicators for long operations

### 2.4 Responsive Design Breakpoints

```css
/* Mobile First Approach */
--breakpoint-sm: 640px   /* Small tablets */
--breakpoint-md: 768px   /* Tablets */
--breakpoint-lg: 1024px  /* Small laptops */
--breakpoint-xl: 1280px  /* Desktops */
--breakpoint-2xl: 1536px /* Large desktops */

/* Layout Adaptations */
Mobile (< 768px):
  - Stack PDF viewer and chat vertically
  - Collapsible sections
  - Bottom sheet for chat input

Tablet (768px - 1024px):
  - Side-by-side with adjustable split
  - Full feature set available

Desktop (> 1024px):
  - Optimal side-by-side layout
  - Multi-panel support
  - Keyboard shortcuts enabled
```

---

## Part 3: Technology Stack & Architecture

### 3.1 Backend Stack

```yaml
Core Framework:
  - FastAPI (Python 3.11+)
  - Uvicorn (ASGI server)
  - Pydantic (data validation)

RAG Engine:
  - LlamaIndex (latest)
  - Embeddings: OpenAI text-embedding-3-large (or Cohere)
  - LLM: Claude 3.5 Sonnet (via Anthropic API)
  - Reranking: Cohere rerank-english-v3.0
  - Vector Store: ChromaDB (local) or Pinecone (cloud)

Document Processing:
  - PyPDF2 / pdfplumber (PDF parsing)
  - python-docx (DOCX support)
  - Tesseract OCR (scanned PDFs)
  - Unstructured.io (advanced parsing)

API Layer:
  - FastAPI REST endpoints
  - WebSocket support (streaming responses)
  - MCP server (Cursor integration)
  - OpenAPI/Swagger documentation
```

### 3.2 Frontend Stack

```yaml
Framework:
  - React 18+ (TypeScript)
  - Vite (build tool)
  - React Router (navigation)

UI Component Library:
  - ShadCN/UI (base components)
  - Radix UI (accessible primitives)
  - Tailwind CSS (styling)

PDF Viewer:
  - react-pdf-viewer (PDF.js wrapper)
  - react-pdf-highlighter (annotations)

Chat Interface:
  - Assistant UI (streaming, markdown)
  - React Markdown (rendering)
  - Prism.js (code highlighting)

State Management:
  - Zustand (lightweight state)
  - React Query (server state)

Accessibility:
  - @radix-ui/react-* (ARIA compliant)
  - react-aria (interactions)
  - @axe-core/react (testing)
```

### 3.3 System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    CURSOR IDE                            │
│  ┌────────────────────────────────────────────────────┐ │
│  │  Custom React UI (ShadCN/UI + Tailwind)            │ │
│  │  • Document Viewer                                  │ │
│  │  • Chat Interface                                   │ │
│  │  • Report Builder                                   │ │
│  │  • Question Templates                               │ │
│  └────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
                        │
        ┌───────────────┴───────────────┐
        │                               │
        ▼                               ▼
┌───────────────┐            ┌──────────────────┐
│  MCP Server   │            │  FastAPI REST    │
│  (Cursor)     │            │  API              │
│               │            │                   │
│  • Tools      │            │  • /query         │
│  • Resources  │            │  • /ingest        │
│  • Prompts    │            │  • /report        │
└───────────────┘            │  • /stream        │
                             └──────────────────┘
                                      │
                    ┌─────────────────┼─────────────────┐
                    ▼                 ▼                 ▼
            ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
            │  LlamaIndex  │  │  ChromaDB    │  │  Document    │
            │  RAG Engine  │  │  Vector Store│  │  Processor   │
            │              │  │              │  │              │
            │  • Query     │  │  • Embeddings│  │  • PDF Parse │
            │  • Rerank    │  │  • Metadata  │  │  • OCR       │
            │  • Generate  │  │  • Search    │  │  • Chunking  │
            └──────────────┘  └──────────────┘  └──────────────┘
```

---

## Part 4: Implementation Plan

### Phase 1: Core RAG Backend (Week 1-2)

#### **1.1 Project Setup**
```bash
# Create project structure
shareholders-rag/
├── backend/
│   ├── app/
│   │   ├── main.py (FastAPI app)
│   │   ├── rag/
│   │   │   ├── engine.py (LlamaIndex setup)
│   │   │   ├── reranker.py (Cohere reranking)
│   │   │   └── query_engine.py (multi-step queries)
│   │   ├── document/
│   │   │   ├── parser.py (PDF/DOCX parsing)
│   │   │   ├── chunker.py (semantic chunking)
│   │   │   └── ocr.py (Tesseract integration)
│   │   ├── api/
│   │   │   ├── routes/
│   │   │   │   ├── query.py
│   │   │   │   ├── ingest.py
│   │   │   │   └── report.py
│   │   │   └── models.py (Pydantic schemas)
│   │   └── mcp/
│   │       └── server.py (MCP server for Cursor)
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── DocumentViewer/
│   │   │   ├── ChatInterface/
│   │   │   ├── ReportBuilder/
│   │   │   └── QuestionTemplates/
│   │   ├── hooks/
│   │   ├── lib/
│   │   └── App.tsx
│   ├── package.json
│   └── vite.config.ts
└── docs/
```

#### **1.2 RAG Engine Implementation**
- [ ] Set up LlamaIndex with vector store
- [ ] Implement Cohere reranking
- [ ] Create multi-step query engine
- [ ] Add citation tracking
- [ ] Implement streaming responses

#### **1.3 Document Processing**
- [ ] PDF parser with text extraction
- [ ] OCR for scanned documents
- [ ] Semantic chunking (legal-aware)
- [ ] Metadata extraction (page numbers, sections)

#### **1.4 FastAPI Endpoints**
- [ ] `POST /api/v1/ingest` - Upload document
- [ ] `POST /api/v1/query` - Ask question
- [ ] `GET /api/v1/query/stream` - Streaming query
- [ ] `POST /api/v1/report/generate` - Generate report
- [ ] `GET /api/v1/health` - Health check

### Phase 2: MCP Server Integration (Week 2)

#### **2.1 MCP Server Setup**
- [ ] Create MCP server with LlamaIndex backend
- [ ] Expose tools: `query_document`, `generate_report`
- [ ] Expose resources: document sections
- [ ] Configure Cursor MCP settings

#### **2.2 Cursor Integration**
- [ ] Test MCP server in Cursor
- [ ] Create Claude skills for advanced queries
- [ ] Document usage patterns

### Phase 3: Premium UI/UX (Week 3-4)

#### **3.1 Design System Setup**
- [ ] Install ShadCN/UI components
- [ ] Configure Tailwind with design tokens
- [ ] Set up dark/light theme system
- [ ] Create component library structure

#### **3.2 Document Viewer Component**
- [ ] Integrate react-pdf-viewer
- [ ] Implement citation highlighting
- [ ] Add zoom/scroll controls
- [ ] Keyboard navigation
- [ ] Screen reader support

#### **3.3 Chat Interface Component**
- [ ] Build message bubbles (user/AI)
- [ ] Streaming response display
- [ ] Citation chips with links
- [ ] Markdown rendering
- [ ] Copy/regenerate buttons

#### **3.4 Question Templates Component**
- [ ] Pre-built question library
- [ ] Categorization system
- [ ] One-click insertion
- [ ] Recent questions history

#### **3.5 Report Builder Component**
- [ ] Section builder UI
- [ ] Template system
- [ ] Export functionality (PDF/DOCX)
- [ ] Preview mode

### Phase 4: Accessibility & Polish (Week 4-5)

#### **4.1 Accessibility Audit**
- [ ] Run axe-core tests
- [ ] Keyboard navigation testing
- [ ] Screen reader testing (VoiceOver, NVDA)
- [ ] Color contrast verification
- [ ] Focus management

#### **4.2 Performance Optimization**
- [ ] Code splitting
- [ ] Lazy loading components
- [ ] Image optimization
- [ ] Response caching
- [ ] Bundle size optimization

#### **4.3 User Testing**
- [ ] Test with target user (75-year-old)
- [ ] Gather feedback
- [ ] Iterate on UX
- [ ] Refine accessibility features

---

## Part 5: Default UI Components Inventory

### What You Get Out-of-the-Box

#### **From ShadCN/UI:**
- ✅ Button (variants: default, destructive, outline, ghost, link)
- ✅ Input (text, textarea, search)
- ✅ Card (header, content, footer)
- ✅ Dialog/Modal
- ✅ Dropdown Menu
- ✅ Select
- ✅ Tabs
- ✅ Toast/Notifications
- ✅ Tooltip
- ✅ Scroll Area
- ✅ Separator
- ✅ Skeleton (loading states)
- ✅ Badge
- ✅ Avatar

#### **From Assistant UI:**
- ✅ Chat message components
- ✅ Streaming text display
- ✅ Markdown rendering
- ✅ Code block highlighting
- ✅ File attachment UI

#### **From react-pdf-viewer:**
- ✅ PDF rendering
- ✅ Page navigation
- ✅ Zoom controls
- ✅ Text selection
- ✅ Search functionality

#### **Custom Components to Build:**
- 🔨 Document Viewer (PDF + highlights)
- 🔨 Citation Chips (numbered, clickable)
- 🔨 Question Template Cards
- 🔨 Report Section Builder
- 🔨 Citation Highlighter (PDF overlay)
- 🔨 Export Dialog (format selection)

---

## Part 6: Recommended Starting Points

### Option A: Fork & Customize Existing
**Best Repos to Fork:**
1. **RAGIndex** (`rigvedrs/RAGIndex`)
   - Good LlamaIndex + Streamlit base
   - Has OCR, caching, citations
   - Easy to convert to FastAPI + React

2. **LegalRAG** (`arulkumarann/legalRAG`)
   - Already has FastAPI
   - Legal-specific optimizations
   - Can migrate to LlamaIndex

### Option B: Build from Scratch (Recommended)
**Why:**
- Full control over UI/UX
- No legacy code to maintain
- Modern stack from day one
- Better accessibility implementation

**Starter Template:**
```bash
# Backend
npx create-fastapi-app shareholders-rag-backend
cd shareholders-rag-backend
pip install llama-index fastapi uvicorn

# Frontend
npm create vite@latest shareholders-rag-frontend -- --template react-ts
cd shareholders-rag-frontend
npx shadcn-ui@latest init
npm install assistant-ui react-pdf-viewer
```

---

## Part 7: Success Metrics

### User Experience Metrics
- ✅ Task completion rate > 90%
- ✅ Average query response time < 3 seconds
- ✅ User satisfaction score > 4.5/5
- ✅ Accessibility score: WCAG 2.1 AAA

### Technical Metrics
- ✅ API response time < 500ms (non-streaming)
- ✅ Streaming latency < 100ms
- ✅ Document ingestion time < 30 seconds (60 pages)
- ✅ Citation accuracy > 95%

### Accessibility Metrics
- ✅ Keyboard navigation: 100% coverage
- ✅ Screen reader compatibility: Full
- ✅ Color contrast: AAA compliant
- ✅ Text resize: Up to 200% functional

---

## Part 8: Next Steps

1. **Review & Approve Plan** ✅
2. **Set up Development Environment**
   - Install Python 3.11+, Node.js 20+
   - Set up API keys (Anthropic, Cohere, OpenAI)
3. **Initialize Project Structure**
   - Create backend FastAPI project
   - Create frontend React + Vite project
4. **Begin Phase 1: Core RAG Backend**
   - Start with document ingestion
   - Build query engine
   - Test with sample document

---

## Appendix: Key Files Reference

### Backend Files
- `backend/app/main.py` - FastAPI application entry
- `backend/app/rag/engine.py` - LlamaIndex RAG engine
- `backend/app/api/routes/query.py` - Query endpoints
- `backend/app/mcp/server.py` - MCP server for Cursor

### Frontend Files
- `frontend/src/App.tsx` - Main application component
- `frontend/src/components/DocumentViewer/` - PDF viewer
- `frontend/src/components/ChatInterface/` - Chat UI
- `frontend/src/components/ReportBuilder/` - Report generator

### Configuration Files
- `backend/.env` - API keys, configuration
- `frontend/.env` - Frontend configuration
- `.cursor/mcp.json` - Cursor MCP server config

---

**End of Plan Document**




























