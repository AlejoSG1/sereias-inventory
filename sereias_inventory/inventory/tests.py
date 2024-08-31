from django.test import TestCase
from .models import Producto, MovimientoInventario

class ProductoModelTest(TestCase):

    def test_creacion_producto_registro_cantidad_inicial(self):
        # Crear un producto con una cantidad inicial
        producto = Producto.objects.create(
            codigo="P001",
            categoria="Jabón Líquido",
            nombre="Jabón Líquido Bubble Gum",
            presentacion=250,
            unidad="ml",
            cantidad=10,  # Cantidad inicial
            costo_unitario=1.14,
            precio_unitario=3.20
        )

        # Verificar que la cantidad inicial no se duplica
        producto.refresh_from_db()  # Asegúrate de obtener el producto actualizado desde la base de datos
        self.assertEqual(producto.cantidad, 10)

        # Verificar que se haya creado un movimiento de inventario con la cantidad inicial
        movimientos = MovimientoInventario.objects.filter(producto=producto)
        self.assertEqual(movimientos.count(), 1)
        self.assertEqual(movimientos.first().concepto, 'cantidad_inicial')
        self.assertEqual(movimientos.first().cantidad, 10)

    def test_movimiento_entrada_no_duplica_cantidad(self):
        # Crear un producto con una cantidad inicial
        producto = Producto.objects.create(
            codigo="P002",
            categoria="Jabón Líquido",
            nombre="Jabón Líquido Lavender",
            presentacion=250,
            unidad="ml",
            cantidad=10,  # Cantidad inicial
            costo_unitario=1.14,
            precio_unitario=3.20
        )

        # Registrar un movimiento de entrada
        MovimientoInventario.objects.create(
            producto=producto,
            concepto='entrada',
            cantidad=5
        )

        # Verificar que la cantidad del producto se actualizó correctamente
        producto.refresh_from_db()
        self.assertEqual(producto.cantidad, 15)  # 10 inicial + 5 de entrada
