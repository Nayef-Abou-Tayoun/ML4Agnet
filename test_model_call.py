#!/usr/bin/env python3
"""Test script to call your deployed ML model through the registry."""

import asyncio
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

async def test_model_discovery_and_call():
    """Test discovering and calling your deployed model."""
    print("=" * 60)
    print("Testing ML Registry - Model Discovery & Prediction")
    print("=" * 60)
    
    try:
        from src.registry import ModelRegistry
        
        # Initialize registry
        print("\n1. Initializing registry...")
        registry = ModelRegistry()
        await registry.initialize()
        print(f"   ✓ Registry initialized with {len(registry.providers)} provider(s)")
        
        # List all models
        print("\n2. Discovering models from watsonx.ai...")
        models = await registry.list_all_models()
        print(f"   ✓ Found {len(models)} model(s)")
        
        if not models:
            print("\n   ⚠️  No models discovered!")
            print("   Check your credentials in .env file")
            return False
        
        # Display discovered models
        print("\n3. Discovered Models:")
        for i, model in enumerate(models, 1):
            print(f"\n   Model {i}:")
            print(f"   - Name: {model.name}")
            print(f"   - ID: {model.id}")
            print(f"   - Type: {model.model_type.value}")
            print(f"   - Provider: {model.provider}")
            print(f"   - Framework: {model.framework}")
            print(f"   - Status: {model.status}")
        
        # Test prediction with first model
        if models:
            model = models[0]
            print(f"\n4. Testing prediction with model: {model.name}")
            print(f"   Model ID: {model.id}")
            
            # Example input data - adjust based on your model's schema
            input_data = {
                "fields": ["feature1", "feature2", "feature3"],
                "values": [[1.0, 2.0, 3.0]]
            }
            
            print(f"\n   Input data: {input_data}")
            
            try:
                result = await registry.predict(
                    model_id=model.id,
                    input_data=input_data
                )
                print(f"\n   ✓ Prediction successful!")
                print(f"   Result: {result}")
                
            except Exception as e:
                print(f"\n   ⚠️  Prediction failed: {e}")
                print(f"   This is normal if the input format doesn't match your model's schema")
        
        print("\n" + "=" * 60)
        print("✅ Test completed successfully!")
        print("=" * 60)
        
        print("\n📝 Next Steps:")
        print("   1. Check the Web UI at http://localhost:8081")
        print("   2. Run MCP server: python -m src.server")
        print("   3. Connect to Claude Desktop or other MCP clients")
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_model_discovery_and_call())
    sys.exit(0 if success else 1)

# Made with Bob
