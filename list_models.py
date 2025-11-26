#!/usr/bin/env python3
"""List available Gemini models"""

import google.generativeai as genai

API_KEY = "AIzaSyBwh-Tm3qTDCydj-xCpjpTNtynbT_CAGxE"
genai.configure(api_key=API_KEY)

print("Available Gemini models:\n")
for model in genai.list_models():
    if 'generateContent' in model.supported_generation_methods:
        print(f"  {model.name}")
        print(f"    Display name: {model.display_name}")
        print(f"    Description: {model.description[:80]}...")
        print()
