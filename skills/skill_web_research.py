#!/usr/bin/env python3
"""
Web Research Skill
==================
RU-012: Built-in Skills Package

Comprehensive web research using browser automation.
Integrates with mcp_browser for navigation and extraction.

Features:
- Multi-site research with parallel extraction
- Structured data extraction
- Source aggregation with citations
- Result synthesis

SKILL_MANIFEST required for dynamic loading.
"""

import json
import asyncio
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field


# =============================================================================
# SKILL MANIFEST (Required for skills_registry)
# =============================================================================

SKILL_MANIFEST = {
    "name": "web_research",
    "version": "1.0.0",
    "description": "Deep web research with browser automation, multi-source synthesis",
    "author": "ROXY",
    "keywords": [
        "research", "web", "search", "scrape", "extract", "browse",
        "google", "wikipedia", "article", "news", "information",
        "find", "lookup", "investigate", "query"
    ],
    "capabilities": [
        "web_search", "page_extraction", "multi_site_research",
        "data_synthesis", "citation_generation"
    ],
    "tools": [
        "search", "research_topic", "extract_page", "multi_site", "summarize"
    ],
    "dependencies": ["mcp_browser"],
    "category": "research"
}


# =============================================================================
# Browser Integration
# =============================================================================

# Try to import browser MCP
try:
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent / "mcp"))
    from mcp_browser import (
        browser_goto,
        browser_extract,
        browser_screenshot,
        browser_evaluate
    )
    BROWSER_AVAILABLE = True
except ImportError:
    BROWSER_AVAILABLE = False


async def _call_browser(func, *args, **kwargs):
    """Call browser tool functions whether they are sync or async."""
    if asyncio.iscoroutinefunction(func):
        return await func(*args, **kwargs)
    return await asyncio.to_thread(func, *args, **kwargs)


@dataclass
class SearchResult:
    """Search result from web"""
    title: str
    url: str
    snippet: str
    source: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class ResearchReport:
    """Compiled research report"""
    query: str
    sources: List[SearchResult]
    synthesis: str
    confidence: float
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# =============================================================================
# Core Functions
# =============================================================================

async def search_web(query: str, num_results: int = 5) -> Dict:
    """
    Perform web search using DuckDuckGo.
    
    Args:
        query: Search query
        num_results: Maximum results to return
    
    Returns:
        {success: bool, results: [...]}
    """
    if not BROWSER_AVAILABLE:
        return {"success": False, "error": "Browser MCP not available"}
    
    try:
        engines = [
            {
                "name": "duckduckgo",
                "url": f"https://html.duckduckgo.com/html/?q={query.replace(' ', '+')}",
                "selector": ".result",
            },
            {
                "name": "bing",
                "url": f"https://www.bing.com/search?q={query.replace(' ', '+')}",
                "selector": ".b_algo",
            },
        ]

        for engine in engines:
            nav_result = await _call_browser(browser_goto, engine["url"], timeout=15000)
            if not nav_result.get("success"):
                continue
            status = nav_result.get("status")
            if status and status >= 400:
                continue

            extract_result = await _call_browser(
                browser_extract,
                selector=engine["selector"],
                include_links=True,
                max_items=num_results * 2  # Get extras, filter later
            )
            if not extract_result.get("success"):
                continue

            results = []
            items = extract_result.get("items", [])
            for item in items[:num_results]:
                text = item.get("text", "")
                links = item.get("links", [])

                if links:
                    url = links[0].get("href", "")
                    title = links[0].get("text", "")
                else:
                    url = ""
                    title = text[:100]

                if engine["name"] == "duckduckgo" and "duckduckgo.com" in url:
                    continue

                results.append(SearchResult(
                    title=title[:200],
                    url=url,
                    snippet=text[:500],
                    source=engine["name"]
                ))

            if results:
                return {
                    "success": True,
                    "query": query,
                    "results": [
                        {"title": r.title, "url": r.url, "snippet": r.snippet}
                        for r in results
                    ],
                    "count": len(results)
                }

        return {"success": False, "error": "Extraction failed"}
    
    except Exception as e:
        return {"success": False, "error": str(e)}


