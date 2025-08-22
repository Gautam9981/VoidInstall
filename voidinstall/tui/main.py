import npyscreen
import os
import sys

# Add the parent directory to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.dependencies import install_partitioning_tools, check_and_install_tool

def is_void_linux():
    """Check if we're running on Void Linux"""
    try:
        with open('/etc/os-release', 'r') as f:
            return 'void' in f.read().lower()
    except:
        return False

# Check if we're running on Void Linux
VOID_SYSTEM = is_void_linux()

class VoidInstallTUI(npyscreen.NPSAppManaged):
    def onStart(self):
        self.addForm('MAIN', WelcomeForm, name="Void Linux Installer - Welcome")
        self.addForm('DISK', DiskConfigForm, name="Void Linux Installer - Disk Configuration")
        self.addForm('USER', UserConfigForm, name="Void Linux Installer - User Configuration")
        self.addForm('SYSTEM', SystemConfigForm, name="Void Linux Installer - System Configuration")
        self.addForm('INSTALL', InstallProgressForm, name="Void Linux Installer - Installation Progress")

class WelcomeForm(npyscreen.ActionForm):
    def create(self):
        self.add(npyscreen.TitleText, name="Welcome to Void Linux Installer!", editable=False)
        self.nextrely += 1
        
        welcome_text = [
            "This installer will guide you through installing Void Linux.",
            "",
            "Installation Steps:",
            "1. Configure disk and encryption settings",
            "2. Set up user account",
            "3. Configure system settings",
            "4. Install the system",
            "",
            "Press OK to continue or Cancel to exit."
        ]
        
        for line in welcome_text:
            self.add(npyscreen.FixedText, value=line, editable=False)
    
    def on_ok(self):
        self.parentApp.switchForm('DISK')
    
    def on_cancel(self):
        self.parentApp.switchForm(None)

