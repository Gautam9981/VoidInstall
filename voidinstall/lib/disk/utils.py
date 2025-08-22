def manual_partitioning(disk=None):
    """
    Allow the user to manually partition the disk using cfdisk or another tool.
    If disk idef format_partitions(boot_part, root_part, encrypt=False):
    # Ensure filesystem tools are available
    from lib.dependencies import install_filesystem_tools
    install_filesystem_tools()
    
    # Format EFI partition if UEFI
    if boot_part:
        run_command(["mkfs.fat", "-F32", boot_part])
    
    # Only format root partition if not using encryption
    # (encryption setup and formatting is handled separately in main installer)
    if not encrypt:
        run_command(["mkfs.ext4", root_part])nch cfdisk for that disk; otherwise, prompt user.
    """
    import shutil
    tool = None
    for candidate in ["cfdisk", "fdisk", "parted"]:
        if shutil.which(candidate):
            tool = candidate
            break
    if not tool:
        print("[ERROR] No partitioning tool (cfdisk, fdisk, parted) found in PATH.")
        return
    if not disk:
        disk = input("Enter disk to partition (e.g., /dev/sda): ")
    print(f"[INFO] Launching {tool} for manual partitioning on {disk}...")
    import subprocess
    subprocess.run([tool, disk], check=True)

def list_partitions(disk):
    """
    List partitions on the given disk after manual partitioning.
    """
    import subprocess
    result = subprocess.run(["lsblk", "-o", "NAME,SIZE,TYPE,MOUNTPOINT", disk], capture_output=True, text=True)
    print(result.stdout)
"""
Disk utility functions for voidinstall
"""
import subprocess
from lib.sudo_utils import run_command

def get_partition_name(disk, partition_number):
    """
    Get the correct partition name for a disk, handling different disk types.
    
    Args:
        disk: Base disk path (e.g., '/dev/sda', '/dev/nvme0n1', '/dev/vda')
        partition_number: Partition number (1, 2, etc.)
    
    Returns:
        Full partition path (e.g., '/dev/sda1', '/dev/nvme0n1p1', '/dev/vda1')
    """
    if 'nvme' in disk or 'mmcblk' in disk or 'loop' in disk:
        # NVMe, eMMC, or loop devices use 'p' separator
        return f"{disk}p{partition_number}"
    else:
        # Regular SATA/SCSI drives, virtio drives (vda), etc.
        return f"{disk}{partition_number}"

def list_disks():
    result = run_command(["lsblk", "-d", "-o", "NAME,SIZE,TYPE"], capture_output=True, text=True)
    return result.stdout

def wipe_disk(disk):
    """Wipe disk using available partitioning tool"""
    import shutil
    if shutil.which("sgdisk"):
        run_command(["sgdisk", "--zap-all", disk])
    elif shutil.which("parted"):
        run_command(["parted", disk, "mklabel", "gpt"])
    elif shutil.which("fdisk"):
        # Use fdisk to create new GPT table
        run_command(["fdisk", disk], input_data=b"g\nw\n")
    else:
        raise RuntimeError("No partitioning tool (sgdisk, parted, fdisk) found")

def create_partitions_uefi(disk):
    """Create UEFI partition layout: EFI + root"""
    import shutil
    if shutil.which("sgdisk"):
        # EFI system partition (512MB)
        run_command(["sgdisk", "-n", "1:0:+512M", "-t", "1:ef00", disk])
        # Root partition (rest of disk)
        run_command(["sgdisk", "-n", "2:0:0", "-t", "2:8300", disk])
        run_command(["partprobe", disk])
    elif shutil.which("parted"):
        run_command(["parted", disk, "mkpart", "primary", "fat32", "1MiB", "513MiB"])
        run_command(["parted", disk, "set", "1", "esp", "on"])
        run_command(["parted", disk, "mkpart", "primary", "ext4", "513MiB", "100%"])
    else:
        raise RuntimeError("No partitioning tool available for UEFI setup")

def create_partitions_bios(disk):
    """Create BIOS partition layout: just root partition"""
    import shutil
    if shutil.which("sgdisk"):
        # Single root partition
        run_command(["sgdisk", "-n", "1:0:0", "-t", "1:8300", disk])
        run_command(["partprobe", disk])
    elif shutil.which("parted"):
        run_command(["parted", disk, "mkpart", "primary", "ext4", "1MiB", "100%"])
    else:
        raise RuntimeError("No partitioning tool available for BIOS setup")

def create_partition(disk):
    """Create partitions based on boot mode"""
    import os
    uefi = os.path.exists("/sys/firmware/efi")
    
    if uefi:
        create_partitions_uefi(disk)
    else:
        create_partitions_bios(disk)

def get_partition(disk, uefi=None):
    """Get root partition device based on boot mode"""
    import os
    if uefi is None:
        uefi = os.path.exists("/sys/firmware/efi")
    
    if uefi:
        return get_partition_name(disk, 2)  # Second partition is root in UEFI layout
    else:
        return get_partition_name(disk, 1)  # First partition is root in BIOS layout

def get_efi_partition(disk):
    """Get EFI partition device (only for UEFI)"""
    return get_partition_name(disk, 1)

def setup_encryption(device, password):
    """Set up disk encryption using cryptsetup with provided password"""
    try:
        # Ensure encryption tools are available
        from lib.dependencies import install_encryption_tools
        install_encryption_tools()
        
        print(f"Setting up encryption on {device}...")
        
        run_command([
            "cryptsetup", "luksFormat", device,
            "--batch-mode",  # Don't ask for confirmation
            "--force-password"  # Don't complain about password quality
        ], input_data=password.encode())
        
        run_command([
            "cryptsetup", "open", device, "void_root"
        ], input_data=password.encode())
        
        return "/dev/mapper/void_root"
    except subprocess.CalledProcessError as e:
        print(f"Error setting up encryption: {e}")
        raise

def partition_disk(disk, encrypt=False):
    """Partition disk and return boot and root partition paths"""
    import os
    
    wipe_disk(disk)
    create_partition(disk)
    
    uefi = os.path.exists("/sys/firmware/efi")
    root_part = get_partition(disk, uefi)
    boot_part = get_efi_partition(disk) if uefi else None
    
    return boot_part, root_part

def format_partitions(boot_part, root_part, encrypt=False):
    """Format partitions with appropriate filesystems"""
    # Ensure filesystem tools are available
    from lib.dependencies import install_filesystem_tools
    install_filesystem_tools()
    
    # Format EFI partition if UEFI
    if boot_part:
        run_command(["mkfs.fat", "-F32", boot_part])
    
    # Only format root partition if not using encryption
    # (encryption setup and formatting is handled separately in main installer)
    if not encrypt:
        run_command(["mkfs.ext4", root_part])
