# Generated by Django 5.1 on 2024-08-28 00:46

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='producto',
            name='codigo',
            field=models.CharField(default='', max_length=20, unique=True),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='producto',
            name='categoria',
            field=models.CharField(choices=[('Jabón Líquido', 'Jabón Líquido'), ('Jabón Sólido', 'Jabón Sólido'), ('Exfoliante', 'Exfoliante'), ('Body Lotion', 'Body Lotion'), ('Chapstick', 'Chapstick'), ('Crema Facial', 'Crema Facial'), ('Manteca Corporal', 'Manteca Corporal'), ('Toallas', 'Toallas'), ('Especiarías', 'Especiarías'), ('Suculentas', 'Suculentas'), ('Velas', 'Velas'), ('Hinode-Otros', 'Hinode-Otros')], max_length=50),
        ),
    ]