class DiskConfigForm(npyscreen.ActionForm):
    def create(self):
        self.name = "Disk Configuration"
        
        # Simplified form with direct partitioning approach
        self.add(npyscreen.FixedText, value="Disk Partitioning Setup", editable=False)
        self.nextrely += 1
        
        self.add(npyscreen.FixedText, value="Target Disk:", editable=False)
        self.disk = self.add(npyscreen.Textfield, value="/dev/sda", scroll_exit=True)
        
        self.nextrely += 1
        self.add(npyscreen.FixedText, value="Partitioning Method:", editable=False)
        
        self.partition_method = self.add(npyscreen.SelectOne, 
                                        values=["Launch cfdisk (Recommended)", 
                                               "Auto partition", 
                                               "Manual partition setup"], 
                                        max_height=4, 
                                        value=[0],
                                        scroll_exit=True,
                                        exit_left=True,
                                        exit_right=True)
        
        self.nextrely += 1
        self.add(npyscreen.FixedText, value="Root Filesystem:", editable=False)
        
        # Filesystem choice
        self.filesystem = self.add(npyscreen.SelectOne,
                                  values=["ext4", "xfs", "btrfs", "f2fs"],
                                  max_height=5,
                                  value=[0],
                                  scroll_exit=True,
                                  exit_left=True,
                                  exit_right=True)
        
        self.nextrely += 1
        self.add(npyscreen.FixedText, value="LUKS Encryption:", editable=False)
        
        # Encryption toggle
        self.encrypt = self.add(npyscreen.SelectOne, 
                               values=["No", "Yes"], 
                               max_height=3, 
                               value=[0],
                               scroll_exit=True,
                               exit_left=True,
                               exit_right=True)
        
        self.nextrely += 1
        # Password fields with separate labels for better positioning
        self.add(npyscreen.FixedText, value="Encryption password:", editable=False)
        self.encrypt_pass = self.add(npyscreen.PasswordEntry, value="", scroll_exit=True)
        
        self.add(npyscreen.FixedText, value="Confirm password:", editable=False)
        self.encrypt_pass_confirm = self.add(npyscreen.PasswordEntry, value="", scroll_exit=True)
        
        self.nextrely += 1
        self.add(npyscreen.FixedText, value="• cfdisk: Interactive partition editor", editable=False)
        self.add(npyscreen.FixedText, value="• Auto: Automatic EFI+Root+Swap layout", editable=False)
        self.add(npyscreen.FixedText, value="• Manual: Configure partition sizes manually", editable=False)
    
    def on_ok(self):
        # Basic validation
        disk = self.disk.value.strip()
        if not disk or not disk.startswith('/dev/'):
            npyscreen.notify_confirm("Please enter a valid disk path (e.g., /dev/sda)", title="Error")
            return
        
        # Check if disk exists
        import os
        if not os.path.exists(disk):
            npyscreen.notify_confirm(f"Disk {disk} does not exist!", title="Error")
            return
        
        # Get partition method
        method_index = getattr(self.partition_method, 'value', [0])[0]
        method = self.partition_method.values[method_index]
        
        # Handle different partitioning methods
        if method == "Launch cfdisk (Recommended)":
            # Ensure partitioning tools are installed
            if not VOID_SYSTEM:
                npyscreen.notify_confirm("Installing required partitioning tools...", title="Dependencies")
            
            # Install partitioning tools including cfdisk
            try:
                if VOID_SYSTEM:
                    install_partitioning_tools()
                else:
                    # On non-Void systems, just check if cfdisk exists
                    import shutil
                    if not shutil.which('cfdisk'):
                        npyscreen.notify_confirm("cfdisk not found! On a real Void Linux system, it would be automatically installed.", title="Non-Void System")
                        # Continue anyway for testing
            except Exception as e:
                npyscreen.notify_confirm(f"Error installing partitioning tools: {e}", title="Error")
                return
            
            # Check if cfdisk is now available
            import shutil
            if not shutil.which('cfdisk'):
                npyscreen.notify_confirm("cfdisk still not available after installation attempt!", title="Error")
                return
            
            # Save current terminal state and launch cfdisk
            npyscreen.notify_confirm(f"About to launch cfdisk for {disk}.\n\nThis will open the partition editor.\nCreate your partitions and save when done.\n\nRecommended layout:\n• EFI System (512MB, type EF00)\n• Linux root (remaining space, type 8300)\n• Linux swap (optional, type 8200)", 
                                   title="Launch cfdisk")
            
            # Temporarily exit npyscreen to run cfdisk
            import subprocess
            
            # Exit the TUI temporarily
            self.parentApp.onCleanExit()
            
            try:
                # Launch cfdisk
                result = subprocess.run(['cfdisk', disk], check=False)
                if result.returncode != 0:
                    print(f"cfdisk exited with error code {result.returncode}")
            except Exception as e:
                print(f"Error launching cfdisk: {e}")
            
            # Ask user to continue
            input("\nPress Enter to continue with the installer...")
            
            # Re-initialize the TUI
            self.parentApp.onInMainLoop()
        
        # Validate encryption passwords if enabled
        encrypt_enabled = getattr(self.encrypt, 'value', [0])[0] == 1
        if encrypt_enabled:
            pass1 = self.encrypt_pass.value
            pass2 = self.encrypt_pass_confirm.value
            if not pass1 or pass1 != pass2:
                npyscreen.notify_confirm("Encryption passwords don't match or are empty", title="Error")
                return
        
        # Get filesystem choice
        fs_index = getattr(self.filesystem, 'value', [0])[0]
        filesystem = self.filesystem.values[fs_index]
        
        # Store configuration
        setattr(self.parentApp, 'disk_config', {
            'disk': disk,
            'partition_method': method,
            'filesystem': filesystem,
            'encrypt': encrypt_enabled,
            'encrypt_password': self.encrypt_pass.value if encrypt_enabled else ''
        })
        
        self.parentApp.switchForm('USER')
    
    def on_cancel(self):
        self.parentApp.switchForm('MAIN')

