#!/usr/bin/env python3
"""Test script for MCP prediction endpoint."""

import requests
import json

# MCP endpoint
MCP_URL = "http://localhost:8082/mcp"

# Test data
test_request = {
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
        "name": "watsonx_demand_forecasting_ml",
        "arguments": {
            "input_data": [{
                "fields": [
                    "PART_NUM", "STOCKING_PCT", "PART_SALES_QTY", "PART_SALES_AMT",
                    "PART_SHIP_QTY", "PART_SHIP_AMT", "PART_DEMAND", "PART_CLASS_CDE",
                    "PART_SALES_QTY_lag1", "PART_SALES_QTY_lag2", "PART_SALES_QTY_lag3",
                    "PART_SALES_QTY_lag4", "PART_SALES_QTY_lag5", "PART_SALES_QTY_lag6",
                    "rmean_PART_SALES_QTY_3", "month", "quarter", "year", "age_month"
                ],
                "values": [[
                    1129, 0, 0, 0, 0, 0, 44, 3, 4, 0, 0, 0, 0, 0, 1.33333333, 3, 1, 2018, 113.81
                ]]
            }]
        }
    },
    "id": 1
}

print("=" * 80)
print("Testing MCP Prediction Endpoint")
print("=" * 80)
print(f"\nEndpoint: {MCP_URL}")
print(f"\nRequest:")
print(json.dumps(test_request, indent=2))

try:
    response = requests.post(MCP_URL, json=test_request, timeout=30)
    print(f"\nStatus Code: {response.status_code}")
    print(f"\nResponse:")
    
    result = response.json()
    print(json.dumps(result, indent=2))
    
    if "result" in result:
        print("\n✅ SUCCESS!")
        content = result["result"]["content"][0]["text"]
        prediction_data = json.loads(content)
        prediction_value = prediction_data["predictions"][0]["values"][0][0]
        print(f"\n🎯 Prediction: {prediction_value}")
    elif "error" in result:
        print(f"\n❌ ERROR: {result['error']['message']}")
    
except Exception as e:
    print(f"\n❌ Exception: {e}")

print("\n" + "=" * 80)

# Made with Bob
