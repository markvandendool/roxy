# Shareholders RAG System - Open Source Resources Inventory

> **Purpose:** Comprehensive list of production-ready open source repos we can use/fork  
> **Status:** Research Complete  
> **Last Updated:** 2025-01-XX

---

## 🏆 Tier 1: Complete Solutions (Use/Fork These First)

### 1. **RAGFlow** ⭐ 68,925 stars
**Repository:** `infiniflow/ragflow`  
**URL:** https://github.com/infiniflow/ragflow

**What It Includes:**
- ✅ **Complete RAG Engine** - Production-ready RAG with agent capabilities
- ✅ **Modern UI** - Built with shadcn/ui + Tailwind CSS (exactly what we need!)
- ✅ **PDF Viewer** - Built-in PDF parser with multiple parsing methods
- ✅ **Chat Interface** - Interactive chat with documents
- ✅ **Document Support** - PDF, DOCX, TXT, images with OCR
- ✅ **Semantic Search** - Vector search with Pinecone/pgvector
- ✅ **Dark Mode** - Responsive interface with dark mode
- ✅ **Enterprise Security** - AES-256, RLS, authentication
- ✅ **Multi-AI Support** - OpenRouter, OpenAI, Anthropic, ImageRouter

**Key Features:**
- PDF parsing: DeepDoc, Naive, MinerU, Docling
- Multiple chunking methods: General, Manual, Paper, Book, Laws, Presentation
- Docker Compose deployment (one command!)
- Production-ready architecture

**Why This Is Perfect:**
- Already has premium UI with shadcn/ui
- Complete solution - minimal customization needed
- Enterprise-grade security
- Active development (68k+ stars)

**How to Use:**
```bash
git clone https://github.com/infiniflow/ragflow.git
cd ragflow/docker
docker compose up --build --force-recreate
# Access at http://localhost
```

**Customization Needed:**
- Add MCP server integration for Cursor
- Customize UI for legal document focus
- Add report generation module
- Enhance citation highlighting

---

### 2. **Document Chat System** ⭐ (Growing)
**Repository:** `watat83/document-chat-system`  
**URL:** https://github.com/watat83/document-chat-system

**What It Includes:**
- ✅ **Next.js Frontend** - React with TypeScript
- ✅ **FastAPI Backend** - High-performance API
- ✅ **PostgreSQL + Prisma** - Modern database stack
- ✅ **Semantic Search** - RAG implementation
- ✅ **Multi-AI Support** - OpenRouter, OpenAI, ImageRouter
- ✅ **Tailwind CSS** - Modern styling
- ✅ **Live Demo** - Available at Vercel

**Key Features:**
- Document upload and processing
- Chat interface with document context
- Semantic search capabilities
- Production-ready stack

**Why This Is Great:**
- Clean, modern architecture
- FastAPI backend (matches our plan)
- Next.js frontend (React-based)
- MIT License (commercial use allowed)

**How to Use:**
```bash
git clone https://github.com/watat83/document-chat-system.git
cd document-chat-system
# Follow setup instructions in README
```

**Customization Needed:**
- Add PDF viewer component
- Enhance citation system
- Add report generation
- MCP server integration

---

### 3. **Dify** ⭐ 120,796 stars
**Repository:** `langgenius/dify`  
**URL:** https://github.com/langgenius/dify

**What It Includes:**
- ✅ **Visual Workflow Builder** - No-code AI workflow design
- ✅ **RAG Pipeline** - Complete RAG with document ingestion
- ✅ **Agent Capabilities** - LLM Function Calling, ReAct
- ✅ **Model Management** - Support for GPT, Mistral, Llama3, etc.
- ✅ **LLMOps** - Monitoring and analytics
- ✅ **Backend-as-a-Service** - Comprehensive APIs
- ✅ **Document Support** - PDF, PPT, and more

**Key Features:**
- Visual canvas for workflow design
- 50+ built-in tools (Google Search, DALL·E, etc.)
- Production monitoring and analytics
- Docker Compose deployment

