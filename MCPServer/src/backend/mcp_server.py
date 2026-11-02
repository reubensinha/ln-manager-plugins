from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import APIRouter
from mcp.server import MCPServer
from mcp.server.transport_security import TransportSecuritySettings

from backend.core.plugins.generic import GenericPlugin
from backend.plugins.MCPServer.library_tools import register_tools


class MCPServerPlugin(GenericPlugin):
    """Serves the library over MCP (Streamable HTTP) under this plugin's API prefix."""

    name = "MCPServer"
    version = "0.1.0"
    description = "Exposes the library over the Model Context Protocol (read-only)"

    # The handler is attached as a raw ASGI route, so it sees the full request path.
    mcp_path = f"/api/plugins/{name}/mcp"

    def start(self) -> None:
        self.mcp = MCPServer(
            "LN-Manager",
            instructions=(
                "Read-only access to a light novel library. Start with list_library "
                "or search_library, then drill into get_series / get_book. "
                "upcoming_releases lists what is coming out soon."
            ),
        )
        register_tools(self.mcp)
        # The app is reached via LAN hostnames / Docker, not just localhost, so the
        # SDK's localhost-only DNS-rebinding allowlist would reject real clients.
        self.asgi_app = self.mcp.streamable_http_app(
            streamable_http_path=self.mcp_path,
            transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
        )
        self.logger.info(f"MCP server ready at {self.mcp_path}")

    def stop(self) -> None:
        self.logger.info("MCP server stopped")

    @asynccontextmanager
    async def lifespan(self) -> AsyncGenerator[None, None]:
        async with self.mcp.session_manager.run():
            yield

    def get_api_router(self) -> APIRouter:
        router = APIRouter()
        router.add_route("/mcp", self.asgi_app)

        @router.get("/info")
        async def info():
            return {
                "endpoint": self.mcp_path,
                "transport": "streamable-http",
                "auth": "none",
                "tools": [t.name for t in await self.mcp.list_tools()],
            }

        return router
