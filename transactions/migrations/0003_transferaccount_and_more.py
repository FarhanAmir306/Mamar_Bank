# Generated by Django 4.2.7 on 2023-12-27 12:45

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
        ('transactions', '0002_moneytransferform_transaction_transfer_acc_username'),
    ]

    operations = [
        migrations.CreateModel(
            name='TransferAccount',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.DecimalField(decimal_places=2, max_digits=12)),
                ('transfer_acc_username', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='transfer', to='accounts.userbankaccount')),
            ],
        ),
        migrations.RemoveField(
            model_name='transaction',
            name='transfer_acc_username',
        ),
        migrations.DeleteModel(
            name='MoneyTransferForm',
        ),
    ]
