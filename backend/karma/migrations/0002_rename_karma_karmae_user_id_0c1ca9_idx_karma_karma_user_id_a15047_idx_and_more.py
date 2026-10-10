from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('karma', '0001_initial'),
    ]

    operations = [
        migrations.RenameIndex(
            model_name='karmaevent',
            new_name='karma_karma_user_id_a15047_idx',
            old_name='karma_karmae_user_id_0c1ca9_idx',
        ),
        migrations.RenameIndex(
            model_name='karmaevent',
            new_name='karma_karma_kind_324ac5_idx',
            old_name='karma_karmae_kind_2c38ec_idx',
        ),
    ]
