import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('karma', '0002_rename_karma_karmae_user_id_0c1ca9_idx_karma_karma_user_id_a15047_idx_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='karmaevent',
            name='source_key',
            field=models.CharField(blank=True, max_length=200, null=True, unique=True),
        ),
        migrations.CreateModel(
            name='Badge',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('kind', models.CharField(choices=[('problem_solver', 'Résolveur de problèmes'), ('reliable_partner', 'Partenaire fiable')], max_length=32)),
                ('awarded_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='karma_badges', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-awarded_at'],
                'constraints': [models.UniqueConstraint(fields=('user', 'kind'), name='unique_karma_badge_per_user')],
            },
        ),
    ]
