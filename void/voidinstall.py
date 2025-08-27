#!/usr/bin/env python3
# --- Modular Installer Inspired by archinstall ---
import subprocess
import sys
import getpass
import os
import shutil

VOID_MIRROR = "https://repo-default.voidlinux.org/current"
BASE_PKGS = "base-system"
DESKTOP_ENVIRONMENTS = {
    "xfce": "xfce4 xfce4-terminal lightdm lightdm-gtk3-greeter",
    "gnome": "gnome gdm",
    "kde": "kde5 sddm",
    "none": ""
}

# Required dependencies for the installer
REQUIRED_DEPS = [
    "util-linux",      # for lsblk, mount, umount, wipefs, cfdisk
    "gptfdisk",        # for sgdisk
    "parted",          # for partprobe
    "e2fsprogs",       # for mkfs.ext4
    "dosfstools",      # for mkfs.vfat
    "xbps",            # for xbps-install (should be included in live image)
    "coreutils",       # for basic commands
    "procps-ng",       # for process management
    "which",           # for command checking
]

def check_dependencies():
    """Check if required dependencies are available and install missing ones."""
    print(f"{Style.HEADER}{Style.BOLD}Checking dependencies...{Style.ENDC}")
    
    missing_deps = []
    command_checks = {
        'lsblk': 'util-linux',
        'sgdisk': 'gptfdisk', 
        'partprobe': 'parted',
        'mkfs.ext4': 'e2fsprogs',
        'mkfs.vfat': 'dosfstools',
        'xbps-install': 'xbps',
        'mount': 'util-linux',
        'umount': 'util-linux',
        'cfdisk': 'util-linux',
        'wipefs': 'util-linux',
        'lspci': 'pciutils',
        'lsusb': 'usbutils'
    }
    
    for cmd, package in command_checks.items():
        if not shutil.which(cmd):
            if package not in missing_deps:
                missing_deps.append(package)
            print(f"{Style.WARNING}Missing command: {cmd} (from package: {package}){Style.ENDC}")
    
    if missing_deps:
        print(f"\n{Style.FAIL}Missing dependencies: {' '.join(missing_deps)}{Style.ENDC}")
        print(f"{Style.OKCYAN}Attempting to install missing dependencies...{Style.ENDC}")
        
        try:
            # Update package database first
            run_cmd("xbps-install -S", check=False)
            # Install missing packages
            deps_str = ' '.join(missing_deps)
            run_cmd(f"xbps-install -y {deps_str}")
            print(f"{Style.OKGREEN}Successfully installed missing dependencies.{Style.ENDC}")
        except Exception as e:
            print(f"{Style.FAIL}Failed to install dependencies: {e}{Style.ENDC}")
            print(f"{Style.WARNING}Please ensure you're running this on a Void Linux live system with internet access.{Style.ENDC}")
            sys.exit(1)
    else:
        print(f"{Style.OKGREEN}All required dependencies are available.{Style.ENDC}")

class Style:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def run_cmd(cmd, check=True, chroot=False):
    if chroot:
        cmd = f"chroot /mnt /bin/bash -c '{cmd}'"
    print(f"\n{Style.OKBLUE}[RUNNING]{Style.ENDC} {cmd}")
    result = subprocess.run(cmd, shell=True)
    if check and result.returncode != 0:
        print(f"[ERROR] Command failed: {cmd}")
        sys.exit(1)

def mount_chroot_dirs():
    print(f"{Style.OKBLUE}Mounting chroot directories...{Style.ENDC}")
    run_cmd("mount --bind /dev /mnt/dev")
    run_cmd("mount --bind /dev/pts /mnt/dev/pts")
    run_cmd("mount -t proc none /mnt/proc")
    run_cmd("mount -t sysfs none /mnt/sys")
    run_cmd("mount -t tmpfs tmpfs /mnt/run")

def umount_chroot_dirs():
    print(f"{Style.OKBLUE}Unmounting chroot directories...{Style.ENDC}")
    run_cmd("umount -l /mnt/dev/pts", check=False)
    run_cmd("umount -l /mnt/dev", check=False)
    run_cmd("umount -l /mnt/proc", check=False)
    run_cmd("umount -l /mnt/sys", check=False)
    run_cmd("umount -l /mnt/run", check=False)

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

