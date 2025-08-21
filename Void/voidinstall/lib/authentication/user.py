"""
Authentication utilities for voidinstall
"""
import subprocess

def create_user_chroot(username, chroot_target="/mnt"):
    subprocess.run(["chroot", chroot_target, "useradd", "-m", "-G", "wheel", username], check=True)

def set_password(username):
    subprocess.run(["passwd", username], check=True)

def set_password_chroot(username, chroot_target="/mnt"):
    subprocess.run(["chroot", chroot_target, "passwd", username], check=True)

def lock_root():
    subprocess.run(["passwd", "-l", "root"], check=True)

def lock_root_chroot(chroot_target="/mnt"):
    subprocess.run(["chroot", chroot_target, "passwd", "-l", "root"], check=True)
