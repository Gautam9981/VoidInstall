
import npyscreen

class VoidInstallTUI(npyscreen.NPSAppManaged):
    def onStart(self):
        self.addForm('MAIN', MainForm, name="Void Linux Installer")

class MainForm(npyscreen.FormBaseNew):
    def create(self):
        self.add(npyscreen.TitleText, name="Welcome to Void Linux Installer!", editable=False)
        self.disk = self.add(npyscreen.TitleText, name="Disk (e.g., /dev/sda):")
        self.username = self.add(npyscreen.TitleText, name="Username:")
        self.encrypt = self.add(npyscreen.TitleSelectOne, max_height=2, value=[0], name="Encrypt root?", values=["No", "Yes"], scroll_exit=True)

        self.desktop = self.add(
            npyscreen.TitleSelectOne,
            max_height=5,
            value=[0],
            name="Desktop Environment:",
            values=["XFCE", "GNOME", "KDE", "MATE", "Cinnamon"],
            scroll_exit=True
        )

        self.sound = self.add(
            npyscreen.TitleSelectOne,
            max_height=2,
            value=[0],
            name="Sound System:",
            values=["PipeWire", "PulseAudio"],
            scroll_exit=True
        )

        self.install_btn = self.add(npyscreen.ButtonPress, name="Install")
        self.install_btn.whenPressed = self.on_install
        self.status = self.add(npyscreen.FixedText, value="", editable=False)

    def on_install(self):
        from lib.disk.utils import wipe_disk, create_partition, get_partition
        from lib.disk.filesystem import format_ext4, mount_root
        from lib.crypt.luks import luks_format
        from lib.packages.xbps import enable_repos, install_packages, upgrade_packages
        from lib.authentication.user import create_user_chroot, set_password_chroot, lock_root_chroot
        from lib.boot.grub import install_grub_chroot
        from lib.locale.config import configure_locale_chroot
        from lib.sound import install_sound
        import subprocess
        import traceback

        disk = self.disk.value
        username = self.username.value
        encrypt = self.encrypt.get_selected_objects()[0] == "Yes"
        desktop = self.desktop.get_selected_objects()[0].lower() if self.desktop.get_selected_objects() else "xfce4"
        sound = self.sound.get_selected_objects()[0].lower() if self.sound.get_selected_objects() else "pipewire"
        # Map desktop to package
        de_map = {
            "xfce": "xfce4",
            "gnome": "gnome",
            "kde": "kde5",
            "mate": "mate",
            "cinnamon": "cinnamon"
        }
        de_pkg = de_map.get(desktop, "xfce4")
        # Map sound
        sound_system = "pipewire" if "pipewire" in sound else "pulseaudio"
        # Graphics driver selection (prompt for now)
        driver_map = {
            "1": "xf86-video-intel*",
            "2": "xf86-video-amdgpu*",
            "3": "nvidia*",
            "4": "xf86-video-vmware*",
            "5": "xf86-video-modesetting*"
        }
        # For now, prompt for driver
        driver_choice = npyscreen.notify_input("Select graphics driver (1=intel,2=amd,3=nvidia,4=vmware,5=modesetting):", title="Graphics Driver", editw=1)
        driver_pkg = driver_map.get(driver_choice, "xf86-video-modesetting*")

        try:
            self.status.value = "[INSTALL] Partitioning and encrypting disk..."
            self.display()
            wipe_disk(disk)
            create_partition(disk)
            root_part = get_partition(disk)

            if encrypt:
                luks_mapper = luks_format(root_part)
                root_device = luks_mapper
            else:
                root_device = root_part

            self.status.value = "[INSTALL] Setting up filesystem..."
            self.display()
            format_ext4(root_device)
            mount_root(root_device)

            self.status.value = "[INSTALL] Installing base system..."
            self.display()
            enable_repos()
            install_packages("/mnt", "base-system", "linux", "grub-x86_64-efi", "cryptsetup", "sudo", "vim", "glibc-locales")
            upgrade_packages()

            self.status.value = "[INSTALL] Configuring locale..."
            self.display()
            locale = npyscreen.notify_input("Enter locale (e.g., en_US.UTF-8):", title="Locale", editw=1)
            configure_locale_chroot(locale)

            self.status.value = "[INSTALL] Setting hostname..."
            self.display()
            hostname = npyscreen.notify_input("Enter hostname:", title="Hostname", editw=1)
            with open("/mnt/etc/hostname", "w") as f:
                f.write(f"{hostname}\n")

            self.status.value = "[INSTALL] Creating user and locking root..."
            self.display()
            create_user_chroot(username)
            set_password_chroot(username)
            lock_root_chroot()

            self.status.value = "[INSTALL] Installing graphics, desktop, and sound..."
            self.display()
            install_packages("/mnt", driver_pkg, de_pkg)
            install_sound("/mnt", sound_system)

            # Enable dbus and display manager
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

            self.status.value = "[INSTALL] Installing bootloader..."
            self.display()
            install_grub_chroot()

            self.status.value = "[INSTALL] Installation complete!"
            self.display()
        except Exception as e:
            self.status.value = f"[ERROR] {e}\n{traceback.format_exc()}"
            self.display()

def launch_tui():
    VoidInstallTUI().run()
