from django.db.models.functions import TruncMonth
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.db.models import Q
from .models import Producto, MovimientoInventario, Cliente, Venta, DetalleVenta, Pedido, Pago
from .forms import ProductoForm, MovimientoInventarioForm, ClienteForm, VentaForm, DetalleVentaForm, PedidoForm, DetalleVentaFormSet, PagoForm
from django.http import JsonResponse
from django.forms import modelformset_factory
from django.contrib import messages
from django.db import transaction
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from django.db.models import Sum, Count, F, ExpressionWrapper, DecimalField
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle
from django.db import IntegrityError, transaction
from django.http import HttpResponse
from django.core.paginator import Paginator
from decimal import Decimal
import pandas as pd

def inventario_principal(request):
    productos = Producto.objects.all()

    # Calcular totales del inventario
    total_costo_inventario = sum(producto.total_costo for producto in productos)
    total_ingresos_esperados = sum(producto.total_precio for producto in productos)
    total_utilidad_esperada = sum(producto.utilidad_operativa for producto in productos)

    # Calcular número y monto de ventas
    numero_ventas = Venta.objects.count()
    monto_ventas = Venta.objects.aggregate(total=Sum('total'))['total'] or Decimal(0.00)

    # Calcular utilidad generada
    utilidad_generada = Venta.objects.aggregate(
        utilidad=Sum(F('detalles__subtotal') - F('detalles__producto__costo_unitario') * F('detalles__cantidad'))
    )['utilidad'] or Decimal(0.00)

    # Calcular monto de pagos pendientes
    monto_pagos_pendientes = 0
    ventas = Venta.objects.all()
    for venta in ventas:
        total_pagado = venta.pagos.aggregate(Sum('monto'))['monto__sum'] or Decimal(0.00)
        saldo_pendiente = venta.total - total_pagado
        monto_pagos_pendientes += saldo_pendiente

    # Calcular pedidos pendientes de entrega
    pedidos_pendientes = Pedido.objects.filter(estado__in=['pendiente', 'procesando', 'enviado']).count()

    context = {
        'productos': productos,
        'total_costo_inventario': total_costo_inventario,
        'total_ingresos_esperados': total_ingresos_esperados,
        'total_utilidad_esperada': total_utilidad_esperada,
        'numero_ventas': numero_ventas,
        'monto_ventas': monto_ventas,
        'utilidad_generada': utilidad_generada,
        'monto_pagos_pendientes': monto_pagos_pendientes,
        'pedidos_pendientes': pedidos_pendientes,
    }

    return render(request, 'inventory/inventario_principal.html', context)

def agregar_producto(request):
    if request.method == 'POST':
        form = ProductoForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('inventario_principal')
    else:
        form = ProductoForm()

    return render(request, 'inventory/agregar_producto.html', {'form': form})

def registrar_movimiento_inventario(request):
    if request.method == 'POST':
        form = MovimientoInventarioForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('inventario_principal')
    else:
        form = MovimientoInventarioForm()

    return render(request, 'inventory/registrar_movimiento.html', {'form': form})

def historial_movimientos(request):
    movimientos_list = MovimientoInventario.objects.all().order_by('-fecha')
    paginator = Paginator(movimientos_list, 10)  # 10 registros por página

    page_number = request.GET.get('page')
    movimientos = paginator.get_page(page_number)

    return render(request, 'inventory/historial_movimientos.html', {'movimientos': movimientos})



def reporte_inventario(request):
    productos = Producto.objects.all()
    total_costo = sum(producto.total_costo for producto in productos)
    total_venta = sum(producto.total_precio for producto in productos)
    total_utilidad = sum(producto.utilidad_operativa for producto in productos)

    context = {
        'productos': productos,
        'total_costo': total_costo,
        'total_venta': total_venta,
        'total_utilidad': total_utilidad,
    }

    return render(request, 'inventory/reporte_inventario.html', context)

def reporte_movimientos(request):
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')

    # Usamos select_related para evitar consultas adicionales al acceder al producto
    if fecha_inicio and fecha_fin:
        movimientos = MovimientoInventario.objects.filter(
            fecha__range=[fecha_inicio, fecha_fin]
        ).select_related('producto').order_by('-fecha')
    else:
        movimientos = MovimientoInventario.objects.select_related('producto').order_by('-fecha')

    return render(request, 'inventory/reporte_movimientos.html', {'movimientos': movimientos})