class UserConfigForm(npyscreen.ActionForm):
    def create(self):
        self.add(npyscreen.TitleText, name="User Account Configuration", editable=False)
        self.nextrely += 2
        
        # User account section
        self.add(npyscreen.FixedText, value="User Account Details:", editable=False)
        self.add(npyscreen.FixedText, value="Username:", editable=False)
        self.username = self.add(npyscreen.Textfield, max_width=40, scroll_exit=True)
        
        self.nextrely += 1
        
        # Password section
        self.add(npyscreen.FixedText, value="Password Configuration:", editable=False)
        self.add(npyscreen.FixedText, value="Password:", editable=False)
        self.password = self.add(npyscreen.PasswordEntry, max_width=40, scroll_exit=True)
        
        self.add(npyscreen.FixedText, value="Confirm Password:", editable=False)
        self.password_confirm = self.add(npyscreen.PasswordEntry, max_width=40, scroll_exit=True)
        
        self.nextrely += 2
        
        # User account information
        self.add(npyscreen.FixedText, value="Account Information:", editable=False)
        info_text = [
            "• User will be added to wheel group (sudo access)",
            "• Root account will be locked for security",
            "• Password must be at least 6 characters long",
            "• Choose a strong password for your account"
        ]
        
        for line in info_text:
            self.add(npyscreen.FixedText, value=line, editable=False)
    
    def on_ok(self):
        # Validate inputs
        if not self.username.value:
            npyscreen.notify_confirm("Please enter a username.", title="Validation Error")
            return
            
        if not self.password.value:
            npyscreen.notify_confirm("Please enter a password.", title="Validation Error")
            return
            
        if self.password.value != self.password_confirm.value:
            npyscreen.notify_confirm("Passwords do not match. Please try again.", title="Validation Error")
            return
            
        if len(self.password.value) < 6:
            npyscreen.notify_confirm("Password must be at least 6 characters long.", title="Validation Error")
            return
        
        setattr(self.parentApp, 'user_config', {
            'username': self.username.value,
            'password': self.password.value
        })
        self.parentApp.switchForm('SYSTEM')
    
    def on_cancel(self):
        self.parentApp.switchForm('DISK')

class SystemConfigForm(npyscreen.ActionForm):
    def create(self):
        self.add(npyscreen.TitleText, name="System Configuration", editable=False)
        self.nextrely += 2
        
        # System identity section
        self.add(npyscreen.FixedText, value="System Identity:", editable=False)
        self.add(npyscreen.FixedText, value="Hostname:", editable=False)
        self.hostname = self.add(npyscreen.Textfield, value="voidlinux", max_width=40, scroll_exit=True)
        
        self.add(npyscreen.FixedText, value="Locale:", editable=False)
        self.locale = self.add(npyscreen.Textfield, value="en_US.UTF-8", max_width=40, scroll_exit=True)
        
        self.nextrely += 2
        
        # Desktop environment section
        self.add(npyscreen.FixedText, value="Desktop Environment:", editable=False)
        self.desktop = self.add(npyscreen.SelectOne,
                               max_height=6,
                               value=[0],
                               values=["XFCE", "GNOME", "KDE", "MATE", "Cinnamon"],
                               scroll_exit=True,
                               exit_left=True,
                               exit_right=True)

        self.nextrely += 1
        
        # Audio system section
        self.add(npyscreen.FixedText, value="Audio System:", editable=False)
        self.sound = self.add(npyscreen.SelectOne,
                             max_height=3,
                             value=[0],
                             values=["PipeWire", "PulseAudio"],
                             scroll_exit=True,
                             exit_left=True,
                             exit_right=True)
        
        self.nextrely += 2
        
        # Configuration help
        self.add(npyscreen.FixedText, value="Configuration Help:", editable=False)
        info_text = [
            "• Hostname: Network name for your computer",
            "• Locale: Language and regional settings", 
            "• Desktop: Graphical user interface",
            "• Audio: Sound system for multimedia"
        ]
        
        for line in info_text:
            self.add(npyscreen.FixedText, value=line, editable=False)
    
    def on_ok(self):
        # Validate inputs
        if not self.hostname.value:
            npyscreen.notify_confirm("Please enter a hostname.", title="Validation Error")
            return
            
        if not self.locale.value:
            npyscreen.notify_confirm("Please enter a locale.", title="Validation Error")
            return
        
        # Basic hostname validation
        hostname = self.hostname.value.strip()
        if not hostname.replace('-', '').replace('_', '').isalnum():
            npyscreen.notify_confirm("Hostname should only contain letters, numbers, hyphens, and underscores.", title="Validation Error")
            return
            
        if len(hostname) > 63:
            npyscreen.notify_confirm("Hostname should be 63 characters or less.", title="Validation Error")
            return
        
        # Get selections using value index
        desktop_index = getattr(self.desktop, 'value', [0])[0]
        desktop = self.desktop.values[desktop_index].lower()
        
        sound_index = getattr(self.sound, 'value', [0])[0] 
        sound = self.sound.values[sound_index].lower()
        
        setattr(self.parentApp, 'system_config', {
            'desktop': desktop,
            'sound': sound,
            'hostname': hostname,
            'locale': self.locale.value.strip()
        })
        self.parentApp.switchForm('INSTALL')
    
    def on_cancel(self):
        self.parentApp.switchForm('USER')

