# Generated by Django 5.1 on 2024-08-28 00:35

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Producto',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('categoria', models.CharField(choices=[('Jabón Líquido', 'Jabón Líquido')], max_length=50)),
                ('nombre', models.CharField(max_length=100)),
                ('presentacion', models.DecimalField(decimal_places=2, max_digits=10)),
                ('unidad', models.CharField(max_length=10)),
                ('cantidad', models.PositiveIntegerField()),
                ('costo_unitario', models.DecimalField(decimal_places=2, max_digits=10)),
                ('total_costo', models.DecimalField(decimal_places=2, editable=False, max_digits=10)),
                ('precio_unitario', models.DecimalField(decimal_places=2, max_digits=10)),
                ('total_precio', models.DecimalField(decimal_places=2, editable=False, max_digits=10)),
                ('utilidad_operativa', models.DecimalField(decimal_places=2, editable=False, max_digits=10)),
                ('utilidad_unitaria', models.DecimalField(decimal_places=2, editable=False, max_digits=10)),
                ('rentabilidad', models.DecimalField(decimal_places=2, editable=False, max_digits=5)),
            ],
        ),
    ]
