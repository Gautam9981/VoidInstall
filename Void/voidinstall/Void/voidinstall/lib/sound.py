"""
Sound system selection and installation for voidinstall (Void Linux)
"""
def install_sound(target="/mnt", system="pipewire"):

import subprocess
import os

def ensure_chroot_mounts(target="/mnt"):
    """
    Ensure /dev, /proc, /sys, and /run are mounted in the chroot target.
    """
    mounts = [
        ("/dev", os.path.join(target, "dev")),
        ("/proc", os.path.join(target, "proc")),
        ("/sys", os.path.join(target, "sys")),
        ("/run", os.path.join(target, "run")),
    ]
    for src, dst in mounts:
        if not os.path.ismount(dst):
            subprocess.run(["mount", "--bind", src, dst], check=True)

def install_sound(target="/mnt", system="pipewire"):
    """
    Install and enable the selected sound system (pipewire or pulseaudio) in the target system.
    """
    ensure_chroot_mounts(target)
    if system == "pipewire":
        pkgs = ["alsa-utils", "pipewire", "wireplumber"]
        services = ["pipewire", "wireplumber"]
    else:
        pkgs = ["alsa-utils", "pulseaudio"]
        services = ["pulseaudio"]
    subprocess.run(["chroot", target, "xbps-install", "-Sy"] + pkgs, check=True)
    for svc in services:
        subprocess.run(["chroot", target, "sh", "-c", f"[ -d /etc/sv/{svc} ] && ln -sf /etc/sv/{svc} /var/service/"], check=True)
    print(f"[INFO] Installed and enabled {system} sound system.")
