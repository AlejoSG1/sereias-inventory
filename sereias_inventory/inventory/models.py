from django.db import models
from django.utils import timezone
from decimal import Decimal
from django.db.models import Sum

class Producto(models.Model):
    UNIDADES = [
        ('g', 'Gramos'),
        ('ml', 'Mililitros'),
        ('unidad', 'Unidades'),
    ]
    
    CATEGORIAS = [
        ('Jabón Líquido', 'Jabón Líquido'),
        ('Jabón Sólido', 'Jabón Sólido'),
        ('Exfoliante', 'Exfoliante'),
        ('Body Lotion', 'Body Lotion'),
        ('Chapstick', 'Chapstick'),
        ('Crema Facial', 'Crema Facial'),
        ('Manteca Corporal', 'Manteca Corporal'),
        ('Toallas', 'Toallas'),
        ('Especiarías', 'Especiarías'),
        ('Suculentas', 'Suculentas'),
        ('Velas', 'Velas'),
        ('Hinode-Otros', 'Hinode-Otros'),
    ]
    
    codigo = models.CharField(max_length=20, unique=True)
    categoria = models.CharField(max_length=50, choices=CATEGORIAS)
    nombre = models.CharField(max_length=100)
    presentacion = models.DecimalField(max_digits=10, decimal_places=2)
    unidad = models.CharField(max_length=10, choices=UNIDADES)
    cantidad = models.PositiveIntegerField()
    costo_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    total_costo = models.DecimalField(max_digits=10, decimal_places=2, editable=False)
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    total_precio = models.DecimalField(max_digits=10, decimal_places=2, editable=False)
    utilidad_operativa = models.DecimalField(max_digits=10, decimal_places=2, editable=False)
    utilidad_unitaria = models.DecimalField(max_digits=10, decimal_places=2, editable=False)
    rentabilidad = models.DecimalField(max_digits=5, decimal_places=2, editable=False)

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        self.total_costo = self.cantidad * self.costo_unitario
        self.total_precio = self.cantidad * self.precio_unitario
        self.utilidad_unitaria = self.precio_unitario - self.costo_unitario
        self.utilidad_operativa = self.utilidad_unitaria * self.cantidad
        self.rentabilidad = (self.utilidad_unitaria / self.costo_unitario) * 100
        super().save(*args, **kwargs)
        if is_new:
            # Crear un registro de movimiento para la cantidad inicial, pero no actualizar la cantidad
            MovimientoInventario.objects.create(
                producto=self,
                concepto='cantidad_inicial',
                cantidad=self.cantidad,
                observaciones='Cantidad inicial al crear el producto'
            )

    def __str__(self):
        return self.nombre

class MovimientoInventario(models.Model):
    CONCEPTOS = [
        ('entrada', 'Entrada'),
        ('salida', 'Salida'),
        ('cantidad_inicial', 'Cantidad Inicial'),
        ('venta', 'Venta'),
        ('devolución', 'Devolución'),
        ('ajuste', 'Ajuste'),
        ('otro', 'Otro'),
    ]
    
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    concepto = models.CharField(max_length=20, choices=CONCEPTOS)
    cantidad = models.PositiveIntegerField()
    fecha = models.DateTimeField(auto_now_add=True)
    observaciones = models.TextField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if self.concepto == 'entrada':
            self.producto.cantidad += self.cantidad
        elif self.concepto == 'salida':
            self.producto.cantidad -= self.cantidad
        elif self.concepto == 'venta':
            self.producto.cantidad -= self.cantidad
        elif self.concepto == 'devolución':
            self.producto.cantidad += self.cantidad
        elif self.concepto == 'ajuste':
            # Aquí podríamos manejar ajustes específicos
            pass
        # Evitar modificar la cantidad si es "cantidad_inicial"
        if self.concepto != 'cantidad_inicial':
            self.producto.save()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.concepto.capitalize()} de {self.cantidad} {self.producto.unidad} - {self.producto.nombre}"

class Cliente(models.Model):
    nombre = models.CharField(max_length=255)
    email = models.EmailField(blank=True, null=True)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    direccion = models.TextField(blank=True, null=True)
    identificacion = models.CharField(max_length=50, blank=True, null=True)  # Nuevo campo agregado
    creado = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nombre
    
class Venta(models.Model):
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE)
    fecha = models.DateTimeField(default=timezone.now)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    estado_pago = models.CharField(max_length=20, choices=[('pendiente', 'Pendiente'), ('pagado', 'Pagado')], default='pendiente')
    es_pedido = models.BooleanField(default=False)
    pedido_enviado = models.BooleanField(default=False)

    @property
    def saldo_pendiente(self):
        total_pagado = self.pagos.aggregate(Sum('monto'))['monto__sum'] or 0
        return self.total - total_pagado

    def actualizar_estado_pago(self):
        if self.saldo_pendiente <= 0:
            self.estado_pago = 'pagado'
        else:
            self.estado_pago = 'pendiente'
        self.save()

    def __str__(self):
        return f"Venta {self.id} - {self.cliente.nombre}"

    
class DetalleVenta(models.Model):
    venta = models.ForeignKey(Venta, related_name='detalles', on_delete=models.CASCADE)
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT)
    cantidad = models.PositiveIntegerField()
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)

    def save(self, *args, **kwargs):
        # Asegúrate de que el precio unitario esté asignado antes de calcular el subtotal
        if not self.precio_unitario:
            self.precio_unitario = self.producto.precio_unitario  # Asigna el precio del producto
        self.subtotal = self.cantidad * self.precio_unitario
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.cantidad} x {self.producto.nombre}"

class Pedido(models.Model):
    ESTADOS_PEDIDO = [
        ('pendiente', 'Pendiente'),
        ('procesando', 'Procesando'),
        ('enviado', 'Enviado'),
        ('entregado', 'Entregado'),
        ('cancelado', 'Cancelado'),
    ]

    venta = models.OneToOneField(Venta, on_delete=models.CASCADE, primary_key=True)
    direccion_envio = models.TextField()
    fecha_envio = models.DateTimeField(blank=True, null=True)
    estado = models.CharField(max_length=20, choices=ESTADOS_PEDIDO, default='pendiente')

    def __str__(self):
        return f"Pedido {self.venta.id} - {self.venta.cliente.nombre}"


class Pago(models.Model):
    FORMA_PAGO_CHOICES = [
        ('transferencia', 'Transferencia'),
        ('efectivo', 'Efectivo'),
        ('cheque', 'Cheque'),
        ('tarjeta', 'Tarjeta'),
    ]

    venta = models.ForeignKey(Venta, related_name='pagos', on_delete=models.CASCADE)
    fecha = models.DateTimeField(default=timezone.now)
    fecha_pago = models.DateField(default=timezone.now)
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    forma_pago = models.CharField(max_length=20, choices=FORMA_PAGO_CHOICES)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Después de guardar el pago, actualizamos el estado de la venta
        self.venta.actualizar_estado_pago()

    def __str__(self):
        return f"Pago de {self.monto} para Venta {self.venta.id} ({self.get_forma_pago_display()})"