def reporte_bajo_inventario(request):
    umbral = request.GET.get('umbral', 5)  # Umbral por defecto de 5 unidades
    productos = Producto.objects.filter(cantidad__lt=umbral)

    return render(request, 'inventory/reporte_bajo_inventario.html', {'productos': productos, 'umbral': umbral})

def reporte_utilidad(request):
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')

    if fecha_inicio and fecha_fin:
        movimientos = MovimientoInventario.objects.filter(
            fecha__range=[fecha_inicio, fecha_fin],
            concepto='venta'
        )
    else:
        movimientos = MovimientoInventario.objects.filter(concepto='venta')

    # Realizar el cálculo de la utilidad total para cada movimiento
    for movimiento in movimientos:
        movimiento.utilidad_total = movimiento.producto.utilidad_unitaria * movimiento.cantidad

    total_utilidad = sum(movimiento.utilidad_total for movimiento in movimientos)

    return render(request, 'inventory/reporte_utilidad.html', {'total_utilidad': total_utilidad, 'movimientos': movimientos})

def lista_clientes(request):
    clientes_list = Cliente.objects.all().order_by('nombre')
    paginator = Paginator(clientes_list, 10)  # 10 registros por página

    page_number = request.GET.get('page')
    clientes = paginator.get_page(page_number)

    return render(request, 'inventory/lista_clientes.html', {'clientes': clientes})


def crear_cliente(request):
    if request.method == 'POST':
        form = ClienteForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('lista_clientes')
    else:
        form = ClienteForm()
    return render(request, 'inventory/crear_cliente.html', {'form': form})

def editar_cliente(request, cliente_id):
    cliente = get_object_or_404(Cliente, id=cliente_id)
    if request.method == 'POST':
        form = ClienteForm(request.POST, instance=cliente)
        if form.is_valid():
            form.save()
            return redirect('lista_clientes')
    else:
        form = ClienteForm(instance=cliente)
    return render(request, 'inventory/editar_cliente.html', {'form': form})

def eliminar_cliente(request, cliente_id):
    cliente = get_object_or_404(Cliente, id=cliente_id)
    if request.method == 'POST':
        cliente.delete()
        return redirect('lista_clientes')
    return render(request, 'inventory/eliminar_cliente.html', {'cliente': cliente})

def crear_venta(request):
    DetalleVentaFormSet = modelformset_factory(DetalleVenta, form=DetalleVentaForm, extra=1, can_delete=True)

    if request.method == 'POST':
        cliente_form = ClienteForm(request.POST)
        detalle_venta_formset = DetalleVentaFormSet(request.POST, queryset=DetalleVenta.objects.none())

        nombre = request.POST.get('nombre')
        identificacion = request.POST.get('identificacion')
        es_pedido = request.POST.get('es_pedido') == 'on'
        direccion_envio = request.POST.get('direccion_envio')
        fecha_envio = request.POST.get('fecha_envio')

        cliente = Cliente.objects.filter(Q(nombre=nombre) | Q(identificacion=identificacion)).first()

        if not cliente:
            if cliente_form.is_valid():
                cliente = cliente_form.save()
        else:
            cliente_form = ClienteForm(request.POST, instance=cliente)
            if cliente_form.is_valid():
                cliente = cliente_form.save()

        if cliente and detalle_venta_formset.is_valid():
            total = 0
            hay_error = False
            mensajes_error = []

            try:
                with transaction.atomic():
                    venta = Venta.objects.create(cliente=cliente)

                    for detalle_form in detalle_venta_formset:
                        detalle_venta = detalle_form.save(commit=False)
                        detalle_venta.venta = venta
                        producto = detalle_venta.producto

                        # Verificar si la cantidad es suficiente
                        if detalle_venta.cantidad > producto.cantidad:
                            mensajes_error.append(f"No hay suficiente stock para {producto.nombre}. Quedan {producto.cantidad} unidades.")
                            hay_error = True
                        else:
                            detalle_venta.precio_unitario = producto.precio_unitario
                            detalle_venta.subtotal = detalle_venta.cantidad * detalle_venta.precio_unitario
                            detalle_venta.save()

                            # Aquí ya no reducimos manualmente la cantidad de productos.
                            # La reducción se manejará en el modelo `MovimientoInventario`.

                            MovimientoInventario.objects.create(
                                producto=producto,
                                concepto='venta',
                                cantidad=detalle_venta.cantidad,
                                observaciones=f"Venta registrada para {venta.cliente.nombre}"
                            )

                            total += detalle_venta.subtotal

                    if hay_error:
                        raise IntegrityError("\n".join(mensajes_error))

                    venta.total = total
                    venta.es_pedido = es_pedido
                    venta.save()

                    if es_pedido:
                        Pedido.objects.create(
                            venta=venta,
                            direccion_envio=direccion_envio,
                            fecha_envio=fecha_envio
                        )

                    return redirect('detalle_venta', venta_id=venta.id)

            except IntegrityError as e:
                messages.error(request, str(e))

        else:
            messages.error(request, "Error al procesar la venta.")
    else:
        cliente_form = ClienteForm()
        detalle_venta_formset = DetalleVentaFormSet(queryset=DetalleVenta.objects.none())

    return render(request, 'inventory/crear_venta.html', {
        'cliente_form': cliente_form,
        'detalle_venta_formset': detalle_venta_formset,
    })


