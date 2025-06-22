import aiohttp
import asyncio
import json
import uuid
from typing import Any, Dict, Optional, AsyncGenerator

NOTION_MCP_URL = "http://localhost:3000/mcp"

async def send_notion_mcp_request(method: str, params: Dict[str, Any]) -> Any:
    """
    Send a request to the Notion MCP server and handle both JSON and event-stream responses.
    Returns the first event or the JSON response.
    """
    payload = {
        "jsonrpc": "2.0",
        "id": str(uuid.uuid4()),
        "method": method,
        "params": params,
    }
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream"
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(NOTION_MCP_URL, json=payload, headers=headers) as resp:
            ctype = resp.headers.get("Content-Type", "")
            if resp.status != 200:
                text = await resp.text()
                raise RuntimeError(f"MCP error {resp.status}: {text}")
            if ctype.startswith("application/json"):
                return await resp.json()
            elif ctype.startswith("text/event-stream"):
                # Read the first event (or all events if you want streaming)
                async for line in resp.content:
                    line = line.decode().strip()
                    if line.startswith("data: "):
                        return json.loads(line[6:])
                raise RuntimeError("No data event in event-stream response")
            else:
                raise RuntimeError(f"Unexpected content-type: {ctype}")

# Example: Search pages
async def notion_search_pages(query: str = "") -> Any:
    params = {
        "name": "v1/search",
        "arguments": {
            "filter": {"value": "page", "property": "object"},
            **({"query": query} if query else {})
        }
    }
    return await send_notion_mcp_request("tools/call", params)

# Example: Get page content
async def notion_get_page(page_id: str) -> Any:
    params = {
        "name": "v1/pages/{page_id}",
        "arguments": {"page_id": page_id}
    }
    return await send_notion_mcp_request("tools/call", params)

# Example: Create a page
async def notion_create_page(title: str, parent_page_id: str, content: Optional[str] = None) -> Any:
    page_data = {
        "parent": {"page_id": parent_page_id},
        "properties": {
            "title": {
                "title": [
                    {"text": {"content": title}}
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
                        {"type": "text", "text": {"content": content}}
                    ]
                }
            }
        ]
    params = {
        "name": "v1/pages",
        "arguments": page_data
    }
    return await send_notion_mcp_request("tools/call", params)

# Example usage
if __name__ == "__main__":
    async def main():
        print("🔍 Searching for pages containing 'Getting started'...")
        result = await notion_search_pages("Getting started")
        print(json.dumps(result, indent=2))

        # Uncomment and fill in a real page ID to test get/create
        # print("\n📄 Getting a page by ID...")
        # page = await notion_get_page("your-page-id")
        # print(json.dumps(page, indent=2))

        # print("\n📝 Creating a new page...")
        # new_page = await notion_create_page("Test Page", "your-parent-page-id", "This is a test.")
        # print(json.dumps(new_page, indent=2))

    asyncio.run(main()) 