"""
Locale utilities for voidinstall
"""
import json

def load_locale(locale_file):
    with open(locale_file, "r") as f:
        return json.load(f)