def detect_hardware():
    """Detect hardware and determine required packages."""
    print(f"\n{Style.HEADER}{Style.BOLD}Detecting hardware...{Style.ENDC}")
    
    hardware_pkgs = []
    
    # Detect CPU and microcode
    try:
        with open('/proc/cpuinfo', 'r') as f:
            cpu_info = f.read().lower()
        
        if 'intel' in cpu_info:
            print(f"{Style.OKCYAN}Intel CPU detected - adding Intel microcode{Style.ENDC}")
            hardware_pkgs.append("intel-ucode")
        elif 'amd' in cpu_info:
            print(f"{Style.OKCYAN}AMD CPU detected - adding AMD microcode{Style.ENDC}")
            hardware_pkgs.append("linux-firmware-amd")
    except Exception as e:
        print(f"{Style.WARNING}Could not detect CPU type: {e}{Style.ENDC}")
    
    # Detect GPU
    try:
        result = subprocess.run("lspci | grep -i vga", shell=True, capture_output=True, text=True)
        gpu_info = result.stdout.lower()
        
        if 'nvidia' in gpu_info:
            print(f"{Style.OKCYAN}NVIDIA GPU detected - adding proprietary drivers{Style.ENDC}")
            hardware_pkgs.extend(["nvidia", "nvidia-libs-32bit"])
        elif 'amd' in gpu_info or 'ati' in gpu_info:
            print(f"{Style.OKCYAN}AMD GPU detected - adding Mesa drivers{Style.ENDC}")
            hardware_pkgs.extend(["mesa-dri", "mesa-vulkan-radeon", "mesa-vaapi", "mesa-vdpau"])
        elif 'intel' in gpu_info:
            print(f"{Style.OKCYAN}Intel GPU detected - adding Intel drivers{Style.ENDC}")
            hardware_pkgs.extend(["mesa-dri", "intel-video-accel", "mesa-vulkan-intel"])
            
    except Exception as e:
        print(f"{Style.WARNING}Could not detect GPU: {e}{Style.ENDC}")
    
    # Detect WiFi hardware
    try:
        result = subprocess.run("lspci | grep -i wireless", shell=True, capture_output=True, text=True)
        wifi_info = result.stdout.lower()
        
        if wifi_info:
            print(f"{Style.OKCYAN}WiFi hardware detected - adding firmware{Style.ENDC}")
            hardware_pkgs.extend(["linux-firmware-network", "wpa_supplicant", "NetworkManager"])
            
    except Exception as e:
        print(f"{Style.WARNING}Could not detect WiFi hardware: {e}{Style.ENDC}")
    
    # Detect Bluetooth
    try:
        result = subprocess.run("lsusb | grep -i bluetooth", shell=True, capture_output=True, text=True)
        bt_info = result.stdout.lower()
        
        if bt_info:
            print(f"{Style.OKCYAN}Bluetooth hardware detected - adding support{Style.ENDC}")
            hardware_pkgs.extend(["bluez", "bluez-alsa"])
            
    except Exception as e:
        print(f"{Style.WARNING}Could not detect Bluetooth hardware: {e}{Style.ENDC}")
    
    return hardware_pkgs



def detect_uefi():
    # UEFI systems have /sys/firmware/efi
    try:
        with open('/sys/firmware/efi/fw_platform_size') as f:
            return True
    except FileNotFoundError:
        return False

def select_disk():
    print(f"\n{Style.HEADER}{Style.BOLD}Available disks:{Style.ENDC}")
    run_cmd("lsblk -d -o NAME,SIZE,MODEL")
    disk = input("Enter the disk to install Void Linux on (e.g., sda): ")
    return f"/dev/{disk}"

def auto_partition_disk(disk, uefi, use_swap, swap_size):
    print(f"\n{Style.WARNING}{Style.BOLD}Auto-partitioning {disk} (this will erase all data on the disk!){Style.ENDC}")
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
    print(f"{Style.OKGREEN}Partitions created:{Style.ENDC}")
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

def manual_partition_disk(disk):
    print(f"\n{Style.WARNING}{Style.BOLD}Manual partitioning for {disk}.{Style.ENDC}")
    print(f"{Style.OKCYAN}You will be dropped into cfdisk. Create partitions as needed (root, swap, home, EFI, etc.).{Style.ENDC}")
    input("Press Enter to continue...")
    run_cmd(f"cfdisk {disk}")

def format_and_mount_manual():
    print(f"\n{Style.HEADER}{Style.BOLD}List partitions:{Style.ENDC}")
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

