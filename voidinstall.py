#!/usr/bin/env python3
import shlex
import argparse
import subprocess
import sys
import getpass
import os
import shutil
import platform # --- ADDED ---

# --- Configuration ---
# --- MODIFIED ---: Base mirror URL, architecture will be appended.
VOID_MIRROR_BASE = "https://repo-default.voidlinux.org/current"
BASE_PKGS = "base-system xorg NetworkManager elogind"
DESKTOP_ENVIRONMENTS = {
    "xfce": "xfce4 xfce4-terminal lightdm lightdm-gtk3-greeter gvfs thunar-volman thunar-archive-plugin xfce4-pulseaudio-plugin network-manager-applet",
    "gnome": "gnome gdm gnome-tweaks gnome-software gvfs network-manager-applet network-manager gnome-shell gnome-terminal",
    "kde": "kde5 sddm konsole plasma-workspace plasma-desktop kdeplasma-addons kde-cli-tools kde-gtk-config kdeconnect dolphin konsole ark sddm-kcm gvfs network-manager-applet",
    "none": ""
}
# --- Global variable for architecture --- ADDED ---
ARCH = ""

# --- ANSI Color/Style Codes ---
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

# --- Core Functions ---
def run_cmd(cmd, check=True, chroot=False):
    """Executes a command in the shell, optionally within a chroot."""
    if chroot:
        # Sanitize command for chroot execution
        cmd_sanitized = cmd.replace("'", "'\\''")
        cmd = f"chroot /mnt /bin/bash -c '{cmd_sanitized}'"
        
    print(f"{Style.OKBLUE}[RUNNING]{Style.ENDC} {cmd}")
    result = subprocess.run(cmd, shell=True, text=True)

    if result.returncode != 0:
        print(f"{Style.FAIL}[ERROR] Command failed with exit code {result.returncode}: {cmd}{Style.ENDC}")
        if check:
            print(f"{Style.WARNING}Exiting due to critical error.{Style.ENDC}")
            sys.exit(1)
        else:
            print(f"{Style.WARNING}Continuing despite error (check=False).{Style.ENDC}")

def check_dependencies():
    """Checks for required commands and installs missing packages."""
    print(f"{Style.HEADER}{Style.BOLD}Checking dependencies...{Style.ENDC}")
    missing_deps = []
    command_checks = {
        'lsblk': 'util-linux', 'sgdisk': 'gptfdisk', 'partprobe': 'parted',
        'mkfs.ext4': 'e2fsprogs', 'mkfs.vfat': 'dosfstools', 'xbps-install': 'xbps',
        'mount': 'util-linux', 'wipefs': 'util-linux', 'lspci': 'pciutils',
        'lsusb': 'usbutils', 'cryptsetup': 'cryptsetup'
    }
    
    for cmd, package in command_checks.items():
        if not shutil.which(cmd) and package not in missing_deps:
            missing_deps.append(package)
            print(f"{Style.WARNING}Missing command: {cmd} (from package: {package}){Style.ENDC}")
    
    if missing_deps:
        print(f"\n{Style.FAIL}Missing dependencies: {' '.join(missing_deps)}{Style.ENDC}")
        print(f"{Style.OKCYAN}Attempting to install...{Style.ENDC}")
        try:
            run_cmd("xbps-install -S", check=False)
            run_cmd(f"xbps-install -y {' '.join(missing_deps)}")
            print(f"{Style.OKGREEN}Successfully installed missing dependencies.{Style.ENDC}")
        except Exception as e:
            print(f"{Style.FAIL}Failed to install dependencies: {e}{Style.ENDC}")
            sys.exit(1)
    else:
        print(f"{Style.OKGREEN}All required dependencies are present.{Style.ENDC}")

