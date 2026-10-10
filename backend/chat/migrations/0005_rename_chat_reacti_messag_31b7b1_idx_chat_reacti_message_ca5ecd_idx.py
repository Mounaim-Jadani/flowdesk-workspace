from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [('chat', '0004_reaction')]

    operations = [
        migrations.RenameIndex(
            model_name='reaction',
            new_name='chat_reacti_message_ca5ecd_idx',
            old_name='chat_reacti_messag_31b7b1_idx',
        ),
    ]
