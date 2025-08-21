"""
Filesystem utilities for voidinstall (Void Linux)
"""
import subprocess

def format_ext4(device):
    subprocess.run(["mkfs.ext4", device], check=True)

def mount_root(device, target="/mnt"):
    subprocess.run(["mount", device, target], check=True)

def unmount_all(target="/mnt"):
    subprocess.run(["umount", "-R", target], check=True)