def unmount_all(disk):
    """Force unmounts all partitions on a specified disk."""
    print(f"{Style.WARNING}Attempting to unmount all partitions on {disk}...{Style.ENDC}")
    
    # Unmount everything under /mnt first, deepest paths first
    result = subprocess.run("mount | grep '^/dev/' | grep '/mnt' | awk '{print $3}'", shell=True, capture_output=True, text=True)
    mount_points = sorted([line for line in result.stdout.strip().split('\n') if line], key=len, reverse=True)
    for mp in mount_points:
        run_cmd(f"umount -lf {mp}", check=False)

    # Turn off any swap partitions on the target disk
    result = subprocess.run(f"blkid -t TYPE=swap -o device {disk}*", shell=True, capture_output=True, text=True)
    for swap_dev in result.stdout.strip().split('\n'):
        if swap_dev:
            run_cmd(f"swapoff {swap_dev}", check=False)

    run_cmd(f"umount -R /mnt", check=False)

def mount_chroot_dirs():
    """Mounts virtual filesystems needed for chroot."""
    print(f"{Style.OKCYAN}Mounting virtual filesystems for chroot...{Style.ENDC}")
    run_cmd("mount --bind /dev /mnt/dev")
    run_cmd("mount --bind /dev/pts /mnt/dev/pts")
    run_cmd("mount -t proc proc /mnt/proc")
    run_cmd("mount -t sysfs sysfs /mnt/sys")
    if os.path.exists("/sys/firmware/efi"):
        run_cmd("mount --bind /sys/firmware/efi /mnt/sys/firmware/efi", check=False)

def umount_chroot_dirs():
    """Unmounts virtual filesystems."""
    print(f"{Style.OKCYAN}Unmounting virtual filesystems...{Style.ENDC}")
    run_cmd("umount -R /mnt/dev", check=False)
    run_cmd("umount -R /mnt/proc", check=False)
    run_cmd("umount -R /mnt/sys", check=False)

# --- Detection Functions ---
def detect_uefi():
    """Checks if the system is booted in UEFI mode."""
    return os.path.exists('/sys/firmware/efi')

def detect_vm():
    """Detects if the script is running in a virtual machine."""
    try:
        with open('/proc/cpuinfo', 'r') as f:
            if 'hypervisor' in f.read().lower():
                return True
    except Exception: pass
    
    dmi_vendors = ['qemu', 'virtualbox', 'vmware', 'bochs', 'hyper-v', 'microsoft']
    try:
        sys_vendor = subprocess.run("cat /sys/class/dmi/id/sys_vendor", shell=True, capture_output=True, text=True).stdout.lower()
        for vendor in dmi_vendors:
            if vendor in sys_vendor:
                return True
    except Exception: pass
    return False

# --- ADDED ---: Detect machine architecture
def detect_arch():
    """Detects the system's architecture."""
    # Use platform.machine() for a standard way to get arch
    arch = platform.machine()
    if arch == "x86_64":
        return "x86_64"
    elif arch == "aarch64":
        return "aarch64"
    elif "arm" in arch:
        return "armv7l" # Default to armv7l for 32-bit arm
    else:
        print(f"{Style.FAIL}Unsupported architecture: {arch}. Exiting.{Style.ENDC}")
        sys.exit(1)

# --- Installation Steps ---
def select_disk():
    """Prompts the user to select an installation disk."""
    print(f"\n{Style.HEADER}{Style.BOLD}Available disks:{Style.ENDC}")
    run_cmd("lsblk -d -o NAME,SIZE,MODEL")
    disk = input("Enter the disk to install on (e.g., sda, nvme0n1): ").strip()
    return f"/dev/{disk}"


# Helper to build partition device names correctly (handles nvme/mmcblk/loop)
def part_path(disk, partnum):
    """
    Return partition device path for a given disk and partition number.
    Examples:
      /dev/sda  -> /dev/sda1
      /dev/nvme0n1 -> /dev/nvme0n1p1
      /dev/mmcblk0 -> /dev/mmcblk0p1
      /dev/loop0 -> /dev/loop0p1
    """
    name = os.path.basename(disk)
    # If device name ends with a digit (nvme0n1, mmcblk0, loop0), use 'p' before partition number
    if name and name[-1].isdigit():
        return f"{disk}p{partnum}"
    return f"{disk}{partnum}"

