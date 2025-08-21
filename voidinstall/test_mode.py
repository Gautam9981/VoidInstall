"""
Test mode / dry run functionality for the Void Linux installer.
This module simulates installation steps when running on non-Void systems
or when explicitly enabled for testing purposes.
"""

import time
import os
import random

def is_void_linux():
    """Check if we're running on Void Linux"""
    try:
        with open('/etc/os-release', 'r') as f:
            return 'void' in f.read().lower()
    except:
        return False

def is_test_mode():
    """Check if we should run in test mode"""
    return not is_void_linux() or os.environ.get('VOID_INSTALLER_TEST_MODE') == '1'

class TestModeInstaller:
    """Simulates the installation process for testing purposes"""
    
    def __init__(self, progress_callback=None):
        self.progress_callback = progress_callback or (lambda x: print(x))
        self.step_delay = 2  # Seconds to wait between steps
        
    def simulate_step(self, message, delay=None):
        """Simulate a single installation step"""
        self.progress_callback(message)
        time.sleep(delay or self.step_delay)
        
        # Randomly simulate some steps taking longer
        if random.random() < 0.3:  # 30% chance of longer step
            time.sleep(1)
    
    def simulate_installation(self, config):
        """
        Simulate the complete installation process
        
        Args:
            config (dict): Installation configuration containing:
                - disk: Target disk
                - encrypt: Whether to encrypt
                - username: User to create
                - password: User password
                - desktop: Desktop environment
                - sound: Sound system
                - locale: System locale
                - hostname: System hostname
        """
        try:
            self.simulate_step("[TEST] Starting installation simulation...")
            
            # Extract config
            disk = config.get('disk', '/dev/sda')
            encrypt = config.get('encrypt', False)
            username = config.get('username', 'void')
            password = config.get('password', '******')  # Don't log actual password
            desktop = config.get('desktop', 'xfce')
            sound = config.get('sound', 'pipewire')
            locale = config.get('locale', 'en_US.UTF-8')
            hostname = config.get('hostname', 'voidlinux')
            
            self.simulate_step(f"[TEST] Configuration loaded - Disk: {disk}, User: {username}, Desktop: {desktop.upper()}")
            
            self.simulate_step("[TEST] Checking network connection...")
            
            self.simulate_step("[TEST] Installing required dependencies...")
            
            self.simulate_step("[TEST] Detecting hardware...")
            self.simulate_step("  - CPU: Detected (simulated)")
            self.simulate_step("  - GPU: Detected (simulated)")
            self.simulate_step("  - Audio: Detected (simulated)")
            
            # Detect boot mode (this is real)
            uefi = os.path.exists("/sys/firmware/efi")
            self.simulate_step(f"[TEST] Boot mode: {'UEFI' if uefi else 'BIOS/Legacy'}")
            
            self.simulate_step(f"[TEST] Partitioning disk {disk}...")
            self.simulate_step(f"[TEST] Using partition scheme: {config.get('partition_scheme', 'Auto')}")
            
            # Simulate partition creation based on scheme
            boot_size = config.get('boot_size', 512)
            root_size = config.get('root_size', 0)
            swap_size = config.get('swap_size', 0)
            home_separate = config.get('home_separate', False)
            home_size = config.get('home_size', 0)
            filesystem = config.get('filesystem', 'ext4')
            
            self.simulate_step(f"[TEST] Creating boot partition ({boot_size}MB)...")
            self.simulate_step(f"[TEST] Creating root partition ({root_size}GB, 0=remaining)...")
            
            if swap_size > 0:
                self.simulate_step(f"[TEST] Creating swap partition ({swap_size}GB)...")
            else:
                self.simulate_step("[TEST] Skipping swap partition...")
                
            if home_separate:
                self.simulate_step(f"[TEST] Creating separate /home partition ({home_size}GB)...")
            else:
                self.simulate_step("[TEST] Using root partition for /home...")
            
            if encrypt:
                self.simulate_step("[TEST] Setting up LUKS encryption on root partition...")
                self.simulate_step("[TEST] Formatting LUKS container...")
                self.simulate_step("[TEST] Opening encrypted partition...")
            
            self.simulate_step(f"[TEST] Formatting partitions with {filesystem} filesystem...")
            self.simulate_step("[TEST] Mounting root filesystem...")
            
            if uefi:
                self.simulate_step("[TEST] Setting up EFI boot partition...")
            else:
                self.simulate_step("[TEST] Setting up BIOS boot...")
            
            self.simulate_step("[TEST] Installing base system packages...")
            base_packages = ["base-system", "linux", "grub", "sudo", "vim"]
            for pkg in base_packages:
                self.simulate_step(f"  - Installing {pkg}...")
                time.sleep(0.5)
            
            self.simulate_step(f"[TEST] Configuring locale ({locale})...")
            
            self.simulate_step(f"[TEST] Setting hostname ({hostname})...")
            
            self.simulate_step(f"[TEST] Creating user '{username}'...")
            self.simulate_step("[TEST] Setting user password...")
            self.simulate_step("[TEST] Adding user to wheel group...")
            self.simulate_step("[TEST] Locking root account...")
            
            self.simulate_step(f"[TEST] Installing desktop environment ({desktop.upper()})...")
            self.simulate_step(f"[TEST] Installing sound system ({sound})...")
            self.simulate_step("[TEST] Installing graphics drivers...")
            
            self.simulate_step("[TEST] Configuring network...")
            self.simulate_step("[TEST] Enabling system services...")
            
            # Display manager setup
            dm_map = {
                "xfce": "lightdm",
                "gnome": "gdm", 
                "kde": "sddm",
                "mate": "lightdm",
                "cinnamon": "lightdm"
            }
            dm = dm_map.get(desktop, "lightdm")
            self.simulate_step(f"[TEST] Enabling display manager ({dm})...")
            
            self.simulate_step("[TEST] Installing bootloader...")
            if uefi:
                self.simulate_step("  - Installing GRUB for UEFI...")
            else:
                self.simulate_step("  - Installing GRUB for BIOS...")
            
            self.simulate_step("[TEST] Generating initramfs...")
            self.simulate_step("[TEST] Updating GRUB configuration...")
            
            self.simulate_step("[TEST] Installation simulation completed successfully!")
            
            return True
            
        except Exception as e:
            self.simulate_step(f"[TEST ERROR] Simulation failed: {str(e)}")
            return False
    
    def get_test_summary(self, config):
        """Generate a summary of what would be installed"""
        return [
            "=== INSTALLATION SIMULATION SUMMARY ===",
            "",
            f"Target Disk: {config.get('disk', '/dev/sda')}",
            f"Encryption: {'Yes' if config.get('encrypt', False) else 'No'}",
            f"Username: {config.get('username', 'void')}",
            f"Password: {'*' * len(config.get('password', 'void'))} (hidden)",
            f"Desktop: {config.get('desktop', 'xfce').upper()}",
            f"Sound System: {config.get('sound', 'pipewire')}",
            f"Locale: {config.get('locale', 'en_US.UTF-8')}",
            f"Hostname: {config.get('hostname', 'voidlinux')}",
            f"Boot Mode: {'UEFI' if os.path.exists('/sys/firmware/efi') else 'BIOS/Legacy'}",
            "",
            "*** THIS IS A SIMULATION - NO ACTUAL CHANGES MADE ***"
        ]

def create_test_config(**kwargs):
    """Create a test configuration dictionary"""
    return {
        'disk': kwargs.get('disk', '/dev/sda'),
        'encrypt': kwargs.get('encrypt', False),
        'username': kwargs.get('username', 'void'),
        'password': kwargs.get('password', 'testpass'),
        'desktop': kwargs.get('desktop', 'xfce'),
        'sound': kwargs.get('sound', 'pipewire'),
        'locale': kwargs.get('locale', 'en_US.UTF-8'),
        'hostname': kwargs.get('hostname', 'voidlinux')
    }

# Example usage
if __name__ == "__main__":
    print("Void Linux Installer - Test Mode")
    print("=" * 40)
    
    config = create_test_config(
        disk="/dev/sdb",
        encrypt=True,
        username="testuser",
        desktop="gnome"
    )
    
    installer = TestModeInstaller()
    print("\nConfiguration Summary:")
    for line in installer.get_test_summary(config):
        print(line)
    
    print("\nStarting simulation...")
    installer.simulate_installation(config)
