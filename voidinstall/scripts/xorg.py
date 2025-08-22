"""
Xorg install profile for Void Linux (inspired by archinstall)
"""
from lib.packages.xbps import enable_repos, install_packages

def run(target="/mnt"):
    """
    Installs a minimal Xorg environment with basic drivers and tools.
    """
    enable_repos(target)
    # Install Xorg, drivers, and basic utilities
    install_packages(target,
        "xorg",
        "xinit",
        "xf86-input-libinput",
        "xf86-video-vesa",
        "mesa-dri",
        "xterm",
        "setxkbmap",
        "xrandr",
        "xauth"
    )
    print("[INFO] Xorg environment installed.")

if __name__ == "__main__":
    run()
