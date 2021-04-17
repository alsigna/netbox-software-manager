from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("software_manager", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="scheduledtask",
            name="transfer_method",
            field=models.CharField(default="ftp", max_length=8),
        ),
    ]
