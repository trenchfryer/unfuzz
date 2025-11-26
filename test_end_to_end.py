#!/usr/bin/env python3
"""End-to-end test of image upload and analysis"""

import requests
import json
import time

API_BASE = "http://localhost:8000/api/v1"

print("=" * 60)
print("UnFuzz End-to-End Test")
print("=" * 60)

# Step 1: Upload an image
print("\n1. Testing image upload...")
try:
    with open("test_image.jpg", "rb") as f:
        files = {"file": ("test_image.jpg", f, "image/jpeg")}
        response = requests.post(f"{API_BASE}/images/upload", files=files)

    if response.status_code == 200:
        upload_data = response.json()
        image_id = upload_data["id"]
        print(f"✓ Upload successful!")
        print(f"  Image ID: {image_id}")
        print(f"  Filename: {upload_data['filename']}")
        print(f"  Status: {upload_data['status']}")
    else:
        print(f"✗ Upload failed: {response.status_code}")
        print(f"  Response: {response.text}")
        exit(1)
except Exception as e:
    print(f"✗ Upload failed: {e}")
    exit(1)

# Step 2: Analyze the image
print(f"\n2. Testing image analysis...")
try:
    response = requests.post(f"{API_BASE}/analysis/analyze/{image_id}")

    if response.status_code == 200:
        analysis_data = response.json()
        print(f"✓ Analysis successful!")
        print(f"  Status: {analysis_data.get('status', 'unknown')}")

        # Print analysis details if available
        if "analysis" in analysis_data and analysis_data["analysis"]:
            analysis = analysis_data["analysis"]
            print(f"\n  Analysis Results:")
            print(f"    Overall Score: {analysis.get('overall_score', 'N/A')}")
            print(f"    Quality Tier: {analysis.get('quality_tier', 'N/A')}")

            if "technical_quality" in analysis:
                tq = analysis["technical_quality"]
                print(f"    Technical Quality: {tq.get('overall_score', 'N/A')}")

            if "ai_reasoning" in analysis:
                reasoning = analysis["ai_reasoning"]
                print(f"\n  AI Reasoning:")
                print(f"    {reasoning[:200]}...")
        else:
            print(f"  (No detailed analysis in response)")
    else:
        print(f"✗ Analysis failed: {response.status_code}")
        print(f"  Response: {response.text}")
        exit(1)
except Exception as e:
    print(f"✗ Analysis failed: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

print("\n" + "=" * 60)
print("✓ All end-to-end tests passed!")
print("=" * 60)
