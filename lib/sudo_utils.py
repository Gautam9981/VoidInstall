"""
Sudo utilities for voidinstall - handles running commands with sudo in live environment
"""
import subprocess
import os

def run_command(cmd, check=True, input_data=None, capture_output=False, text=False):
    """
    Run a command with sudo for privileged operations in live installer.
    
    Args:
        cmd: Command as list or string
        check: Whether to check return code (default: True)
        input_data: Input data to pass to the command
        capture_output: Whether to capture output (default: False)
        text: Whether to treat input/output as text (default: False)
    
    Returns:
        subprocess.CompletedProcess object
    """
    if isinstance(cmd, str):
        cmd = cmd.split()
    
    # Commands that don't need sudo (read-only operations)
    readonly_commands = ['lsblk', 'ls', 'cat', 'echo', 'which', 'find', 'test', 'stat']
    needs_sudo = not any(cmd[0].endswith(readonly_cmd) for readonly_cmd in readonly_commands)
    
    # Use sudo for privileged operations if we're not already root
    if needs_sudo and os.geteuid() != 0:
        # Ensure sudo is available
        if not subprocess.run(['which', 'sudo'], capture_output=True).returncode == 0:
            print("[WARNING] sudo not found - some operations may fail")
            print("[INFO] Installing sudo...")
            try:
                subprocess.run(['xbps-install', '-y', 'sudo'], check=True)
            except:
                print("[ERROR] Failed to install sudo")
        else:
            cmd = ['sudo'] + cmd
    
    return subprocess.run(
        cmd, 
        check=check, 
        input=input_data, 
        capture_output=capture_output, 
        text=text
    )

def run_chroot_command(target, cmd, check=True, input_data=None):
    """
    Run a command in chroot environment with sudo.
    
    Args:
        target: Chroot target directory (e.g., "/mnt")
        cmd: Command to run inside chroot
        check: Whether to check return code (default: True)
        input_data: Input data to pass to the command
    
    Returns:
        subprocess.CompletedProcess object
    """
    if isinstance(cmd, str):
        cmd = cmd.split()
    
    chroot_cmd = ['sudo', 'chroot', target] + cmd
    return subprocess.run(
        chroot_cmd, 
        check=check, 
        input=input_data
    )
