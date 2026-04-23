"""Main MCP server with stdio transport."""

import asyncio
import json
import sys
import logging
from typing import Any, Dict
from .config import settings
from .registry import ModelRegistry
from .mcp.tools import generate_mcp_tools, execute_tool

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr  # Log to stderr to avoid interfering with stdio protocol
)
logger = logging.getLogger(__name__)


class MCPServer:
    """MCP server for ML model registry."""
    
    def __init__(self):
        self.registry = ModelRegistry()
        self.initialized = False
    
    async def initialize(self):
        """Initialize the server and registry."""
        if self.initialized:
            return
        
        logger.info("Initializing MCP server...")
        await self.registry.initialize()
        self.initialized = True
        logger.info("MCP server initialized successfully")
    
    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming MCP request.
        
        Args:
            request: JSON-RPC request
            
        Returns:
            JSON-RPC response
        """
        method = request.get("method")
        params = request.get("params", {})
        request_id = request.get("id")
        
        logger.debug(f"Handling request: method={method}, id={request_id}")
        
        try:
            if method == "initialize":
                return await self._handle_initialize(request_id)
            
            elif method == "tools/list":
                return await self._handle_tools_list(request_id)
            
            elif method == "tools/call":
                return await self._handle_tools_call(request_id, params)
            
            elif method == "ping":
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {"status": "ok"}
                }
            
            else:
                logger.warning(f"Unknown method: {method}")
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32601,
                        "message": f"Method not found: {method}"
                    }
                }
        
        except Exception as e:
            logger.error(f"Error handling request: {e}", exc_info=True)
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32603,
                    "message": f"Internal error: {str(e)}"
                }
            }
    
    async def _handle_initialize(self, request_id: Any) -> Dict[str, Any]:
        """Handle initialize request."""
        await self.initialize()
        
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {}
                },
                "serverInfo": {
                    "name": settings.server_name,
                    "version": settings.server_version
                }
            }
        }
    
    async def _handle_tools_list(self, request_id: Any) -> Dict[str, Any]:
        """Handle tools/list request."""
        if not self.initialized:
            await self.initialize()
        
        logger.info("Listing available models...")
        models = await self.registry.list_all_models()
        tools = generate_mcp_tools(models)
        
        logger.info(f"Returning {len(tools)} tools")
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "tools": tools
            }
        }
    
    async def _handle_tools_call(self, request_id: Any, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tools/call request."""
        if not self.initialized:
            await self.initialize()
        
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        
        if not tool_name:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32602,
                    "message": "Missing required parameter: name"
                }
            }
        
        logger.info(f"Calling tool: {tool_name}")
        
        try:
            result = await execute_tool(tool_name, arguments, self.registry)
            
            # Format result as MCP content
            result_text = json.dumps(result, indent=2)
            
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": result_text
                        }
                    ]
                }
            }
        except Exception as e:
            logger.error(f"Tool execution failed: {e}", exc_info=True)
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32000,
                    "message": f"Tool execution failed: {str(e)}"
                }
            }
    
    async def run_stdio(self):
        """Run server with stdio transport.
        
        This is the main entry point for MCP clients like Claude Desktop.
        Reads JSON-RPC requests from stdin and writes responses to stdout.
        """
        await self.initialize()
        
        logger.info("MCP server running on stdio transport")
        logger.info(f"Enabled providers: {list(self.registry.providers.keys())}")
        
        # Read from stdin line by line
        while True:
            try:
                # Read a line from stdin
                line = await asyncio.get_event_loop().run_in_executor(
                    None, sys.stdin.readline
                )
                
                if not line:
                    logger.info("EOF received, shutting down")
                    break
                
                line = line.strip()
                if not line:
                    continue
                
                # Parse JSON-RPC request
                try:
                    request = json.loads(line)
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON: {e}")
                    continue
                
                # Handle request
                response = await self.handle_request(request)
                
                # Write response to stdout
                response_json = json.dumps(response)
                sys.stdout.write(response_json + "\n")
                sys.stdout.flush()
                
            except KeyboardInterrupt:
                logger.info("Received interrupt, shutting down")
                break
            except Exception as e:
                logger.error(f"Error in stdio loop: {e}", exc_info=True)
                break
        
        logger.info("MCP server stopped")


async def main():
    """Main entry point."""
    logger.info(f"Starting {settings.server_name} v{settings.server_version}")
    
    server = MCPServer()
    
    if settings.mcp_transport == "stdio":
        await server.run_stdio()
    else:
        logger.error(f"Unsupported transport: {settings.mcp_transport}")
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)

# Made with Bob
