"""
Locale configuration for voidinstall
"""
import subprocess
import os
from lib.sound import ensure_chroot_mounts

def configure_locale_chroot(locale, chroot_target="/mnt"):
    """
    Configure locale in the chrooted target system.
    """
    ensure_chroot_mounts(chroot_target)
    with open(os.path.join(chroot_target, "etc/locale.conf"), "w") as f:
        f.write(f"LANG={locale}\n")
    with open(os.path.join(chroot_target, "etc/locale.gen"), "w") as f:
        f.write(f"{locale} UTF-8\n")
    subprocess.run(["chroot", chroot_target, "xbps-reconfigure", "-f", "glibc-locales"], check=True)
