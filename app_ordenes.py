import streamlit as st
import pandas as pd
from datetime import datetime
import sqlite3
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
import io

# ---------------------------------------------------------
# CONFIGURACIÓN DE LA BASE DE DATOS DE ÓRDENES DE COMPRA
# ---------------------------------------------------------
def inicializar_bd_oc():
    conn = sqlite3.connect("ordenes_compra_the_oranges.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ordenes_compra (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero_oc TEXT UNIQUE,
            fecha TEXT,
            proveedor TEXT,
            nit TEXT,
            contacto TEXT,
            fruta TEXT,
            calidad TEXT,
            cantidad_kg REAL,
            precio_unitario REAL,
            subtotal REAL,
            retencion REAL,
            total REAL,
            observaciones TEXT,
            estado TEXT
        )
    ''')
    conn.commit()
    return conn

conn_oc = inicializar_bd_oc()

# Configuración de página de Streamlit
st.set_page_config(
    page_title="Órdenes de Compra - The Oranges",
    layout="wide",
    page_icon="📋"
)

st.title("📋 Módulo de Órdenes de Compra - The Oranges")
st.write("Genera, consulta y descarga órdenes de compra oficiales para proveedores de fruta y pulpa.")

# Pestañas de navegación interna en la barra lateral
menu = st.sidebar.selectbox("Navegación", ["➕ Crear Nueva Orden de Compra", "🔍 Consultar Órdenes Registradas"])

# ---------------------------------------------------------
# PESTAÑA 1: CREAR NUEVA ORDEN DE COMPRA
# ---------------------------------------------------------
if menu == "➕ Crear Nueva Orden de Compra":
    st.subheader("1. Datos del Proveedor y de la OC")
    
    # Autogenerar número de OC consecutivo de forma segura
    try:
        cursor = conn_oc.cursor()
        cursor.execute("SELECT COUNT(*) FROM ordenes_compra")
        res = cursor.fetchone()
        consecutivo = (res[0] if res else 0) + 1
    except Exception:
        consecutivo = 1
        
    default_oc_num = f"OC-{datetime.now().strftime('%Y')}-{consecutivo:03d}"

    col1, col2, col3 = st.columns(3)
    with col1:
        numero_oc = st.text_input("Número de Orden de Compra", value=default_oc_num)
        proveedor = st.text_input("Nombre del Proveedor / Finca", placeholder="Ej: Finca El Paraíso S.A.S.")
    with col2:
        nit = st.text_input("NIT / Cédula del Proveedor", placeholder="Ej: 900.123.456-7")
        contacto = st.text_input("Teléfono o Contacto", placeholder="Ej: 3101234567")
    with col3:
        fecha_oc = st.date_input("Fecha de Emisión", value=datetime.now())
        estado = st.selectbox("Estado de la Orden", ["Emitida / Activa", "Aprobada", "Entregada / Cerrada", "Anulada"])

    st.divider()
    st.subheader("2. Detalle del Producto (Materia Prima)")

    col_p1, col_p2, col_p3 = st.columns(3)
    with col_p1:
        fruta = st.selectbox("Fruta / Insumo", ["MARACUYA", "MANGO", "MORA", "LULO", "GUANABANA", "LIMON", "NARANJA", "PIÑA", "PULPA DE FRUTA", "OTRA"])
        calidad = st.selectbox("Calidad / Presentación", ["Primera", "Segunda", "Industrial / Pulpa", "Estandar"])
    with col_p2:
        cantidad_kg = st.number_input("Cantidad Solicitada (Kg)", min_value=1.0, value=1000.0, step=50.0)
    with col_p3:
        precio_unitario = st.number_input("Precio Pactado por Kg ($)", min_value=0.0, value=2500.0, step=100.0)

    # Cálculos automáticos
    subtotal = cantidad_kg * precio_unitario
    aplicar_ret = st.checkbox("¿Aplicar retención en la fuente / deducciones?", value=False)
    retencion = subtotal * 0.035 if aplicar_ret else 0.0
    total = subtotal - retencion

    st.markdown("### Resumen Financiero")
    col_m1, col_m2, col_m3 = st.columns(3)
    with col_m1:
        st.metric("Subtotal", f"$ {subtotal:,.2f}")
    with col_m2:
        st.metric("Deducciones / Retención", f"$ {retencion:,.2f}")
    with col_m3:
        st.metric("TOTAL ESTIMADO ORDEN", f"$ {total:,.2f}")

    observaciones = st.text_area("Observaciones, condiciones de entrega o lugar de descargue", placeholder="Ej: Entrega en planta principal en horario de 7:00 AM a 2:00 PM.")

    st.divider()

    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        guardar_db = st.button("💾 Guardar Orden de Compra en la Nube / Base de Datos", use_container_width=True)
        if guardar_db:
            if not proveedor:
                st.error("⚠️ Por favor ingresa el nombre del proveedor antes de guardar.")
            else:
                try:
                    cursor.execute('''
                        INSERT INTO ordenes_compra (numero_oc, fecha, proveedor, nit, contacto, fruta, calidad, cantidad_kg, precio_unitario, subtotal, retencion, total, observaciones, estado)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (numero_oc, str(fecha_oc), proveedor, nit, contacto, fruta, calidad, cantidad_kg, precio_unitario, subtotal, retencion, total, observaciones, estado))
                    conn_oc.commit()
                    st.success(f"¡Orden de Compra {numero_oc} guardada exitosamente!")
                except sqlite3.IntegrityError:
                    st.error(f"⚠️ El número de orden {numero_oc} ya existe en la base de datos. Cambia el número de OC.")

    # ---------------------------------------------------------
    # GENERADOR DE PDF PARA LA ORDEN DE COMPRA
    # ---------------------------------------------------------
    def generar_pdf_oc():
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
        elements = []
        
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=16, textColor=colors.HexColor('#1B4D3E'), alignment=1, spaceAfter=4)
        subtitle_style = ParagraphStyle('SubtitleStyle', parent=styles['Normal'], fontSize=10, textColor=colors.HexColor('#555555'), alignment=1, spaceAfter=15)
        bold_text = ParagraphStyle('BoldText', parent=styles['Normal'], fontSize=9, fontName='Helvetica-Bold')
        regular_text = ParagraphStyle('RegularText', parent=styles['Normal'], fontSize=9)

        elements.append(Paragraph("THE ORANGES S.A.S.", title_style))
        elements.append(Paragraph("Comercialización y Transformación de Fruta — ORDEN DE COMPRA", subtitle_style))
        
        data_info = [
            [Paragraph("No. Orden:", bold_text), Paragraph(numero_oc, regular_text),
             Paragraph("Fecha Emisión:", bold_text), Paragraph(str(fecha_oc), regular_text)],
            [Paragraph("Proveedor:", bold_text), Paragraph(proveedor or 'N/A', regular_text),
             Paragraph("Estado:", bold_text), Paragraph(estado, regular_text)],
            [Paragraph("NIT / CC:", bold_text), Paragraph(nit or 'N/A', regular_text),
             Paragraph("Contacto:", bold_text), Paragraph(contacto or 'N/A', regular_text)]
        ]
        
        t_info = Table(data_info, colWidths=[90, 180, 90, 180])
        t_info.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F9F9F9')),
            ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#DCDCDC')),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('PADDING', (0,0), (-1,-1), 5),
        ]))
        elements.append(t_info)
        elements.append(Spacer(1, 15))
        
        table_data = [
            ["Descripción del Producto", "Calidad", "Cantidad (Kg)", "Vr. Unitario ($)", "Total ($)"],
            [f"Fruta: {fruta}", calidad, f"{cantidad_kg:,.2f}", f"$ {precio_unitario:,.2f}", f"$ {subtotal:,.2f}"]
        ]
        
        t_detalle = Table(table_data, colWidths=[140, 90, 80, 90, 140])
        t_detalle.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1B4D3E')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,0), 9),
            ('BOTTOMPADDING', (0,0), (-1,0), 6),
            ('BACKGROUND', (0,1), (-1,-1), colors.HexColor('#FCFCFC')),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E0E0E0')),
            ('PADDING', (0,0), (-1,-1), 6),
        ]))
        elements.append(t_detalle)
        
        totales_data = [
            ["Subtotal:", f"$ {subtotal:,.2f}"],
            ["Retenciones / Deducciones:", f"$ {retencion:,.2f}"],
            ["TOTAL A PAGAR:", f"$ {total:,.2f}"]
        ]
        t_totales = Table(totales_data, colWidths=[400, 140])
        t_totales.setStyle(TableStyle([
            ('ALIGN', (0,0), (-1,-1), 'RIGHT'),
            ('FONTNAME', (0,0), (-1,-2), 'Helvetica'),
            ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
            ('TEXTCOLOR', (0,-1), (-1,-1), colors.HexColor('#1B4D3E')),
            ('FONTSIZE', (0,0), (-1,-1), 9),
            ('PADDING', (0,0), (-1,-1), 4),
        ]))
        elements.append(Spacer(1, 10))
        elements.append(t_totales)
        
        elements.append(Spacer(1, 15))
        obs_data = [
            [Paragraph(f"<b>Observaciones e Instrucciones:</b><br/>{observaciones if observaciones else 'Ninguna'}", regular_text)]
        ]
        t_obs = Table(obs_data, colWidths=[540])
        t_obs.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F2F4F3')),
            ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#DCDCDC')),
            ('PADDING', (0,0), (-1,-1), 8),
        ]))
        elements.append(t_obs)
        
        elements.append(Spacer(1, 40))
        firma_data = [
            ["____________________________________", "____________________________________"],
            ["Elaborado / Compras The Oranges", "Aprobación Gerencia / Proveedor"]
        ]
        t_firmas = Table(firma_data, colWidths=[270, 270])
        t_firmas.setStyle(TableStyle([
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
            ('FONTSIZE', (0,0), (-1,-1), 9),
            ('TEXTCOLOR', (0,0), (-1,-1), colors.HexColor('#333333')),
        ]))
        elements.append(t_firmas)
        
        doc.build(elements)
        buffer.seek(0)
        return buffer.getvalue()

    pdf_bytes_oc = generar_pdf_oc()

    with col_btn2:
        st.download_button(
            label="📥 Descargar Orden de Compra en PDF",
            data=pdf_bytes_oc,
            file_name=f"Orden_Compra_{numero_oc}.pdf",
            mime="application/pdf",
            use_container_width=True
        )

# ---------------------------------------------------------
# PESTAÑA 2: CONSULTAR ÓRDENES REGISTRADAS
# ---------------------------------------------------------
elif menu == "🔍 Consultar Órdenes Registradas":
    st.subheader("Historial de Órdenes de Compra en la Nube / Base de Datos")
    
    try:
        df_ocs = pd.read_sql("SELECT numero_oc as 'No. OC', fecha as 'Fecha', proveedor as 'Proveedor', nit as 'NIT', fruta as 'Fruta', cantidad_kg as 'Cantidad (Kg)', total as 'Total ($)', estado as 'Estado' FROM ordenes_compra", conn_oc)
    except Exception:
        df_ocs = pd.DataFrame()
    
    if not df_ocs.empty:
        st.dataframe(df_ocs, use_container_width=True)
        st.info("💡 Cada orden generada queda almacenada permanentemente en el sistema.")
    else:
        st.warning("⚠️ No hay órdenes de compra registradas todavía. Ve a la pestaña 'Crear Nueva Orden de Compra' y guarda tu primera orden.")