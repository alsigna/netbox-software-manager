from extras.plugins import PluginConfig


class SoftwareManager(PluginConfig):
    name = "software_manager"
    verbose_name = "Software Manager"
    description = "Software Manager for Cisco IOS/IOS-XE devices"
    version = "0.0.3"
    author = "Alexander Ignatov"
    author_email = "ignatov.alx@gmail.com"
    required_settings = []
    default_settings = {}
    base_url = "software-manager"
    caching_config = {}


config = SoftwareManager