async def extract_page_content(url: str, selectors: List[str] = None) -> Dict:
    """
    Extract content from a specific webpage.
    
    Args:
        url: Page URL
        selectors: CSS selectors to target (default: article, main, body)
    
    Returns:
        {success: bool, content: str, metadata: {...}}
    """
    if not BROWSER_AVAILABLE:
        return {"success": False, "error": "Browser MCP not available"}
    
    selectors = selectors or ["article", "main", "[role='main']", ".content", "body"]
    
    try:
        nav_result = await _call_browser(browser_goto, url, timeout=20000)
        if not nav_result.get("success"):
            return {"success": False, "error": f"Navigation failed: {nav_result.get('error')}"}
        
        # Try each selector until one works
        content = ""
        for selector in selectors:
            try:
                extract_result = await _call_browser(
                    browser_extract,
                    selector=selector,
                    include_links=True,
                    max_items=1
                )
                if extract_result.get("success") and extract_result.get("items"):
                    content = extract_result["items"][0].get("text", "")
                    if len(content) > 100:  # Found meaningful content
                        break
            except:
                continue
        
        # Get page metadata
        meta_script = """
        ({
            title: document.title,
            description: document.querySelector('meta[name="description"]')?.content || '',
            author: document.querySelector('meta[name="author"]')?.content || '',
            published: document.querySelector('meta[property="article:published_time"]')?.content || ''
        })
        """
        meta_result = await browser_evaluate(meta_script)
        metadata = meta_result.get("result", {}) if meta_result.get("success") else {}
        
        return {
            "success": True,
            "url": url,
            "content": content[:10000],  # Limit content size
            "content_length": len(content),
            "metadata": metadata
        }
    
    except Exception as e:
        return {"success": False, "error": str(e)}


async def research_topic(topic: str, depth: int = 3) -> Dict:
    """
    Comprehensive topic research.
    
    Args:
        topic: Research topic
        depth: Number of sources to consult
    
    Returns:
        ResearchReport as dict
    """
    if not BROWSER_AVAILABLE:
        return {"success": False, "error": "Browser MCP not available"}
    
    try:
        # Step 1: Search
        search_result = await search_web(topic, num_results=depth + 2)
        if not search_result.get("success"):
            return search_result
        
        # Step 2: Extract from top results
        sources = []
        contents = []
        
        for result in search_result.get("results", [])[:depth]:
            url = result.get("url", "")
            if not url:
                continue
            
            extract = await extract_page_content(url)
            if extract.get("success"):
                sources.append(SearchResult(
                    title=result.get("title", ""),
                    url=url,
                    snippet=extract.get("content", "")[:1000],
                    source="extracted"
                ))
                contents.append(extract.get("content", ""))
        
        # Step 3: Synthesize (basic for now, LLM would enhance)
        synthesis = f"Research on '{topic}' compiled from {len(sources)} sources:\n\n"
        for i, source in enumerate(sources, 1):
            synthesis += f"[{i}] {source.title}\n"
            synthesis += f"    URL: {source.url}\n"
            synthesis += f"    Summary: {source.snippet[:300]}...\n\n"
        
        report = ResearchReport(
            query=topic,
            sources=sources,
            synthesis=synthesis,
            confidence=min(0.9, 0.3 * len(sources))  # More sources = higher confidence
        )
        
        return {
            "success": True,
            "topic": topic,
            "source_count": len(sources),
            "synthesis": report.synthesis,
            "confidence": report.confidence,
            "sources": [
                {"title": s.title, "url": s.url, "snippet": s.snippet[:200]}
                for s in sources
            ]
        }
    
    except Exception as e:
        return {"success": False, "error": str(e)}


