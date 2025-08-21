"""
Void Linux installer - guided, templates, etc.
"""
import importlib
import os
import sys
import traceback

# Placeholder for argument handler (to be expanded)
def print_help():
    print("Usage: voidinstall [--help] [--script SCRIPT]")
    print("Available scripts: guided (default)")


def main():
    if '--help' in sys.argv or '-h' in sys.argv:
        print_help()
        return 0

    if os.name != 'nt' and hasattr(os, 'geteuid') and os.geteuid() != 0:
        print('voidinstall requires root privileges to run.')
        return 1

    # Default script
    script = 'guided'
    for i, arg in enumerate(sys.argv):
        if arg == '--script' and i + 1 < len(sys.argv):
            script = sys.argv[i + 1]

    mod_name = f'scripts.{script}'
    try:
        importlib.import_module(mod_name)
    except Exception as e:
        print(f'Error running script {script}: {e}')
        traceback.print_exc()
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())