def setup_mirrors():
    print(f"\n{Style.OKCYAN}Setting up Void Linux mirrors...{Style.ENDC}")
    run_cmd("mkdir -p /mnt/etc/xbps.d")
    
    # Main repository
    repo_conf = f"repository={VOID_MIRROR}\n"
    with open("/mnt/etc/xbps.d/00-repository-main.conf", "w") as f:
        f.write(repo_conf)
    
    # Add non-free repositories to the target system
    print(f"{Style.OKCYAN}Setting up non-free repositories in target system...{Style.ENDC}")
    
    # Non-free repository
    nonfree_conf = f"repository={VOID_MIRROR}/nonfree\n"
    with open("/mnt/etc/xbps.d/10-repository-nonfree.conf", "w") as f:
        f.write(nonfree_conf)
    
    # Multilib non-free repository  
    multilib_nonfree_conf = f"repository={VOID_MIRROR}/multilib/nonfree\n"
    with open("/mnt/etc/xbps.d/10-repository-multilib-nonfree.conf", "w") as f:
        f.write(multilib_nonfree_conf)
    
    # Multilib repository (for 32-bit packages)
    multilib_conf = f"repository={VOID_MIRROR}/multilib\n"
    with open("/mnt/etc/xbps.d/10-repository-multilib.conf", "w") as f:
        f.write(multilib_conf)
    
    print(f"{Style.OKGREEN}All repositories configured in target system.{Style.ENDC}")

def setup_bootstrap_repos():
    """Setup non-free repositories for the live system during bootstrap."""
    print(f"\n{Style.OKCYAN}Setting up non-free repositories for bootstrap...{Style.ENDC}")
    
    try:
        # Install repository packages on live system
        run_cmd("xbps-install -Sy void-repo-nonfree void-repo-multilib-nonfree", check=False)
        
        # Update package database to include new repositories
        run_cmd("xbps-install -S")
        
        print(f"{Style.OKGREEN}Bootstrap repositories configured successfully.{Style.ENDC}")
        return True
    except Exception as e:
        print(f"{Style.WARNING}Could not set up bootstrap repositories: {e}{Style.ENDC}")
        print(f"{Style.WARNING}Will continue with limited package availability.{Style.ENDC}")
        return False

def install_base():
    print(f"\n{Style.OKCYAN}Installing base system from mirrors...{Style.ENDC}")
    
    # Detect hardware and get required packages
    hardware_pkgs = detect_hardware()
    
    # Combine base packages with hardware-specific packages
    all_pkgs = BASE_PKGS
    if hardware_pkgs:
        all_pkgs += " " + " ".join(hardware_pkgs)
        print(f"{Style.OKCYAN}Installing hardware-specific packages: {' '.join(hardware_pkgs)}{Style.ENDC}")
    
    run_cmd(f"xbps-install -Sy -y -R {VOID_MIRROR} -r /mnt {all_pkgs}")
    
    # Enable hardware-specific services
    if "NetworkManager" in hardware_pkgs:
        run_cmd("ln -sf /etc/sv/NetworkManager /mnt/etc/runit/runsvdir/default/", check=False)
        print(f"{Style.OKGREEN}NetworkManager service enabled.{Style.ENDC}")
    
    if "bluez" in hardware_pkgs:
        run_cmd("ln -sf /etc/sv/bluetoothd /mnt/etc/runit/runsvdir/default/", check=False)
        print(f"{Style.OKGREEN}Bluetooth service enabled.{Style.ENDC}")
    
    # Handle NVIDIA-specific setup
    if "nvidia" in hardware_pkgs:
        print(f"{Style.WARNING}NVIDIA drivers installed. You may need to blacklist nouveau manually.{Style.ENDC}")
        mount_chroot_dirs()
        run_cmd("echo 'blacklist nouveau' >> /mnt/etc/modprobe.d/nvidia.conf", check=False)
        umount_chroot_dirs()

def create_user():
    print(f"\n{Style.HEADER}{Style.BOLD}User creation:{Style.ENDC}")
    username = input("Enter username: ")
    password = getpass.getpass("Enter password: ")
    mount_chroot_dirs()
    run_cmd(f"useradd -m -G wheel,audio,video -s /bin/bash {username}", chroot=True)
    run_cmd(f"echo '{username}:{password}' | chpasswd", chroot=True)
    # Add sudo
    run_cmd(f"xbps-install -Sy -y sudo", chroot=True)
    run_cmd(f"mkdir -p /mnt/etc/sudoers.d", check=False)
    run_cmd(f"echo '{username} ALL=(ALL) ALL' > /mnt/etc/sudoers.d/{username}", check=True)
    print(f"User {username} created and sudo enabled.")
    umount_chroot_dirs()