# def detalle_venta(request, venta_id):
#     venta = get_object_or_404(Venta, id=venta_id)
#     return render(request, 'inventory/detalle_venta.html', {'venta': venta})

def buscar_cliente(request):
    query = request.GET.get('q', '')
    resultados = Cliente.objects.filter(Q(nombre__icontains=query) | Q(email__icontains=query))

    data = [{
        'id': cliente.id,
        'nombre': cliente.nombre,
        'email': cliente.email,
        'telefono': cliente.telefono,
        'direccion': cliente.direccion,
    } for cliente in resultados]

    return JsonResponse(data, safe=False)

def obtener_precio_unitario(request):
    producto_id = request.GET.get('id')
    if producto_id:
        try:
            producto = Producto.objects.get(id=producto_id)
            data = {
                'precio_unitario': float(producto.precio_unitario),  # Asegúrate de convertir el Decimal a float
            }
            return JsonResponse(data)
        except Producto.DoesNotExist:
            return JsonResponse({'error': 'Producto no encontrado'}, status=404)
    return JsonResponse({'error': 'ID de producto no proporcionado'}, status=400)

def obtener_stock(request):
    producto_id = request.GET.get('id')
    if producto_id:
        try:
            producto = Producto.objects.get(id=producto_id)
            data = {
                'nombre': producto.nombre,
                'stock_disponible': producto.cantidad,
            }
            return JsonResponse(data)
        except Producto.DoesNotExist:
            return JsonResponse({'error': 'Producto no encontrado'}, status=404)
    return JsonResponse({'error': 'ID de producto no proporcionado'}, status=400)

