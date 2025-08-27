def unmount_disk_partitions(disk):
    # Unmount all mounted partitions of the disk
    import re
    print(f"Unmounting all partitions on {disk}...")
    # List mounted partitions
    result = subprocess.run("lsblk -ln -o NAME,MOUNTPOINT", shell=True, capture_output=True, text=True)
    for line in result.stdout.strip().split('\n'):
        parts = line.split()
        if len(parts) == 2:
            partname, mnt = parts
            if mnt != "" and partname.startswith(disk.replace('/dev/', '')):
                run_cmd(f"umount /dev/{partname}", check=False)
def detect_uefi():
    # UEFI systems have /sys/firmware/efi
    try:
        with open('/sys/firmware/efi/fw_platform_size') as f:
            return True
    except FileNotFoundError:
        return False

def install_bootloader(disk):
    print("\nInstalling GRUB bootloader...")
    uefi = detect_uefi()
    if uefi:
        # UEFI: install grub-x86_64-efi and efibootmgr
        run_cmd(f"xbps-install -Sy -R {VOID_MIRROR} -r /mnt grub-x86_64-efi efibootmgr")
        efi_part = input("Enter EFI partition (e.g., /dev/sda1, or leave blank if already mounted): ")
        if efi_part:
            run_cmd(f"mkdir -p /mnt/boot/efi")
            run_cmd(f"mount {efi_part} /mnt/boot/efi")
        run_cmd(f"chroot /mnt grub-install --target=x86_64-efi --efi-directory=/boot/efi --bootloader-id=Void --recheck")
    else:
        # Legacy BIOS: install grub
        run_cmd(f"xbps-install -Sy -R {VOID_MIRROR} -r /mnt grub")
        run_cmd(f"chroot /mnt grub-install --target=i386-pc {disk}")
    run_cmd(f"chroot /mnt grub-mkconfig -o /boot/grub/grub.cfg")
    print("GRUB installation complete.")
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

def auto_partition_disk(disk, uefi, use_swap, swap_size):
    print(f"\nAuto-partitioning {disk} (this will erase all data on the disk!)")
    if uefi:
        if use_swap:
            print(f"UEFI detected: Will create EFI (512M, type ef00), root (ext4), and swap ({swap_size}) partitions.")
        else:
            print("UEFI detected: Will create EFI (512M, type ef00) and root (ext4) partitions. No swap.")
    else:
        if use_swap:
            print(f"Legacy BIOS detected: Will create root (ext4) and swap ({swap_size}) partitions.")
        else:
            print("Legacy BIOS detected: Will create root (ext4) partition. No swap.")
    confirm = input("Type 'YES' to continue: ")
    if confirm != 'YES':
        print("Aborting.")
        sys.exit(0)
    unmount_disk_partitions(disk)
    run_cmd(f"wipefs -a {disk}")
    run_cmd(f"sgdisk -Z {disk}")
    if uefi:
        run_cmd(f"sgdisk -n 1:0:+512M -t 1:ef00 {disk}")  # EFI
        if use_swap:
            run_cmd(f"sgdisk -n 2:0:+20G -t 2:8300 {disk}")    # root
            run_cmd(f"sgdisk -n 3:0:+{swap_size} -t 3:8200 {disk}")  # swap
        else:
            run_cmd(f"sgdisk -n 2:0:0 -t 2:8300 {disk}")    # root (rest of disk)
    else:
        if use_swap:
            run_cmd(f"sgdisk -n 1:0:+20G -t 1:8300 {disk}")    # root
            run_cmd(f"sgdisk -n 2:0:+{swap_size} -t 2:8200 {disk}")  # swap
        else:
            run_cmd(f"sgdisk -n 1:0:0 -t 1:8300 {disk}")    # root (rest of disk)
    run_cmd(f"partprobe {disk}")
    print("Partitions created:")
    run_cmd(f"lsblk {disk}")

def format_auto_partitions(disk, uefi, use_swap):
    if uefi:
        efi = f"{disk}1"
        root = f"{disk}2"
        run_cmd(f"mkfs.vfat -F32 {efi}")
        run_cmd(f"mkfs.ext4 {root}")
        run_cmd(f"mount {root} /mnt")
        run_cmd(f"mkdir -p /mnt/boot/efi")
        run_cmd(f"mount {efi} /mnt/boot/efi")
        if use_swap:
            swap = f"{disk}3"
            run_cmd(f"mkswap {swap}")
            run_cmd(f"swapon {swap}")
        return root
    else:
        root = f"{disk}1"
        run_cmd(f"mkfs.ext4 {root}")
        run_cmd(f"mount {root} /mnt")
        if use_swap:
            swap = f"{disk}2"
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
    # Add sudo
    run_cmd(f"xbps-install -Sy sudo", chroot=True)
    run_cmd(f"echo '{username} ALL=(ALL) ALL' >> /mnt/etc/sudoers.d/{username}", check=True)
    print(f"User {username} created and sudo enabled.")

