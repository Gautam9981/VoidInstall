"""
Menu utilities for voidinstall (placeholder for TUI integration)
"""
def select_option(prompt, options):
    print(prompt)
    for i, opt in enumerate(options, 1):
        print(f"{i}) {opt}")
    choice = input("Select option: ")
    return options[int(choice)-1] if choice.isdigit() and 1 <= int(choice) <= len(options) else options[0]
