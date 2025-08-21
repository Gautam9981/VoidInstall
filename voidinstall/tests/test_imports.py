"""
Example test stub for voidinstall (pytest compatible)
"""
def test_imports():
    import lib.disk.partition
    import lib.disk.filesystem
    import lib.crypt.luks
    import lib.networking.utils
    import lib.packages.xbps
    import lib.boot.grub
    import lib.authentication.user
    import lib.profile.loader
    import lib.plugins.loader
    assert True
