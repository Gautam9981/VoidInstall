"""
Guided installation script for Void Linux (voidinstall)
"""
from lib.installer import Installer

def run():
    installer = Installer()
    installer.run()

if __name__ == "__main__":
    run()
