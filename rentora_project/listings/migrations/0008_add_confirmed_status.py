from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('listings', '0007_conversation_message'),
    ]

    operations = [
        migrations.AlterField(
            model_name='booking',
            name='status',
            field=models.CharField(
                choices=[
                    ('pending',         'Pending'),
                    ('payment_pending', 'Payment Pending'),
                    ('approved',        'Approved'),
                    ('confirmed',       'Confirmed'),
                    ('rejected',        'Rejected'),
                    ('return_pending',  'Return Pending'),
                    ('completed',       'Completed'),
                    ('cancelled',       'Cancelled'),
                ],
                default='pending',
                help_text='Lifecycle state of this rental request.',
                max_length=20,
            ),
        ),
    ]
