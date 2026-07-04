from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('listings', '0004_add_return_pending_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='booking',
            name='actual_return_date',
            field=models.DateField(
                blank=True,
                null=True,
                help_text='Date the tool was physically returned (recorded when owner marks as returned).',
            ),
        ),
    ]
