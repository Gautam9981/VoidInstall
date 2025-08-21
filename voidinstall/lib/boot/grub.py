"""
Bootloader utilities for voidinstall
"""

import subprocess
from lib.sound import ensure_chroot_mounts


def install_grub_chroot(target="/mnt", efi=True):
    """
    Install and configure GRUB bootloader in the chrooted target system.
    Uses runit for service management if needed.
    """
    ensure_chroot_mounts(target)
    if efi:
        subprocess.run(["chroot", target, "grub-install", "--target=x86_64-efi"], check=True)
    else:
        subprocess.run(["chroot", target, "grub-install", "--target=i386-pc", "/dev/sda"], check=True)  # Adjust disk as needed
    subprocess.run(["chroot", target, "grub-mkconfig", "-o", "/boot/grub/grub.cfg"], check=True)