def install_desktop_and_sound():
    print(f"\n{Style.HEADER}{Style.BOLD}Available desktop environments:{Style.ENDC}")
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
    sound_pkgs = "alsa-utils pulseaudio pavucontrol pipewire wireplumber sof-firmware"
    
    if pkgs:
        print(f"{Style.OKCYAN}Installing {de_key} and sound packages...{Style.ENDC}")
        run_cmd(f"xbps-install -Sy -y -R {VOID_MIRROR} -r /mnt {pkgs} {sound_pkgs}")
        # Enable display manager
        if de_key == "xfce":
            run_cmd("ln -sf /etc/sv/lightdm /mnt/etc/runit/runsvdir/default/", check=False)
        elif de_key == "gnome":
            run_cmd("ln -sf /etc/sv/gdm /mnt/etc/runit/runsvdir/default/", check=False)
        elif de_key == "kde":
            run_cmd("ln -sf /etc/sv/sddm /mnt/etc/runit/runsvdir/default/", check=False)
    else:
        print(f"{Style.WARNING}No desktop environment will be installed. Installing sound packages only...{Style.ENDC}")
        run_cmd(f"xbps-install -Sy -y -R {VOID_MIRROR} -r /mnt {sound_pkgs}")
    
    # Enable sound services
    run_cmd("ln -sf /etc/sv/dbus /mnt/etc/runit/runsvdir/default/", check=False)
    run_cmd("ln -sf /etc/sv/pipewire /mnt/etc/runit/runsvdir/default/", check=False)
    run_cmd("ln -sf /etc/sv/pulseaudio /mnt/etc/runit/runsvdir/default/", check=False)
    print(f"{Style.OKGREEN}Desktop and sound setup complete.{Style.ENDC}")

def install_bootloader(disk):
    print("\nInstalling GRUB bootloader...")
    uefi = detect_uefi()
    mount_chroot_dirs()
    if uefi:
        # UEFI: install grub-x86_64-efi and efibootmgr
        run_cmd(f"xbps-install -Sy -y -R {VOID_MIRROR} -r /mnt grub-x86_64-efi efibootmgr")
        efi_part = input("Enter EFI partition (e.g., /dev/sda1, or leave blank if already mounted): ")
        if efi_part:
            run_cmd(f"mkdir -p /mnt/boot/efi")
            run_cmd(f"mount {efi_part} /mnt/boot/efi")
        run_cmd(f"chroot /mnt grub-install --target=x86_64-efi --efi-directory=/boot/efi --bootloader-id=Void --recheck")
    else:
        # Legacy BIOS: install grub
        run_cmd(f"xbps-install -Sy -y -R {VOID_MIRROR} -r /mnt grub")
        run_cmd(f"chroot /mnt grub-install --target=i386-pc {disk}")
    run_cmd(f"chroot /mnt grub-mkconfig -o /boot/grub/grub.cfg")
    print("GRUB installation complete.")
    umount_chroot_dirs()

def main():
    print(f"{Style.BOLD}{Style.OKGREEN}=== Void Linux Interactive Installer ==={Style.ENDC}")
    
    # Check if running as root
    if os.geteuid() != 0:
        print(f"{Style.FAIL}This installer must be run as root.{Style.ENDC}")
        sys.exit(1)
    
    # Check and install dependencies first
    check_dependencies()
    
    # Setup non-free repositories for bootstrap (live system)
    nonfree_available = setup_bootstrap_repos()
    if not nonfree_available:
        print(f"{Style.WARNING}Continuing without non-free repositories. Some hardware may not be fully supported.{Style.ENDC}")
    
    uefi = detect_uefi()
    if uefi:
        print(f"{Style.OKCYAN}System booted in UEFI mode.{Style.ENDC}")
        print(f"{Style.OKBLUE}For UEFI, you need an EFI partition (FAT32, 512M recommended) mounted at /boot/efi.{Style.ENDC}")
    else:
        print(f"{Style.OKCYAN}System booted in Legacy BIOS mode.{Style.ENDC}")
        print(f"{Style.OKBLUE}For BIOS, you need a root partition (ext4) and swap.{Style.ENDC}")
    
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
    else:
        manual_partition_disk(disk)
        format_and_mount_manual()
    
    install_base()
    setup_mirrors()
    create_user()
    install_desktop_and_sound()
    install_bootloader(disk)
    
    print(f"\n{Style.OKGREEN}{Style.BOLD}Installation steps complete! System is ready to reboot.{Style.ENDC}")

if __name__ == "__main__":
    main()
