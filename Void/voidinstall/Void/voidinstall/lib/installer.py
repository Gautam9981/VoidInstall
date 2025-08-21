"""
Core installation logic for voidinstall (Void Linux TUI installer)
"""

from lib.disk.utils import wipe_disk, create_partition, get_partition
from lib.disk.filesystem import format_ext4, mount_root
from lib.crypt.luks import luks_format
from lib.packages.xbps import enable_repos, install_packages, upgrade_packages
from lib.authentication.user import create_user_chroot, set_password_chroot, lock_root_chroot
from lib.boot.grub import install_grub_chroot
from lib.locale.config import configure_locale_chroot
from lib.sound import install_sound


def main():
    print("[INSTALL] Partitioning and encrypting disk...")
    disk = input("Enter disk to use (e.g., /dev/sda): ")
    wipe_disk(disk)
    create_partition(disk)
    root_part = get_partition(disk)

    encrypt = input("Encrypt root partition with LUKS? (y/N): ").lower() == 'y'
    if encrypt:
        luks_mapper = luks_format(root_part)
        root_device = luks_mapper
    else:
        root_device = root_part

    print("[INSTALL] Setting up filesystem...")
    format_ext4(root_device)
    mount_root(root_device)

    print("[INSTALL] Installing base system...")
    enable_repos()
    install_packages("/mnt", "base-system", "linux", "grub-x86_64-efi", "cryptsetup", "sudo", "vim", "glibc-locales")
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
    print("Available drivers: 1) intel 2) amd 3) nvidia 4) vmware 5) modesetting")
    driver_map = {
        "1": "xf86-video-intel",
        "2": "xf86-video-amdgpu",
        "3": "nvidia",
        "4": "xf86-video-vmware",
        "5": "xf86-video-modesetting"
    }
    driver_choice = input("Select graphics driver (number): ")
    driver_pkg = driver_map.get(driver_choice, "xf86-video-modesetting")
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

    install_packages("/mnt", driver_pkg, de_pkg)
    install_sound("/mnt", sound_system)

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
    install_grub_chroot()

    print("[INSTALL] Installation complete!")

if __name__ == "__main__":
    main()
