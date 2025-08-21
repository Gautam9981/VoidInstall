"""
Filesystem utilities for voidinstall (Void Linux)
"""
import subprocess
import os

def format_ext4(device):
    subprocess.run(["mkfs.ext4", device], check=True)

def create_efi_partition(device):
    """Create and format EFI system partition for UEFI boot"""
    subprocess.run(["mkfs.fat", "-F32", device], check=True)

def mount_root(device, target="/mnt"):
    subprocess.run(["mount", device, target], check=True)

def mount_efi(device, target="/mnt"):
    """Mount EFI system partition"""
    efi_mount = os.path.join(target, "boot/efi")
    os.makedirs(efi_mount, exist_ok=True)
    subprocess.run(["mount", device, efi_mount], check=True)

def setup_boot_partitions(disk, root_device, target="/mnt", uefi=None):
    """
    Set up boot partitions based on boot mode (UEFI or BIOS)
    """
    if uefi is None:
        uefi = os.path.exists("/sys/firmware/efi")
    
    if uefi:
        # UEFI: need EFI system partition
        # Assume partition 1 is EFI, partition 2 is root (or encrypted root)
        efi_part = f"{disk}1"
        
        # Create EFI partition if it doesn't exist or needs formatting
        try:
            create_efi_partition(efi_part)
            mount_efi(efi_part, target)
        except subprocess.CalledProcessError:
            print(f"[WARNING] Could not format/mount EFI partition {efi_part}")
    
    # Mount root (already done in main installer, but ensure it's mounted)
    mount_root(root_device, target)

def unmount_all(target="/mnt"):
    subprocess.run(["umount", "-R", target], check=True)
