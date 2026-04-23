#!/usr/bin/env python3
"""Test the records format with the deployed ML Registry."""

import asyncio
import json
import os
from src.providers.watsonx import WatsonxProvider
from src.config import settings

async def test_records_format():
    """Test prediction with records format."""
    
    # Initialize provider with config dict
    provider = WatsonxProvider({
        "api_key": settings.watsonx_api_key,
        "url": settings.watsonx_url,
        "project_id": settings.watsonx_project_id,
        "space_id": settings.watsonx_space_id
    })
    await provider.initialize()
    
    # Test input with records format
    input_data = {
        "input_data": {
            "fields": [
                "PART_NUM",
                "STOCKING_PCT",
                "PART_SALES_QTY",
                "PART_SALES_AMT",
                "PART_SHIP_QTY",
                "PART_SHIP_AMT",
                "PART_DEMAND",
                "PART_CLASS_CDE",
                "PART_SALES_QTY_lag1",
                "PART_SALES_QTY_lag2",
                "PART_SALES_QTY_lag3",
                "PART_SALES_QTY_lag4",
                "PART_SALES_QTY_lag5",
                "PART_SALES_QTY_lag6",
                "rmean_PART_SALES_QTY_3",
                "month",
                "quarter",
                "year",
                "age_month"
            ],
            "records": [
                [
                    1129,
                    0,
                    0,
                    0,
                    0,
                    0,
                    44,
                    3,
                    4,
                    0,
                    0,
                    0,
                    0,
                    0,
                    1.33333333,
                    3,
                    1,
                    2018,
                    113.81
                ]
            ]
        },
        "parameters": {
            "timeout": 60
        }
    }
    
    # Model ID
    model_id = "019db7a0-c668-70a0-8a32-6dcc5a1041df"
    
    print("Testing prediction with 'records' format...")
    print(f"Model ID: {model_id}")
    print(f"Input fields count: {len(input_data['input_data']['fields'])}")
    print(f"Input values count: {len(input_data['input_data']['records'][0])}")
    print()
    
    try:
        result = await provider.predict(model_id, input_data)
        print("✅ SUCCESS!")
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_records_format())

# Made with Bob