def install_desktop_and_sound():
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
    # Sound packages (ALSA, Pulse, PipeWire)
    sound_pkgs = "alsa-utils pulseaudio pavucontrol pipewire pipewire-alsa pipewire-pulse"
    if pkgs:
        print(f"Installing {de_key} and sound packages...")
        run_cmd(f"xbps-install -Sy -R {VOID_MIRROR} -r /mnt {pkgs} {sound_pkgs}")
        # Enable display manager
        if de_key == "xfce":
            run_cmd("ln -sf /etc/sv/lightdm /mnt/etc/runit/runsvdir/default/", check=False)
        elif de_key == "gnome":
            run_cmd("ln -sf /etc/sv/gdm /mnt/etc/runit/runsvdir/default/", check=False)
        elif de_key == "kde":
            run_cmd("ln -sf /etc/sv/sddm /mnt/etc/runit/runsvdir/default/", check=False)
    else:
        print("No desktop environment will be installed. Installing sound packages only...")
        run_cmd(f"xbps-install -Sy -R {VOID_MIRROR} -r /mnt {sound_pkgs}")
    # Enable sound services
    run_cmd("ln -sf /etc/sv/dbus /mnt/etc/runit/runsvdir/default/", check=False)
    run_cmd("ln -sf /etc/sv/pipewire /mnt/etc/runit/runsvdir/default/", check=False)
    run_cmd("ln -sf /etc/sv/pulseaudio /mnt/etc/runit/runsvdir/default/", check=False)
    print("Desktop and sound setup complete.")

    return

def manual_partition_disk(disk):
    print(f"\nManual partitioning for {disk}.")
    print("You will be dropped into cfdisk. Create partitions as needed (root, swap, home, EFI, etc.).")
    input("Press Enter to continue...")
    run_cmd(f"cfdisk {disk}")

def format_and_mount_manual():
    print("\nList partitions:")
    run_cmd("lsblk -o NAME,SIZE,TYPE,MOUNTPOINT")
    partitions = []
    while True:
        part = input("Enter partition device (e.g., /dev/sda1, blank to finish): ")
        if not part:
            break
        mnt = input("Mount point (e.g., /, /home, swap, /boot/efi): ")
        fstype = input("Filesystem type (ext4, vfat, swap, etc.): ")
        if fstype == "swap":
            run_cmd(f"mkswap {part}")
            run_cmd(f"swapon {part}")
        else:
            run_cmd(f"mkfs.{fstype} {part}")
            if mnt != "swap":
                partitions.append((part, mnt))
    # Mount all partitions
    for part, mnt in partitions:
        if mnt == "/":
            run_cmd(f"mount {part} /mnt")
        else:
            run_cmd(f"mkdir -p /mnt{mnt}")
            run_cmd(f"mount {part} /mnt{mnt}")
    return

    print("=== Void Linux Interactive Installer ===")
    uefi = detect_uefi()
    if uefi:
        print("System booted in UEFI mode.")
        print("For UEFI, you need an EFI partition (FAT32, 512M recommended) mounted at /boot/efi.")
    else:
        print("System booted in Legacy BIOS mode.")
        print("For BIOS, you need a root partition (ext4) and swap.")
    disk = select_disk()
    mode = input("Partitioning mode? [a]uto/[m]anual: ").strip().lower()
    if mode == "a":
        auto_partition_disk(disk, uefi)
        root = format_auto_partitions(disk, uefi)
        # mount_partitions(root) # now handled in format_auto_partitions
    else:
        manual_partition_disk(disk)
        format_and_mount_manual()
    install_base()
    setup_mirrors()
    create_user()
    install_desktop_and_sound()
    install_bootloader(disk)
    print("\nInstallation steps complete! System is ready to reboot.")

def main():
    print("=== Void Linux Interactive Installer ===")
    uefi = detect_uefi()
    if uefi:
        print("System booted in UEFI mode.")
        print("For UEFI, you need an EFI partition (FAT32, 512M recommended) mounted at /boot/efi.")
    else:
        print("System booted in Legacy BIOS mode.")
        print("For BIOS, you need a root partition (ext4) and swap.")
    disk = select_disk()
    mode = input("Partitioning mode? [a]uto/[m]anual: ").strip().lower()
    use_swap = False
    swap_size = ""
    if mode == "a":
        swap_choice = input("Create a swap partition? [y/N]: ").strip().lower()
        if swap_choice == "y":
            use_swap = True
            swap_size = input("Enter swap size (e.g., 2G, 512M): ").strip()
        auto_partition_disk(disk, uefi, use_swap, swap_size)
        root = format_auto_partitions(disk, uefi, use_swap)
        # mount_partitions(root) # now handled in format_auto_partitions
    else:
        manual_partition_disk(disk)
        format_and_mount_manual()
    install_base()
    setup_mirrors()
    create_user()
    install_desktop_and_sound()
    install_bootloader(disk)
    print("\nInstallation steps complete! System is ready to reboot.")

if __name__ == "__main__":
    main()
