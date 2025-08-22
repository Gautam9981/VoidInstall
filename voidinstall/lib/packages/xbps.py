"""
Package management utilities for voidinstall
"""

import subprocess
from lib.sound import ensure_chroot_mounts
from lib.sudo_utils import run_command, run_chroot_command

def enable_repos(target="/mnt"):
    """
    Enable void-repo-nonfree and void-repo-multilib in the target system.
    """
    ensure_chroot_mounts(target)
    run_chroot_command(target, ["xbps-install", "-Sy", "void-repo-nonfree", "void-repo-multilib"])


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
    run_command(["xbps-install", "-S", "-R", repo_url, "-r", target] + filtered_pkgs)
    print(f"[INFO] Installed packages: {', '.join(filtered_pkgs)}")

def upgrade_packages(target="/mnt"):
    """
    Upgrade all packages in the target system.
    """
    ensure_chroot_mounts(target)
    run_chroot_command(target, ["xbps-install", "-Syu"])
