
import npyscreen

class VoidInstallTUI(npyscreen.NPSAppManaged):
    def onStart(self):
        self.addForm('MAIN', MainForm, name="Void Linux Installer")

class MainForm(npyscreen.FormBaseNew):
    def create(self):
        # Add title with more space
        self.add(npyscreen.TitleText, name="Welcome to Void Linux Installer!", editable=False)
        self.nextrely += 1  # Add spacing
        
        # Input fields with better sizing
        self.disk = self.add(npyscreen.TitleText, name="Disk (e.g., /dev/sda):", max_width=50)
        self.username = self.add(npyscreen.TitleText, name="Username:", max_width=40)
        
        self.nextrely += 1  # Add spacing before options
        
        # Encrypt option with proper height
        self.encrypt = self.add(npyscreen.TitleSelectOne, 
                               max_height=3, 
                               value=[0], 
                               name="Encrypt root?", 
                               values=["No", "Yes"], 
                               scroll_exit=True)

        self.nextrely += 1  # Add spacing
        
        # Desktop environment selection
        self.desktop = self.add(npyscreen.TitleSelectOne,
                               max_height=6,
                               value=[0],
                               name="Desktop Environment:",
                               values=["XFCE", "GNOME", "KDE", "MATE", "Cinnamon"],
                               scroll_exit=True)

        self.nextrely += 1  # Add spacing
        
        # Sound system selection
        self.sound = self.add(npyscreen.TitleSelectOne,
                             max_height=3,
                             value=[0],
                             name="Sound System:",
                             values=["PipeWire", "PulseAudio"],
                             scroll_exit=True)

        self.nextrely += 2  # Add more spacing before button
        
        # Install button
        self.install_btn = self.add(npyscreen.ButtonPress, name="Install")
        self.install_btn.whenPressed = self.on_install
        
        self.nextrely += 1  # Add spacing
        
        # Status display with proper height
        self.status = self.add(npyscreen.MultiLineEdit, 
                              value="Ready to install. Fill in the fields above and press Install.", 
                              max_height=8,
                              editable=False)

    def on_install(self):
        import sys
        import os
        # Add the parent directory to Python path so we can import lib modules
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
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
        from lib.dependencies import install_all_dependencies
        import subprocess
        import traceback

        # Check network connection first (like archinstall)
        if not check_network_connection():
            npyscreen.notify_confirm("No network connection detected. Some packages may not install correctly.", title="Network Warning")

        # Get user selections
        disk = self.disk.value
        username = self.username.value
        encrypt = self.encrypt.get_selected_objects()[0] == "Yes"
        desktop = self.desktop.get_selected_objects()[0].lower() if self.desktop.get_selected_objects() else "xfce4"
        sound = self.sound.get_selected_objects()[0].lower() if self.sound.get_selected_objects() else "pipewire"

        try:
            # Install required dependencies based on user selections
            self.status.value = "[INSTALL] Installing required dependencies..."
            self.status.display()
            install_all_dependencies(encryption_needed=encrypt)

            # Detect hardware
            self.status.value = "[INSTALL] Detecting hardware..."
            self.status.display()
            hardware.print_hardware_summary()
            recommended_packages = hardware.get_recommended_packages()
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
        
        # Auto-detect graphics driver
        detected_driver = hardware.detect_graphics_driver()
        graphics_packages = detected_driver.get_void_packages()
        
        # For TUI, we could add a confirmation dialog, but for now use auto-detection
        # driver_choice = npyscreen.notify_input("Select graphics driver (1=intel,2=amd,3=nvidia,4=vmware,5=modesetting):", title="Graphics Driver", editw=1)
        # For now, just use the detected driver

        try:
            # Detect boot mode
            uefi = os.path.exists("/sys/firmware/efi")
            self.status.value = f"[INSTALL] Boot mode: {'UEFI' if uefi else 'BIOS/Legacy'}"
            self.display()

            self.status.value = "            # Partition and format disk
            self.status.value = "[INSTALL] Partitioning disk..."
            self.status.display()
            
            # Ensure partitioning tools are available
            from lib.dependencies import install_partitioning_tools
            install_partitioning_tools()
            
            from lib.disk.utils import partition_disk, format_partitions
            boot_part, root_part = partition_disk(disk, encrypt)
            format_partitions(boot_part, root_part, encrypt)"
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
            
            # Set up boot partitions (EFI if UEFI, nothing special if BIOS)
            setup_boot_partitions(disk, root_device, "/mnt", uefi)

            self.status.value = "[INSTALL] Installing base system..."
            self.display()
            enable_repos()
            
            # Install appropriate GRUB package based on boot mode
            grub_pkg = "grub-x86_64-efi" if uefi else "grub"
            base_packages = ["base-system", "linux", grub_pkg, "cryptsetup", "sudo", "vim", "glibc-locales"]
            
            # Add hardware-specific packages
            base_packages.extend(recommended_packages['microcode'])
            base_packages.extend(recommended_packages['audio_firmware'])
            
            install_packages("/mnt", *base_packages)
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
            install_packages("/mnt", de_pkg, *graphics_packages)
            install_sound("/mnt", sound_system, recommended_packages['audio_firmware'])

            self.status.value = "[INSTALL] Configuring network..."
            self.display()
            copy_network_config("/mnt", de_pkg)

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
            install_grub_chroot("/mnt", disk)

            self.status.value = "[INSTALL] Installation complete!"
            self.status.display()
        except Exception as e:
            error_msg = f"[ERROR] {str(e)}\n{traceback.format_exc()}"
            self.status.value = error_msg
            self.status.display()

def launch_tui():
    import sys
    import os
    # Add the parent directory to Python path so we can import lib modules
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    app = VoidInstallTUI()
    app.run()

if __name__ == "__main__":
    launch_tui()
