"""
Bootloader utilities for voidinstall
"""

import subprocess
from lib.sound import ensure_chroot_mounts
from lib.sudo_utils import run_command, run_chroot_command


def detect_boot_mode():
    """
    Detect if system is booted in UEFI or BIOS mode.
    """
    import os
    return os.path.exists("/sys/firmware/efi")

def install_grub_chroot(target="/mnt", disk=None, efi=None):
    """
    Install and configure GRUB bootloader in the chrooted target system.
    Auto-detects UEFI/BIOS mode if not specified.
    """
    ensure_chroot_mounts(target)
    
    # Auto-detect boot mode if not specified
    if efi is None:
        efi = detect_boot_mode()
    
    print(f"[INFO] Installing GRUB bootloader ({'UEFI' if efi else 'BIOS'} mode)")
    
    if efi:
        # UEFI mode - install EFI bootloader
        run_chroot_command(target, ["grub-install", "--target=x86_64-efi", "--efi-directory=/boot/efi", "--bootloader-id=void"])
        print("[INFO] GRUB installed to EFI system partition")
    else:
        # BIOS mode - install to disk MBR
        if not disk:
            # Try to detect disk from mounted root
            result = run_command(["findmnt", "-n", "-o", "SOURCE", target], capture_output=True, text=True)
            if result.returncode == 0:
                device = result.stdout.strip()
                # Extract disk from partition (e.g., /dev/sda1 -> /dev/sda)
                if device.startswith("/dev/mapper/"):
                    # For encrypted devices, need to find underlying disk
                    result = run_command(["cryptsetup", "status", device.split("/")[-1]], capture_output=True, text=True)
                    if result.returncode == 0:
                        for line in result.stdout.split("\n"):
                            if "device:" in line:
                                underlying = line.split()[-1]
                                disk = underlying.rstrip("0123456789")
                                break
                else:
                    disk = device.rstrip("0123456789")
        
        if not disk:
            raise RuntimeError("Could not determine target disk for BIOS boot. Please specify disk parameter.")
        
        run_chroot_command(target, ["grub-install", "--target=i386-pc", disk])
        print(f"[INFO] GRUB installed to disk {disk}")
    
    run_chroot_command(target, ["grub-mkconfig", "-o", "/boot/grub/grub.cfg"])
    print("[INFO] GRUB configuration generated")
