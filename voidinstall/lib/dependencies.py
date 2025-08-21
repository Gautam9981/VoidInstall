"""
Dependency management for voidinstall - ensures required tools are installed
"""
import subprocess
import shutil
from lib.sudo_utils import run_command

def check_and_install_tool(tool_name, package_name=None):
    """Check if a tool exists, install it if not"""
    if package_name is None:
        package_name = tool_name
    
    if not shutil.which(tool_name):
        print(f"[INFO] Installing required tool: {package_name}")
        try:
            run_command(["xbps-install", "-y", package_name])
            return True
        except subprocess.CalledProcessError:
            print(f"[WARNING] Failed to install {package_name}")
            return False
    return True

def install_partitioning_tools():
    """Install partitioning tools"""
    tools = [
        ("gdisk", "gptfdisk"),     # GPT fdisk for GUID partition tables
        ("sgdisk", "gptfdisk"),    # Scriptable GPT fdisk
        ("parted", "parted"),      # GNU parted partition editor
        ("fdisk", "util-linux"),   # Classic fdisk (MBR and GPT)
        ("cfdisk", "util-linux"),  # Curses-based fdisk (interactive)
        ("sfdisk", "util-linux")   # Scriptable fdisk
    ]
    
    print("[INFO] Ensuring partitioning tools are available...")
    for tool, package in tools:
        check_and_install_tool(tool, package)

def install_filesystem_tools():
    """Install filesystem tools"""
    tools = [
        ("mkfs.ext4", "e2fsprogs"),
        ("mkfs.fat", "dosfstools"),
        ("mount", "util-linux")
    ]
    
    print("[INFO] Ensuring filesystem tools are available...")
    for tool, package in tools:
        check_and_install_tool(tool, package)

def install_encryption_tools():
    """Install encryption tools for LUKS"""
    tools = [
        ("cryptsetup", "cryptsetup")
    ]
    
    print("[INFO] Installing encryption tools...")
    for tool, package in tools:
        check_and_install_tool(tool, package)

def install_all_dependencies(encryption_needed=False):
    """Install all required dependencies based on user selections"""
    print("[INFO] Installing required dependencies...")
    
    # Always needed
    install_partitioning_tools()
    install_filesystem_tools()
    
    # Only if encryption is selected
    if encryption_needed:
        install_encryption_tools()
    
    print("[INFO] Dependencies installation complete")