def generar_factura_pdf(request, venta_id):
    venta = Venta.objects.select_related('cliente').prefetch_related('detalles__producto').get(id=venta_id)

    # Asegúrate de obtener también los detalles del pedido si es un pedido
    pedido = None
    if venta.es_pedido:
        try:
            pedido = venta.pedido
        except Pedido.DoesNotExist:
            pass  # En caso de que no exista un pedido

    detalles = venta.detalles.all()

    # Crear un objeto HttpResponse con el tipo de contenido PDF
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Factura_Venta_{venta_id}.pdf"'

    # Crear el documento PDF
    doc = SimpleDocTemplate(response, pagesize=letter)
    elements = []

    # Estilos
    styles = getSampleStyleSheet()

    # Título y Fecha
    elements.append(Paragraph(f"INVOICE", styles['Title']))
    elements.append(Paragraph(f"Date: {venta.fecha.strftime('%d/%m/%Y')}", styles['Normal']))

    # Información del Cliente
    cliente_info = f"""
    <strong>BILLING TO:</strong><br/>
    {venta.cliente.nombre}<br/>
    ID: {venta.cliente.identificacion}<br/>
    Email: {venta.cliente.email}<br/>
    Phone: {venta.cliente.telefono}<br/>
    Address: {venta.cliente.direccion}
    """
    elements.append(Paragraph(cliente_info, styles['Normal']))

    # Información del Pedido (si aplica)
    if pedido:
        pedido_info = f"""
        <br/><br/><strong>SHIPPING TO:</strong><br/>
        Address: {pedido.direccion_envio}<br/>
        Shipping Date: {pedido.fecha_envio.strftime('%d/%m/%Y') if pedido.fecha_envio else 'Pending'}<br/>
        Delivered: {'Yes' if pedido.entregado else 'No'}
        """
        elements.append(Paragraph(pedido_info, styles['Normal']))

    elements.append(Paragraph("<br/><br/>", styles['Normal']))

    # Tabla de productos
    data = [['SL', 'Item Description', 'Price', 'Qty', 'Total']]
    for i, detalle in enumerate(detalles, 1):
        data.append([str(i), f'{detalle.producto.nombre} {detalle.producto.presentacion} {detalle.producto.unidad}', f"${detalle.precio_unitario:.2f}", str(detalle.cantidad), f"${detalle.subtotal:.2f}"])

    # Subtotal y total
    data.append(['', '', '', 'Sub Total:', f"${venta.total:.2f}"])
    data.append(['', '', '', 'Tax:', '0.00'])
    data.append(['', '', '', 'Total:', f"${venta.total:.2f}"])

    # Crear la tabla
    table = Table(data, colWidths=[0.5*inch, 2.5*inch, 1.25*inch, 1*inch, 1.5*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    elements.append(table)

    # Firmas y condiciones
    elements.append(Paragraph("<br/><br/>", styles['Normal']))
    elements.append(Paragraph("Payment Info:", styles['Normal']))
    elements.append(Paragraph("Account Name: Sereias", styles['Normal']))
    elements.append(Paragraph("Bank Details: Bank Name, Account Number, etc.", styles['Normal']))
    elements.append(Paragraph("<br/><br/>", styles['Normal']))
    elements.append(Paragraph("Terms & Conditions:", styles['Normal']))
    elements.append(Paragraph("All sales are final. No refunds or exchanges.", styles['Normal']))
    elements.append(Paragraph("<br/><br/>", styles['Normal']))
    elements.append(Paragraph("Authorized Sign", styles['Normal']))

    # Build the PDF
    doc.build(elements)

    return response


def historial_ventas(request):
    # Filtros
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    cliente_id = request.GET.get('cliente')
    estado_pago = request.GET.get('estado_pago')

    # Consulta base
    ventas_list = Venta.objects.all().order_by('-fecha')

    # Aplicar filtros si están presentes
    if fecha_inicio and fecha_fin:
        ventas_list = ventas_list.filter(fecha__range=[fecha_inicio, fecha_fin])
    if cliente_id:
        ventas_list = ventas_list.filter(cliente_id=cliente_id)
    if estado_pago:
        ventas_list = ventas_list.filter(estado_pago=estado_pago)

    paginator = Paginator(ventas_list, 10)  # 10 registros por página

    page_number = request.GET.get('page')
    ventas = paginator.get_page(page_number)

    return render(request, 'inventory/historial_ventas.html', {
        'ventas': ventas,
        'clientes': Cliente.objects.all(),  # Para el filtro por cliente
        'estado_pago_choices': Venta._meta.get_field('estado_pago').choices,  # Para el filtro por estado de pago
    })



def detalle_venta(request, venta_id):
    # Usamos select_related para cargar la relación de cliente en la misma consulta
    venta = get_object_or_404(Venta.objects.select_related('cliente'), id=venta_id)

    # Usamos prefetch_related para cargar todas las relaciones DetalleVenta y Producto en la misma consulta
    detalles = venta.detalles.select_related('producto').all()

    return render(request, 'inventory/detalle_venta.html', {
        'venta': venta,
        'detalles': detalles,
    })

def lista_pedidos(request):
    estado = request.GET.get('estado')
    cliente_id = request.GET.get('cliente')
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')

    pedidos = Pedido.objects.select_related('venta__cliente').all()

    if estado:
        pedidos = pedidos.filter(estado=estado)
    if cliente_id:
        pedidos = pedidos.filter(venta__cliente_id=cliente_id)
    if fecha_inicio and fecha_fin:
        pedidos = pedidos.filter(venta__fecha__range=[fecha_inicio, fecha_fin])

    paginator = Paginator(pedidos, 10)  # Mostrar 10 pedidos por página
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'inventory/lista_pedidos.html', {
        'page_obj': page_obj,
        'clientes': Cliente.objects.all(),
        'estado_choices': Pedido.ESTADOS_PEDIDO,
    })

def detalle_pedido(request, pedido_id):
    pedido = get_object_or_404(Pedido, venta_id=pedido_id)

    if request.method == 'POST':
        nuevo_estado = request.POST.get('estado')
        if nuevo_estado in dict(Pedido.ESTADOS_PEDIDO).keys():
            pedido.estado = nuevo_estado
            if nuevo_estado == 'enviado':
                pedido.fecha_envio = timezone.now()
            pedido.save()
            messages.success(request, f"El estado del pedido {pedido_id} ha sido actualizado a {nuevo_estado}.")
        else:
            messages.error(request, "Estado inválido.")

    return render(request, 'inventory/detalle_pedido.html', {'pedido': pedido})

def actualizar_estado_pedido(request, pedido_id):
    pedido = get_object_or_404(Pedido, id=pedido_id)

    if request.method == 'POST':
        nuevo_estado = request.POST.get('estado')
        if nuevo_estado:
            pedido.estado = nuevo_estado
            pedido.save()
            messages.success(request, "Estado del pedido actualizado correctamente.")
        else:
            messages.error(request, "Por favor, selecciona un estado válido.")

    return redirect('detalle_pedido', pedido_id=pedido_id)



def registrar_pago(request, venta_id):
    venta = get_object_or_404(Venta, id=venta_id)

    if request.method == 'POST':
        monto = Decimal(request.POST.get('monto'))
        forma_pago = request.POST.get('forma_pago')
        fecha_pago = request.POST.get('fecha_pago')

        if monto > 0 and monto <= venta.saldo_pendiente:
            Pago.objects.create(venta=venta, monto=monto, forma_pago=forma_pago, fecha_pago=fecha_pago)

            # Después de registrar el pago, actualizar el estado de pago de la venta
            venta.actualizar_estado_pago()

            messages.success(request, 'El pago ha sido registrado correctamente.')
        else:
            messages.error(request, 'Monto inválido o superior al saldo pendiente.')

    return redirect('detalle_venta', venta_id=venta.id)

def lista_pagos(request):
    # Filtros
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    forma_pago = request.GET.get('forma_pago')

    # Consulta base
    pagos_list = Pago.objects.all().order_by('-fecha_pago')  # Ordenar del más reciente al más antiguo

    # Aplicar filtros si están presentes
    if fecha_inicio:
        pagos_list = pagos_list.filter(fecha_pago__gte=fecha_inicio)
    if fecha_fin:
        pagos_list = pagos_list.filter(fecha_pago__lte=fecha_fin)
    if forma_pago:
        pagos_list = pagos_list.filter(forma_pago=forma_pago)

    return render(request, 'inventory/lista_pagos.html', {
        'pagos': pagos_list,
        'forma_pago_choices': Pago._meta.get_field('forma_pago').choices,
    })

def generar_excel_pagos(request):
    # Filtros similares a los usados en la vista 'lista_pagos'
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    forma_pago = request.GET.get('forma_pago')

    pagos_list = Pago.objects.all().order_by('-fecha_pago')

    if fecha_inicio:
        pagos_list = pagos_list.filter(fecha_pago__gte=fecha_inicio)
    if fecha_fin:
        pagos_list = pagos_list.filter(fecha_pago__lte=fecha_fin)
    if forma_pago:
        pagos_list = pagos_list.filter(forma_pago=forma_pago)

def generar_excel_pagos(request):
    # Filtros similares a los usados en la vista 'lista_pagos'
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    forma_pago = request.GET.get('forma_pago')

    pagos_list = Pago.objects.all().order_by('-fecha_pago')

    if fecha_inicio:
        pagos_list = pagos_list.filter(fecha_pago__gte=fecha_inicio)
    if fecha_fin:
        pagos_list = pagos_list.filter(fecha_pago__lte=fecha_fin)
    if forma_pago:
        pagos_list = pagos_list.filter(forma_pago=forma_pago)

    # Crear el DataFrame
    data = []
    for pago in pagos_list:
        data.append({
            'Fecha de Pago': pago.fecha_pago.strftime('%d/%m/%Y'),
            'Venta ID': pago.venta.id,
            'Cliente': pago.venta.cliente.nombre,
            'Monto': pago.monto,
            'Forma de Pago': pago.get_forma_pago_display(),
        })
    df = pd.DataFrame(data)

    # Crear respuesta de Excel
    response = HttpResponse(content_type='application/vnd.ms-excel')
    response['Content-Disposition'] = 'attachment; filename="pagos.xlsx"'
    df.to_excel(response, index=False)

    return response

from django.db.models import Count, Sum, F, ExpressionWrapper, DecimalField

def dashboard_analisis_ventas(request):
    # Filtros de fecha
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')

    # Ventas por periodo
    ventas = Venta.objects.all()
    if fecha_inicio and fecha_fin:
        ventas = ventas.filter(fecha__range=[fecha_inicio, fecha_fin])

    total_ventas = ventas.aggregate(Sum('total'))['total__sum'] or 0
    numero_ventas = ventas.count()

    # Productos más vendidos
    productos_mas_vendidos = DetalleVenta.objects.values('producto__nombre').annotate(
        cantidad_total=Sum('cantidad')
    ).order_by('-cantidad_total')[:5]

    # Productos menos vendidos
    productos_menos_vendidos = DetalleVenta.objects.values('producto__nombre').annotate(
        cantidad_total=Sum('cantidad')
    ).order_by('cantidad_total')[:5]

    # Clientes recurrentes
    clientes_recurrentes = Cliente.objects.annotate(
        numero_compras=Count('venta')
    ).order_by('-numero_compras')[:5]

    # Clientes con más pagos pendientes
    clientes_mas_pagos_pendientes = Venta.objects.filter(estado_pago='pendiente').values(
        'cliente__nombre'
    ).annotate(saldo_pendiente=Sum('total') - Sum('pagos__monto')).order_by('-saldo_pendiente')[:5]

    # Utilidad generada por periodo
    utilidad_por_periodo = ventas.annotate(
        utilidad=Sum(F('detalles__subtotal') - F('detalles__producto__costo_unitario') * F('detalles__cantidad'))
    ).aggregate(Sum('utilidad'))['utilidad__sum'] or Decimal(0.00)

    context = {
        'total_ventas': total_ventas,
        'numero_ventas': numero_ventas,
        'productos_mas_vendidos': productos_mas_vendidos,
        'productos_menos_vendidos': productos_menos_vendidos,
        'clientes_recurrentes': clientes_recurrentes,
        'clientes_mas_pagos_pendientes': clientes_mas_pagos_pendientes,
        'utilidad_por_periodo': utilidad_por_periodo,
    }

    return render(request, 'inventory/dashboard_analisis_ventas.html', context)

def generar_proforma(request):
    return render(request, 'inventory/generar_proforma.html')

def generar_proforma_pdf(cliente, detalles, total):
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="Proforma.pdf"'

    doc = SimpleDocTemplate(response, pagesize=letter)
    elements = []

    styles = getSampleStyleSheet()

    # Información del Cliente
    cliente_info = f"""
    <strong>BILLING TO:</strong><br/>
    {cliente.nombre}<br/>
    ID: {cliente.identificacion}<br/>
    Email: {cliente.email}<br/>
    Phone: {cliente.telefono}<br/>
    Address: {cliente.direccion}
    """
    elements.append(Paragraph(cliente_info, styles['Normal']))

    elements.append(Paragraph("<br/><br/>", styles['Normal']))

    # Tabla de productos
    data = [['SL', 'Item Description', 'Price', 'Qty', 'Total']]
    for i, detalle in enumerate(detalles, 1):
        data.append([str(i), detalle['producto'], f"${detalle['precio_unitario']:.2f}", str(detalle['cantidad']), f"${detalle['subtotal']:.2f}"])

    # Subtotal y total
    data.append(['', '', '', 'Sub Total:', f"${total:.2f}"])
    data.append(['', '', '', 'Tax:', '0.00'])
    data.append(['', '', '', 'Total:', f"${total:.2f}"])

    # Crear la tabla
    table = Table(data, colWidths=[0.5 * inch, 2.5 * inch, 1.25 * inch, 1 * inch, 1.5 * inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    elements.append(table)

    doc.build(elements)

    return response

def generar_proforma(request):
    DetalleVentaFormSet = modelformset_factory(DetalleVenta, form=DetalleVentaForm, extra=1, can_delete=True)

    if request.method == 'POST':
        cliente_form = ClienteForm(request.POST)
        detalle_venta_formset = DetalleVentaFormSet(request.POST, queryset=DetalleVenta.objects.none())

        if cliente_form.is_valid() and detalle_venta_formset.is_valid():
            cliente = cliente_form.save(commit=False)  # No guardamos el cliente en la BD
            detalles = []
            total = 0

            for form in detalle_venta_formset:
                detalle = form.cleaned_data
                producto = detalle['producto']
                cantidad = detalle['cantidad']
                precio_unitario = producto.precio_unitario
                subtotal = cantidad * precio_unitario
                total += subtotal
                detalles.append({
                    'producto': producto.nombre,
                    'cantidad': cantidad,
                    'precio_unitario': precio_unitario,
                    'subtotal': subtotal
                })

            # Generar PDF
            return generar_proforma_pdf(cliente, detalles, total)

    else:
        cliente_form = ClienteForm()
        detalle_venta_formset = DetalleVentaFormSet(queryset=DetalleVenta.objects.none())

    return render(request, 'inventory/generar_proforma.html', {
        'cliente_form': cliente_form,
        'detalle_venta_formset': detalle_venta_formset,
    })