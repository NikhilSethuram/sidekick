#!/usr/bin/env python3
"""
Microsoft 365 MCP Client for Outlook Integration
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import aiohttp

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

    # ---------------------------------------------------------------------- init
    async def start_server(self) -> bool:
        """Create one long-lived aiohttp session."""
        logger.info("Starting Microsoft 365 MCP server …")
        self.session = aiohttp.ClientSession()
        self.is_connected = True
        logger.info("✅ MCP server connected")
        return True

    # --------------------------------------------------------------------- close
    async def stop_server(self) -> None:
        """Close the long-lived session (avoids ‘Unclosed client session’)."""
        if self.session and not self.session.closed:
            await self.session.close()
        self.is_connected = False
        logger.info("🛑 MCP server stopped")

    # ------------------------------------------------------------------- request
    async def send_mcp_request(self, method: str,
                               params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make one JSON-RPC 2.0 call.
        Uses a short-lived *per-request* session so we don’t depend
        on the long-lived one for actual I/O.
        """
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

        async with aiohttp.ClientSession() as s:
            async with s.post(f"{self.mcp_server_url}/mcp",
                              json=payload, headers=headers) as r:
                ctype = r.headers.get("Content-Type", "")
                if r.status != 200:
                    return {"error": f"{r.status}: {await r.text()}"}

                if ctype.startswith("application/json"):
                    return await r.json()

                if ctype.startswith("text/event-stream"):
                    async for line in r.content:
                        if line.startswith(b"data: "):
                            return json.loads(line[6:].decode())

                return {"error": f"unexpected content-type {ctype}"}


# ────────────────────────────────────────────────────────────────────────────────
# Outlook-level helper
# ────────────────────────────────────────────────────────────────────────────────
class OutlookIntegration:
    def __init__(self) -> None:
        self.mcp_client = Microsoft365MCPClient()
        self.is_initialized = False

    # ---------------------------------------------------------------- init/stop
    async def initialize(self) -> bool:
        self.is_initialized = await self.mcp_client.start_server()
        return self.is_initialized

    async def shutdown(self) -> None:
        await self.mcp_client.stop_server()
        self.is_initialized = False

    # ---------------------------------------------------------------- send mail
    async def send_email(self, *, to: List[str], subject: str, body: str,
                         cc: Optional[List[str]] = None,
                         bcc: Optional[List[str]] = None) -> Dict[str, Any]:
        if not self.is_initialized:
            raise RuntimeError("Outlook integration not initialized")

        # field names must be lower-camel exactly as in microsoft_graph_message
        message = {
            "subject": subject,
            "body": {
                "contentType": "Text",
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

        result = await self.mcp_client.send_mcp_request(
            "tools/call",
            {
                "name": "send-mail",
                "arguments": {
                    "body": {
                        "Message": message,
                        "SaveToSentItems": True,
                    }
                },
            },
        )
        return {"success": "error" not in result, **result}

    # -------------------------------------------------------------- create event
    async def schedule_meeting(self, *, subject: str,
                               start_time: datetime,
                               duration_minutes: int = 60,
                               attendees: Optional[List[str]] = None,
                               description: str = "") -> Dict[str, Any]:
        if not self.is_initialized:
            raise RuntimeError("Outlook integration not initialized")

        event = {
            "subject": subject,
            "body": {
                "contentType": "text",        # enum is lower-case here
                "content": description,
            },
            "start": {
                "dateTime": start_time.isoformat(),
                "timeZone": "UTC",
            },
            "end": {
                "dateTime": (start_time + timedelta(
                    minutes=duration_minutes)).isoformat(),
                "timeZone": "UTC",
            },
            "attendees": [
                {"emailAddress": {"address": e}} for e in (attendees or [])
            ],
            "location": {"displayName": "Teams Meeting"},
        }

        result = await self.mcp_client.send_mcp_request(
            "tools/call",
            {"name": "create-calendar-event", "arguments": {"body": event}},
        )
        return {"success": "error" not in result, **result}

    # other helpers unchanged ---------------------------------------------------
    async def get_calendar_events(self, start_date: datetime = None,
                                  end_date: datetime = None) -> Dict[str, Any]:
        if not self.is_initialized:
            raise RuntimeError("Outlook integration not initialized")

        start_date = start_date or datetime.utcnow()
        end_date = end_date or (start_date + timedelta(days=7))

        result = await self.mcp_client.send_mcp_request(
            "tools/call",
            {
                "name": "list-calendar-events",
                "arguments": {
                    "startTime": start_date.isoformat(),
                    "endTime": end_date.isoformat(),
                },
            },
        )
        return {"success": "error" not in result, **result}

    async def check_availability(self, start_time: datetime,
                                 end_time: datetime) -> Dict[str, Any]:
        if not self.is_initialized:
            raise RuntimeError("Outlook integration not initialized")

        result = await self.mcp_client.send_mcp_request(
            "tools/call",
            {
                "name": "get-calendar-view",
                "arguments": {
                    "startDateTime": start_time.isoformat(),
                    "endDateTime": end_time.isoformat(),
                },
            },
        )
        return {"success": "error" not in result, **result}


# ────────────────────────────────────────────────────────────────────────────────
# Minimal self-test with proper cleanup (no “Unclosed client session” warning)
# ────────────────────────────────────────────────────────────────────────────────
async def _quick_test() -> None:
    oi = OutlookIntegration()
    await oi.initialize()

    try:
        print("📧  sending test email …")
        print(await oi.send_email(
            to=["you@example.com"],
            subject="[MCP] hello",
            body="This came from the fixed script!"
        ))

        print("📅  creating test meeting …")
        print(await oi.schedule_meeting(
            subject="[MCP] quick meet",
            start_time=datetime.utcnow() + timedelta(hours=2),
            attendees=["you@example.com"],
            description="demo"
        ))
    finally:
        await oi.shutdown()           # ← ensures session is closed


if __name__ == "__main__":
    asyncio.run(_quick_test())
