"""CLI entry point for ml-registry-mcp-server."""

import sys
import argparse
import asyncio
from .server import main as server_main


def cli():
    """Command-line interface for ML Registry MCP Server."""
    parser = argparse.ArgumentParser(
        description="ML Registry MCP Server - Expose watsonx.ai models via MCP protocol"
    )
    
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse"],
        default="stdio",
        help="Transport protocol (default: stdio)"
    )
    
    parser.add_argument(
        "--wxo",
        action="store_true",
        help="Enable watsonx Orchestrate compatibility mode"
    )
    
    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="Port for SSE transport (default: 8080)"
    )
    
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host for SSE transport (default: 0.0.0.0)"
    )
    
    args = parser.parse_args()
    
    # Set environment variable for transport
    import os
    os.environ["MCP_TRANSPORT"] = args.transport
    
    if args.wxo:
        print("watsonx Orchestrate compatibility mode enabled", file=sys.stderr)
    
    if args.transport == "stdio":
        # Run stdio server
        asyncio.run(server_main())
    elif args.transport == "sse":
        # Run SSE server
        print(f"Starting SSE server on {args.host}:{args.port}", file=sys.stderr)
        from .unified_server import app
        import uvicorn
        uvicorn.run(app, host=args.host, port=args.port)
    else:
        print(f"Unsupported transport: {args.transport}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    cli()

# Made with Bob