class InstallProgressForm(npyscreen.ActionForm):
    def create(self):
        self.add(npyscreen.TitleText, name="Installation Progress", editable=False)
        self.nextrely += 2

        # Progress display using BoxTitle with MultiLine for rolling log
        self.add(npyscreen.FixedText, value="Installation Status:", editable=False)
        self.progress_log = []
        self.progress = self.add(npyscreen.BoxTitle,
                                 name="Progress Log",
                                 max_height=8,
                                 values=["Ready to start installation. Press OK to begin or Cancel to go back."],
                                 editable=False)

        self.nextrely += 2

        # Installation summary
        self.add(npyscreen.FixedText, value="Configuration Summary:", editable=False)
        self.summary = self.add(npyscreen.MultiLineEdit,
                               max_height=10,
                               editable=False)

        # Show configuration summary
        self.show_configuration_summary()
    
    def show_configuration_summary(self):
        """Show the installation configuration summary"""
        disk_config = getattr(self.parentApp, 'disk_config', {})
        user_config = getattr(self.parentApp, 'user_config', {})
        system_config = getattr(self.parentApp, 'system_config', {})
        
        # Build a nice formatted summary
        summary_lines = []
        summary_lines.append("╔══════ INSTALLATION CONFIGURATION ══════╗")
        summary_lines.append("║                                         ║")
        summary_lines.append("║ DISK & PARTITIONING                     ║")
        summary_lines.append(f"║ Disk: {disk_config.get('disk', 'Not configured'):<31} ║")
        summary_lines.append(f"║ Method: {disk_config.get('partition_method', 'Auto'):<29} ║")
        summary_lines.append(f"║ Filesystem: {disk_config.get('filesystem', 'ext4'):<25} ║")
        summary_lines.append(f"║ Encryption: {'Yes' if disk_config.get('encrypt', False) else 'No':<27} ║")
        summary_lines.append("║                                         ║")
        summary_lines.append("║ USER & SYSTEM                           ║")
        summary_lines.append(f"║ Username: {user_config.get('username', 'Not configured'):<29} ║")
        summary_lines.append(f"║ Desktop: {system_config.get('desktop', 'Not configured').upper():<30} ║")
        summary_lines.append(f"║ Sound: {system_config.get('sound', 'Not configured'):<32} ║")
        summary_lines.append(f"║ Hostname: {system_config.get('hostname', 'Not configured'):<29} ║")
        summary_lines.append(f"║ Locale: {system_config.get('locale', 'Not configured'):<31} ║")
        summary_lines.append("║                                         ║")
        summary_lines.append("╚═════════════════════════════════════════╝")
        summary_lines.append("")
        summary_lines.append("Press OK to start installation or Cancel to go back")
        
        # For now, just display without trying to set values
        self.display()
    
    def on_ok(self):
        """Start the installation when OK is pressed"""
        self.start_installation()
    
    def on_cancel(self):
        """Go back to system configuration"""
        self.parentApp.switchForm('SYSTEM')
    
    def start_installation(self):
        """Start the installation process"""
        import sys
        import os
        import time
        import traceback
        
        # Add the parent directory to Python path so we can import lib modules
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        try:
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
        except ImportError as e:
            npyscreen.notify_confirm(f"Import error: {e}. Cannot proceed with installation.", title="Import Error")
            self.parentApp.switchForm(None)  # Exit application
            return

        # Get configuration from the app
        disk_config = getattr(self.parentApp, 'disk_config', {})
        user_config = getattr(self.parentApp, 'user_config', {})
        system_config = getattr(self.parentApp, 'system_config', {})
        
        disk = disk_config.get('disk', '/dev/sda')
        encrypt = disk_config.get('encrypt', False)
        encrypt_password = disk_config.get('encrypt_password', '')
        username = user_config.get('username', 'void')
        desktop = system_config.get('desktop', 'xfce')
        sound = system_config.get('sound', 'pipewire')
        locale = system_config.get('locale', 'en_US.UTF-8')
        hostname = system_config.get('hostname', 'voidlinux')

        # Update summary - for now, just display without values assignment
        summary_lines = [
            f"Disk: {disk}",
            f"Encryption: {'Yes' if encrypt else 'No'}",
            f"Username: {username}",
            f"Desktop: {desktop.upper()}",
            f"Sound: {sound}",
            f"Locale: {locale}",
            f"Hostname: {hostname}"
        ]
        # Note: Will improve summary display later

        try:
            # Check network connection first
            if not check_network_connection():
                npyscreen.notify_confirm("No network connection detected. Some packages may not install correctly.", title="Network Warning")

            # Install required dependencies
            self.update_progress("[INSTALL] Installing required dependencies...")
            install_all_dependencies(encryption_needed=encrypt)

            # Detect hardware
            self.update_progress("[INSTALL] Detecting hardware...")
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
            sound_system = "pipewire" if "pipewire" in sound else "pulseaudio"
            
            # Auto-detect graphics driver
            detected_driver = hardware.detect_graphics_driver()
            graphics_packages = detected_driver.get_void_packages()
            
            # Detect boot mode
            uefi = os.path.exists("/sys/firmware/efi")
            self.update_progress(f"[INSTALL] Boot mode: {'UEFI' if uefi else 'BIOS/Legacy'}")

            self.update_progress("[INSTALL] Partitioning disk...")
            
            # Ensure partitioning tools are available
            from lib.dependencies import install_partitioning_tools
            install_partitioning_tools()
            
            from lib.disk.utils import partition_disk, format_partitions
            boot_part, root_part = partition_disk(disk, encrypt)
            format_partitions(boot_part, root_part, encrypt)
            
            if encrypt:
                luks_mapper = luks_format(root_part, encrypt_password)
                root_device = luks_mapper
            else:
                root_device = root_part

            self.update_progress("[INSTALL] Setting up filesystem...")
            format_ext4(root_device)
            mount_root(root_device)
            
            # Set up boot partitions
            boot_msg = setup_boot_partitions(disk, root_device, "/mnt", uefi)
            self.update_progress(boot_msg)

            self.update_progress("[INSTALL] Installing base system...")
            
            # Install appropriate GRUB package based on boot mode
            grub_pkg = "grub-x86_64-efi" if uefi else "grub"
            base_packages = ["base-system", "linux", grub_pkg, "cryptsetup", "sudo", "vim", "glibc-locales"]
            
            # Add hardware-specific packages
            base_packages.extend(recommended_packages['microcode'])
            base_packages.extend(recommended_packages['audio_firmware'])
            
            install_packages("/mnt", *base_packages)
            
            # Enable additional repos after base system is installed
            self.update_progress("[INSTALL] Enabling additional repositories...")
            enable_repos()
            upgrade_packages()

            self.update_progress("[INSTALL] Configuring locale...")
            configure_locale_chroot(locale)

            self.update_progress("[INSTALL] Setting hostname...")
            with open("/mnt/etc/hostname", "w") as f:
                f.write(f"{hostname}\n")

            self.update_progress("[INSTALL] Creating user and locking root...")
            create_user_chroot(username)
            set_password_chroot(username)
            lock_root_chroot()

            self.update_progress("[INSTALL] Installing graphics, desktop, and sound...")
            install_packages("/mnt", de_pkg, *graphics_packages)
            sound_msg = install_sound("/mnt", sound_system, recommended_packages['audio_firmware'])
            self.update_progress(sound_msg)

            self.update_progress("[INSTALL] Configuring network...")
            copy_network_config("/mnt", de_pkg)

            # Enable dbus and display manager
            from lib.sudo_utils import run_chroot_command
            run_chroot_command("/mnt", ["sh", "-c", "[ -d /etc/sv/dbus ] && ln -sf /etc/sv/dbus /var/service/"])
            display_services = {
                "gnome": "gdm",
                "kde5": "sddm",
                "xfce4": "lightdm",
                "mate": "lightdm",
                "cinnamon": "lightdm"
            }
            display_service = display_services.get(de_pkg)
            if display_service:
                run_chroot_command("/mnt", ["sh", "-c", f"[ -d /etc/sv/{display_service} ] && ln -sf /etc/sv/{display_service} /var/service/"])
                self.update_progress(f"[INSTALL] Enabled {display_service} display manager")

            self.update_progress("[INSTALL] Installing bootloader...")
            install_grub_chroot("/mnt", disk)

            self.update_progress("[INSTALL] Installation complete!")
            npyscreen.notify_confirm("Installation completed successfully! You can now reboot into your new Void Linux system.", title="Installation Complete")
            
        except Exception as e:
            error_msg = f"[ERROR] {str(e)}\n{traceback.format_exc()}"
            self.update_progress(error_msg)
            npyscreen.notify_confirm(f"Installation failed: {str(e)}", title="Installation Error")
            self.parentApp.switchForm(None)  # Exit application after fatal error
    
    def update_progress(self, message):
        """Update the progress display with a rolling log, avoiding zigzag/wrapping issues"""
        self.progress_log.append(str(message))
        if len(self.progress_log) > 50:
            self.progress_log = self.progress_log[-50:]
        # Update the entry_widget.values for BoxTitle (MultiLine)
        self.progress.entry_widget.values = self.progress_log
        self.progress.entry_widget.display()

