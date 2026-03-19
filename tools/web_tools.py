#!/usr/bin/env python3
"""
Web Tools - WebSearch and WebFetch capabilities
Part of ROXY-AUTONOMOUS-CODING-AGENT-V1 (RCA-005)
"""
import asyncio
import json
import logging
import re
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

logger = logging.getLogger("roxy.web_tools")

MAX_RESULTS = 10
MAX_FETCH_SIZE = 100 * 1024
USER_AGENT = "ROXY/1.0 (AI Assistant)"


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str
    source: str = "duckduckgo"


@dataclass
class FetchResult:
    url: str
    title: str
    content: str
    status_code: int
    headers: Dict[str, str]
    content_type: str
    fetch_time: float


class WebSearch:
    """Web search using DuckDuckGo HTML."""
    
    async def search(
        self,
        query: str,
        num_results: int = MAX_RESULTS
    ) -> List[SearchResult]:
        """
        Search the web.
        
        Args:
            query: Search query
            num_results: Number of results to return
            
        Returns:
            List of SearchResult objects
        """
        try:
            encoded_query = quote(query)
            url = f"https://html.duckduckgo.com/html/?q={encoded_query}"
            
            request = Request(
                url,
                headers={"User-Agent": USER_AGENT}
            )
            
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: urlopen(request, timeout=10)
            )
            
            html = response.read().decode('utf-8', errors='replace')
            results = self._parse_ddg_html(html, num_results)
            
            return results
            
        except HTTPError as e:
            logger.error(f"Search HTTP error: {e.code} {e.reason}")
            return []
        except URLError as e:
            logger.error(f"Search URL error: {e.reason}")
            return []
        except Exception as e:
            logger.error(f"Search error: {e}")
            return []
    
    def _parse_ddg_html(self, html: str, num_results: int) -> List[SearchResult]:
        """Parse DuckDuckGo HTML results."""
        results = []
        
        result_pattern = re.compile(
            r'<a class="result__a" href="([^"]+)">([^<]+)</a>',
            re.IGNORECASE
        )
        
        snippet_pattern = re.compile(
            r'<a class="result__a" href="([^"]+)">([^<]+)</a>.*?<a class="result__snippet"[^>]*>([^<]+)</a>',
            re.DOTALL | re.IGNORECASE
        )
        
        for match in snippet_pattern.finditer(html):
            if len(results) >= num_results:
                break
            
            url = match.group(1)
            title = self._clean_html(match.group(2))
            snippet = self._clean_html(match.group(3))
            
            if url and title:
                results.append(SearchResult(
                    title=title,
                    url=url,
                    snippet=snippet,
                    source="duckduckgo"
                ))
        
        if not results:
            for match in result_pattern.finditer(html):
                if len(results) >= num_results:
                    break
                
                url = match.group(1)
                title = self._clean_html(match.group(2))
                
                if url and title:
                    results.append(SearchResult(
                        title=title,
                        url=url,
                        snippet="",
                        source="duckduckgo"
                    ))
        
        return results
    
    def _clean_html(self, text: str) -> str:
        """Remove HTML entities and tags."""
        if not text:
            return ""
        
        text = re.sub(r'<[^>]+>', '', text)
        text = text.replace('&amp;', '&')
        text = text.replace('&lt;', '<')
        text = text.replace('&gt;', '>')
        text = text.replace('&quot;', '"')
        text = text.replace('&#39;', "'")
        text = text.replace('&nbsp;', ' ')
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()