def manual_partition_and_mount(disk):
    """Guides user through manual partitioning and mounting."""
    print(f"\n{Style.WARNING}{Style.BOLD}Manual Partitioning Mode{Style.ENDC}")
    print("You will now be placed in `cfdisk`. Please create your desired partitions.")
    print("A typical setup includes: an EFI partition (if UEFI), a root partition, and optionally swap and home.")
    input("Press Enter to launch cfdisk...")
    run_cmd(f"cfdisk {disk}")
    
    print(f"\n{Style.HEADER}{Style.BOLD}Available partitions on {disk}:{Style.ENDC}")
    run_cmd(f"lsblk {disk}")

    root_part = input("Enter device for root (/) (e.g., /dev/sda2): ").strip()
    root_fs = input("Enter filesystem for root (e.g., ext4): ").strip()
    run_cmd(f"mkfs.{root_fs} {root_part}")
    run_cmd(f"mount {root_part} /mnt")

    if detect_uefi():
        efi_part = input("Enter device for EFI partition (e.g., /dev/sda1): ").strip()
        run_cmd(f"mkfs.vfat -F32 {efi_part}")
        run_cmd("mkdir -p /mnt/boot/efi")
        run_cmd(f"mount {efi_part} /mnt/boot/efi")

    if input("Do you have a separate /boot partition? [y/N]: ").lower() == 'y':
        boot_part = input("Enter device for /boot (e.g., /dev/sda3): ").strip()
        boot_fs = input("Enter filesystem for /boot (e.g., ext4): ").strip()
        run_cmd(f"mkfs.{boot_fs} {boot_part}")
        if not os.path.exists("/mnt/boot"): run_cmd("mkdir -p /mnt/boot")
        run_cmd(f"mount {boot_part} /mnt/boot")
    
    if input("Do you have a swap partition? [y/N]: ").lower() == 'y':
        swap_part = input("Enter device for swap (e.g., /dev/sda4): ").strip()
        run_cmd(f"mkswap {swap_part}")
        run_cmd(f"swapon {swap_part}")

# --- MODIFIED ---: Function now uses global ARCH variable
def setup_repos():
    """Sets up main and non-free repositories on the target system."""
    global ARCH
    print(f"{Style.OKCYAN}Setting up XBPS repositories for {ARCH}...{Style.ENDC}")
    run_cmd("mkdir -p /mnt/etc/xbps.d")
    
    repo_url = f"{VOID_MIRROR_BASE}/{ARCH}" if ARCH != "x86_64" else VOID_MIRROR_BASE
    
    with open("/mnt/etc/xbps.d/00-repository-main.conf", "w") as f:
        f.write(f"repository={repo_url}\n")
    with open("/mnt/etc/xbps.d/10-repository-nonfree.conf", "w") as f:
        f.write(f"repository={repo_url}/nonfree\n")
    
    # Multilib is only for x86_64
    if ARCH == "x86_64":
        with open("/mnt/etc/xbps.d/20-repository-multilib.conf", "w") as f:
            f.write(f"repository={repo_url}/multilib\n")

# --- MODIFIED ---: Function now uses global ARCH variable for repo path
def install_base_system():
    """Installs the Void Linux base system."""
    global ARCH
    repo_url = f"{VOID_MIRROR_BASE}/{ARCH}" if ARCH != "x86_64" else VOID_MIRROR_BASE
    print(f"\n{Style.HEADER}{Style.BOLD}Installing base system from {repo_url}...{Style.ENDC}")
    run_cmd(f"xbps-install -Sy -R {repo_url} -r /mnt {BASE_PKGS}")

