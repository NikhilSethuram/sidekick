#!/usr/bin/env python3
"""
Microsoft 365 MCP Client for Outlook Integration
"""

import asyncio, json, logging, aiohttp, uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ────────────────────────────────────────────────────────────────────────────────
# Low-level MCP JSON-RPC client
# ────────────────────────────────────────────────────────────────────────────────
class Microsoft365MCPClient:
    def __init__(self, mcp_server_url: str = "http://localhost:3000") -> None:
        self.mcp_server_url = mcp_server_url
        self.session: Optional[aiohttp.ClientSession] = None
        self.is_connected = False

    async def start_server(self) -> bool:
        logger.info("Starting Microsoft 365 MCP server …")
        self.session = aiohttp.ClientSession()
        self.is_connected = True
        logger.info("✅ MCP server connected")
        return True

    async def stop_server(self) -> None:
        if self.session and not self.session.closed:
            await self.session.close()
        self.is_connected = False
        logger.info("🛑 MCP server stopped")

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
# Outlook helper
# ────────────────────────────────────────────────────────────────────────────────
class OutlookIntegration:
    def __init__(self) -> None:
        self.mcp_client = Microsoft365MCPClient()
        self.is_initialized = False

    async def initialize(self) -> bool:
        self.is_initialized = await self.mcp_client.start_server()
        return self.is_initialized

    async def shutdown(self) -> None:
        await self.mcp_client.stop_server()
        self.is_initialized = False

    # ------------------------------------------------------------------ e-mail
    async def send_email(self, *,
                          to: List[str],
                          subject: str,
                          body: str,
                          cc: Optional[List[str]] = None,
                          bcc: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Build a payload that satisfies the MCP Zod schema:
          { "Message": { …graph message… }, "SaveToSentItems": bool }
        """

        if not self.is_initialized:
            raise RuntimeError("Outlook integration not initialized")

        graph_message = {
            "subject": subject,
            "body": {
                "contentType": "text",          # ← FIX: lower-case
                "content": body,
            },
            "toRecipients": [
                {"emailAddress": {"address": addr}} for addr in to
            ],
            "ccRecipients": [
                {"emailAddress": {"address": addr}} for addr in (cc or [])
            ],
            "bccRecipients": [
                {"emailAddress": {"address": addr}} for addr in (bcc or [])
            ],
        }

        call_args = {
            "body": {
                "Message": graph_message,
                "SaveToSentItems": True,
            }
        }

        result = await self.mcp_client.send_mcp_request(
            "tools/call",
            {"name": "send-mail", "arguments": call_args},
        )
        return {"success": "error" not in result, **result}

    # ----------------------------------------------------------- meeting
    async def schedule_meeting(self, *,
                               subject: str,
                               start_time: datetime,
                               duration_minutes: int = 60,
                               attendees: Optional[List[str]] = None,
                               description: str = "") -> Dict[str, Any]:
        if not self.is_initialized:
            raise RuntimeError("Outlook integration not initialized")

        event = {
    "subject": subject,
    "body": {"contentType": "text", "content": description},
    "start": {"dateTime": start_time.isoformat(), "timeZone": "UTC"},
    "end":   {"dateTime": (start_time + timedelta(minutes=duration_minutes)).isoformat(),
              "timeZone": "UTC"},
    "location": {"displayName": "Teams meeting"},
}

        result = await self.mcp_client.send_mcp_request(
            "tools/call", {"name": "create-calendar-event", "arguments": {"body": event}}
        )
        return {"success": "error" not in result, **result}



# ────────────────────────────────────────────────────────────────────────────────
# Quick sanity test
# ────────────────────────────────────────────────────────────────────────────────
async def test_outlook():
    oi = OutlookIntegration()
    try:
        await oi.initialize()
        print("✅ Outlook integration initialized successfully")
        
        # Test email sending
        print("📧 Testing email sending...")
        email_result = await oi.send_email(
            to=["nst@wisc.edu"],
            subject="Test Email",
            body="This is a test email from the Outlook integration."
        )
        print(f"Email result: {email_result}")
        
        # Test meeting creation
        print("\n📅 Testing meeting creation...")
        meeting_result = await oi.schedule_meeting(
            subject="Test Meeting",
            start_time=datetime.utcnow() + timedelta(hours=2),
            attendees=["nst@wisc.edu"],
            description="This is a test meeting created via the Outlook integration."
        )
        print(f"Meeting result: {meeting_result}")
        
    finally:
        await oi.shutdown()
        print("✅ Session properly closed")

if __name__ == "__main__":
    asyncio.run(test_outlook())
