import getpass
def setup_dhcpcd_live(interface=None):
    """
    Enable and start dhcpcd from the live environment (not chroot).
    """
    subprocess.run(["xbps-install", "-Sy", "dhcpcd"], check=True)
    subprocess.run(["ln", "-sf", "/etc/sv/dhcpcd", "/var/service/"], check=True)
    if interface:
        subprocess.run(["dhcpcd", interface], check=True)
    else:
        subprocess.run(["dhcpcd"], check=True)


def setup_wpa_supplicant_live_prompt(interface):
    """
    Prompt user for SSID and password (hidden), then install and start wpa_supplicant for Wi-Fi from the live environment.
    This is NOT for the chrooted system. After network is up, copy /etc/resolv.conf to /mnt/etc/resolv.conf.
    """
    ssid = input("Enter Wi-Fi SSID: ")
    psk = getpass.getpass("Enter Wi-Fi password: ")
    subprocess.run(["xbps-install", "-Sy", "wpa_supplicant"], check=True)
    subprocess.run(["ln", "-sf", "/etc/sv/wpa_supplicant", "/var/service/"], check=True)
    wpa_conf = f'/etc/wpa_supplicant/wpa_supplicant-{interface}.conf'
    wpa_content = f'''network={{\n    ssid=\"{ssid}\"\n    psk=\"{psk}\"\n}}\n'''
    with open(wpa_conf, 'w') as f:
        f.write(wpa_content)
    subprocess.run(["wpa_supplicant", "-B", "-i", interface, "-c", wpa_conf], check=True)
    print("After network is up, run: sudo cp /etc/resolv.conf /mnt/etc/resolv.conf")

def install_void_scanner_live():
    """
    Install Void Scanner from the live environment (if available).
    """
    subprocess.run(["xbps-install", "-Sy", "void-scanner"], check=False)
"""
Networking utilities for voidinstall
"""
import subprocess

def list_interfaces():
    result = subprocess.run(["ip", "link", "show"], capture_output=True, text=True)
    return result.stdout




def enable_dhcpcd_live(interface=None):
    """
    Enable and start dhcpcd from the live environment (not chroot).
    """
    subprocess.run(["xbps-install", "-Sy", "dhcpcd"], check=True)
    subprocess.run(["ln", "-sf", "/etc/sv/dhcpcd", "/var/service/"], check=True)
    if interface:
        subprocess.run(["dhcpcd", interface], check=True)
    else:
        subprocess.run(["dhcpcd"], check=True)


def enable_wpa_supplicant_live(interface, ssid, psk):
    """
    Install and enable wpa_supplicant for Wi-Fi connections in the live environment.
    """
    subprocess.run(["xbps-install", "-Sy", "wpa_supplicant"], check=True)
    subprocess.run(["ln", "-sf", "/etc/sv/wpa_supplicant", "/var/service/"], check=True)
    wpa_conf = f'/etc/wpa_supplicant/wpa_supplicant-{interface}.conf'
    wpa_content = f'''network={{\n    ssid=\"{ssid}\"\n    psk=\"{psk}\"\n}}\n'''
    with open(wpa_conf, 'w') as f:
        f.write(wpa_content)
    subprocess.run(["wpa_supplicant", "-B", "-i", interface, "-c", wpa_conf], check=True)


def install_void_scanner_live():
    """
    Install Void Scanner from the live environment (if available).
    """
    subprocess.run(["xbps-install", "-Sy", "void-scanner"], check=False)