def install_desktop_and_sound():
    """Installs a desktop environment and sound packages."""
    print(f"\n{Style.HEADER}{Style.BOLD}Desktop Environment Selection:{Style.ENDC}")
    for i, de in enumerate(DESKTOP_ENVIRONMENTS.keys()):
        print(f"  {i+1}. {de}")
    choice_str = input("Select a desktop [number, default 'none']: ").strip()
    
    try:
        choice_idx = int(choice_str) - 1
        de_key = list(DESKTOP_ENVIRONMENTS.keys())[choice_idx]
    except (ValueError, IndexError):
        de_key = "none"

    de_pkgs = DESKTOP_ENVIRONMENTS[de_key]
    sound_pkgs = "alsa-utils pipewire wireplumber sof-firmware alsa-pipewire"
    
    if de_pkgs:
        print(f"{Style.OKCYAN}Installing {de_key} desktop and sound packages...{Style.ENDC}")
        run_cmd(f"xbps-install -Sy -r /mnt {de_pkgs} {sound_pkgs}")
    else:
        print(f"{Style.OKCYAN}Installing sound packages only...{Style.ENDC}")
        run_cmd(f"xbps-install -Sy -r /mnt {sound_pkgs}")


def detect_and_install_graphics(is_vm=False):
    """Detect graphics hardware and install appropriate drivers into the target (/mnt).
    Skips heavy/proprietary installs when running inside virtual machines unless forced.
    """
    print(f"\n{Style.HEADER}{Style.BOLD}Detecting graphics hardware...{Style.ENDC}")

    try:
        result = subprocess.run("lspci -nnk | grep -iE 'vga|3d|display' -A2", shell=True, capture_output=True, text=True)
        out = result.stdout.lower()
    except Exception as e:
        print(f"{Style.WARNING}Could not run lspci: {e}. Skipping graphics autodetection.{Style.ENDC}")
        return

    found = set()
    if 'nvidia' in out:
        found.add('nvidia')
    if 'radeon' in out or 'amd' in out or 'advanced micro devices' in out:
        found.add('amd')
    if 'intel' in out and 'intel corporation' in out or 'intel' in out:
        # catch many intel strings
        found.add('intel')

    if not found:
        print(f"{Style.OKGREEN}No discrete graphics detected or only virtual graphics present.{Style.ENDC}")
        return

    print(f"{Style.OKCYAN}Detected graphics adapters: {', '.join(found)}{Style.ENDC}")

    # For bare metal installs only: install vendor drivers into /mnt
    if is_vm:
        print(f"{Style.WARNING}Running in a VM - skipping proprietary or host-specific graphics driver installation by default.{Style.ENDC}")
        print(f"If you want drivers installed anyway, re-run with --force-removable or install manually inside the target after first boot.{Style.ENDC}")
        return

    pkgs = []
    # NVIDIA
    if 'nvidia' in found:
        print(f"{Style.OKCYAN}Preparing to install NVIDIA drivers (proprietary).{Style.ENDC}")
        # Recommend non-free repository, but attempt install anyway
        pkgs.extend(["nvidia"])

    # AMD
    if 'amd' in found:
        print(f"{Style.OKCYAN}Preparing to install AMD/Mesa drivers.{Style.ENDC}")
        pkgs.extend(["mesa-dri", "mesa-vulkan-radeon", "mesa-vaapi", "mesa-vdpau"])

    # Intel
    if 'intel' in found:
        print(f"{Style.OKCYAN}Preparing to install Intel Mesa drivers.{Style.ENDC}")
        pkgs.extend(["mesa-dri", "mesa-vulkan-intel", "intel-media-driver"])

    if not pkgs:
        print(f"{Style.WARNING}No driver packages to install after detection.{Style.ENDC}")
        return

    pkgs = list(dict.fromkeys(pkgs))  # deduplicate while preserving order
    pkg_str = ' '.join(pkgs)
    print(f"{Style.OKCYAN}Installing graphics packages into target: {pkg_str}{Style.ENDC}")
    run_cmd(f"xbps-install -Sy -r /mnt {pkg_str}")
    print(f"{Style.OKGREEN}Graphics drivers installation requested. Reconfigure and test after first boot.{Style.ENDC}")