async def multi_site_research(query: str, sites: List[str]) -> Dict:
    """
    Research across specific sites.
    
    Args:
        query: Search query
        sites: List of domains to search (e.g., ["wikipedia.org", "stackoverflow.com"])
    
    Returns:
        Combined results from all sites
    """
    if not BROWSER_AVAILABLE:
        return {"success": False, "error": "Browser MCP not available"}
    
    all_results = []
    
    for site in sites:
        site_query = f"site:{site} {query}"
        result = await search_web(site_query, num_results=3)
        if result.get("success"):
            for r in result.get("results", []):
                r["source_site"] = site
                all_results.append(r)
    
    return {
        "success": True,
        "query": query,
        "sites_searched": sites,
        "results": all_results,
        "count": len(all_results)
    }


# =============================================================================
# Synchronous Wrappers
# =============================================================================

def _run_async(coro):
    """Run async coroutine synchronously"""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


def search(query: str, num_results: int = 5) -> Dict:
    """Sync wrapper for search_web"""
    return _run_async(search_web(query, num_results))


def extract(url: str, selectors: List[str] = None) -> Dict:
    """Sync wrapper for extract_page_content"""
    return _run_async(extract_page_content(url, selectors))


def research(topic: str, depth: int = 3) -> Dict:
    """Sync wrapper for research_topic"""
    return _run_async(research_topic(topic, depth))


def multi_site(query: str, sites: List[str]) -> Dict:
    """Sync wrapper for multi_site_research"""
    return _run_async(multi_site_research(query, sites))


# =============================================================================
# MCP Tool Interface
# =============================================================================

TOOLS = {
    "search": {
        "description": "Search the web using DuckDuckGo",
        "parameters": {
            "query": {"type": "string", "description": "Search query"},
            "num_results": {"type": "integer", "default": 5}
        },
        "required": ["query"]
    },
    "research_topic": {
        "description": "Comprehensive research on a topic with multiple sources",
        "parameters": {
            "topic": {"type": "string", "description": "Topic to research"},
            "depth": {"type": "integer", "default": 3, "description": "Number of sources"}
        },
        "required": ["topic"]
    },
    "extract_page": {
        "description": "Extract content from a specific webpage",
        "parameters": {
            "url": {"type": "string", "description": "Page URL"},
            "selectors": {"type": "array", "items": {"type": "string"}}
        },
        "required": ["url"]
    },
    "multi_site": {
        "description": "Research across specific sites",
        "parameters": {
            "query": {"type": "string"},
            "sites": {"type": "array", "items": {"type": "string"}, "description": "Domains to search"}
        },
        "required": ["query", "sites"]
    }
}


def handle_tool(name: str, params: Dict) -> Any:
    """MCP tool handler"""
    handlers = {
        "search": lambda p: search(p["query"], p.get("num_results", 5)),
        "research_topic": lambda p: research(p["topic"], p.get("depth", 3)),
        "extract_page": lambda p: extract(p["url"], p.get("selectors")),
        "multi_site": lambda p: multi_site(p["query"], p["sites"])
    }
    
    if name not in handlers:
        return {"success": False, "error": f"Unknown tool: {name}"}
    
    return handlers[name](params)


# =============================================================================
# Query Handler (for router integration)
# =============================================================================

def handle_query(query: str, params: Dict = None) -> Dict:
    """
    Handle a routed query.
    Called by expert_router when this skill is selected.
    """
    params = params or {}
    
    # Determine intent from query
    query_lower = query.lower()
    
    if "search" in query_lower and "http" not in query_lower:
        # Extract search terms (remove "search for", "look up", etc.)
        search_terms = query.replace("search for", "").replace("look up", "").strip()
        return search(search_terms)
    
    elif query.startswith("http"):
        # URL extraction
        return extract(query)
    
    else:
        # Default to topic research
        return research(query, params.get("depth", 3))


# =============================================================================
# CLI
# =============================================================================

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: skill_web_research.py <command> <args>")
        print("Commands: search <query>, research <topic>, extract <url>")
        sys.exit(1)
    
    cmd = sys.argv[1]
    arg = " ".join(sys.argv[2:])
    
    if cmd == "search":
        result = search(arg)
    elif cmd == "research":
        result = research(arg)
    elif cmd == "extract":
        result = extract(arg)
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)
    
    print(json.dumps(result, indent=2))
