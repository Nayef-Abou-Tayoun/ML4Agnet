#!/usr/bin/env python3
"""Quick test script for ML Registry MCP Server."""

import asyncio
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

async def test_server():
    """Test the MCP server initialization."""
    print("Testing ML Registry MCP Server...")
    print("-" * 50)
    
    try:
        from src.server import MCPServer
        from src.config import settings
        
        print(f"✓ Imports successful")
        print(f"✓ Server name: {settings.server_name}")
        print(f"✓ Server version: {settings.server_version}")
        print(f"✓ watsonx enabled: {settings.watsonx_enabled}")
        
        # Create server instance
        server = MCPServer()
        print(f"✓ Server instance created")
        
        # Test initialization
        await server.initialize()
        print(f"✓ Server initialized")
        print(f"✓ Providers loaded: {list(server.registry.providers.keys())}")
        
        # Test request handling
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {}
        }
        
        response = await server.handle_request(request)
        print(f"✓ Initialize request handled")
        print(f"✓ Protocol version: {response['result']['protocolVersion']}")
        
        # Test tools/list
        request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {}
        }
        
        response = await server.handle_request(request)
        tools = response['result']['tools']
        print(f"✓ Tools list request handled")
        print(f"✓ Number of tools (models): {len(tools)}")
        
        print("-" * 50)
        print("✅ ALL TESTS PASSED!")
        print("\nThe ML Registry MCP Server is ready for use!")
        print("\nTo run the server:")
        print("  python -m src.server")
        print("\nTo run the Web UI:")
        print("  python -m src.ui")
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_server())
    sys.exit(0 if success else 1)

# Made with Bob
