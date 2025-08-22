"""
Locale configuration for voidinstall
"""
import subprocess
import os
from lib.sound import ensure_chroot_mounts
from lib.sudo_utils import run_chroot_command

def configure_locale_chroot(locale, chroot_target="/mnt"):
    """
    Configure locale in the chrooted target system.
    """
    ensure_chroot_mounts(chroot_target)
    
    # Set locale.conf
    with open(os.path.join(chroot_target, "etc/locale.conf"), "w") as f:
        f.write(f"LANG={locale}\n")
    
    # Set locale.gen
    with open(os.path.join(chroot_target, "etc/locale.gen"), "w") as f:
        f.write(f"{locale} UTF-8\n")
    
    # Reconfigure locales
    run_chroot_command(chroot_target, ["xbps-reconfigure", "-f", "glibc-locales"])
    print(f"[INFO] Configured locale: {locale}")
