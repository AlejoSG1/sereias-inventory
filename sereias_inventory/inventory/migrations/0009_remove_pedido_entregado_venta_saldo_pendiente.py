# Generated by Django 5.1 on 2024-08-30 01:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0008_pedido_estado'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='pedido',
            name='entregado',
        ),
        migrations.AddField(
            model_name='venta',
            name='saldo_pendiente',
            field=models.DecimalField(decimal_places=2, default=0, editable=False, max_digits=10),
        ),
    ]
