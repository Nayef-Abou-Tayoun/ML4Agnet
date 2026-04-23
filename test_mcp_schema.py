#!/usr/bin/env python3
"""Test script to show the MCP tool schema for your model."""

import asyncio
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

async def show_mcp_schema():
    """Show the MCP tool schema that clients will see."""
    print("=" * 60)
    print("MCP Tool Schema for Your Model")
    print("=" * 60)
    
    try:
        from src.registry import ModelRegistry
        from src.mcp.tools import generate_mcp_tools
        
        # Initialize and discover models
        print("\n1. Discovering models...")
        registry = ModelRegistry()
        await registry.initialize()
        models = await registry.list_all_models()
        
        if not models:
            print("   ⚠️  No models found!")
            return
        
        print(f"   ✓ Found {len(models)} model(s)")
        
        # Generate MCP tools
        print("\n2. Generating MCP tool schemas...")
        tools = generate_mcp_tools(models)
        
        # Display each tool schema
        for i, tool in enumerate(tools, 1):
            print(f"\n{'=' * 60}")
            print(f"Tool {i}: {tool['name']}")
            print(f"{'=' * 60}")
            print(f"\nDescription: {tool['description']}")
            print(f"\nInput Schema:")
            print(json.dumps(tool['inputSchema'], indent=2))
        
        print(f"\n{'=' * 60}")
        print("✅ Schema Information Complete")
        print(f"{'=' * 60}")
        
        print("\n📝 What This Means:")
        print("   • MCP clients (Claude, Cline, wxo) will see this schema")
        print("   • They'll know exactly what parameters to send")
        print("   • The schema is automatically extracted from your model")
        print("   • Clients can use this to validate inputs before calling")
        
        print("\n🔧 How Clients Use This:")
        print("   1. Client calls tools/list to get available tools")
        print("   2. Sees 'watsonx_demand_forecasting_ml' with its schema")
        print("   3. Knows what input_data structure to send")
        print("   4. Calls tools/call with properly formatted data")
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(show_mcp_schema())
    sys.exit(0 if success else 1)

# Made with Bob
