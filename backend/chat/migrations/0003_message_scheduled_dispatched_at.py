from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('chat', '0002_message_visible_from')]

    operations = [
        migrations.AddField(
            model_name='message',
            name='scheduled_dispatched_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
