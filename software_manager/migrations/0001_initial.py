import django.core.validators
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    operations = [
        migrations.CreateModel(
            name='SoftwareImage',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False)),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('image', models.FileField(
                    unique=True, upload_to='software-images/', validators=[django.core.validators.FileExtensionValidator(allowed_extensions=['bin'])]
                )),
                ('md5sum', models.CharField(blank=True, max_length=36)),
                ('md5sum_calculated', models.CharField(blank=True, max_length=36)),
                ('version', models.CharField(blank=True, max_length=32)),
                ('filename', models.CharField(blank=True, max_length=255)),
            ],
            options={
                'ordering': ['-filename'],
            },
        ),
        migrations.CreateModel(
            name='ScheduledTask',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False)),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('task_type', models.CharField(default='upload', max_length=255)),
                ('job_id', models.CharField(blank=True, max_length=255)),
                ('status', models.CharField(default='unknown', max_length=255)),
                ('message', models.CharField(blank=True, max_length=511)),
                ('fail_reason', models.CharField(default='fail-unknown', max_length=255)),
                ('confirmed', models.BooleanField(default=False)),
                ('scheduled_time', models.DateTimeField(blank=True)),
                ('start_time', models.DateTimeField(null=True)),
                ('end_time', models.DateTimeField(null=True)),
                ('mw_duration', models.PositiveIntegerField(blank=True)),
                ('log', models.TextField(blank=True)),
                ('user', models.CharField(blank=True, max_length=255)),
                ('device', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='dcim.device')),
            ],
            options={
                'ordering': ['-scheduled_time', '-start_time', '-end_time', 'job_id'],
            },
        ),
        migrations.CreateModel(
            name='GoldenImage',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False)),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('pid', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='golden_image', to='dcim.devicetype')),
                ('sw', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='software_manager.softwareimage')),
            ],
            options={
                'ordering': ['pid'],
            },
        ),
    ]
