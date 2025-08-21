"""
Cryptography/encryption utilities for voidinstall
"""
import subprocess
from lib.sudo_utils import run_command

def luks_format(partition, name="cryptroot"):
    run_command(["cryptsetup", "luksFormat", partition])
    run_command(["cryptsetup", "open", partition, name])
    return f"/dev/mapper/{name}"
