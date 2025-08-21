"""
Core installation logic for voidinstall (Void Linux TUI installer)
"""
import subprocess
import sys

class Installer:
    def __init__(self):
        self.disk = None
        self.encrypted = False
        self.locale = None
        self.hostname = None
        self.username = None
        self.desktop_env = None
        self.graphics_driver = None


    def partition_and_encrypt_disk(self):
        print("[INSTALL] Partitioning and encrypting disk...")
        # Example: /dev/sda, single root partition, LUKS encryption
        self.disk = input("Enter disk to use (e.g., /dev/sda): ")
        subprocess.run(["sgdisk", "--zap-all", self.disk], check=True)
        subprocess.run(["sgdisk", "-n", "1:0:0", "-t", "1:8300", self.disk], check=True)
        subprocess.run(["partprobe", self.disk], check=True)
        luks_part = self.disk + "1"
        luks_name = "cryptroot"
        subprocess.run(["cryptsetup", "luksFormat", luks_part], check=True)
        subprocess.run(["cryptsetup", "open", luks_part, luks_name], check=True)
        self.encrypted = True
        self.luks_mapper = f"/dev/mapper/{luks_name}"


    def setup_filesystem(self):
        print("[INSTALL] Setting up filesystem...")
        # Format and mount root
        subprocess.run(["mkfs.ext4", self.luks_mapper], check=True)
        subprocess.run(["mount", self.luks_mapper, "/mnt"], check=True)


    def configure_locale(self):
        print("[INSTALL] Configuring locale...")
        self.locale = input("Enter locale (e.g., en_US.UTF-8): ")
        with open("/mnt/etc/locale.conf", "w") as f:
            f.write(f"LANG={self.locale}\n")
        with open("/mnt/etc/locale.gen", "w") as f:
            f.write(f"{self.locale} UTF-8\n")
        subprocess.run(["chroot", "/mnt", "xbps-reconfigure", "-f", "glibc-locales"], check=True)


    def set_hostname(self):
        print("[INSTALL] Setting hostname...")
        self.hostname = input("Enter hostname: ")
        with open("/mnt/etc/hostname", "w") as f:
            f.write(f"{self.hostname}\n")


    def create_user_and_lock_root(self):
        print("[INSTALL] Creating user and locking root...")
        self.username = input("Enter username: ")
        subprocess.run(["chroot", "/mnt", "useradd", "-m", "-G", "wheel", self.username], check=True)
        subprocess.run(["chroot", "/mnt", "passwd", self.username], check=True)
        subprocess.run(["chroot", "/mnt", "passwd", "-l", "root"], check=True)


    def install_base_system(self):
        print("[INSTALL] Installing base system...")
        subprocess.run(["xbps-install", "-SyR", "void-repo-nonfree", "-r", "/mnt", "base-system", "linux", "grub-x86_64-efi", "cryptsetup", "sudo", "vim", "glibc-locales"], check=True)


    def install_graphics_and_desktop(self):
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

        # Sound system selection
        print("Available sound systems: 1) PulseAudio 2) PipeWire")
        sound_choice = input("Select sound system (number): ")
        if sound_choice == "2":
            sound_pkgs = ["alsa-utils", "pipewire", "wireplumber"]
            sound_service = "pipewire"
        else:
            sound_pkgs = ["alsa-utils", "pulseaudio"]
            sound_service = "pulseaudio"

        subprocess.run(["chroot", "/mnt", "xbps-install", "-Sy", driver_pkg, de_pkg] + sound_pkgs, check=True)
        # Enable display manager for DE using runit (if service exists)

        # Always enable dbus for DEs
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

        # Enable sound service using runit (if service exists)
        if sound_service == "pipewire":
            for svc in ["pipewire", "wireplumber"]:
                subprocess.run(["chroot", "/mnt", "sh", "-c", f"[ -d /etc/sv/{svc} ] && ln -sf /etc/sv/{svc} /var/service/"], check=True)
        else:
            subprocess.run(["chroot", "/mnt", "sh", "-c", "[ -d /etc/sv/pulseaudio ] && ln -sf /etc/sv/pulseaudio /var/service/"], check=True)

    def run(self):
        self.partition_and_encrypt_disk()
        self.setup_filesystem()
        self.install_base_system()
        self.configure_locale()
        self.set_hostname()
        self.create_user_and_lock_root()
        self.install_graphics_and_desktop()
        print("[INSTALL] Installation complete!")

if __name__ == "__main__":
    installer = Installer()
    installer.run()
