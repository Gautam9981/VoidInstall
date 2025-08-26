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

def unmount_all_partitions(disk):
    """Unmount all partitions on a disk before wiping"""
    import subprocess
    import time
    
    # Multiple aggressive unmount attempts
    for attempt in range(5):
        try:
            # Get all mounted partitions for this disk
            result = run_command(["lsblk", "-ln", "-o", "NAME,MOUNTPOINT", disk], capture_output=True, text=True, check=False)
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    if line.strip():
                        parts = line.split()
                        if len(parts) >= 2 and parts[1] != '':  # Has a mount point
                            device_name = parts[0]
                            # Convert device name to full path
                            if not device_name.startswith('/dev/'):
                                device_path = f"/dev/{device_name}"
                            else:
                                device_path = device_name
                            
                            # Try multiple unmount methods
                            try:
                                run_command(["umount", "-f", device_path], capture_output=True, check=False)
                                run_command(["umount", "-l", device_path], capture_output=True, check=False)  # Lazy unmount
                                run_command(["umount", device_path], capture_output=True, check=False)
                                print(f"Unmounted {device_path}")
                            except:
                                pass  # Ignore unmount errors
            
            # Also try to unmount all partitions of this disk directly
            for i in range(1, 16):  # Check partitions 1-15
                part_path = get_partition_name(disk, i)
                try:
                    run_command(["umount", "-f", part_path], capture_output=True, check=False)
                    run_command(["umount", "-l", part_path], capture_output=True, check=False)
                    run_command(["umount", part_path], capture_output=True, check=False)
                except:
                    pass
            
            time.sleep(1)  # Wait between attempts
        except:
            pass  # Ignore any errors in detection

def wipe_disk(disk):
    """Wipe disk using available partitioning tool with aggressive cleanup"""
    import shutil
    import time
    
    print(f"[INFO] Preparing to wipe disk {disk}...")
    
    # Step 1: Kill any processes using the disk
    try:
        run_command(["fuser", "-km", disk], capture_output=True, check=False)
        time.sleep(2)
    except:
        pass
    
    # Step 2: Close any LUKS/encryption devices
    try:
        result = run_command(["lsblk", "-ln", "-o", "NAME,TYPE"], capture_output=True, text=True, check=False)
        if result.returncode == 0:
            for line in result.stdout.strip().split('\n'):
                if 'crypt' in line:
                    parts = line.split()
                    if parts:
                        crypt_name = parts[0]
                        try:
                            run_command(["cryptsetup", "close", crypt_name], capture_output=True, check=False)
                            print(f"Closed LUKS device: {crypt_name}")
                        except:
                            pass
    except:
        pass
    
    # Step 3: Aggressive unmounting (multiple attempts with different strategies)
    print(f"[INFO] Unmounting all partitions on {disk}...")
    for attempt in range(10):  # More attempts for stubborn mounts
        try:
            # Get all partitions and their mount points
            result = run_command(["lsblk", "-ln", "-o", "NAME,MOUNTPOINT"], capture_output=True, text=True, check=False)
            unmounted_something = False
            
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    if disk.split('/')[-1] in line:  # Line contains our disk
                        parts = line.split()
                        if len(parts) >= 2 and parts[1] and parts[1] != '':
                            device_name = parts[0]
                            mount_point = parts[1]
                            device_path = f"/dev/{device_name}" if not device_name.startswith('/dev/') else device_name
                            
                            # Try different unmount strategies
                            for umount_cmd in [
                                ["umount", "-f", device_path],    # Force
                                ["umount", "-l", device_path],    # Lazy
                                ["umount", device_path],          # Normal
                                ["umount", "-f", mount_point],    # Force by mount point
                                ["umount", "-l", mount_point],    # Lazy by mount point
                                ["umount", mount_point]           # Normal by mount point
                            ]:
                                try:
                                    result = run_command(umount_cmd, capture_output=True, check=False)
                                    if result.returncode == 0:
                                        print(f"Unmounted {device_path} from {mount_point}")
                                        unmounted_something = True
                                        break
                                except:
                                    pass
            
            # Also try to unmount partitions by guessing partition names
            for i in range(1, 16):
                part_path = get_partition_name(disk, i)
                for umount_cmd in [
                    ["umount", "-f", part_path],
                    ["umount", "-l", part_path],
                    ["umount", part_path]
                ]:
                    try:
                        result = run_command(umount_cmd, capture_output=True, check=False)
                        if result.returncode == 0:
                            print(f"Unmounted {part_path}")
                            unmounted_something = True
                            break
                    except:
                        pass
            
            if not unmounted_something:
                break  # Nothing left to unmount
            
            time.sleep(1)
        except:
            pass
    
    # Step 4: Deactivate swap on any partitions
    try:
        result = run_command(["swapon", "--show=NAME", "--noheadings"], capture_output=True, text=True, check=False)
        if result.returncode == 0:
            for line in result.stdout.strip().split('\n'):
                if line.strip() and disk.split('/')[-1] in line:
                    try:
                        run_command(["swapoff", line.strip()], capture_output=True, check=False)
                        print(f"Deactivated swap: {line.strip()}")
                    except:
                        pass
    except:
        pass
    
    # Step 5: Final wait and sync
    time.sleep(3)
    try:
        run_command(["sync"], capture_output=True, check=False)
    except:
        pass
    
    # Step 6: Wipe the disk
    print(f"[INFO] Wiping partition table on {disk}...")
    success = False
    
    if shutil.which("sgdisk"):
        try:
            run_command(["sgdisk", "--zap-all", disk])
            success = True
            print(f"[INFO] Wiped disk using sgdisk")
        except Exception as e:
            print(f"[WARN] sgdisk failed: {e}")
    
    if not success and shutil.which("parted"):
        try:
            run_command(["parted", disk, "mklabel", "gpt"])
            success = True
            print(f"[INFO] Created new GPT table using parted")
        except Exception as e:
            print(f"[WARN] parted failed: {e}")
    
    if not success and shutil.which("fdisk"):
        try:
            run_command(["fdisk", disk], input_data=b"g\nw\n")
            success = True
            print(f"[INFO] Created new GPT table using fdisk")
        except Exception as e:
            print(f"[WARN] fdisk failed: {e}")
    
    if not success:
        raise RuntimeError("All partitioning tools failed to wipe the disk")
    
    # Step 7: Force kernel to re-read partition table and final cleanup
    try:
        run_command(["partprobe", disk], capture_output=True, check=False)
        time.sleep(2)
        run_command(["udevadm", "settle"], capture_output=True, check=False)
        time.sleep(1)
    except:
        pass
    
    print(f"[INFO] Disk {disk} wiped successfully")

