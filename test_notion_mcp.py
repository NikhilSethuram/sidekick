#!/usr/bin/env python3
"""
Test script to check Notion MCP server connection
"""

import asyncio
import aiohttp
import json
import uuid

async def test_mcp_connection():
    """Test if the Notion MCP server is running"""
    
    # MCP server URL (default port)
    mcp_url = "http://localhost:3000/mcp"
    
    # Test payload
    payload = {
        "jsonrpc": "2.0",
        "id": str(uuid.uuid4()),
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {
                "name": "test-client",
                "version": "1.0.0"
            }
        }
    }
    
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream"
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            print(f"🔍 Testing connection to {mcp_url}...")
            
            async with session.post(mcp_url, json=payload, headers=headers) as response:
                print(f"📡 Response status: {response.status}")
                
                if response.status == 200:
                    result = await response.json()
                    print(f"✅ MCP server responded: {result}")
                    return True
                else:
                    error_text = await response.text()
                    print(f"❌ MCP server error: {error_text}")
                    return False
                    
    except aiohttp.ClientConnectorError as e:
        print(f"❌ Could not connect to MCP server: {e}")
        print("💡 Make sure the Notion MCP server is running on localhost:3000")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Testing Notion MCP Server Connection")
    print("=" * 50)
    
    success = asyncio.run(test_mcp_connection())
    
    if success:
        print("\n✅ MCP server is running and accessible!")
    else:
        print("\n❌ MCP server is not accessible")
        print("\n💡 To start the Notion MCP server:")
        print("1. Set environment variable: export OPENAPI_MCP_HEADERS='{\"Authorization\": \"Bearer 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\", \"Notion-Version\": \"2022-06-28\"}'")
        print("2. Run: npx -y @notionhq/notion-mcp-server") 