# Keep the old MainForm for backward compatibility
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
        self.install_btn = self.add(npyscreen.ButtonPress, name="Install", when_pressed_function=self.on_install)
        
        self.nextrely += 1  # Add spacing
        
        # Status display with proper height
        self.status_text = "Ready to install. Fill in the fields above and press Install."
        self.status = self.add(npyscreen.FixedText, 
                              value=self.status_text,
                              max_height=8,
                              editable=False)

    def update_status(self, message):
        """Helper method to update status display"""
        # For now, just refresh the display - we'll improve this later
        self.display()

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
            self.update_status("[INSTALL] Installing required dependencies...")
            install_all_dependencies(encryption_needed=encrypt)

            # Detect hardware
            self.update_status("[INSTALL] Detecting hardware...")
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
            # Detect boot mode
            uefi = os.path.exists("/sys/firmware/efi")
            self.update_status(f"[INSTALL] Boot mode: {'UEFI' if uefi else 'BIOS/Legacy'}")

            self.update_status("[INSTALL] Partitioning disk...")
            
            # Ensure partitioning tools are available
            from lib.dependencies import install_partitioning_tools
            install_partitioning_tools()
            
            from lib.disk.utils import partition_disk, format_partitions
            boot_part, root_part = partition_disk(disk, encrypt)
            format_partitions(boot_part, root_part, encrypt)
            
            if encrypt:
                # For the old MainForm, use a default password since it doesn't collect one
                default_password = "voidinstall123"  # This should be improved to collect from user
                luks_mapper = luks_format(root_part, default_password)
                root_device = luks_mapper
            else:
                root_device = root_part
            if hasattr(self.status, "value"):
                self.update_status("[INSTALL] Setting up filesystem...")
            format_ext4(root_device)
            mount_root(root_device)
            
            # Set up boot partitions (EFI if UEFI, nothing special if BIOS)
            setup_boot_partitions(disk, root_device, "/mnt", uefi)

            self.update_status("[INSTALL] Installing base system...")
            enable_repos()
            
            # Install appropriate GRUB package based on boot mode
            grub_pkg = "grub-x86_64-efi" if uefi else "grub"
            base_packages = ["base-system", "linux", grub_pkg, "cryptsetup", "sudo", "vim", "glibc-locales"]
            
            # Add hardware-specific packages
            base_packages.extend(recommended_packages['microcode'])
            base_packages.extend(recommended_packages['audio_firmware'])
            
            install_packages("/mnt", *base_packages)
            upgrade_packages()

            self.update_status("[INSTALL] Configuring locale...")
            # Use a simple text input instead of notify_input which doesn't exist
            locale = "en_US.UTF-8"  # Default locale for now
            configure_locale_chroot(locale)

            self.update_status("[INSTALL] Setting hostname...")
            # Use a simple hostname for now  
            hostname = "voidlinux"  # Default hostname for now
            with open("/mnt/etc/hostname", "w") as f:
                f.write(f"{hostname}\n")

            self.update_status("[INSTALL] Creating user and locking root...")
            create_user_chroot(username)
            set_password_chroot(username)
            lock_root_chroot()

            self.update_status("[INSTALL] Installing graphics, desktop, and sound...")
            install_packages("/mnt", de_pkg, *graphics_packages)
            install_sound("/mnt", sound_system, recommended_packages['audio_firmware'])

            self.update_status("[INSTALL] Configuring network...")
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

            self.update_status("[INSTALL] Installing bootloader...")
            install_grub_chroot("/mnt", disk)

            self.update_status("[INSTALL] Installation complete!")
        except Exception as e:
            error_msg = f"[ERROR] {str(e)}\n{traceback.format_exc()}"
            self.update_status(error_msg)
            npyscreen.notify_confirm(f"Installation failed: {str(e)}", title="Installation Error")
            sys.exit(1)  # Exit application after fatal error

def launch_tui():
    import sys
    import os
    # Add the parent directory to Python path so we can import lib modules
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    app = VoidInstallTUI()
    app.run()

if __name__ == "__main__":
    launch_tui()

