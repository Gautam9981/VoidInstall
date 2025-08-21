"""
Networking utilities for voidinstall - handles copying network config to installed system
"""
import subprocess
import os
import shutil
from lib.sound import ensure_chroot_mounts

def check_network_connection():
    """
    Check if we have a working network connection (like archinstall assumes)
    """
    try:
        result = subprocess.run(["ping", "-c", "1", "voidlinux.org"], 
                              capture_output=True, timeout=5)
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        return False

def copy_resolv_conf(target="/mnt"):
    """
    Copy DNS configuration from live environment to installed system
    """
    if os.path.exists("/etc/resolv.conf"):
        shutil.copy2("/etc/resolv.conf", os.path.join(target, "etc/resolv.conf"))

def detect_network_manager():
    """
    Detect which network management tools are available in live environment
    """
    managers = {}
    
    # Check for NetworkManager
    if shutil.which("nmcli"):
        managers["networkmanager"] = True
    
    # Check for dhcpcd
    if os.path.exists("/var/service/dhcpcd") or shutil.which("dhcpcd"):
        managers["dhcpcd"] = True
    
    # Check for wpa_supplicant
    if os.path.exists("/var/service/wpa_supplicant") or shutil.which("wpa_supplicant"):
        managers["wpa_supplicant"] = True
    
    return managers

def install_network_manager_chroot(target="/mnt", desktop_env=None):
    """
    Install and configure appropriate network manager for the target system
    Based on desktop environment (like archinstall does)
    """
    ensure_chroot_mounts(target)
    
    if desktop_env in ["gnome", "kde5", "cinnamon"]:
        # Install NetworkManager for modern DEs
        subprocess.run(["chroot", target, "xbps-install", "-Sy", "NetworkManager"], check=True)
        subprocess.run(["chroot", target, "ln", "-sf", "/etc/sv/NetworkManager", "/var/service/"], check=True)
        
        # Disable dhcpcd if it exists to avoid conflicts
        subprocess.run(["chroot", target, "rm", "-f", "/var/service/dhcpcd"], check=False)
        
    elif desktop_env in ["xfce4", "mate"] or desktop_env is None:
        # Install dhcpcd for lightweight DEs or headless systems
        subprocess.run(["chroot", target, "xbps-install", "-Sy", "dhcpcd"], check=True)
        subprocess.run(["chroot", target, "ln", "-sf", "/etc/sv/dhcpcd", "/var/service/"], check=True)
        
        # Also install wpa_supplicant for WiFi support
        subprocess.run(["chroot", target, "xbps-install", "-Sy", "wpa_supplicant"], check=True)

def copy_network_config(target="/mnt", desktop_env=None):
    """
    Copy network configuration from live environment to installed system
    This is the main function that should be called during installation
    """
    # Always copy DNS configuration
    copy_resolv_conf(target)
    
    # Install appropriate network manager
    install_network_manager_chroot(target, desktop_env)
    
    # Copy NetworkManager configuration if it exists and we're using NM
    if desktop_env in ["gnome", "kde5", "cinnamon"]:
        nm_dir = "/etc/NetworkManager/system-connections"
        target_nm_dir = os.path.join(target, "etc/NetworkManager/system-connections")
        
        if os.path.exists(nm_dir) and os.listdir(nm_dir):
            os.makedirs(target_nm_dir, exist_ok=True)
            for config_file in os.listdir(nm_dir):
                src = os.path.join(nm_dir, config_file)
                dst = os.path.join(target_nm_dir, config_file)
                if os.path.isfile(src):
                    shutil.copy2(src, dst)
                    # Set correct permissions
                    os.chmod(dst, 0o600)
    
    # Copy wpa_supplicant configuration if it exists
    wpa_conf_dir = "/etc/wpa_supplicant"
    target_wpa_dir = os.path.join(target, "etc/wpa_supplicant")
    
    if os.path.exists(wpa_conf_dir):
        os.makedirs(target_wpa_dir, exist_ok=True)
        for conf_file in os.listdir(wpa_conf_dir):
            if conf_file.endswith(".conf"):
                src = os.path.join(wpa_conf_dir, conf_file)
                dst = os.path.join(target_wpa_dir, conf_file)
                if os.path.isfile(src):
                    shutil.copy2(src, dst)
                    os.chmod(dst, 0o600)

def list_interfaces():
    """
    List available network interfaces
    """
    result = subprocess.run(["ip", "link", "show"], capture_output=True, text=True)
    return result.stdout
