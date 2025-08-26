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
            "packages": ["base-system", "linux", "xfce4", "lightdm", "linux-headers", "xorg"],
            "desktop": "xfce4"
        },
        "gnome": {
            "name": "desktop-gnome",
            "description": "Desktop Void Linux installation (GNOME)",
            "packages": ["xorg", "base-system", "linux", "gnome", "gdm", "linux-headers"],
            "desktop": "gnome"
        },
        "kde": {
            "name": "desktop-kde",
            "description": "Desktop Void Linux installation (KDE Plasma)",
            "packages": ["xorg", "base-system", "linux", "linux-headers", "kde5", "sddm", "konsole"],
            "desktop": "kde5"
        },
        "mate": {
            "name": "desktop-mate",
            "description": "Desktop Void Linux installation (MATE)",
            "packages": ["base-system", "linux", "mate", "lightdm", "linux-headers", "xorg"],
            "desktop": "mate"
        },
        "cinnamon": {
            "name": "desktop-cinnamon",
            "description": "Desktop Void Linux installation (Cinnamon)",
            "packages": ["base-system", "linux", "cinnamon", "lightdm", "linux-headers", "xorg"],
            "desktop": "cinnamon"
        }
    }
