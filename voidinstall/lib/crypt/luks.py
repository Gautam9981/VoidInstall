"""
Cryptography/encryption utilities for voidinstall
"""
import subprocess
from lib.sudo_utils import run_command

def luks_format(partition, password, name="cryptroot"):
    """
    Format a partition with LUKS encryption using the provided password.
    Fully automated - no user prompts.
    """
    # Format the LUKS partition with batch mode (no confirmation prompt)
    run_command([
        "cryptsetup", "luksFormat", 
        "--batch-mode",  # Don't ask for confirmation
        "--force-password",  # Don't complain about password quality
        partition
    ], input_data=password.encode())
    
    # Open the LUKS partition
    run_command([
        "cryptsetup", "open", 
        partition, name
    ], input_data=password.encode())
    
    return f"/dev/mapper/{name}"
