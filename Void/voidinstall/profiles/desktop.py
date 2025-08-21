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
            "packages": ["base-system", "linux", "xfce4", "lightdm", "alsa-utils"],
            "desktop": "xfce4",
            "sound": "alsa-utils"
        },
        "gnome": {
            "name": "desktop-gnome",
            "description": "Desktop Void Linux installation (GNOME)",
            "packages": ["base-system", "linux", "gnome", "gdm", "alsa-utils"],
            "desktop": "gnome",
            "sound": "alsa-utils"
        },
        "kde": {
            "name": "desktop-kde",
            "description": "Desktop Void Linux installation (KDE Plasma)",
            "packages": ["base-system", "linux", "kde5", "sddm", "alsa-utils"],
            "desktop": "kde5",
            "sound": "alsa-utils"
        },
        "mate": {
            "name": "desktop-mate",
            "description": "Desktop Void Linux installation (MATE)",
            "packages": ["base-system", "linux", "mate", "lightdm", "alsa-utils"],
            "desktop": "mate",
            "sound": "alsa-utils"
        },
        "cinnamon": {
            "name": "desktop-cinnamon",
            "description": "Desktop Void Linux installation (Cinnamon)",
            "packages": ["base-system", "linux", "cinnamon", "lightdm", "alsa-utils"],
            "desktop": "cinnamon",
            "sound": "alsa-utils"
        }
    }