def apply_mount_configuration(mount_config, target="/mnt"):
    """Apply mount configuration by formatting and mounting partitions"""
    import os
    from lib.sudo_utils import run_command
    
    if not mount_config:
        print("[WARN] No mount configuration provided")
        return {}
    
    # Create target directory
    os.makedirs(target, exist_ok=True)
    
    # Sort mount points to mount in correct order (/ first, then subdirs)
    mount_order = []
    swap_partitions = []
    
    for device, config in mount_config.items():
        mount_point = config.get('mount', '')
        if mount_point == 'swap':
            swap_partitions.append((device, config))
        elif mount_point:
            # Calculate depth for proper mounting order
            depth = mount_point.count('/')
            mount_order.append((depth, mount_point, device, config))
    
    # Sort by depth (root first, then subdirectories)
    mount_order.sort(key=lambda x: x[0])
    
    mounted_devices = {}
    
    try:
        # Format and mount filesystems
        for depth, mount_point, device, config in mount_order:
            fs_type = config.get('format', 'ext4')
            full_mount_path = os.path.join(target, mount_point.lstrip('/'))
            
            print(f"[INFO] Formatting {device} as {fs_type}")
            
            # Format the filesystem
            if fs_type in ['ext4', 'ext3', 'ext2']:
                run_command(["mkfs.ext4", "-F", device])
            elif fs_type == 'xfs':
                run_command(["mkfs.xfs", "-f", device])
            elif fs_type == 'btrfs':
                run_command(["mkfs.btrfs", "-f", device])
            elif fs_type in ['fat32', 'vfat']:
                run_command(["mkfs.fat", "-F32", device])
            else:
                print(f"[WARN] Unsupported filesystem type: {fs_type}, using ext4")
                run_command(["mkfs.ext4", "-F", device])
            
            # Create mount point directory
            if mount_point != '/':
                os.makedirs(full_mount_path, exist_ok=True)
            
            # Mount the filesystem
            print(f"[INFO] Mounting {device} to {full_mount_path}")
            run_command(["mount", device, full_mount_path])
            mounted_devices[mount_point] = device
        
        # Handle swap partitions
        for device, config in swap_partitions:
            print(f"[INFO] Setting up swap on {device}")
            run_command(["mkswap", device])
            run_command(["swapon", device])
            mounted_devices['swap'] = device
        
        print(f"[INFO] Successfully mounted {len(mounted_devices)} filesystems")
        return mounted_devices
    
    except Exception as e:
        print(f"[ERROR] Failed to apply mount configuration: {e}")
        # Try to unmount what we mounted
        for mount_point, device in mounted_devices.items():
            if mount_point != 'swap':
                try:
                    full_mount_path = os.path.join(target, mount_point.lstrip('/'))
                    run_command(["umount", full_mount_path], capture_output=True, check=False)
                except:
                    pass
        raise

