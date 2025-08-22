"""
Desktop install profiles for Void Linux
"""

def get_profiles():
    """
    Returns a dictionary of available desktop environment profiles.
    """
    return {
        "xfce4": {
            "name": "desktop-xfce4",
            "description": "Desktop Void Linux installation (XFCE)",
            "packages": ["base-system", "linux", "xfce4", "lightdm"],
            "desktop": "xfce4"
        },
        "gnome": {
            "name": "desktop-gnome",
            "description": "Desktop Void Linux installation (GNOME)",
            "packages": ["base-system", "linux", "gnome", "gdm"],
            "desktop": "gnome"
        },
        "kde": {
            "name": "desktop-kde",
            "description": "Desktop Void Linux installation (KDE Plasma)",
            "packages": ["base-system", "linux", "kde5", "sddm"],
            "desktop": "kde5"
        },
        "mate": {
            "name": "desktop-mate",
            "description": "Desktop Void Linux installation (MATE)",
            "packages": ["base-system", "linux", "mate", "lightdm"],
            "desktop": "mate"
        },
        "cinnamon": {
            "name": "desktop-cinnamon",
            "description": "Desktop Void Linux installation (Cinnamon)",
            "packages": ["base-system", "linux", "cinnamon", "lightdm"],
            "desktop": "cinnamon"
        }
    }
