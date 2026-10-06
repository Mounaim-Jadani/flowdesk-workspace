from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("chat", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="message",
            name="visible_from",
            field=models.DateTimeField(blank=True, db_index=True, null=True),
        ),
    ]
