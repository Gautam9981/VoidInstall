import shlex
import argparse

# --- Modular, robust installer inspired by Le0xFF/VoidLinuxInstaller ---

# --- Modular Installer Inspired by archinstall ---
import subprocess
import sys
import getpass
import os
import shutil

VOID_MIRROR = "https://repo-default.voidlinux.org/current"
BASE_PKGS = "base-system xorg"
DESKTOP_ENVIRONMENTS = {
    "xfce": "xfce4 xfce4-terminal lightdm lightdm-gtk3-greeter gvfs thunar-volman thunar-archive-plugin xfce4-pulseaudio-plugin network-manager-applet",
    "gnome": "gnome gdm gnome-tweaks gnome-software gvfs network-manager-applet",
    "kde": "kde5 sddm plasma-workspace plasma-desktop kdeplasma-addons kde-cli-tools kde-gtk-config kdeconnect dolphin konsole ark sddm-kcm gvfs network-manager-applet",
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
    "cryptsetup",      # for LUKS encryption
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
    if result.returncode != 0:
        print(f"{Style.FAIL}[ERROR] Command failed: {cmd}{Style.ENDC}")
        if check:
            print(f"{Style.WARNING}Please check your input, disk state, or network connection and try again.{Style.ENDC}")
            input("Press Enter to exit...")
            sys.exit(1)
        else:
            print(f"{Style.WARNING}Continuing despite the error (check=False).{Style.ENDC}")

def mount_chroot_dirs():
    print(f"{Style.OKBLUE}Mounting chroot directories...{Style.ENDC}")
    run_cmd("mkdir -p /mnt/dev /mnt/dev/pts /mnt/proc /mnt/sys /mnt/run", check=True)
    run_cmd("mount --bind /dev /mnt/dev")
    run_cmd("mount --bind /dev/pts /mnt/dev/pts")
    run_cmd("mount -t proc none /mnt/proc")
    run_cmd("mount -t sysfs none /mnt/sys")
    run_cmd("mount -t tmpfs tmpfs /mnt/run")
    # If the host has UEFI efivars, expose them inside chroot so efibootmgr works
    try:
        if os.path.exists("/sys/firmware/efi"):
            # Ensure efivarfs is mounted on the host (safe to run even if already mounted)
            run_cmd("mount -t efivarfs efivarfs /sys/firmware/efi/efivars", check=False)
            run_cmd("mkdir -p /mnt/sys/firmware/efi", check=False)
            run_cmd("mount --bind /sys/firmware/efi /mnt/sys/firmware/efi", check=False)
    except Exception:
        # Non-fatal: continue without efivars exposed
        print(f"{Style.WARNING}Could not bind efivars into chroot; efibootmgr may not work.{Style.ENDC}")

def umount_chroot_dirs():
    print(f"{Style.OKBLUE}Unmounting chroot directories...{Style.ENDC}")
    # Unbind efivars/efi if we bound it earlier
    run_cmd("umount -l /mnt/sys/firmware/efi", check=False)
    run_cmd("umount -l /mnt/dev/pts", check=False)
    run_cmd("umount -l /mnt/dev", check=False)
    run_cmd("umount -l /mnt/proc", check=False)
    run_cmd("umount -l /mnt/sys", check=False)
    run_cmd("umount -l /mnt/run", check=False)

def unmount_disk_partitions(disk):
    """
    Force unmount all mounted partitions of the disk (including /mnt and submounts).
    """
    import subprocess
    print(f"{Style.WARNING}Force unmounting all partitions on {disk}...{Style.ENDC}")

    # 1. Unmount all /mnt submounts (deepest first)
    result = subprocess.run("mount | grep '/mnt' | awk '{print $3}'", shell=True, capture_output=True, text=True)
    mnt_points = [mnt for mnt in result.stdout.strip().split('\n') if mnt]
    for mnt in sorted(mnt_points, key=len, reverse=True):
        print(f"{Style.WARNING}Force unmounting {mnt}...{Style.ENDC}")
        run_cmd(f"umount -lf {mnt}", check=False)

    # 2. Turn off all swap on the disk
    result = subprocess.run(f"lsblk -ln -o NAME,TYPE {disk}", shell=True, capture_output=True, text=True)
    for line in result.stdout.strip().split('\n'):
        parts = line.split()
        if len(parts) == 2 and parts[1] == 'part':
            partdev = f"/dev/{parts[0]}"
            # Check if swap
            with open('/proc/swaps', 'r') as f:
                if partdev in f.read():
                    print(f"{Style.WARNING}Turning off swap on {partdev}...{Style.ENDC}")
                    run_cmd(f"swapoff {partdev}", check=False)

    # 3. Close all LUKS/dm-crypt mappings for the disk
    result = subprocess.run("lsblk -ln -o NAME,TYPE", shell=True, capture_output=True, text=True)
    for line in result.stdout.strip().split('\n'):
        parts = line.split()
        if len(parts) == 2 and parts[1] == 'crypt':
            cryptdev = parts[0]
            print(f"{Style.WARNING}Closing LUKS mapping {cryptdev}...{Style.ENDC}")
            run_cmd(f"cryptsetup close {cryptdev}", check=False)

    # 4. Deactivate all LVM volume groups on the disk
    run_cmd("vgchange -an", check=False)

    # 5. Unmount all partitions of the disk (in case any are still mounted elsewhere)
    result = subprocess.run("lsblk -ln -o NAME,MOUNTPOINT", shell=True, capture_output=True, text=True)
    for line in result.stdout.strip().split('\n'):
        parts = line.split()
        if len(parts) == 2:
            partname, mnt = parts
            if mnt and partname.startswith(disk.replace('/dev/', '')):
                print(f"{Style.WARNING}Force unmounting /dev/{partname} from {mnt}...{Style.ENDC}")
                run_cmd(f"umount -lf /dev/{partname}", check=False)

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


def detect_vm():
    """Heuristic detection for common VM environments."""
    try:
        # Check for hypervisor flag in cpuinfo
        with open('/proc/cpuinfo', 'r') as f:
            cpuinfo = f.read().lower()
            if 'hypervisor' in cpuinfo:
                return True
    except Exception:
        pass

    # Check DMI strings
    dmi_paths = [
        '/sys/class/dmi/id/product_name',
        '/sys/class/dmi/id/sys_vendor',
        '/sys/class/dmi/id/board_vendor'
    ]
    vm_signatures = ['virtual', 'vmware', 'kvm', 'qemu', 'virtualbox', 'bochs', 'hyper-v', 'microsoft']
    for p in dmi_paths:
        try:
            if os.path.exists(p):
                with open(p, 'r') as f:
                    txt = f.read().lower()
                    for sig in vm_signatures:
                        if sig in txt:
                            return True
        except Exception:
            continue
    return False

def select_disk():
    print(f"\n{Style.HEADER}{Style.BOLD}Available disks:{Style.ENDC}")
    run_cmd("lsblk -d -o NAME,SIZE,MODEL")
    disk = input("Enter the disk to install Void Linux on (e.g., sda): ")
    return f"/dev/{disk}"

def auto_partition_disk(disk, uefi, use_swap, swap_size):
    print(f"\n{Style.WARNING}{Style.BOLD}Auto-partitioning {disk} (this will erase all data on the disk!){Style.ENDC}")
    print(f"\n{Style.WARNING}NOTE: If you are using LUKS encryption, it is recommended to create a separate /boot partition (ext4, 512M-1G) for GRUB to work reliably.\n{Style.ENDC}")
    if uefi:
        if use_swap:
            print(f"UEFI detected: Will create EFI (512M, type ef00), /boot (1G, ext4, type 8300), root (ext4, encrypted), and swap ({swap_size}) partitions.")
        else:
            print("UEFI detected: Will create EFI (512M, type ef00), /boot (1G, ext4, type 8300), and root (ext4, encrypted) partitions. No swap.")
    else:
        if use_swap:
            print(f"Legacy BIOS detected: Will create /boot (1G, ext4, type 8300), root (ext4, encrypted), and swap ({swap_size}) partitions.")
        else:
            print("Legacy BIOS detected: Will create /boot (1G, ext4, type 8300) and root (ext4, encrypted) partitions. No swap.")
    confirm = input("Type 'YES' to continue: ")
    if confirm != 'YES':
        print("Aborting.")
        sys.exit(0)
    unmount_disk_partitions(disk)
    run_cmd(f"wipefs -a {disk}")
    run_cmd(f"sgdisk -Z {disk}")
    if uefi:
        run_cmd(f"sgdisk -n 1:0:+512M -t 1:ef00 {disk}")  # EFI
        run_cmd(f"sgdisk -n 2:0:+1G -t 2:8300 {disk}")    # /boot
        if use_swap:
            run_cmd(f"sgdisk -n 3:0:+20G -t 3:8300 {disk}")    # root (encrypted)
            run_cmd(f"sgdisk -n 4:0:+{swap_size} -t 4:8200 {disk}")  # swap
        else:
            run_cmd(f"sgdisk -n 3:0:0 -t 3:8300 {disk}")    # root (rest of disk, encrypted)
    else:
        run_cmd(f"sgdisk -n 1:0:+1G -t 1:8300 {disk}")    # /boot
        if use_swap:
            run_cmd(f"sgdisk -n 2:0:+20G -t 2:8300 {disk}")    # root (encrypted)
            run_cmd(f"sgdisk -n 3:0:+{swap_size} -t 3:8200 {disk}")  # swap
        else:
            run_cmd(f"sgdisk -n 2:0:0 -t 2:8300 {disk}")    # root (rest of disk, encrypted)
    run_cmd(f"partprobe {disk}")
    print(f"{Style.OKGREEN}Partitions created:{Style.ENDC}")
    run_cmd(f"lsblk {disk}")

def format_auto_partitions(disk, uefi, use_swap, skip_root_format=False):
    if uefi:
        efi = f"{disk}1"
        boot = f"{disk}2"
        root = f"{disk}3"
        run_cmd(f"mkfs.vfat -F32 {efi}")
        run_cmd(f"mkfs.ext4 {boot}")
        run_cmd(f"mount {root} /mnt")
        run_cmd(f"mkdir -p /mnt/boot")
        run_cmd(f"mount {boot} /mnt/boot")
        run_cmd(f"mkdir -p /mnt/boot/efi")
        run_cmd(f"mount {efi} /mnt/boot/efi")
        if use_swap:
            swap = f"{disk}4"
            run_cmd(f"mkswap {swap}")
            run_cmd(f"swapon {swap}")
        return root
    else:
        boot = f"{disk}1"
        root = f"{disk}2"
        run_cmd(f"mkfs.ext4 {boot}")
        run_cmd(f"mount {root} /mnt")
        run_cmd(f"mkdir -p /mnt/boot")
        run_cmd(f"mount {boot} /mnt/boot")
        if use_swap:
            swap = f"{disk}3"
            run_cmd(f"mkswap {swap}")
            run_cmd(f"swapon {swap}")
        return root

def manual_partition_disk(disk):
    print(f"\n{Style.WARNING}{Style.BOLD}Manual partitioning for {disk}.{Style.ENDC}")
    print(f"{Style.OKCYAN}You will be dropped into cfdisk.\nIf you are using LUKS encryption, it is recommended to create a separate /boot partition (ext4, 512M-1G) for GRUB to work reliably.\nCreate partitions as needed (root, swap, home, EFI, etc.).{Style.ENDC}")
    input("Press Enter to continue...")
    run_cmd(f"cfdisk {disk}")

def format_and_mount_manual():
    print(f"\n{Style.HEADER}{Style.BOLD}List partitions:{Style.ENDC}")
    run_cmd("lsblk -o NAME,SIZE,TYPE,MOUNTPOINT")


    # Accept luks_root_ready and root_part as arguments to avoid duplicate prompts
    import inspect
    frame = inspect.currentframe()
    luks_root_ready = False
    root_part = None
    if frame is not None and frame.f_back is not None:
        luks_root_ready = frame.f_back.f_locals.get('luks_root_ready', False)
        root_part = frame.f_back.f_locals.get('root_for_crypt', None)
    if luks_root_ready and root_part:
        # Ask if filesystem exists, offer to create if not
        fs_check = subprocess.run(f"blkid -o value -s TYPE {root_part}", shell=True, capture_output=True, text=True)
        if fs_check.returncode != 0 or not fs_check.stdout.strip():
            print(f"{Style.WARNING}No filesystem detected on {root_part}.{Style.ENDC}")
            if input(f"Do you want to create an ext4 filesystem on {root_part}? [y/N]: ").strip().lower() == 'y':
                run_cmd(f"mkfs.ext4 {root_part}")
        run_cmd(f"mount {root_part} /mnt")
    else:
        # Ask for root partition first (required)
        root_part = input("Enter the device for the root partition (e.g., /dev/sda2): ").strip()
        root_fstype = input("Filesystem type for root (e.g., ext4): ").strip()
        run_cmd(f"umount -lf {root_part}", check=False)
        run_cmd(f"mkfs.{root_fstype} {root_part}")
        run_cmd(f"mount {root_part} /mnt")

    # Ask for EFI partition if UEFI
    uefi = detect_uefi()
    efi_part = None
    if uefi:
        efi_part = input("Enter the device for the EFI partition (e.g., /dev/sda1, leave blank if not needed): ").strip()
        if efi_part:
            run_cmd(f"umount -lf {efi_part}", check=False)
            run_cmd(f"mkfs.vfat -F32 {efi_part}")
            run_cmd(f"mkdir -p /mnt/boot/efi")
            run_cmd(f"mount {efi_part} /mnt/boot/efi")

    # Ask for /boot partition if LUKS or user wants it
    luks = False
    luks_choice = input("Did you set up LUKS encryption for root? [y/N]: ").strip().lower()
    if luks_choice == "y":
        luks = True
    boot_part = None
    if luks or input("Do you have a separate /boot partition? [y/N]: ").strip().lower() == "y":
        boot_part = input("Enter the device for the /boot partition (e.g., /dev/sda3): ").strip()
        boot_fstype = input("Filesystem type for /boot (e.g., ext4): ").strip()
        run_cmd(f"umount -lf {boot_part}", check=False)
        run_cmd(f"mkfs.{boot_fstype} {boot_part}")
        run_cmd(f"mkdir -p /mnt/boot")
        run_cmd(f"mount {boot_part} /mnt/boot")

    # Ask for swap partition
    swap_part = input("Enter the device for the swap partition (leave blank if none): ").strip()
    if swap_part:
        run_cmd(f"swapoff {swap_part}", check=False)
        run_cmd(f"mkswap {swap_part}")
        run_cmd(f"swapon {swap_part}")

    # Ask for any additional partitions (e.g., /home)
    while True:
        part = input("Enter another partition device (blank to finish): ").strip()
        if not part:
            break
        mnt = input("Mount point (e.g., /home): ").strip()
        fstype = input("Filesystem type (ext4, xfs, etc.): ").strip()
        run_cmd(f"umount -lf {part}", check=False)
        run_cmd(f"mkfs.{fstype} {part}")
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
    print(f"\n{Style.OKCYAN}Installing base system...{Style.ENDC}")
    
    # Install base system first
    run_cmd(f"xbps-install -Sy -y -R {VOID_MIRROR} -r /mnt {BASE_PKGS}")

def install_hardware_packages():
    """Install hardware-specific packages after base system is installed."""
    print(f"\n{Style.OKCYAN}Installing hardware-specific packages...{Style.ENDC}")
    
    # Detect hardware and get required packages
    hardware_pkgs = detect_hardware()
    
    if hardware_pkgs:
        print(f"{Style.OKCYAN}Installing hardware packages: {' '.join(hardware_pkgs)}{Style.ENDC}")
        
        # Install hardware packages to target system
        hardware_pkgs_str = " ".join(hardware_pkgs)
        run_cmd(f"xbps-install -Sy -y -R {VOID_MIRROR} -r /mnt {hardware_pkgs_str}")
        
        # Enable hardware-specific services using runit
        if "NetworkManager" in hardware_pkgs:
            run_cmd("ln -sf /etc/sv/NetworkManager /mnt/var/service", check=False)
            print(f"{Style.OKGREEN}NetworkManager service enabled.{Style.ENDC}")

        if "bluez" in hardware_pkgs:
            run_cmd("ln -sf /etc/sv/bluetoothd /mnt/var/service", check=False)
            print(f"{Style.OKGREEN}Bluetooth service enabled.{Style.ENDC}")

        # Handle NVIDIA-specific setup
        if "nvidia" in hardware_pkgs:
            print(f"{Style.WARNING}NVIDIA drivers installed. Blacklisting nouveau driver.{Style.ENDC}")
            run_cmd("mkdir -p /mnt/etc/modprobe.d", check=False)
            run_cmd("echo 'blacklist nouveau' > /mnt/etc/modprobe.d/nvidia.conf", check=False)
    else:
        print(f"{Style.OKGREEN}No additional hardware packages needed.{Style.ENDC}")

def create_user():
    print(f"\n{Style.HEADER}{Style.BOLD}User creation:{Style.ENDC}")
    username = input("Enter username: ")
    while True:
        password = getpass.getpass("Enter password: ")
        password_confirm = getpass.getpass("Confirm password: ")
        if password == password_confirm:
            break
        else:
            print(f"{Style.FAIL}Passwords do not match. Please try again.{Style.ENDC}")
    mount_chroot_dirs()
    # Check if user exists in chroot, and remove if so
    user_exists = subprocess.run(f"chroot /mnt id -u {username}", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if user_exists.returncode == 0:
        print(f"{Style.WARNING}User {username} already exists. Removing...{Style.ENDC}")
        run_cmd(f"userdel -r {username}", chroot=True)
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
    sound_pkgs = "alsa-utils pipewire wireplumber sof-firmware"
    
    if pkgs:
        print(f"{Style.OKCYAN}Installing {de_key} and sound packages...{Style.ENDC}")
        run_cmd(f"xbps-install -Sy -y -R {VOID_MIRROR} -r /mnt {pkgs} {sound_pkgs}")
        # Enable display manager using runit
        if de_key == "xfce":
            run_cmd("ln -sf /etc/sv/lightdm /mnt/var/service", check=False)
        elif de_key == "gnome":
            run_cmd("ln -sf /etc/sv/gdm /mnt/var/service", check=False)
        elif de_key == "kde":
            run_cmd("ln -sf /etc/sv/sddm /mnt/var/service", check=False)
            # SDDM setup: ensure sddm.conf exists
            run_cmd("chroot /mnt mkdir -p /etc/sddm.conf.d", check=False)
            run_cmd('chroot /mnt bash -c "echo -e \'[Autologin]\\nUser=\\nSession=plasma.desktop\' > /etc/sddm.conf.d/autologin.conf"', check=False)
    else:
        print(f"{Style.WARNING}No desktop environment will be installed. Installing sound packages only...{Style.ENDC}")
        run_cmd(f"xbps-install -Sy -y -R {VOID_MIRROR} -r /mnt {sound_pkgs}")

    # Enable sound services using runit
    run_cmd("ln -sf /etc/sv/dbus /mnt/var/service", check=False)
    run_cmd("ln -sf /etc/sv/pipewire /mnt/var/service", check=False)
    print(f"{Style.OKGREEN}Desktop and sound setup complete.{Style.ENDC}")

def verify_hardware_installation():
    """Verify that hardware packages were installed correctly."""
    print(f"\n{Style.HEADER}{Style.BOLD}Verifying hardware package installation...{Style.ENDC}")
    
    # Check for intel-ucode
    result = subprocess.run("xbps-query -r /mnt intel-ucode", shell=True, capture_output=True, text=True)
    if result.returncode == 0:
        print(f"{Style.OKGREEN}✓ Intel microcode installed successfully{Style.ENDC}")
    else:
        print(f"{Style.WARNING}✗ Intel microcode not found{Style.ENDC}")
    
    # Check for AMD microcode
    result = subprocess.run("xbps-query -r /mnt linux-firmware-amd", shell=True, capture_output=True, text=True)
    if result.returncode == 0:
        print(f"{Style.OKGREEN}✓ AMD microcode installed successfully{Style.ENDC}")
    
    # Check for NVIDIA drivers
    result = subprocess.run("xbps-query -r /mnt nvidia", shell=True, capture_output=True, text=True)
    if result.returncode == 0:
        print(f"{Style.OKGREEN}✓ NVIDIA drivers installed successfully{Style.ENDC}")
    
    # Check if microcode files exist
    if os.path.exists("/mnt/lib/firmware/intel-ucode"):
        print(f"{Style.OKGREEN}✓ Intel microcode firmware files present{Style.ENDC}")
    
    if os.path.exists("/mnt/lib/firmware/amd-ucode"):
        print(f"{Style.OKGREEN}✓ AMD microcode firmware files present{Style.ENDC}")

def install_bootloader(disk):
    print("\nInstalling GRUB bootloader...")
    uefi = detect_uefi()
    mount_chroot_dirs()

    if uefi:
        # UEFI: install grub-x86_64-efi and efibootmgr
        run_cmd(f"xbps-install -Sy -y -R {VOID_MIRROR} -r /mnt grub-x86_64-efi efibootmgr", check=False)

        # Check if /mnt/boot/efi is a mount point
        if not os.path.ismount("/mnt/boot/efi"):
            print(f"{Style.FAIL}/mnt/boot/efi is NOT a mount point!{Style.ENDC}")
            print(f"{Style.WARNING}You MUST mount your EFI partition at /mnt/boot/efi before installing GRUB!{Style.ENDC}")
            efi_part = input("Enter EFI partition to mount at /mnt/boot/efi (e.g., /dev/sda1): ").strip()
            if efi_part:
                run_cmd(f"mkdir -p /mnt/boot/efi")
                run_cmd(f"mount {efi_part} /mnt/boot/efi")
            else:
                print(f"{Style.FAIL}EFI partition is required for UEFI boot. Aborting GRUB install.{Style.ENDC}")
                umount_chroot_dirs()
                return
        else:
            print(f"{Style.OKGREEN}/mnt/boot/efi is already a mount point.{Style.ENDC}")

        # Double-check filesystem type
        blkid_out = subprocess.run("lsblk -no FSTYPE /mnt/boot/efi", shell=True, capture_output=True, text=True)
        if "vfat" not in blkid_out.stdout:
            print(f"{Style.FAIL}/mnt/boot/efi is not FAT32!{Style.ENDC}")
            print(f"{Style.WARNING}EFI partition must be FAT32 (vfat). Aborting GRUB install.{Style.ENDC}")
            umount_chroot_dirs()
            return

        # Double-check inside chroot: /boot/efi must be a mount point
        result = subprocess.run("chroot /mnt mountpoint -q /boot/efi", shell=True)
        if result.returncode != 0:
            print(f"{Style.FAIL}/boot/efi is NOT a mount point inside chroot! Aborting GRUB install.{Style.ENDC}")
            umount_chroot_dirs()
            return

        # Check whether efivars are available inside chroot; if not, skip efibootmgr
        efivars_available = (subprocess.run("chroot /mnt test -d /sys/firmware/efi/efivars", shell=True).returncode == 0)
        if not efivars_available and not os.path.exists("/sys/firmware/efi/efivars"):
            print(f"{Style.WARNING}EFI variables are not available on the host or inside chroot. Installing GRUB in removable mode (--removable).{Style.ENDC}")
            run_cmd(f"chroot /mnt grub-install --target=x86_64-efi --efi-directory=/boot/efi --removable --recheck")
            print(f"{Style.OKGREEN}GRUB installed in removable media mode (should work even without EFI variables).{Style.ENDC}")
        else:
            # Try to install GRUB with efibootmgr first (don't let run_cmd auto-exit — use subprocess)
            print(f"{Style.OKCYAN}Attempting GRUB installation with efibootmgr...{Style.ENDC}")
            result = subprocess.run(f"chroot /mnt grub-install --target=x86_64-efi --efi-directory=/boot/efi --bootloader-id=Void --recheck", shell=True)

            if result.returncode != 0:
                print(f"{Style.WARNING}efibootmgr failed (EFI variables not writable). Trying fallback installation...{Style.ENDC}")
                # Fallback: install without efibootmgr (removable media path)
                run_cmd(f"chroot /mnt grub-install --target=x86_64-efi --efi-directory=/boot/efi --removable --recheck")
                print(f"{Style.OKGREEN}GRUB installed in removable media mode (should work even without EFI variables).{Style.ENDC}")
            else:
                print(f"{Style.OKGREEN}GRUB installed successfully with efibootmgr.{Style.ENDC}")

                # Print efibootmgr output for user to verify boot entries
                print(f"{Style.OKCYAN}efibootmgr output (inside chroot):{Style.ENDC}")
                subprocess.run("chroot /mnt efibootmgr -v", shell=True)
    else:
        # Legacy BIOS: install grub
        run_cmd(f"xbps-install -Sy -y -R {VOID_MIRROR} -r /mnt grub")
        run_cmd(f"chroot /mnt grub-install --target=i386-pc {disk}")

    # Generate GRUB configuration
    run_cmd(f"chroot /mnt grub-mkconfig -o /boot/grub/grub.cfg")
    print(f"{Style.OKGREEN}GRUB installation and configuration complete.{Style.ENDC}")
    print(f"{Style.WARNING}After installation, make sure to set your firmware/BIOS/UEFI boot order to boot from the installed disk, and remove the installation media (CD/DVD/USB) before rebooting!{Style.ENDC}")
    umount_chroot_dirs()

# --- Advanced chroot configuration and bootloader install ---
def chroot_and_configure():
    print("\nEntering chroot configuration...")
    run_cmd("cp /etc/resolv.conf /mnt/etc/resolv.conf")
    run_cmd("chroot /mnt passwd")
    tz = input("Enter timezone (e.g., Europe/London): ")
    run_cmd(f"chroot /mnt ln -sf /usr/share/zoneinfo/{tz} /etc/localtime")
    run_cmd("chroot /mnt hwclock --systohc")
    locale = input("Enter locale (e.g., en_US.UTF-8): ")
    run_cmd(f"chroot /mnt sed -i 's/^#\\s*{locale}/{locale}/' /etc/default/libc-locales")
    run_cmd(f"chroot /mnt xbps-reconfigure -f glibc-locales")
    hostname = input("Enter hostname: ")
    run_cmd(f"echo '{hostname}' > /mnt/etc/hostname")
    username = input("Enter username to create: ")
    run_cmd(f"chroot /mnt useradd -m -G wheel,audio,video -s /bin/bash {username}")
    run_cmd(f"chroot /mnt passwd {username}")
    run_cmd(f"chroot /mnt xbps-install -Sy sudo NetworkManager")
    run_cmd(f"chroot /mnt ln -sf /etc/sv/NetworkManager /var/service")
    run_cmd(f"chroot /mnt ln -sf /etc/sv/dbus /var/service")

def install_bootloader_modular(disk, uefi):
    # Note: caller may pass force_removable and vm_detect to control behavior
    # Signature will be updated by caller.
    if uefi:
        run_cmd(f"chroot /mnt xbps-install -Sy grub-x86_64-efi efibootmgr", check=False)
        # Decide whether to use removable mode automatically
        use_removable = globals().get('FORCE_REMOVABLE', False) or globals().get('VM_DETECTED', False)

        # Ensure /mnt/boot/efi exists
        if not os.path.ismount('/mnt/boot/efi'):
            print(f"{Style.WARNING}/mnt/boot/efi is not mounted. GRUB will attempt removable install if forced or VM detected.{Style.ENDC}")
            # If we're forcing removable or VM, continue; otherwise ask user
            if not use_removable:
                efi_part = input("Enter EFI partition to mount at /mnt/boot/efi (e.g., /dev/sda1) or leave blank to force removable install: ").strip()
                if efi_part:
                    run_cmd("mkdir -p /mnt/boot/efi", check=False)
                    run_cmd(f"mount {efi_part} /mnt/boot/efi", check=True)
                else:
                    use_removable = True

        if use_removable:
            print(f"{Style.OKCYAN}Installing GRUB in removable mode (--removable).{Style.ENDC}")
            run_cmd(f"chroot /mnt grub-install --target=x86_64-efi --efi-directory=/boot/efi --removable --recheck", check=False)
            run_cmd(f"chroot /mnt grub-mkconfig -o /boot/grub/grub.cfg", check=False)
            print(f"{Style.OKGREEN}GRUB installed in removable mode.{Style.ENDC}")
            return
    else:
        run_cmd(f"chroot /mnt xbps-install -Sy grub")
        run_cmd(f"chroot /mnt grub-install --target=i386-pc {disk}")
    run_cmd(f"chroot /mnt grub-mkconfig -o /boot/grub/grub.cfg", check=False)
    print("Bootloader installation complete. Remove install media and reboot.")

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
    # Parse CLI args for force-removable option
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--force-removable', action='store_true', help='Force GRUB --removable installation (no efibootmgr)')
    args, _ = parser.parse_known_args()

    # Set globals used by install_bootloader_modular
    global FORCE_REMOVABLE, VM_DETECTED
    FORCE_REMOVABLE = bool(args.force_removable)
    VM_DETECTED = detect_vm()
    if VM_DETECTED:
        print(f"{Style.WARNING}Virtual machine detected - installer will prefer removable GRUB installation when appropriate.{Style.ENDC}")
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
    # luks = False
    # lvm = False
    # luks_name = "cryptroot"
    # root_for_crypt = None

    # Prompt for LUKS and LVM before partitioning
    # luks_choice = input("Encrypt root partition with LUKS? [y/N]: ").strip().lower()
    # if luks_choice == "y":
    #     luks = True
    #     lvm_choice = input("Use LVM inside LUKS? [y/N]: ").strip().lower()
    #     if lvm_choice == "y":
    #         lvm = True

    if mode == "a":
        swap_choice = input("Create a swap partition? [y/N]: ").strip().lower()
        if swap_choice == "y":
            use_swap = True
            swap_size = input("Enter swap size (e.g., 2G, 512M): ").strip()

        # Partitioning logic: always create partitions, but only wipe/format as needed
        print(f"\n{Style.WARNING}{Style.BOLD}Auto-partitioning {disk} (this will erase all data on the disk!){Style.ENDC}")
        unmount_disk_partitions(disk)
        run_cmd(f"wipefs -a {disk}")
        run_cmd(f"sgdisk -Z {disk}")
        # Partition creation
        if uefi:
            run_cmd(f"sgdisk -n 1:0:+512M -t 1:ef00 {disk}")  # EFI
            run_cmd(f"sgdisk -n 2:0:+1G -t 2:8300 {disk}")    # /boot
            if use_swap:
                run_cmd(f"sgdisk -n 3:0:+20G -t 3:8300 {disk}")    # root
                run_cmd(f"sgdisk -n 4:0:+{swap_size} -t 4:8200 {disk}")  # swap
            else:
                run_cmd(f"sgdisk -n 3:0:0 -t 3:8300 {disk}")    # root (rest of disk)
        else:
            run_cmd(f"sgdisk -n 1:0:+1G -t 1:8300 {disk}")    # /boot
            if use_swap:
                run_cmd(f"sgdisk -n 2:0:+20G -t 2:8300 {disk}")    # root
                run_cmd(f"sgdisk -n 3:0:+{swap_size} -t 3:8200 {disk}")  # swap
            else:
                run_cmd(f"sgdisk -n 2:0:0 -t 2:8300 {disk}")    # root (rest of disk)
        run_cmd(f"partprobe {disk}")
        print(f"{Style.OKGREEN}Partitions created:{Style.ENDC}")
        run_cmd(f"lsblk {disk}")

        # Assign partition variables
        efi_part = None
        if uefi:
            efi_part = f"{disk}1"
            boot_part = f"{disk}2"
            root_part = f"{disk}3"
            swap_part = f"{disk}4" if use_swap else None
        else:
            boot_part = f"{disk}1"
            root_part = f"{disk}2"
            swap_part = f"{disk}3" if use_swap else None

        # Format and mount all partitions (no encryption)
        if uefi:
            run_cmd(f"mkfs.vfat -F32 {efi_part}")
            run_cmd(f"mkfs.ext4 {root_part}")
            run_cmd(f"mount {root_part} /mnt")
            run_cmd(f"mkdir -p /mnt/boot")
            run_cmd(f"mount {boot_part} /mnt/boot")
            run_cmd(f"mkdir -p /mnt/boot/efi")
            run_cmd(f"mount {efi_part} /mnt/boot/efi")
            if use_swap and swap_part:
                run_cmd(f"mkswap {swap_part}")
                run_cmd(f"swapon {swap_part}")
        else:
            run_cmd(f"mkfs.ext4 {boot_part}")
            run_cmd(f"mkfs.ext4 {root_part}")
            run_cmd(f"mount {root_part} /mnt")
            run_cmd(f"mkdir -p /mnt/boot")
            run_cmd(f"mount {boot_part} /mnt/boot")
            if use_swap and swap_part:
                run_cmd(f"mkswap {swap_part}")
                run_cmd(f"swapon {swap_part}")
    else:
        manual_partition_disk(disk)
        format_and_mount_manual()

    # Mount chroot dirs before any installation
    # Mount chroot dirs before any installation
    mount_chroot_dirs()

    install_base()
    setup_mirrors()
    install_hardware_packages()
    verify_hardware_installation()
    chroot_and_configure()
    install_desktop_and_sound()
    install_bootloader_modular(disk, uefi)
    print(f"\n{Style.OKGREEN}{Style.BOLD}Installation steps complete! System is ready to reboot.{Style.ENDC}")

if __name__ == "__main__":
    main()
