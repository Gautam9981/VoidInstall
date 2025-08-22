"""
Sound system selection and installation for voidinstall (Void Linux)
"""
import subprocess
import os

def ensure_chroot_mounts(target="/mnt"):
    """
    Ensure /dev, /proc, /sys, and /run are mounted in the chroot target.
    """
    from lib.sudo_utils import run_command
    
    mounts = [
        ("/dev", os.path.join(target, "dev")),
        ("/proc", os.path.join(target, "proc")),
        ("/sys", os.path.join(target, "sys")),
        ("/run", os.path.join(target, "run")),
    ]
    for src, dst in mounts:
        if not os.path.ismount(dst):
            # Create mount point if it doesn't exist
            os.makedirs(dst, exist_ok=True)
            run_command(["mount", "--bind", src, dst], capture_output=True)

def install_sound(target="/mnt", system="pipewire", hardware_packages=None):
    """
    Install and enable the selected sound system (pipewire or pulseaudio) in the target system.
    Also installs hardware-specific audio firmware if provided.
    """
    from lib.sudo_utils import run_chroot_command
    
    ensure_chroot_mounts(target)
    
    if system == "pipewire":
        pkgs = ["alsa-utils", "pipewire", "wireplumber"]
        services = ["pipewire", "wireplumber"]
    else:
        pkgs = ["alsa-utils", "pulseaudio"]
        services = ["pulseaudio"]
    
    # Add hardware-specific audio firmware packages
    if hardware_packages:
        pkgs.extend(hardware_packages)
    
    run_chroot_command(target, ["xbps-install", "-Sy"] + pkgs)
    
    for svc in services:
        run_chroot_command(target, ["sh", "-c", f"[ -d /etc/sv/{svc} ] && ln -sf /etc/sv/{svc} /var/service/"])
    
    return f"[INFO] Installed and enabled {system} sound system." + (f" Audio firmware: {', '.join(hardware_packages)}" if hardware_packages else "")
