"""
Cryptography/encryption utilities for voidinstall
"""
import subprocess

def luks_format(partition, name="cryptroot"):
    subprocess.run(["cryptsetup", "luksFormat", partition], check=True)
    subprocess.run(["cryptsetup", "open", partition, name], check=True)
    return f"/dev/mapper/{name}"
