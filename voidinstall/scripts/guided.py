"""
Guided installation script for Void Linux (voidinstall)
"""
from tui.main import VoidInstallTUI

def run():
    app = VoidInstallTUI()
    app.run()

if __name__ == "__main__":
    run()
