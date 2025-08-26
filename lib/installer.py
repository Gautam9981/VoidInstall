"""
Core installation logic for voidinstall (Void Linux TUI installer)
"""
import os
import sys

from lib.disk.utils import wipe_disk, create_partition, get_partition, get_efi_partition
from lib.disk.filesystem import format_ext4, mount_root, setup_boot_partitions
from lib.crypt.luks import luks_format
from lib.packages.xbps import enable_repos, install_packages, upgrade_packages
from lib.authentication.user import create_user_chroot, set_password_chroot, lock_root_chroot
from lib.boot.grub import install_grub_chroot
from lib.locale.config import configure_locale_chroot
from lib.sound import install_sound
from lib.networking.utils import check_network_connection, copy_network_config
from lib.hardware import hardware


def check_root_privileges():
    """Check if running as root or with sudo"""
    # Check if we're in test mode first
    if os.environ.get('VOID_INSTALLER_TEST_MODE') == '1':
        return True
        
    try:
        # Try to access a root-only directory
        os.listdir('/root')
        return True
    except PermissionError:
        return False
    except (OSError, FileNotFoundError):
        # Directory might not exist, try another method
        pass
    
    try:
        # Try using subprocess to check user ID
        import subprocess
        result = subprocess.run(['id', '-u'], capture_output=True, text=True, timeout=5)
        return result.returncode == 0 and result.stdout.strip() == '0'
    except:
        pass
    
    # Fallback - check if we can write to /etc
    try:
        test_file = '/etc/.void_installer_test'
        with open(test_file, 'w') as f:
            f.write('test')
        os.remove(test_file)
        return True
    except:
        return False

def main():
    # Check if running as root
    if not check_root_privileges():
        print("[ERROR] This installer must be run as root.")
        print("Please run with: sudo python3 -m voidinstall")
        print("Or: sudo python3 tui/main.py")
        return 1
    
    print("[INSTALL] Checking network connection...")
    if not check_network_connection():
        print("[WARNING] No network connection detected. Some packages may not install correctly.")
        proceed = input("Continue anyway? (y/N): ").lower()
        if proceed != 'y':
            print("[INSTALL] Installation aborted.")
            return
    else:
        print("[INFO] Network connection confirmed.")

    print("[INSTALL] Detecting hardware...")
    hardware.print_hardware_summary()
    recommended_packages = hardware.get_recommended_packages()

    print("[INSTALL] Detecting boot mode...")
    uefi = os.path.exists("/sys/firmware/efi")
    print(f"[INFO] Boot mode: {'UEFI' if uefi else 'BIOS/Legacy'}")

    print("[INSTALL] Partitioning disk...")
    disk = input("Enter disk to use (e.g., /dev/sda): ")
    wipe_disk(disk)
    create_partition(disk)
    root_part = get_partition(disk)

    encrypt = input("Encrypt root partition with LUKS? (y/N): ").lower() == 'y'
    if encrypt:
        password = input("Enter encryption password: ")
        luks_mapper = luks_format(root_part, password)
        root_device = luks_mapper
    else:
        root_device = root_part

    print("[INSTALL] Setting up filesystem...")
    format_ext4(root_device)
    mount_root(root_device)
    
    # Set up boot partitions (EFI if UEFI, nothing special if BIOS)
    setup_boot_partitions(disk, root_device, "/mnt", uefi)

    print("[INSTALL] Installing base system...")
    enable_repos()
    
    # Install appropriate GRUB package based on boot mode
    grub_pkg = "grub-x86_64-efi" if uefi else "grub"
    base_packages = ["base-system", "linux", grub_pkg, "cryptsetup", "sudo", "vim", "glibc-locales"]
    
    # Add hardware-specific packages
    base_packages.extend(recommended_packages['microcode'])
    base_packages.extend(recommended_packages['audio_firmware'])
    
    install_packages("/mnt", *base_packages)
    upgrade_packages()

    print("[INSTALL] Configuring locale...")
    locale = input("Enter locale (e.g., en_US.UTF-8): ")
    configure_locale_chroot(locale)

    print("[INSTALL] Setting hostname...")
    hostname = input("Enter hostname: ")
    with open("/mnt/etc/hostname", "w") as f:
        f.write(f"{hostname}\n")

    print("[INSTALL] Creating user and locking root...")
    username = input("Enter username: ")
    create_user_chroot(username)
    set_password_chroot(username)
    lock_root_chroot()

    print("[INSTALL] Installing graphics drivers, desktop environment, and sound support...")
    
    # Auto-detect graphics driver
    detected_driver = hardware.detect_graphics_driver()
    print(f"[INFO] Detected graphics driver: {detected_driver.value}")
    
    # Allow user to override auto-detection
    override = input(f"Use detected driver ({detected_driver.value})? (Y/n): ").lower()
    if override == 'n':
        print("Available drivers: 1) intel 2) amd 3) nvidia 4) vmware 5) modesetting")
        driver_map = {
            "1": "intel",
            "2": "amd", 
            "3": "nvidia_proprietary",
            "4": "vmware",
            "5": "generic"
        }
        driver_choice = input("Select graphics driver (number): ")
        driver_name = driver_map.get(driver_choice, "generic")
        # Find the corresponding enum
        from lib.hardware import GfxDriver
        for gfx_driver in GfxDriver:
            if gfx_driver.value == driver_name:
                detected_driver = gfx_driver
                break
    
    graphics_packages = detected_driver.get_void_packages()
    
    print("Available DEs: 1) xfce4 2) kde 3) gnome 4) mate 5) cinnamon")
    de_map = {
        "1": "xfce4",
        "2": "kde5",
        "3": "gnome",
        "4": "mate",
        "5": "cinnamon"
    }
    de_choice = input("Select desktop environment (number): ")
    de_pkg = de_map.get(de_choice, "xfce4")

    print("Available sound systems: 1) PulseAudio 2) PipeWire")
    sound_choice = input("Select sound system (number): ")
    sound_system = "pipewire" if sound_choice == "2" else "pulseaudio"

    install_packages("/mnt", de_pkg, *graphics_packages)
    install_sound("/mnt", sound_system, recommended_packages['audio_firmware'])

    print("[INSTALL] Configuring network...")
    copy_network_config("/mnt", de_pkg)

    # Enable dbus and display manager
    import subprocess
    subprocess.run(["chroot", "/mnt", "sh", "-c", "[ -d /etc/sv/dbus ] && ln -sf /etc/sv/dbus /var/service/"], check=True)
    display_services = {
        "gnome": "gdm",
        "kde5": "sddm",
        "xfce4": "lightdm",
        "mate": "lightdm",
        "cinnamon": "lightdm"
    }
    display_service = display_services.get(de_pkg)
    if display_service:
        subprocess.run(["chroot", "/mnt", "sh", "-c", f"[ -d /etc/sv/{display_service} ] && ln -sf /etc/sv/{display_service} /var/service/"], check=True)

    print("[INSTALL] Installing bootloader...")
    install_grub_chroot("/mnt", disk)

    print("[INSTALL] Installation complete!")

if __name__ == "__main__":
    main()