def chroot_and_configure():
    """Performs system configuration inside the chroot."""
    print(f"\n{Style.HEADER}{Style.BOLD}Configuring the new system...{Style.ENDC}")
    run_cmd("cp /etc/resolv.conf /mnt/etc/resolv.conf")

    print(f"{Style.OKCYAN}Set the root password:{Style.ENDC}")
    run_cmd("passwd", chroot=True)

    tz = input("Enter your timezone (e.g., America/New_York): ").strip()
    run_cmd(f"ln -sf /usr/share/zoneinfo/{tz} /etc/localtime", chroot=True)
    run_cmd("hwclock --systohc", chroot=True)

    locale = input("Enter desired locale (e.g., en_US.UTF-8): ").strip()
    run_cmd(f"echo '{locale} UTF-8' > /etc/default/libc-locales", chroot=True)
    run_cmd("xbps-reconfigure -f glibc-locales", chroot=True)

    hostname = input("Enter a hostname for this computer: ").strip()
    run_cmd(f"echo '{hostname}' > /etc/hostname", chroot=True)

    # !! CRITICAL FIX !!
    # Reconfigure all packages to run post-install hooks, essential for the kernel and grub.
    print(f"\n{Style.OKCYAN}Finalizing package configuration (this may take a moment)...{Style.ENDC}")
    run_cmd("xbps-reconfigure -fa", chroot=True)

    print(f"{Style.OKCYAN}Creating a user account...{Style.ENDC}")
    username = input("Enter a username: ").strip()
    while True:
        password = getpass.getpass(f"Enter password for {username}: ")
        password_confirm = getpass.getpass("Confirm password: ")
        if password == password_confirm:
            break
        print(f"{Style.FAIL}Passwords do not match. Please try again.{Style.ENDC}")
    
    run_cmd(f"useradd -m -G wheel,audio,video -s /bin/bash {username}", chroot=True)
    run_cmd(f"echo '{username}:{password}' | chpasswd", chroot=True)

    print(f"{Style.OKCYAN}Setting up sudo and enabling services...{Style.ENDC}")
    run_cmd(f"echo '%wheel ALL=(ALL:ALL) ALL' > /etc/sudoers.d/wheel", chroot=True)

    # Enable essential services
    run_cmd("ln -s /etc/sv/dbus /var/service/", chroot=True, check=False)
    run_cmd("ln -s /etc/sv/NetworkManager /var/service/", chroot=True, check=False)
    # Enable display manager if a DE was installed
    if 'lightdm' in DESKTOP_ENVIRONMENTS.get(globals().get('de_key', 'none'), ''):
        run_cmd("ln -s /etc/sv/lightdm /var/service/", chroot=True, check=False)
    elif 'gdm' in DESKTOP_ENVIRONMENTS.get(globals().get('de_key', 'none'), ''):
        run_cmd("ln -s /etc/sv/gdm /var/service/", chroot=True, check=False)
    elif 'sddm' in DESKTOP_ENVIRONMENTS.get(globals().get('de_key', 'none'), ''):
        run_cmd("ln -s /etc/sv/sddm /var/service/", chroot=True, check=False)

