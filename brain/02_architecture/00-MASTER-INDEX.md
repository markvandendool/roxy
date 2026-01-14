# 🏗️ MindSong JukeHub - Master Architecture Index

**Document Version:** 1.0.0  
**Last Updated:** November 13, 2025  
**Lead Architect:** Mark van den Dool  
**Status:** 🚨 SYSTEM COMPLEXITY AUDIT IN PROGRESS

---

## 📋 Executive Summary

MindSong JukeHub has evolved through **6 major architectural iterations** over multiple years:

1. **NovaxeV1** (music_project) - Original TypeScript foundation
2. **NovaxeV2** (novaxe-seb) - Angular migration
3. **Angular 20** - Full framework upgrade
4. **MSM** (Million Song Mind) - Harmonic profile system, MusicViz, Data3 ingestion
5. **Chord Cubes** - 18,000 LOC Apollo.js audio engine
6. **Theater/Quantum/Olympus** - Multi-page visualization suite + timeline systems

**Current Challenge:** After 300+ services and overlapping systems, the original architect has lost mental model. This documentation suite provides forensic clarity.

---

## 📚 Documentation Structure

### Level 1: System Context (External View)
**Audience:** Executives, stakeholders, new engineers  
**Purpose:** What does the system do? Who uses it? What integrations exist?

- [01-SYSTEM-CONTEXT.md](./01-SYSTEM-CONTEXT.md) - C4 Level 1 diagram + external actors

### Level 2: Container Architecture (High-Level Tech)
**Audience:** Solution architects, senior engineers  
**Purpose:** What are the major technical components? How do they communicate?

- [02-CONTAINER-ARCHITECTURE.md](./02-CONTAINER-ARCHITECTURE.md) - Browser runtime, Web Workers, WASM modules
- [02a-DATA-FLOW-ARCHITECTURE.md](./02a-DATA-FLOW-ARCHITECTURE.md) - Score ingestion → playback pipeline

### Level 3: Component Architecture (Internal Structure)
**Audience:** Development team, code reviewers  
**Purpose:** What services/classes exist? What are their responsibilities?

- [03-TRANSPORT-TIMELINE-ARCHITECTURE.md](./03-TRANSPORT-TIMELINE-ARCHITECTURE.md) - 5 competing timeline systems mapped
- [03a-AUDIO-PLAYBACK-ARCHITECTURE.md](./03a-AUDIO-PLAYBACK-ARCHITECTURE.md) - Apollo, Tone.js, Kronos, AudioScheduler
- [03b-PAGE-ROUTING-ARCHITECTURE.md](./03b-PAGE-ROUTING-ARCHITECTURE.md) - 20+ pages (NVX1, Theater, Olympus, MSM)
- [03c-SERVICE-INVENTORY.md](./03c-SERVICE-INVENTORY.md) - Complete catalog of 300+ services

### Level 4: Code/Sequence Diagrams
**Audience:** Developers debugging specific features  
**Purpose:** How does X work at the function-call level?

- [04-PLAY-PAUSE-SEQUENCE.md](./04-PLAY-PAUSE-SEQUENCE.md) - NVX1Score → Quantum → Kernel → Apollo
- [04a-SCORE-LOADING-SEQUENCE.md](./04a-SCORE-LOADING-SEQUENCE.md) - Upload → conversion → store → playback
- [04b-MIDI-ROUTING-SEQUENCE.md](./04b-MIDI-ROUTING-SEQUENCE.md) - Hardware → service → visualization

### Supporting Documentation
- [05-DEPENDENCY-GRAPH.md](./05-DEPENDENCY-GRAPH.md) - Visual service dependency tree
- [06-MIGRATION-HISTORY.md](./06-MIGRATION-HISTORY.md) - Evolution timeline with key decisions
- [07-KNOWN-ISSUES.md](./07-KNOWN-ISSUES.md) - Technical debt, overlaps, redundancies
- [08-CONSOLIDATION-ROADMAP.md](./08-CONSOLIDATION-ROADMAP.md) - Plan to reduce complexity

