#!/usr/bin/env python3
"""
Notion MCP Client for Notion Integration
"""

import asyncio, json, logging, aiohttp, uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ────────────────────────────────────────────────────────────────────────────────
# Low-level MCP JSON-RPC client for Notion
# ────────────────────────────────────────────────────────────────────────────────
class NotionMCPClient:
    def __init__(self, mcp_server_url: str = "http://localhost:3000") -> None:
        self.mcp_server_url = mcp_server_url
        self.session: Optional[aiohttp.ClientSession] = None
        self.is_connected = False

    async def start_server(self) -> bool:
        logger.info("Starting Notion MCP server …")
        self.session = aiohttp.ClientSession()
        self.is_connected = True
        logger.info("✅ Notion MCP server connected")
        return True

    async def stop_server(self) -> None:
        if self.session and not self.session.closed:
            await self.session.close()
        self.is_connected = False
        logger.info("🛑 Notion MCP server stopped")

    async def send_mcp_request(self, method: str,
                               params: Dict[str, Any]) -> Dict[str, Any]:
        if not self.session:
            return {"error": "No active session"}

        payload = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": method,
            "params": params,
        }
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }

        async with self.session.post(f"{self.mcp_server_url}/mcp",
                                     json=payload, headers=headers) as r:
            ctype = r.headers.get("Content-Type", "")
            if r.status != 200:
                return {"error": f"{r.status}: {await r.text()}"}

            if ctype.startswith("application/json"):
                return await r.json()

            if ctype.startswith("text/event-stream"):
                async for line in r.content:
                    line = line.decode().strip()
                    if line.startswith("data: "):
                        return json.loads(line[6:])

            return {"error": f"unexpected content-type {ctype}"}


# ────────────────────────────────────────────────────────────────────────────────
# Notion helper
# ────────────────────────────────────────────────────────────────────────────────
class NotionIntegration:
    def __init__(self) -> None:
        self.mcp_client = NotionMCPClient()
        self.is_initialized = False

    async def initialize(self) -> bool:
        self.is_initialized = await self.mcp_client.start_server()
        return self.is_initialized

    async def shutdown(self) -> None:
        await self.mcp_client.stop_server()
        self.is_initialized = False

    # ------------------------------------------------------------------ Search pages
    async def search_pages(self, query: str = "") -> Dict[str, Any]:
        """Search for pages in Notion"""
        if not self.is_initialized:
            raise RuntimeError("Notion integration not initialized")

        search_params = {
            "filter": {
                "value": "page",
                "property": "object"
            }
        }
        
        if query:
            search_params["query"] = query

        result = await self.mcp_client.send_mcp_request(
            "tools/call",
            {"name": "v1/search", "arguments": search_params},
        )
        return {"success": "error" not in result, **result}

    # ------------------------------------------------------------------ Get page content
    async def get_page_content(self, page_id: str) -> Dict[str, Any]:
        """Get the content of a specific page"""
        if not self.is_initialized:
            raise RuntimeError("Notion integration not initialized")

        result = await self.mcp_client.send_mcp_request(
            "tools/call",
            {"name": "v1/pages/{page_id}", "arguments": {"page_id": page_id}},
        )
        return {"success": "error" not in result, **result}

    # ------------------------------------------------------------------ Create page
    async def create_page(self, *, 
                         title: str,
                         parent_page_id: str,
                         content: str = "") -> Dict[str, Any]:
        """Create a new page in Notion"""
        if not self.is_initialized:
            raise RuntimeError("Notion integration not initialized")

        page_data = {
            "parent": {
                "page_id": parent_page_id
            },
            "properties": {
                "title": {
                    "title": [
                        {
                            "text": {
                                "content": title
                            }
                        }
                    ]
                }
            }
        }

        if content:
            page_data["children"] = [
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": content
                                }
                            }
                        ]
                    }
                }
            ]

        result = await self.mcp_client.send_mcp_request(
            "tools/call",
            {"name": "v1/pages", "arguments": page_data},
        )
        return {"success": "error" not in result, **result}

    # ------------------------------------------------------------------ Add comment
    async def add_comment(self, *, 
                         page_id: str,
                         comment_text: str) -> Dict[str, Any]:
        """Add a comment to a page"""
        if not self.is_initialized:
            raise RuntimeError("Notion integration not initialized")

        comment_data = {
            "parent": {
                "page_id": page_id
            },
            "rich_text": [
                {
                    "text": {
                        "content": comment_text
                    }
                }
            ]
        }

        result = await self.mcp_client.send_mcp_request(
            "tools/call",
            {"name": "v1/comments", "arguments": comment_data},
        )
        return {"success": "error" not in result, **result}


# ────────────────────────────────────────────────────────────────────────────────
# Quick sanity test
# ────────────────────────────────────────────────────────────────────────────────
async def test_notion():
    ni = NotionIntegration()
    try:
        await ni.initialize()
        print("✅ Notion integration initialized successfully")
        
        # Test page search
        print("🔍 Testing page search...")
        search_result = await ni.search_pages("Getting started")
        print(f"Search result: {search_result}")
        
        # Test page creation (commented out as it requires valid page IDs)
        # print("\n📝 Testing page creation...")
        # create_result = await ni.create_page(
        #     title="Test Page via MCP",
        #     parent_page_id="your-parent-page-id",
        #     content="This is a test page created via the Notion MCP integration."
        # )
        # print(f"Create result: {create_result}")
        
    finally:
        await ni.shutdown()
        print("✅ Session properly closed")

if __name__ == "__main__":
    asyncio.run(test_notion()) 