**Why This Is Powerful:**
- Most comprehensive platform
- Visual workflow builder (great for non-technical users)
- Enterprise features included
- Massive community (120k+ stars)

**How to Use:**
```bash
git clone https://github.com/langgenius/dify.git
cd dify/docker
cp .env.example .env
docker compose up -d
# Access at http://localhost/install
```

**Customization Needed:**
- Customize UI for legal documents
- Add PDF viewer with highlights
- MCP server integration
- Report generation module

---

### 4. **Open-WebUI** ⭐ 117,212 stars
**Repository:** `open-webui/open-webui`  
**URL:** https://github.com/open-webui/open-webui

**What It Includes:**
- ✅ **Document Upload** - PDF, DOCX, TXT support
- ✅ **OpenAI PDF Support** - Multi-modal PDF queries
- ✅ **RAG Integration** - Document library with RAG
- ✅ **Chat Interface** - Modern chat UI
- ✅ **Web Browsing** - URL integration
- ✅ **Image Generation** - DALL-E, local tools
- ✅ **RBAC** - Role-based access control
- ✅ **Rich HTML UI** - Interactive HTML injection

**Key Features:**
- Self-hosted interface
- Multiple AI provider support
- Document library management
- Persistent vector-based memory (in development)

**Why This Is Useful:**
- User-friendly interface
- Document upload built-in
- RAG support
- Active development

**How to Use:**
```bash
git clone https://github.com/open-webui/open-webui.git
# Follow Docker setup instructions
```

**Customization Needed:**
- Add PDF viewer component
- Enhance citation system
- Legal document focus
- Report generation

---

### 5. **LobeChat** ⭐ (Growing)
**Repository:** `lobehub/lobe-chat`  
**URL:** https://github.com/lobehub/lobe-chat

**What It Includes:**
- ✅ **Knowledge Base** - Unlimited knowledge bases
- ✅ **File Upload** - PDF, DOCX, XLSX, PPTX, HTML, MD
- ✅ **RAG Technology** - Vector embeddings for documents
- ✅ **Multi-Model Support** - GPT-4, Claude 3.5, Gemini, Ollama
- ✅ **Self-Hosting** - Docker, Vercel, Zeabur options
- ✅ **Modern UI** - High-performance chat framework

**Key Features:**
- Document management system
- Vector-based document retrieval
- Multi-modal AI support
- Extensible plugin system

**Why This Is Good:**
- Clean architecture
- Knowledge base management
- Multiple deployment options
- Active development

**Customization Needed:**
- PDF viewer integration
- Citation highlighting
- Report generation
- Legal document focus

---

## 🎨 Tier 2: UI Component Libraries

### 6. **react-pdf-viewer** ⭐ 2,000+ stars
**Repository:** `react-pdf-viewer/react-pdf-viewer`  
**URL:** https://github.com/react-pdf-viewer/react-pdf-viewer

**What It Includes:**
- ✅ **PDF Rendering** - PDF.js wrapper
- ✅ **TypeScript** - Full TypeScript support
- ✅ **Plugin System** - Extensible with plugins
- ✅ **Customizable UI** - Full control over appearance
- ✅ **React Hooks** - Modern React patterns

**Plugins Available:**
- Zoom plugin
- Page navigation
- Text selection
- Search plugin
- Highlight plugin (separate package)

**Why Use This:**
- Most mature React PDF viewer
- Excellent TypeScript support
- Plugin architecture
- Active maintenance

---

### 7. **react-pdf-highlighter** ⭐ 1,500+ stars
**Repository:** `agentcooper/react-pdf-highlighter`  
**URL:** https://github.com/agentcooper/react-pdf-highlighter

**What It Includes:**
- ✅ **Text Highlighting** - Highlight selected text
- ✅ **Image Highlights** - Highlight image regions
- ✅ **Popover Text** - Add notes to highlights
- ✅ **Scroll to Highlights** - Navigate to annotations
- ✅ **PDF.js Based** - Built on Mozilla PDF.js