---

## 🎯 Quick Navigation by Role

### **I'm a new engineer - where do I start?**
1. Read [01-SYSTEM-CONTEXT.md](./01-SYSTEM-CONTEXT.md) (5 min)
2. Read [02-CONTAINER-ARCHITECTURE.md](./02-CONTAINER-ARCHITECTURE.md) (10 min)
3. Skim [03c-SERVICE-INVENTORY.md](./03c-SERVICE-INVENTORY.md) to see what exists

### **I need to fix playback issues**
1. Read [03-TRANSPORT-TIMELINE-ARCHITECTURE.md](./03-TRANSPORT-TIMELINE-ARCHITECTURE.md)
2. Read [04-PLAY-PAUSE-SEQUENCE.md](./04-PLAY-PAUSE-SEQUENCE.md)
3. Check [07-KNOWN-ISSUES.md](./07-KNOWN-ISSUES.md) for existing bugs

### **I'm adding a new audio feature**
1. Read [03a-AUDIO-PLAYBACK-ARCHITECTURE.md](./03a-AUDIO-PLAYBACK-ARCHITECTURE.md)
2. Check [05-DEPENDENCY-GRAPH.md](./05-DEPENDENCY-GRAPH.md) to avoid circular dependencies
3. Review [08-CONSOLIDATION-ROADMAP.md](./08-CONSOLIDATION-ROADMAP.md) to align with cleanup plan

### **I'm the original architect trying to remember WTF I built**
1. Read all of [02-CONTAINER-ARCHITECTURE.md](./02-CONTAINER-ARCHITECTURE.md)
2. Read [06-MIGRATION-HISTORY.md](./06-MIGRATION-HISTORY.md) to recall decisions
3. Review [07-KNOWN-ISSUES.md](./07-KNOWN-ISSUES.md) for current chaos points
4. Use [03c-SERVICE-INVENTORY.md](./03c-SERVICE-INVENTORY.md) as reference when exploring code

---

## 📊 Metrics & Health

| Metric | Current | Target | Status |
|--------|---------|--------|--------|
| **Total Services** | 300+ | <100 | 🔴 Critical |
| **Timeline Systems** | 5 competing | 1 unified | 🔴 Critical |
| **Audio Engines** | 3 (Apollo, Tone, Kronos) | 2 (Apollo + Kronos) | 🟡 Acceptable |
| **Page Components** | 20+ | 15 (consolidate) | 🟡 Moderate |
| **Documented Architecture** | 0% | 100% | 🟢 In Progress |

---

## 🔄 Document Maintenance

This documentation is **living** - it should be updated whenever:
- New services are added
- Major refactoring occurs
- Architecture decisions are made
- External dependencies change

**Update Process:**
1. Edit relevant `.md` files in `docs/architecture/`
2. Regenerate Mermaid diagrams if structure changed
3. Update version number in this index
4. Notify team in #engineering channel

---

## 🛠️ Tools & Standards

**Diagramming:**
- **C4 Model** for architecture levels (Context → Container → Component → Code)
- **Mermaid** for all diagrams (renderable in GitHub/VSCode/Obsidian)
- **PlantUML** for complex sequence diagrams (exported to SVG)

**Documentation Format:**
- Markdown with Mermaid code blocks
- Exported PDFs available in `docs/architecture/exports/`
- Interactive HTML viewer: `npm run docs:serve`

**Reference Materials:**
- [C4 Model Official Docs](https://c4model.com/)
- [Mermaid Live Editor](https://mermaid.live/)
- [Software Architecture Patterns](https://www.oreilly.com/library/view/software-architecture-patterns/9781491971437/)

---

## 📞 Questions?

- **Architecture Questions:** Contact Mark van den Dool (lead architect)
- **Documentation Issues:** Open issue with `docs` label
- **Missing Information:** Add TODO comment in relevant `.md` file

---

**Next Steps:** Review [01-SYSTEM-CONTEXT.md](./01-SYSTEM-CONTEXT.md) to understand the big picture.
