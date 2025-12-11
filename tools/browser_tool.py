"""
Browser Tool - Web browsing superpowers using Playwright
Read websites, extract content, find contact info
"""
import asyncio
import re
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
from .base_tool import BaseTool, ToolResult

# Limits
MAX_PAGE_LOAD_TIME = 30000  # 30 seconds for full page load
MAX_CONTENT_LENGTH = 8000  # chars to send to LLM


class BrowserTool(BaseTool):
    name = "browser"
    description = "Browse websites, read content, extract information"
    
    def get_function_schemas(self) -> list[dict]:
        return [
            self._make_schema(
                name="browse_website",
                description="Visit a website and extract its main content. Use this to read company websites, find contact info, get details about businesses.",
                parameters={
                    "url": {"type": "string", "description": "The URL to visit (e.g., https://example.com)"},
                    "extract": {"type": "string", "description": "What to extract: 'all' for full content, 'contact' for contact info, 'about' for about/company info", "enum": ["all", "contact", "about"]}
                },
                required=["url"]
            ),
            self._make_schema(
                name="search_and_browse",
                description="Search Google and browse the top result to get detailed information",
                parameters={
                    "query": {"type": "string", "description": "Search query"},
                },
                required=["query"]
            ),
        ]
    
    async def execute(self, function_name: str, arguments: dict) -> ToolResult:
        try:
            if function_name == "browse_website":
                return await self._browse_website(**arguments)
            elif function_name == "search_and_browse":
                return await self._search_and_browse(**arguments)
            else:
                return ToolResult(success=False, error=f"Unknown function: {function_name}")
        except Exception as e:
            return ToolResult(success=False, error=str(e))
    
    async def _browse_website(self, url: str, extract: str = "all") -> ToolResult:
        """Browse a website and extract content"""
        browser = None
        try:
            # Ensure URL has protocol
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                )
                page = await context.new_page()
                
                # Navigate with timeout - wait for network to be idle
                try:
                    await page.goto(url, timeout=MAX_PAGE_LOAD_TIME, wait_until="networkidle")
                except PlaywrightTimeout:
                    # Try with just load if networkidle times out
                    try:
                        await page.goto(url, timeout=15000, wait_until="load")
                    except:
                        await browser.close()
                        return ToolResult(success=False, error=f"Page took too long to load: {url}")
                
                # Wait for any animations/dynamic content to settle
                await asyncio.sleep(2)
                
                # Wait for body to be stable (no more changes)
                try:
                    await page.wait_for_load_state("networkidle", timeout=5000)
                except:
                    pass  # Continue anyway if this times out
                
                # Extract based on type
                if extract == "contact":
                    content = await self._extract_contact_info(page)
                elif extract == "about":
                    content = await self._extract_about_info(page)
                else:
                    content = await self._extract_all_content(page)
                
                await browser.close()
                
                if not content:
                    return ToolResult(success=True, data="Could not extract content from this page")
                
                # Limit content length
                if len(content) > MAX_CONTENT_LENGTH:
                    content = content[:MAX_CONTENT_LENGTH] + "\n\n[Content truncated...]"
                
                return ToolResult(success=True, data=content)
        
        except PlaywrightTimeout:
            return ToolResult(success=False, error=f"Timeout loading {url}")
        except Exception as e:
            return ToolResult(success=False, error=f"Failed to browse {url}: {str(e)}")
        finally:
            if browser:
                try:
                    await browser.close()
                except:
                    pass
    
    async def _extract_all_content(self, page) -> str:
        """Extract main text content from page"""
        # Get page title
        title = await page.title()
        
        # Try to get main content
        content_selectors = [
            'main', 'article', '[role="main"]', '.content', '#content',
            '.main-content', '#main-content', '.post-content', '.entry-content'
        ]
        
        text = ""
        for selector in content_selectors:
            try:
                element = await page.query_selector(selector)
                if element:
                    text = await element.inner_text()
                    break
            except:
                continue
        
        # Fallback to body
        if not text:
            text = await page.inner_text('body')
        
        # Clean up text
        text = self._clean_text(text)
        
        # Limit length
        if len(text) > 4000:
            text = text[:4000] + "..."
        
        return f"**{title}**\n\n{text}"
    
    async def _extract_contact_info(self, page) -> str:
        """Extract contact information from page"""
        html = await page.content()
        text = await page.inner_text('body')
        
        results = []
        
        # Find emails
        emails = set(re.findall(r'[\w\.-]+@[\w\.-]+\.\w+', html))
        if emails:
            results.append(f"**Emails:** {', '.join(emails)}")
        
        # Find phone numbers
        phones = set(re.findall(r'[\+]?[(]?[0-9]{1,4}[)]?[-\s\.]?[0-9]{1,4}[-\s\.]?[0-9]{1,9}', text))
        phones = [p for p in phones if len(p.replace(' ', '').replace('-', '')) >= 7]
        if phones:
            results.append(f"**Phones:** {', '.join(list(phones)[:5])}")
        
        # Find social links
        social_patterns = {
            'LinkedIn': r'linkedin\.com/(?:company|in)/[\w-]+',
            'Twitter': r'twitter\.com/[\w]+',
            'Facebook': r'facebook\.com/[\w]+',
            'Instagram': r'instagram\.com/[\w]+',
        }
        
        for platform, pattern in social_patterns.items():
            matches = re.findall(pattern, html)
            if matches:
                results.append(f"**{platform}:** https://{matches[0]}")
        
        # Find address
        address_keywords = ['address', 'location', 'office', 'headquarters']
        for kw in address_keywords:
            try:
                elem = await page.query_selector(f'[class*="{kw}"], [id*="{kw}"]')
                if elem:
                    addr_text = await elem.inner_text()
                    if addr_text and len(addr_text) < 200:
                        results.append(f"**Address:** {addr_text.strip()}")
                        break
            except:
                continue
        
        # Look for contact page link
        contact_link = await page.query_selector('a[href*="contact"]')
        if contact_link:
            href = await contact_link.get_attribute('href')
            if href:
                results.append(f"**Contact Page:** {href}")
        
        if not results:
            return "No contact information found on this page"
        
        return "\n".join(results)
    
    async def _extract_about_info(self, page) -> str:
        """Extract about/company information"""
        title = await page.title()
        
        # Try about-specific selectors
        about_selectors = [
            '[class*="about"]', '[id*="about"]',
            '[class*="company"]', '[id*="company"]',
            '[class*="who-we-are"]', '[class*="our-story"]',
            'main', 'article'
        ]
        
        text = ""
        for selector in about_selectors:
            try:
                element = await page.query_selector(selector)
                if element:
                    text = await element.inner_text()
                    if len(text) > 100:
                        break
            except:
                continue
        
        if not text:
            text = await page.inner_text('body')
        
        text = self._clean_text(text)
        
        if len(text) > 3000:
            text = text[:3000] + "..."
        
        return f"**{title}**\n\n{text}"
    
    async def _search_and_browse(self, query: str) -> ToolResult:
        """Search Google and browse top result"""
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                )
                page = await context.new_page()
                
                # Search Google
                search_url = f"https://www.google.com/search?q={query}"
                await page.goto(search_url, timeout=15000, wait_until="networkidle")
                await asyncio.sleep(2)
                
                # Get first result link
                result_link = await page.query_selector('div.g a[href^="http"]')
                if not result_link:
                    await browser.close()
                    return ToolResult(success=False, error="No search results found")
                
                href = await result_link.get_attribute('href')
                
                # Navigate to result - wait for full load
                await page.goto(href, timeout=MAX_PAGE_LOAD_TIME, wait_until="networkidle")
                await asyncio.sleep(2)
                
                # Extra wait for dynamic content
                try:
                    await page.wait_for_load_state("networkidle", timeout=5000)
                except:
                    pass
                
                # Extract content
                content = await self._extract_all_content(page)
                
                await browser.close()
                
                return ToolResult(success=True, data=f"**Source:** {href}\n\n{content}")
                
        except Exception as e:
            return ToolResult(success=False, error=f"Search and browse failed: {str(e)}")
    
    def _clean_text(self, text: str) -> str:
        """Clean extracted text"""
        # Remove excessive whitespace
        text = re.sub(r'\n\s*\n', '\n\n', text)
        text = re.sub(r' +', ' ', text)
        # Remove common navigation/footer junk
        lines = text.split('\n')
        cleaned = []
        skip_patterns = ['cookie', 'privacy policy', 'terms of service', 'all rights reserved']
        for line in lines:
            line = line.strip()
            if line and len(line) > 2:
                if not any(p in line.lower() for p in skip_patterns):
                    cleaned.append(line)
        return '\n'.join(cleaned)
