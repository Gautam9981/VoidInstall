"""
Package management utilities for voidinstall
"""
import subprocess

def enable_repos(target="/mnt"):
    """
    Enable void-repo-nonfree and void-repo-multilib in the target system.
    """
    subprocess.run(["chroot", target, "xbps-install", "-Sy", "void-repo-nonfree", "void-repo-multilib"], check=True)


def install_packages(target, *pkgs):
    """
    Install packages in the target system using xbps with the official repo URL.
    """
    repo_url = "https://repo-default.voidlinux.org/current"
    subprocess.run(["xbps-install", "-S", "-R", repo_url, "-r", target] + list(pkgs), check=True)

def upgrade_packages(target="/mnt"):
    """
    Upgrade all packages in the target system.
    """
    subprocess.run(["chroot", target, "xbps-install", "-Syu"], check=True)
