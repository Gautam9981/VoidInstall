"""
Authentication utilities for voidinstall
"""

import subprocess
import os
from lib.sound import ensure_chroot_mounts

def create_user_chroot(username, chroot_target="/mnt"):
    """Create a user in the chrooted target system with wheel group membership"""
    ensure_chroot_mounts(chroot_target)
    subprocess.run(["chroot", chroot_target, "useradd", "-m", "-G", "wheel", username], check=True)
    print(f"[INFO] Created user '{username}' with wheel group membership")

def set_password(username):
    """Set password for user in live environment"""
    subprocess.run(["passwd", username], check=True)

def set_password_chroot(username, chroot_target="/mnt"):
    """Set password for user in chrooted target system"""
    ensure_chroot_mounts(chroot_target)
    subprocess.run(["chroot", chroot_target, "passwd", username], check=True)
    print(f"[INFO] Set password for user '{username}'")

def lock_root():
    """Lock root account in live environment"""
    subprocess.run(["passwd", "-l", "root"], check=True)

def lock_root_chroot(chroot_target="/mnt"):
    """Lock root account in chrooted target system"""
    ensure_chroot_mounts(chroot_target)
    subprocess.run(["chroot", chroot_target, "passwd", "-l", "root"], check=True)
    print("[INFO] Locked root account for security")
