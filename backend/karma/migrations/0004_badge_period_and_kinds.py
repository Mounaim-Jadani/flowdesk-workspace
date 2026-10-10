from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('karma', '0003_karmaevent_source_key_badge')]

    operations = [
        migrations.AddField(
            model_name='badge', name='period_key',
            field=models.CharField(blank=True, max_length=16, null=True),
        ),
        migrations.AlterField(
            model_name='badge', name='kind',
            field=models.CharField(choices=[
                ('problem_solver', 'Résolveur de problèmes'),
                ('reliable_partner', 'Partenaire fiable'),
                ('mentor', 'Mentor'),
                ('pillar', 'Pilier de l’équipe'),
                ('top_contributor', 'Top Contributeur'),
            ], max_length=32),
        ),
        migrations.RemoveConstraint(model_name='badge', name='unique_karma_badge_per_user'),
        migrations.AddConstraint(
            model_name='badge',
            constraint=models.UniqueConstraint(fields=('user', 'kind', 'period_key'), name='unique_karma_badge_per_user_period'),
        ),
    ]
