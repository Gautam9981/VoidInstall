"""
Authentication utilities for voidinstall
"""

import subprocess
import os
from lib.sound import ensure_chroot_mounts
from lib.sudo_utils import run_command, run_chroot_command

def create_user_chroot(username, chroot_target="/mnt"):
    """Create a user in the chrooted target system with wheel group membership"""
    ensure_chroot_mounts(chroot_target)
    run_chroot_command(chroot_target, ["useradd", "-m", "-G", "wheel", username])
    print(f"[INFO] Created user '{username}' with wheel group membership")

def set_password(username):
    """Set password for user in live environment"""
    run_command(["passwd", username])

def set_password_chroot(username, chroot_target="/mnt"):
    """Set password for user in chrooted target system"""
    ensure_chroot_mounts(chroot_target)
    run_chroot_command(chroot_target, ["passwd", username])
    print(f"[INFO] Set password for user '{username}'")

def lock_root():
    """Lock root account in live environment"""
    run_command(["passwd", "-l", "root"])

def lock_root_chroot(chroot_target="/mnt"):
    """Lock root account in chrooted target system"""
    ensure_chroot_mounts(chroot_target)
    run_chroot_command(chroot_target, ["passwd", "-l", "root"])
    print("[INFO] Locked root account for security")