class WebFetch:
    """Fetch web page content."""
    
    async def fetch(
        self,
        url: str,
        include_content: bool = True,
        timeout: float = 15.0
    ) -> FetchResult:
        """
        Fetch a web page.
        
        Args:
            url: URL to fetch
            include_content: Whether to include full content
            timeout: Timeout in seconds
            
        Returns:
            FetchResult object
        """
        start_time = time.time()
        
        try:
            request = Request(
                url,
                headers={
                    "User-Agent": USER_AGENT,
                    "Accept": "text/html,application/xhtml+xml,*/*",
                    "Accept-Language": "en-US,en;q=0.9"
                }
            )
            
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: urlopen(request, timeout=timeout)
            )
            
            status_code = response.getcode()
            headers = dict(response.headers)
            content_type = headers.get('Content-Type', 'text/html')
            
            raw_content = response.read()
            
            if len(raw_content) > MAX_FETCH_SIZE:
                raw_content = raw_content[:MAX_FETCH_SIZE]
            
            try:
                content = raw_content.decode('utf-8', errors='replace')
            except:
                content = raw_content.decode('latin-1', errors='replace')
            
            title = self._extract_title(content, url)
            
            if include_content:
                content = self._clean_content(content)
            else:
                content = content[:2000] + "..." if len(content) > 2000 else content
            
            return FetchResult(
                url=url,
                title=title,
                content=content,
                status_code=status_code,
                headers=headers,
                content_type=content_type,
                fetch_time=time.time() - start_time
            )
            
        except HTTPError as e:
            logger.error(f"Fetch HTTP error: {e.code} {e.reason}")
            return FetchResult(
                url=url,
                title="",
                content=f"HTTP Error: {e.code} {e.reason}",
                status_code=e.code,
                headers={},
                content_type="",
                fetch_time=time.time() - start_time
            )
        except URLError as e:
            logger.error(f"Fetch URL error: {e.reason}")
            return FetchResult(
                url=url,
                title="",
                content=f"URL Error: {e.reason}",
                status_code=0,
                headers={},
                content_type="",
                fetch_time=time.time() - start_time
            )
        except Exception as e:
            logger.error(f"Fetch error: {e}")
            return FetchResult(
                url=url,
                title="",
                content=f"Error: {str(e)}",
                status_code=0,
                headers={},
                content_type="",
                fetch_time=time.time() - start_time
            )
    
    def _extract_title(self, content: str, url: str) -> str:
        """Extract page title."""
        title_match = re.search(
            r'<title[^>]*>([^<]+)</title>',
            content,
            re.IGNORECASE
        )
        
        if title_match:
            return self._clean_html(title_match.group(1))
        
        h1_match = re.search(
            r'<h1[^>]*>([^<]+)</h1>',
            content,
            re.IGNORECASE
        )
        
        if h1_match:
            return self._clean_html(h1_match.group(1))
        
        return url
    
    def _clean_html(self, text: str) -> str:
        """Clean HTML entities."""
        if not text:
            return ""
        
        text = text.replace('&amp;', '&')
        text = text.replace('&lt;', '<')
        text = text.replace('&gt;', '>')
        text = text.replace('&quot;', '"')
        text = text.replace('&#39;', "'")
        text = text.replace('&nbsp;', ' ')
        
        return text.strip()
    
    def _clean_content(self, content: str) -> str:
        """Remove scripts, styles, and extra whitespace."""
        content = re.sub(r'<script[^>]*>[\s\S]*?</script>', '', content)
        content = re.sub(r'<style[^>]*>[\s\S]*?</style>', '', content)
        content = re.sub(r'<nav[^>]*>[\s\S]*?</nav>', '', content)
        content = re.sub(r'<footer[^>]*>[\s\S]*?</footer>', '', content)
        content = re.sub(r'<header[^>]*>[\s\S]*?</header>', '', content)
        content = re.sub(r'<[^>]+>', ' ', content)
        content = re.sub(r'\s+', ' ', content)
        content = self._clean_html(content)
        
        return content.strip()


class WebTools:
    """Combined web search and fetch."""
    
    def __init__(self):
        self.search = WebSearch()
        self.fetch = WebFetch()
    
    async def search_and_summarize(
        self,
        query: str,
        num_results: int = 5
    ) -> Dict[str, Any]:
        """
        Search and return summarized results.
        
        Args:
            query: Search query
            num_results: Number of results
            
        Returns:
            Dict with results and metadata
        """
        results = await self.search.search(query, num_results)
        
        return {
            "query": query,
            "results_count": len(results),
            "results": [
                {
                    "title": r.title,
                    "url": r.url,
                    "snippet": r.snippet,
                    "source": r.source
                }
                for r in results
            ],
            "summary": self._format_results(results) if results else "No results found"
        }
    
    def _format_results(self, results: List[SearchResult]) -> str:
        """Format search results as readable text."""
        lines = []
        for i, result in enumerate(results, 1):
            lines.append(f"{i}. {result.title}")
            lines.append(f"   {result.url}")
            if result.snippet:
                lines.append(f"   {result.snippet[:150]}...")
            lines.append("")
        
        return "\n".join(lines)


async def test_web_tools():
    """Test web search and fetch."""
    tools = WebTools()
    
    print("Testing WebSearch...")
    results = await tools.search.search("Python async programming", 5)
    print(f"Found {len(results)} results")
    for r in results[:3]:
        print(f"  - {r.title}")
        print(f"    {r.url}")
    
    print("\nTesting WebFetch...")
    if results:
        fetch_result = await tools.fetch.fetch(results[0].url)
        print(f"Title: {fetch_result.title}")
        print(f"Status: {fetch_result.status_code}")
        print(f"Fetch time: {fetch_result.fetch_time:.2f}s")
        print(f"Content preview: {fetch_result.content[:200]}...")
    
    print("\nTesting combined search and summarize...")
    summary = await tools.search_and_summarize("TypeScript best practices", 3)
    print(summary.get("summary", "No summary")[:500])


if __name__ == "__main__":
    asyncio.run(test_web_tools())