# --- MODIFIED ---: Major rewrite for multi-architecture support
def install_bootloader(disk, uefi, force_removable=True, is_vm=False):
    """Installs and configures the GRUB bootloader based on architecture."""
    global ARCH
    print(f"\n{Style.HEADER}{Style.BOLD}Installing bootloader for {ARCH}...{Style.ENDC}")

    if ARCH == "x86_64":
        if uefi:
            print(f"{Style.OKCYAN}UEFI system detected.{Style.ENDC}")
            run_cmd("xbps-install -Sy grub-x86_64-efi efibootmgr", chroot=True)
            # Always use --removable for VMs to ensure bootloader works
            if is_vm or force_removable:
                print(f"{Style.WARNING}VM detected or removable mode forced. Installing GRUB in removable mode.{Style.ENDC}")
                # Install both ways for maximum compatibility in VMs
                run_cmd("grub-install --target=x86_64-efi --efi-directory=/boot/efi --removable --recheck", chroot=True)
                run_cmd("grub-install --target=x86_64-efi --efi-directory=/boot/efi --bootloader-id=void --recheck", chroot=True, check=False)
            else:
                print(f"{Style.OKCYAN}Attempting standard UEFI GRUB installation...{Style.ENDC}")
                result = subprocess.run(f"chroot /mnt /bin/bash -c 'grub-install --target=x86_64-efi --efi-directory=/boot/efi --bootloader-id=void --recheck'", shell=True)
                if result.returncode != 0:
                    print(f"{Style.WARNING}Standard GRUB install failed. Falling back to removable mode.{Style.ENDC}")
                    run_cmd("grub-install --target=x86_64-efi --efi-directory=/boot/efi --removable --recheck", chroot=True)
        else:
            print(f"{Style.OKCYAN}Legacy BIOS system detected.{Style.ENDC}")
            run_cmd("xbps-install -Sy grub", chroot=True)
            run_cmd(f"grub-install --target=i386-pc {disk}", chroot=True)
    
    elif ARCH == "aarch64":
        if uefi:
            print(f"{Style.OKCYAN}AArch64 UEFI system detected.{Style.ENDC}")
            run_cmd("xbps-install -Sy grub-arm64-efi efibootmgr", chroot=True)
            run_cmd("grub-install --target=arm64-efi --efi-directory=/boot/efi --bootloader-id=Void --recheck", chroot=True)
        else:
            print(f"{Style.WARNING}Non-UEFI AArch64 systems (e.g., using U-Boot) require manual bootloader setup.{Style.ENDC}")
            print("Please consult the Void Linux documentation for your specific device after the script finishes.")
            return # Skip grub-mkconfig

    else: # armv7l and other ARM architectures
        print(f"{Style.WARNING}Automatic bootloader installation is not supported for {ARCH}.{Style.ENDC}")
        print("ARM devices like the Raspberry Pi or those using U-Boot have device-specific boot requirements.")
        print("Please consult the Void Linux documentation for your board to set up the bootloader manually.")
        return # Skip grub-mkconfig

    print(f"{Style.OKCYAN}Generating GRUB configuration...{Style.ENDC}")
    # Ensure grub2 directory exists inside chroot before generating config
    run_cmd("mkdir -p /mnt/boot/grub2", check=False)
    run_cmd("grub-mkconfig -o /boot/grub/grub.cfg", chroot=True)
    print(f"{Style.OKGREEN}Bootloader installation step complete.{Style.ENDC}")


