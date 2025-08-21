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
    subprocess.run(["sgdisk", "--zap-all", disk], check=True)

def create_partition(disk):
    subprocess.run(["sgdisk", "-n", "1:0:0", "-t", "1:8300", disk], check=True)
    subprocess.run(["partprobe", disk], check=True)

def get_partition(disk):
    return f"{disk}1"