def create_partitions_uefi(disk):
    """Create UEFI partition layout: EFI + root"""
    import shutil
    from lib.dependencies import install_partitioning_tools
    
    # Ensure partitioning tools are available
    install_partitioning_tools()
    
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
    elif shutil.which("fdisk"):
        # Fallback to fdisk if available
        print("[WARNING] Using fdisk fallback - creating GPT partition table")
        # Create GPT table and partitions using fdisk
        import subprocess
        fdisk_commands = "g\nn\n1\n\n+512M\nt\n1\nn\n2\n\n\nw\n"
        proc = subprocess.Popen(["fdisk", disk], stdin=subprocess.PIPE, text=True)
        proc.communicate(input=fdisk_commands)
    else:
        raise RuntimeError("No partitioning tool available for UEFI setup. Install sgdisk, parted, or fdisk.")

def create_partitions_bios(disk):
    """Create BIOS partition layout: just root partition"""
    import shutil
    from lib.dependencies import install_partitioning_tools
    
    # Ensure partitioning tools are available
    install_partitioning_tools()
    
    if shutil.which("sgdisk"):
        # Single root partition
        run_command(["sgdisk", "-n", "1:0:0", "-t", "1:8300", disk])
        run_command(["partprobe", disk])
    elif shutil.which("parted"):
        run_command(["parted", disk, "mkpart", "primary", "ext4", "1MiB", "100%"])
    elif shutil.which("fdisk"):
        # Fallback to fdisk
        print("[WARNING] Using fdisk fallback for BIOS setup")
        import subprocess
        fdisk_commands = "o\nn\np\n1\n\n\na\n1\nw\n"
        proc = subprocess.Popen(["fdisk", disk], stdin=subprocess.PIPE, text=True)
        proc.communicate(input=fdisk_commands)
    else:
        raise RuntimeError("No partitioning tool available for BIOS setup. Install sgdisk, parted, or fdisk.")

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
    
    # Force unmount and wait before formatting
    import time
    
    def is_mounted(device):
        """Check if a device is mounted"""
        try:
            result = run_command(["mount"], capture_output=True, text=True, check=False)
            return device in result.stdout
        except:
            return False
    
    def force_unmount(device):
        """Aggressively unmount a device"""
        for attempt in range(5):
            try:
                run_command(["umount", "-f", device], capture_output=True, check=False)
                run_command(["umount", "-l", device], capture_output=True, check=False)  # Lazy unmount
                run_command(["umount", device], capture_output=True, check=False)
            except:
                pass
            time.sleep(1)
            if not is_mounted(device):
                break
        
        # Final check
        if is_mounted(device):
            raise RuntimeError(f"Unable to unmount {device} - device is busy")
    
    # Format EFI partition if UEFI
    if boot_part:
        force_unmount(boot_part)
        run_command(["mkfs.fat", "-F32", boot_part])
    
    # Only format root partition if not using encryption
    # (encryption setup and formatting is handled separately in main installer)
    if not encrypt:
        force_unmount(root_part)
        run_command(["mkfs.ext4", "-F", root_part])
