# Generated by Django 4.2.7 on 2023-12-27 11:12

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('transactions', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='MoneyTransferForm',
            fields=[
                ('transaction_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='transactions.transaction')),
            ],
            bases=('transactions.transaction',),
        ),
        migrations.AddField(
            model_name='transaction',
            name='transfer_acc_username',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
    ]
