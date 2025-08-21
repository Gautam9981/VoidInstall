def manual_partitioning(disk=None):
    """
    Allow the user to manually partition the disk using cfdisk or another tool.
    If disk is specified, launch cfdisk for that disk; otherwise, prompt user.
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

def list_disks():
    result = subprocess.run(["lsblk", "-d", "-o", "NAME,SIZE,TYPE"], capture_output=True, text=True)
    return result.stdout

def wipe_disk(disk):
    """Wipe disk using available partitioning tool"""
    import shutil
    if shutil.which("sgdisk"):
        subprocess.run(["sgdisk", "--zap-all", disk], check=True)
    elif shutil.which("parted"):
        subprocess.run(["parted", disk, "mklabel", "gpt"], check=True)
    elif shutil.which("fdisk"):
        # Use fdisk to create new GPT table
        subprocess.run(["fdisk", disk], input=b"g\nw\n", check=True)
    else:
        raise RuntimeError("No partitioning tool (sgdisk, parted, fdisk) found")

def create_partitions_uefi(disk):
    """Create UEFI partition layout: EFI + root"""
    import shutil
    if shutil.which("sgdisk"):
        # EFI system partition (512MB)
        subprocess.run(["sgdisk", "-n", "1:0:+512M", "-t", "1:ef00", disk], check=True)
        # Root partition (rest of disk)
        subprocess.run(["sgdisk", "-n", "2:0:0", "-t", "2:8300", disk], check=True)
        subprocess.run(["partprobe", disk], check=True)
    elif shutil.which("parted"):
        subprocess.run(["parted", disk, "mkpart", "primary", "fat32", "1MiB", "513MiB"], check=True)
        subprocess.run(["parted", disk, "set", "1", "esp", "on"], check=True)
        subprocess.run(["parted", disk, "mkpart", "primary", "ext4", "513MiB", "100%"], check=True)
    else:
        raise RuntimeError("No partitioning tool available for UEFI setup")

def create_partitions_bios(disk):
    """Create BIOS partition layout: just root partition"""
    import shutil
    if shutil.which("sgdisk"):
        # Single root partition
        subprocess.run(["sgdisk", "-n", "1:0:0", "-t", "1:8300", disk], check=True)
        subprocess.run(["partprobe", disk], check=True)
    elif shutil.which("parted"):
        subprocess.run(["parted", disk, "mkpart", "primary", "ext4", "1MiB", "100%"], check=True)
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
        return f"{disk}2"  # Second partition is root in UEFI layout
    else:
        return f"{disk}1"  # First partition is root in BIOS layout

def get_efi_partition(disk):
    """Get EFI partition device (only for UEFI)"""
    return f"{disk}1"

def setup_encryption(device):
    """Set up disk encryption using cryptsetup"""
    try:
        # Ensure encryption tools are available
        from lib.dependencies import install_encryption_tools
        install_encryption_tools()
        
        print(f"Setting up encryption on {device}...")
        # Generate a random passphrase for testing (in real installer, user would provide)
        passphrase = "voidinstall123"
        
        subprocess.run([
            "cryptsetup", "luksFormat", device,
            "--batch-mode"
        ], input=passphrase.encode(), check=True)
        
        subprocess.run([
            "cryptsetup", "open", device, "void_root",
            "--batch-mode"
        ], input=passphrase.encode(), check=True)
        
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
        subprocess.run(["mkfs.fat", "-F32", boot_part], check=True)
    
    # Handle encryption
    if encrypt:
        encrypted_device = setup_encryption(root_part)
        subprocess.run(["mkfs.ext4", encrypted_device], check=True)
    else:
        subprocess.run(["mkfs.ext4", root_part], check=True)
