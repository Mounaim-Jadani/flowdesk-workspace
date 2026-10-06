# Generated manually to keep the digest app installable before Django is
# available in the local shell. Run makemigrations to verify in the project
# environment when dependencies are installed.

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("chat", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="RoomDigest",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("since", models.DateTimeField()),
                ("until", models.DateTimeField()),
                ("summary", models.TextField(blank=True, default="")),
                ("key_points", models.JSONField(default=list)),
                ("mentions", models.JSONField(default=list)),
                ("stats", models.JSONField(default=dict)),
                ("generated_at", models.DateTimeField(auto_now_add=True)),
                ("consumed_at", models.DateTimeField(blank=True, null=True)),
                (
                    "room",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="digests",
                        to="chat.chatroom",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="digests",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "unique_together": {("room", "user", "since")},
            },
        ),
    ]
