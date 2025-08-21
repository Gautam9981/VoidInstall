"""
Package management utilities for voidinstall
"""

import subprocess
from lib.sound import ensure_chroot_mounts

def enable_repos(target="/mnt"):
    """
    Enable void-repo-nonfree and void-repo-multilib in the target system.
    """
    ensure_chroot_mounts(target)
    subprocess.run(["chroot", target, "xbps-install", "-Sy", "void-repo-nonfree", "void-repo-multilib"], check=True)


def install_packages(target, *pkgs):
    """
    Install packages in the target system using xbps with the official repo URL.
    Filters out empty strings and None values from package list.
    """
    ensure_chroot_mounts(target)
    # Filter out empty strings and None values
    filtered_pkgs = [pkg for pkg in pkgs if pkg and pkg.strip()]
    
    if not filtered_pkgs:
        print("[WARNING] No packages to install")
        return
    
    repo_url = "https://repo-default.voidlinux.org/current"
    subprocess.run(["xbps-install", "-S", "-R", repo_url, "-r", target] + filtered_pkgs, check=True)
    print(f"[INFO] Installed packages: {', '.join(filtered_pkgs)}")

def upgrade_packages(target="/mnt"):
    """
    Upgrade all packages in the target system.
    """
    ensure_chroot_mounts(target)
    subprocess.run(["chroot", target, "xbps-install", "-Syu"], check=True)
