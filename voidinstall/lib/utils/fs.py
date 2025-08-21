"""
Utility functions for voidinstall
"""
import os

def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)
