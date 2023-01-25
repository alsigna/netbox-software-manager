from extras.plugins import PluginMenuItem

menu_items = (
    PluginMenuItem(
        link="plugins:software_manager:softwareimage_list",
        link_text="Software Repository",
        permissions=["software_manager.view_softwareimage"],
    ),
    PluginMenuItem(
        link="plugins:software_manager:goldenimage_list",
        link_text="Golden Images",
        permissions=["software_manager.view_goldenimage"],
    ),
    PluginMenuItem(
        link="plugins:software_manager:upgradedevice_list",
        link_text="Upgrade Devices",
        permissions=["software_manager.view_device"],
    ),
    PluginMenuItem(
        link="plugins:software_manager:scheduledtask_list",
        link_text="Scheduled Tasks",
        permissions=["software_manager.view_scheduledtask"],
    ),
)
