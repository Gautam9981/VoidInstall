"""
Disk partitioning and management for voidinstall (Void Linux)
"""
import subprocess

def list_disks():
    result = subprocess.run(["lsblk", "-d", "-o", "NAME,SIZE,TYPE"], capture_output=True, text=True)
    return result.stdout

def wipe_disk(disk):
    subprocess.run(["sgdisk", "--zap-all", disk], check=True)

def create_gpt_partition(disk, start="0", end="0", typecode="8300"):
    subprocess.run(["sgdisk", "-n", f"1:{start}:{end}", "-t", f"1:{typecode}", disk], check=True)
    subprocess.run(["partprobe", disk], check=True)

def get_partition(disk):
    return f"{disk}1"