**Why Use This:**
- Perfect for citation highlighting
- Well-documented
- React-friendly
- Can combine with react-pdf-viewer

---

### 8. **Assistant UI** ⭐ (Growing)
**Repository:** `assistant-ui/assistant-ui`  
**URL:** https://github.com/assistant-ui/assistant-ui

**What It Includes:**
- ✅ **Chat Components** - Pre-built chat UI
- ✅ **Streaming Support** - Real-time streaming
- ✅ **Markdown Rendering** - Code highlighting
- ✅ **File Attachments** - Attachment UI
- ✅ **Generative UI** - Dynamic UI generation
- ✅ **TypeScript** - Full TypeScript support

**Why Use This:**
- Modern chat interface
- Streaming built-in
- Markdown support
- ShadCN/UI compatible

---

## 🔧 Tier 3: Backend Components

### 9. **LlamaIndex-FastAPI** ⭐ (Growing)
**Repository:** `pengxiaoo/llama-index-fastapi`  
**URL:** https://github.com/pengxiaoo/llama-index-fastapi

**What It Includes:**
- ✅ **FastAPI Integration** - LlamaIndex + FastAPI
- ✅ **Q&A Mode** - Question answering
- ✅ **Chatbot Mode** - Conversational interface
- ✅ **OpenAI Integration** - Embeddings and responses
- ✅ **Scalable** - Designed for millions of users

**Why Use This:**
- Perfect FastAPI + LlamaIndex combo
- Production-ready structure
- Good starting point

---

### 10. **MCP Local RAG** ⭐ (Growing)
**Repository:** `shinpr/mcp-local-rag`  
**URL:** https://github.com/shinpr/mcp-local-rag

**What It Includes:**
- ✅ **MCP Server** - Model Context Protocol server
- ✅ **Cursor Integration** - Works with Cursor IDE
- ✅ **Claude Integration** - Compatible with Claude Desktop
- ✅ **Privacy-First** - All processing local
- ✅ **Document Support** - PDF, DOCX, TXT, MD

**Why Use This:**
- **PERFECT for Cursor integration!**
- Already MCP-compatible
- Privacy-focused
- Can be extended

**How to Use:**
```bash
npx -y mcp-local-rag
# Configure in ~/.cursor/mcp.json
```

**Customization Needed:**
- Enhance with LlamaIndex backend
- Add report generation
- Improve UI components

---

### 11. **PDF RAG MCP Server** ⭐ (Growing)
**Repository:** `hyson666/pdf-rag-mcp-server`  
**URL:** https://github.com/hyson666/pdf-rag-mcp-server

**What It Includes:**
- ✅ **PDF Processing** - PDF document handling
- ✅ **RAG Implementation** - Semantic search
- ✅ **MCP Server** - MCP protocol support
- ✅ **Web Interface** - Modern web UI
- ✅ **Cursor Compatible** - Works with Cursor

**Why Use This:**
- PDF-focused RAG
- MCP server included
- Good for our use case

---

### 12. **RAG-MCP** ⭐ (Growing)
**Repository:** `alejandro-ao/RAG-MCP`  
**URL:** https://github.com/alejandro-ao/RAG-MCP

**What It Includes:**
- ✅ **LlamaParse Integration** - Easy ETL processes
- ✅ **MCP Server** - MCP protocol
- ✅ **Document Ingestion** - Document processing
- ✅ **Semantic Search** - Vector search
- ✅ **Cursor/Claude Compatible** - Works with both

**Why Use This:**
- LlamaParse integration (great for PDFs)
- MCP server ready
- Good document processing

---

## 📊 Tier 4: Report Generation

### 13. **pdfme** ⭐ 4,000+ stars
**Repository:** `pdfme/pdfme`  
**URL:** https://github.com/pdfme/pdfme

**What It Includes:**
- ✅ **WYSIWYG Designer** - Visual template designer
- ✅ **PDF Viewer** - Built-in viewer
- ✅ **PDF Generation** - TypeScript/React
- ✅ **Template System** - Reusable templates
- ✅ **Browser/Node.js** - Works everywhere

