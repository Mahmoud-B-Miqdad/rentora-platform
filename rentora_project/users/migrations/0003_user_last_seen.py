from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0002_alter_user_profile_image_emailverification'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='last_seen',
            field=models.DateTimeField(
                blank=True,
                null=True,
                help_text='Automatically updated on every page request via LastSeenMiddleware.',
            ),
        ),
    ]
