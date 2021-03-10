from extras.plugins import PluginConfig


class software_manager(PluginConfig):
    name = 'software_manager'
    verbose_name = 'Software Manager'
    description = 'Software Manager for Cisco IOS/IOS-XE devices'
    version = '0.1'
    author = 'Alexander Ignatov'
    author_email = 'ignatov.alx@gmail.com'
    required_settings = []
    default_settings = {}
    base_url = 'software_manager'
    caching_config = {}


config = software_manager