**Why Use This:**
- Best PDF generation library
- WYSIWYG designer (great for reports)
- React integration
- Active development

---

### 14. **docxtemplater** ⭐ 3,000+ stars
**Repository:** `open-xml-templating/docxtemplater`  
**URL:** https://github.com/open-xml-templating/docxtemplater

**What It Includes:**
- ✅ **DOCX Generation** - Word document creation
- ✅ **Template System** - Word template-based
- ✅ **React Compatible** - Works with React
- ✅ **Browser/Node.js** - Universal support

**Why Use This:**
- Perfect for Word report generation
- Template-based (professional)
- Well-maintained

---

## 🎯 Recommended Approach: Hybrid Strategy

### Option A: Fork RAGFlow (Recommended)
**Why:**
- Most complete solution
- Premium UI already built (shadcn/ui)
- Enterprise features included
- Production-ready

**What to Add:**
1. MCP server integration (use `mcp-local-rag` as reference)
2. Enhanced citation highlighting (use `react-pdf-highlighter`)
3. Report generation (use `pdfme` + `docxtemplater`)
4. Legal document optimizations

**Effort:** Low (mostly integration work)

---

### Option B: Combine Best Components
**Stack:**
1. **Backend:** `document-chat-system` (FastAPI + LlamaIndex)
2. **Frontend:** `RAGFlow` UI components (shadcn/ui)
3. **PDF Viewer:** `react-pdf-viewer` + `react-pdf-highlighter`
4. **Chat UI:** `Assistant UI`
5. **MCP Server:** `mcp-local-rag` (enhanced)
6. **Report Gen:** `pdfme` + `docxtemplater`

**Effort:** Medium (integration work)

---

### Option C: Use Dify Platform
**Why:**
- Most comprehensive platform
- Visual workflow builder
- Enterprise features
- Can customize UI

**What to Add:**
1. Custom UI for legal documents
2. PDF viewer with highlights
3. MCP server integration
4. Report generation module

**Effort:** Medium-High (customization)

---

## 📋 Quick Start Recommendations

### For Fastest Setup:
1. **Fork RAGFlow** - Already has 90% of what we need
2. **Add MCP Server** - Use `mcp-local-rag` as reference
3. **Enhance Citations** - Integrate `react-pdf-highlighter`
4. **Add Reports** - Integrate `pdfme`

**Time Estimate:** 1-2 weeks

### For Maximum Customization:
1. **Use Document Chat System** - Clean architecture
2. **Add RAGFlow UI Components** - Premium UI
3. **Integrate PDF Viewer** - `react-pdf-viewer` + highlighter
4. **Build MCP Server** - Custom with LlamaIndex
5. **Add Report Generation** - `pdfme` + `docxtemplater`

**Time Estimate:** 2-3 weeks

---

## 🔗 Additional Resources

### MCP Servers for Reference:
- `shinpr/mcp-local-rag` - Privacy-first RAG MCP
- `hyson666/pdf-rag-mcp-server` - PDF-focused MCP
- `alejandro-ao/RAG-MCP` - LlamaParse MCP
- `ContextualAI/contextual-mcp-server` - Contextual AI MCP

### UI Component Libraries:
- `shadcn/ui` - Base components (used by RAGFlow)
- `radix-ui` - Accessible primitives
- `assistant-ui` - Chat components

### Backend Frameworks:
- `llama-index` - RAG framework
- `fastapi` - API framework
- `haystack` - Alternative RAG framework

---

## ✅ Action Items

1. **Evaluate RAGFlow** - Test the complete solution
2. **Test MCP Servers** - Try `mcp-local-rag` in Cursor
3. **Review Document Chat System** - Check architecture
4. **Decide on Approach** - Fork vs. Combine vs. Custom
5. **Start Integration** - Begin with chosen approach

---

**End of Open Source Resources Inventory**




























