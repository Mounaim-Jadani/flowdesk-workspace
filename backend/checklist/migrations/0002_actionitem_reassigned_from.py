from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('checklist', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='actionitem',
            name='reassigned_from',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='reassigned_action_items', to=settings.AUTH_USER_MODEL),
        ),
    ]
