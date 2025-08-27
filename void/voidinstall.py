#!/usr/bin/env python3
# --- Modular Installer Inspired by archinstall ---
import subprocess
import sys
import getpass

VOID_MIRROR = "https://repo-default.voidlinux.org/current"
BASE_PKGS = "base-system"
DESKTOP_ENVIRONMENTS = {
    "xfce": "xfce4 xfce4-terminal lightdm lightdm-gtk3-greeter",
    "gnome": "gnome gdm",
    "kde": "kde5 sddm",
    "none": ""
}

def run_cmd(cmd, check=True, chroot=False):
    if chroot:
        cmd = f"chroot /mnt /bin/bash -c '{cmd}'"
    print(f"\n[RUNNING] {cmd}")
    result = subprocess.run(cmd, shell=True)
    if check and result.returncode != 0:
        print(f"[ERROR] Command failed: {cmd}")
        sys.exit(1)

def select_disk():
    print("\nAvailable disks:")
    run_cmd("lsblk -d -o NAME,SIZE,MODEL")
    disk = input("Enter the disk to install Void Linux on (e.g., sda): ")
    return f"/dev/{disk}"

def partition_disk(disk):
    print(f"\nPartitioning {disk} (this will erase all data on the disk!)")
    confirm = input("Type 'YES' to continue: ")
    if confirm != 'YES':
        print("Aborting.")
        sys.exit(0)
    run_cmd(f"cfdisk {disk}", check=True)

def format_partitions():
    print("\nList partitions:")
    run_cmd("lsblk -o NAME,SIZE,TYPE,MOUNTPOINT")
    root = input("Enter root partition (e.g., /dev/sda1): ")
    run_cmd(f"mkfs.ext4 {root}")
    swap = input("Enter swap partition (or leave blank): ")
    if swap:
        run_cmd(f"mkswap {swap}")
        run_cmd(f"swapon {swap}")
    return root

def mount_partitions(root):
    run_cmd(f"mount {root} /mnt")

def setup_mirrors():
    print("\nSetting up Void Linux mirrors...")
    repo_conf = f"repository={VOID_MIRROR}\n"
    with open("/mnt/etc/xbps.d/00-repository-main.conf", "w") as f:
        f.write(repo_conf)

def install_base():
    print("\nInstalling base system from mirrors...")
    run_cmd(f"xbps-install -Sy -R {VOID_MIRROR} -r /mnt {BASE_PKGS}")

def create_user():
    print("\nUser creation:")
    username = input("Enter username: ")
    password = getpass.getpass("Enter password: ")
    run_cmd(f"useradd -m -G wheel,audio,video -s /bin/bash {username}", chroot=True)
    run_cmd(f"echo '{username}:{password}' | chpasswd", chroot=True)
    print(f"User {username} created.")

def install_desktop():
    print("\nAvailable desktop environments:")
    for i, de in enumerate(DESKTOP_ENVIRONMENTS.keys()):
        print(f"  {i+1}. {de}")
    choice = input("Select desktop environment [number, default none]: ")
    try:
        idx = int(choice) - 1
        de_key = list(DESKTOP_ENVIRONMENTS.keys())[idx]
    except (ValueError, IndexError):
        de_key = "none"
    pkgs = DESKTOP_ENVIRONMENTS[de_key]
    if pkgs:
        print(f"Installing {de_key}...")
        run_cmd(f"xbps-install -Sy -R {VOID_MIRROR} -r /mnt {pkgs}")
        # Enable display manager
        if de_key == "xfce":
            run_cmd("ln -sf /etc/sv/lightdm /mnt/etc/runit/runsvdir/default/", check=False)
        elif de_key == "gnome":
            run_cmd("ln -sf /etc/sv/gdm /mnt/etc/runit/runsvdir/default/", check=False)
        elif de_key == "kde":
            run_cmd("ln -sf /etc/sv/sddm /mnt/etc/runit/runsvdir/default/", check=False)
    else:
        print("No desktop environment will be installed.")

def main():
    print("=== Void Linux Interactive Installer ===")
    disk = select_disk()
    partition_disk(disk)
    root = format_partitions()
    mount_partitions(root)
    install_base()
    setup_mirrors()
    create_user()
    install_desktop()
    print("\nInstallation steps complete! Continue with chroot configuration and bootloader setup.")

if __name__ == "__main__":
    main()
