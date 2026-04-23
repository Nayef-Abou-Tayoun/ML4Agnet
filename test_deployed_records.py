#!/usr/bin/env python3
"""Test the deployed ML Registry with records format via MCP protocol."""

import asyncio
import json
import httpx

async def test_deployed_mcp():
    """Test prediction via deployed MCP endpoint."""
    
    # Deployed server URL
    base_url = "https://mlregistry12.27jid12fsm9n.us-south.codeengine.appdomain.cloud"
    
    # MCP tool call request
    mcp_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "watsonx_demand_forecasting_ml",
            "arguments": {
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
        }
    }
    
    print("Testing deployed ML Registry MCP endpoint...")
    print(f"URL: {base_url}/mcp")
    print(f"Model ID: 019db7a0-c668-70a0-8a32-6dcc5a1041df")
    print(f"Input format: records (19 fields, 19 values)")
    print()
    
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            # Send MCP request
            response = await client.post(
                f"{base_url}/mcp",
                json=mcp_request,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                result = response.json()
                print("✅ SUCCESS!")
                print(json.dumps(result, indent=2))
            else:
                print(f"❌ ERROR: HTTP {response.status_code}")
                print(response.text)
                
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_deployed_mcp())

# Made with Bob
