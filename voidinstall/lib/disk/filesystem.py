"""
Filesystem utilities for voidinstall (Void Linux)
"""
import subprocess
import os
from lib.sudo_utils import run_command

def format_ext4(device):
    """Format device with ext4 filesystem"""
    # Ensure the device is unmounted before formatting
    try:
        run_command(["umount", device], capture_output=True, check=False)
    except:
        pass  # Ignore if already unmounted
    
    run_command(["mkfs.ext4", "-F", device])

def create_efi_partition(device):
    """Create and format EFI system partition for UEFI boot"""
    # Ensure the device is unmounted before formatting
    try:
        run_command(["umount", device], capture_output=True, check=False)
    except:
        pass  # Ignore if already unmounted
    
    # Force format the EFI partition
    run_command(["mkfs.fat", "-F32", device])

def mount_root(device, target="/mnt"):
    run_command(["mount", device, target])

def mount_efi(device, target="/mnt"):
    """Mount EFI system partition"""
    efi_mount = os.path.join(target, "boot/efi")
    os.makedirs(efi_mount, exist_ok=True)
    run_command(["mount", device, efi_mount])

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
            return f"[INFO] UEFI boot configured with EFI partition {efi_part}"
        except Exception as e:
            return f"[WARNING] Could not format/mount EFI partition {efi_part}: {str(e)}"
    
    # Mount root (already done in main installer, but ensure it's mounted)
    try:
        mount_root(root_device, target)
        return f"[INFO] Boot partitions configured for {'UEFI' if uefi else 'BIOS'} mode"
    except Exception as e:
        return f"[ERROR] Failed to mount root device {root_device}: {str(e)}"

def unmount_all(target="/mnt"):
    run_command(["umount", "-R", target])