def main():
    """Main installer workflow."""
    global ARCH # --- ADDED ---
    print(f"{Style.HEADER}{Style.BOLD}=== Void Linux Interactive Installer ==={Style.ENDC}")
    if os.geteuid() != 0:
        print(f"{Style.FAIL}This script must be run as root.{Style.ENDC}")
        sys.exit(1)

    parser = argparse.ArgumentParser(description="Void Linux Installer Script")
    parser.add_argument('--force-removable', action='store_true', help='Force GRUB to install in removable media mode (for UEFI).')
    args = parser.parse_args()

    # --- ADDED ---: Detect and confirm architecture first
    ARCH = detect_arch()
    print(f"{Style.OKCYAN}Detected Architecture: {Style.BOLD}{ARCH}{Style.ENDC}")

    check_dependencies()
    uefi = detect_uefi()
    is_vm = detect_vm()

    if is_vm:
        print(f"{Style.WARNING}Virtual machine environment detected. Using safer defaults.{Style.ENDC}")

    disk = select_disk()
    unmount_all(disk)

    mode = input("Choose partitioning mode [a]uto/[m]anual: ").strip().lower()

    if mode == 'a':
        print(f"\n{Style.WARNING}{Style.BOLD}Auto-partitioning {disk} will erase all data!{Style.ENDC}")
        if input("Type 'YES' to confirm: ").strip() != 'YES':
            print("Aborting.")
            sys.exit(0)

        run_cmd(f"sgdisk -Z {disk}") # Zap GPT table
        if uefi:
            # EFI (512M), SWAP (optional), ROOT (rest)
            run_cmd(f"sgdisk -n 1:0:+512M -t 1:ef00 {disk}") # EFI
            if input("Create a swap partition? [y/N]: ").lower() == 'y':
                swap_size = input("Enter swap size (e.g., 4G): ").strip()
                run_cmd(f"sgdisk -n 2:0:+{swap_size} -t 2:8200 {disk}") # SWAP
                run_cmd(f"sgdisk -n 3:0:0 -t 3:8300 {disk}") # ROOT
                swap_part, root_part = part_path(disk, 2), part_path(disk, 3)
                run_cmd(f"mkswap {swap_part}"); run_cmd(f"swapon {swap_part}")
            else:
                run_cmd(f"sgdisk -n 2:0:0 -t 2:8300 {disk}") # ROOT
                root_part = part_path(disk, 2)
            
            efi_part = part_path(disk, 1)
            run_cmd(f"mkfs.vfat -F32 {efi_part}")
            run_cmd(f"mkfs.ext4 {root_part}")
            run_cmd(f"mount {root_part} /mnt")
            run_cmd("mkdir -p /mnt/boot/efi")
            run_cmd(f"mount {efi_part} /mnt/boot/efi")
        else: # BIOS / Legacy (relevant for x86_64, but generic for partitioning)
            # BOOT (1M bios_boot), SWAP (optional), ROOT (rest)
            run_cmd(f"sgdisk -n 1:0:+1M -t 1:ef02 {disk}") # BIOS Boot
            if input("Create a swap partition? [y/N]: ").lower() == 'y':
                swap_size = input("Enter swap size (e.g., 4G): ").strip()
                run_cmd(f"sgdisk -n 2:0:+{swap_size} -t 2:8200 {disk}") # SWAP
                run_cmd(f"sgdisk -n 3:0:0 -t 3:8300 {disk}") # ROOT
                swap_part, root_part = part_path(disk, 2), part_path(disk, 3)
                run_cmd(f"mkswap {swap_part}"); run_cmd(f"swapon {swap_part}")
            else:
                run_cmd(f"sgdisk -n 2:0:0 -t 2:8300 {disk}") # ROOT
                root_part = part_path(disk, 2)
            
            run_cmd(f"mkfs.ext4 {root_part}")
            run_cmd(f"mount {root_part} /mnt")
        
        run_cmd(f"partprobe {disk}")
        print(f"{Style.OKGREEN}Auto-partitioning complete.{Style.ENDC}")
    else:
        manual_partition_and_mount(disk)

    # --- Installation and Configuration ---
    setup_repos() # Setup repos before installing base
    install_base_system()
    install_desktop_and_sound() # Call this before chroot config to enable correct services
    mount_chroot_dirs()
    # Install graphics drivers on bare-metal only (skip in VMs)
    detect_and_install_graphics(is_vm)
    chroot_and_configure()
    install_bootloader(disk, uefi, args.force_removable, is_vm)
    umount_chroot_dirs()

    print(f"\n{Style.OKGREEN}{Style.BOLD}Installation is complete!{Style.ENDC}")
    print("You can now reboot your system. Don't forget to remove the installation media.")
    if input("Reboot now? [y/N]: ").lower() == 'y':
        run_cmd("reboot")

if __name__ == "__main__":
    main()
