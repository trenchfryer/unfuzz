#!/usr/bin/env python3
"""Quick test to verify Gemini API is working"""

import google.generativeai as genai
from PIL import Image
import os

# Configure Gemini
API_KEY = "AIzaSyBwh-Tm3qTDCydj-xCpjpTNtynbT_CAGxE"
MODEL = "gemini-2.5-flash"

print(f"Testing Gemini API with key: {API_KEY[:20]}...")
print(f"Model: {MODEL}")

genai.configure(api_key=API_KEY)
model = genai.GenerativeModel(MODEL)

# Test with a simple text prompt first
try:
    print("\n1. Testing text generation...")
    response = model.generate_content("Say 'Hello from Gemini!' in exactly those words.")
    print(f"✓ Text test successful: {response.text}")
except Exception as e:
    print(f"✗ Text test failed: {e}")
    exit(1)

# Test with an image if one exists
image_path = "./uploads/dfedce6a-46e2-4afc-ac9b-8d771e633718_20251102_125708_img_daaad2ff3cd7.png"
if os.path.exists(image_path):
    print(f"\n2. Testing image analysis with: {image_path}")
    try:
        img = Image.open(image_path)
        response = model.generate_content([
            "Describe this image in one sentence.",
            img
        ])
        print(f"✓ Image test successful: {response.text}")
    except Exception as e:
        print(f"✗ Image test failed: {e}")
        exit(1)
else:
    print(f"\n2. Skipping image test (no image found at {image_path})")

print("\n✓ All tests passed! Gemini is working correctly.")
