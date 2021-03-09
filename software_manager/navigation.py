from extras.plugins import PluginMenuItem, PluginMenuButton
from utilities.choices import ButtonColorChoices

menu_items = (
    PluginMenuItem(
        link='plugins:software_manager:software_list',
        link_text='Software Repository',
        permissions=['software_manager.view_softwareimage'],
    ),
    PluginMenuItem(
        link='plugins:software_manager:golden_image_list',
        link_text='Golden Images',
        permissions=['software_manager.view_goldenimage'],
    ),
    PluginMenuItem(
        link='plugins:software_manager:upgrade_device_list',
        link_text='Upgrade Devices',
        permissions=['software_manager.view_device'],
        buttons=(
            PluginMenuButton(
                link='plugins:software_manager:scheduled_task_list',
                title='Schedule tasks',
                icon_class='mdi mdi-update',
                color=ButtonColorChoices.BLUE,
                permissions=['software_manager.view_scheduledtask'],
            ),
        ),
    ),
)
