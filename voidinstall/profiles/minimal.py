"""
Default minimal install profile for Void Linux
"""
def get_profile():
    return {
        "name": "minimal",
        "description": "Minimal Void Linux installation",
        "packages": ["base-system", "linux", "vim"],
        "desktop": None,
        "sound": None
    }
