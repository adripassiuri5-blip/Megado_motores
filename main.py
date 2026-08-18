import datetime
import io
import pandas as pd
import streamlit as st
import gspread

# Configuración de la página web
st.set_page_config(
    page_title="Control de Megado de Motores",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Importaciones para generación de PDF
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

# Conexión con Google Sheets
@st.cache_resource
def conectar_gsheets():
    try:
        gc = gspread.service_account_from_dict(st.secrets["gcp_service_account"])
        sh = gc.open_by_url(st.secrets["connections"]["gsheets"]["spreadsheet"])
        return sh
    except Exception:
        return None

sh = conectar_gsheets()

# ==========================================
# 1. FUNCIONES DE LECTURA Y ESCRITURA
# ==========================================
def obtener_motores_df():
    try:
        ws = sh.worksheet("motores")
        data = ws.get_all_records()
        return pd.DataFrame(data)
    except Exception:
        return pd.DataFrame(columns=["id", "zona", "nombre", "ubicacion_tdf", "potencia_hp"])

def obtener_mediciones_df():
    try:
        ws = sh.worksheet("mediciones")
        data = ws.get_all_records()
        return pd.DataFrame(data)
    except Exception:
        return pd.DataFrame(columns=["id", "motor_id", "fecha", "res_l1", "res_l2", "res_l3", "voltaje_prueba", "tecnico", "estado", "observacion"])

def generar_pdf_bytes(df_mediciones, anio_filtro, semestre_filtro):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        rightMargin=20, leftMargin=20, topMargin=25, bottomMargin=25
    )

    elementos = []
    styles = getSampleStyleSheet()

    style_title = ParagraphStyle('TitleStyle', parent=styles['Title'], fontSize=16, leading=18, textColor=colors.HexColor('#1E3A8A'))
    style_sub = ParagraphStyle('SubTitleStyle', parent=styles['Normal'], fontSize=9, textColor=colors.HexColor('#475569'))
    style_cell = ParagraphStyle('Cell', parent=styles['Normal'], fontSize=8, leading=10)
    style_header = ParagraphStyle('HeaderCell', parent=styles['Normal'], fontSize=8, leading=10, textColor=colors.white, fontName="Helvetica-Bold")
    style_firma = ParagraphStyle('FirmaCell', parent=styles['Normal'], fontSize=9, leading=12, alignment=1)

    elementos.append(Paragraph("REPORTE TÉCNICO DE MEGADO Y RESISTENCIA DE AISLAMIENTO EN MOTORES", style_title))
    elementos.append(Spacer(1, 4))
    elementos.append(Paragraph(f"Filtro Aplicado: Año: <b>{anio_filtro}</b> | Semestre: <b>{semestre_filtro}</b> — Generado el: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", style_sub))
    elementos.append(Spacer(1, 12))

    headers = ["Fecha / Hora", "Zona", "Motor", "Ubicación", "L1 (MΩ)", "L2 (MΩ)", "L3 (MΩ)", "Volt (V)", "Técnico", "Estado", "Observación"]
    data = [[Paragraph(h, style_header) for h in headers]]

    for _, row in df_mediciones.iterrows():
        fila = [
            Paragraph(str(row.get('fecha', '')), style_cell),
            Paragraph(str(row.get('zona', '')), style_cell),
            Paragraph(str(row.get('nombre', '')), style_cell),
            Paragraph(str(row.get('ubicacion_tdf', '') or ''), style_cell),
            Paragraph(str(row.get('res_l1', '')), style_cell),
            Paragraph(str(row.get('res_l2', '')), style_cell),
            Paragraph(str(row.get('res_l3', '')), style_cell),
            Paragraph(str(row.get('voltaje_prueba', '')), style_cell),
            Paragraph(str(row.get('tecnico', '')), style_cell),
            Paragraph(str(row.get('estado', '')), style_cell),
            Paragraph(str(row.get('observacion', '') or ''), style_cell)
        ]
        data.append(fila)

    col_widths = [90, 65, 110, 80, 50, 50, 50, 50, 90, 60, 100]
    tabla_pdf = Table(data, colWidths=col_widths, repeatRows=1)

    ts = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1E3A8A')),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
    ])

    for i in range(1, len(data)):
        if i % 2 == 0:
            ts.add('BACKGROUND', (0, i), (-1, i), colors.HexColor('#F8FAFC'))

    tabla_pdf.setStyle(ts)
    elementos.append(tabla_pdf)

    elementos.append(Spacer(1, 45))

    firmas_data = [
        [
            Paragraph("___________________________________<br/><b>TÉCNICO RESPONSABLE</b><br/>Firma y Nombre", style_firma),
            "",
            Paragraph("___________________________________<br/><b>JEFE DE MANTENIMIENTO</b><br/>Firma y Nombre", style_firma)
        ]
    ]

    tabla_firmas = Table(firmas_data, colWidths=[300, 190, 300])
    tabla_firmas.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))

    elementos.append(tabla_firmas)
    doc.build(elementos)
    buffer.seek(0)
    return buffer

LISTA_TECNICOS = [
    "ADRIANA PASSIURI",
    "ANTONY LIRA",
    "ELTON BEGAZO",
    "MARCO ALVITEZ",
    "MILTON HERRERA"
]

# ==========================================
# 2. INTERFAZ EN STREAMLIT
# ==========================================
st.title("⚡ Sistema de Control de Megado de Motores")

pestaña1, pestaña2 = st.tabs(["📝 Registrar Datos", "📊 Historial de Mediciones"])

df_motores = obtener_motores_df()
df_mediciones = obtener_mediciones_df()

# --- PESTAÑA 1: REGISTRO ---
with pestaña1:
    st.header("1. Registro de Motor")
    with st.form("form_motor", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            zona = st.text_input("Zona *")
            ubicacion_tdf = st.text_input("Ubicación (TDF)")
        with col2:
            nombre = st.text_input("Nombre / Equipo *")
            potencia = st.number_input("Potencia (HP)", min_value=0.0, step=0.1)

        btn_guardar_motor = st.form_submit_button("Guardar Motor", use_container_width=True)
        if btn_guardar_motor:
            if not zona or not nombre:
                st.error("La Zona y el Nombre del motor son obligatorios.")
            else:
                try:
                    ws_m = sh.worksheet("motores")
                    nuevo_id = int(df_motores["id"].max() + 1) if not df_motores.empty and pd.notna(df_motores["id"].max()) else 1
                    ws_m.append_row([nuevo_id, zona, nombre, ubicacion_tdf, potencia if potencia > 0 else ""])
                    st.success(f"Motor '{nombre}' guardado exitosamente.")
                except Exception as e:
                    st.error(f"Error al guardar: {e}")

    st.divider()

    st.header("2. Nueva Medición de Megado")
    
    if df_motores.empty:
        st.warning("Primero debes registrar al menos un motor.")
    else:
        dict_motores = {f"{row['id']} - {row['zona']} ({row['nombre']})": row['id'] for _, row in df_motores.iterrows()}

        with st.form("form_medicion", clear_on_submit=True):
            col_m1, col_m2 = st.columns(2)
            with col_m1:
                fecha_sel = st.date_input("Fecha de Medición *", datetime.date.today())
                motor_sel_label = st.selectbox("Seleccionar Motor *", list(dict_motores.keys()))
            with col_m2:
                tecnico_sel = st.selectbox("Técnico Responsable *", LISTA_TECNICOS)
                estado_sel = st.selectbox("Estado del Motor *", ["NORMAL", "OBSERVADO", "CRÍTICO"])

            col_r1, col_r2, col_r3, col_v = st.columns(4)
            with col_r1:
                res_l1 = st.number_input("FASE 1 (MΩ) *", min_value=0.0, step=0.1)
            with col_r2:
                res_l2 = st.number_input("FASE 2 (MΩ) *", min_value=0.0, step=0.1)
            with col_r3:
                res_l3 = st.number_input("FASE 3 (MΩ) *", min_value=0.0, step=0.1)
            with col_v:
                voltaje_p = st.number_input("Voltaje Prueba (V) *", min_value=0.0, step=50.0)

            observacion = st.text_input("Observaciones")

            btn_guardar_med = st.form_submit_button("Guardar Medición", use_container_width=True)

            if btn_guardar_med:
                if res_l1 == 0 or res_l2 == 0 or res_l3 == 0 or voltaje_p == 0:
                    st.error("Por favor ingresa valores válidos de Resistencia y Voltaje.")
                else:
                    try:
                        ws_med = sh.worksheet("mediciones")
                        motor_id = dict_motores[motor_sel_label]
                        hora_actual = datetime.datetime.now().strftime("%H:%M:%S")
                        fecha_formateada = f"{fecha_sel.strftime('%Y-%m-%d')} {hora_actual}"

                        nuevo_med_id = int(df_mediciones["id"].max() + 1) if not df_mediciones.empty and pd.notna(df_mediciones["id"].max()) else 1

                        ws_med.append_row([nuevo_med_id, motor_id, fecha_formateada, res_l1, res_l2, res_l3, voltaje_p, tecnico_sel, estado_sel, observacion])
                        st.success(f"Medición guardada para el {fecha_sel}.")
                    except Exception as e:
                        st.error(f"Error al guardar medición: {e}")

# --- PESTAÑA 2: HISTORIAL Y FILTROS ---
with pestaña2:
    st.header("Historial y Filtros para Auditoría")

    if not df_mediciones.empty and not df_motores.empty:
        df_completo = df_mediciones.merge(df_motores, left_on="motor_id", right_on="id", suffixes=('', '_motor'))
        
        df_completo['fecha_dt'] = pd.to_datetime(df_completo['fecha'], errors='coerce')
        df_completo['anio'] = df_completo['fecha_dt'].dt.year.astype(str)

        anios_disponibles = sorted(list(df_completo['anio'].dropna().unique()), reverse=True)
        anios_disponibles.insert(0, "TODOS")

        f_col1, f_col2 = st.columns(2)
        with f_col1:
            filtro_anio = st.selectbox("Filtrar por Año", anios_disponibles)
        with f_col2:
            filtro_semestre = st.selectbox("Filtrar por Semestre", ["TODOS", "I Semestre (Ene - Jun)", "II Semestre (Jul - Dic)"])

        df_filtrado = df_completo.copy()

        if filtro_anio != "TODOS":
            df_filtrado = df_filtrado[df_filtrado['anio'] == filtro_anio]

        if filtro_semestre == "I Semestre (Ene - Jun)":
            df_filtrado = df_filtrado[df_filtrado['fecha_dt'].dt.month.between(1, 6)]
        elif filtro_semestre == "II Semestre (Jul - Dic)":
            df_filtrado = df_filtrado[df_filtrado['fecha_dt'].dt.month.between(7, 12)]

        columnas_mostrar = ["id", "fecha", "zona", "nombre", "ubicacion_tdf", "res_l1", "res_l2", "res_l3", "voltaje_prueba", "tecnico", "estado", "observacion"]
        df_mostrar = df_filtrado[columnas_mostrar]

        st.dataframe(df_mostrar, use_container_width=True)

        # Botón PDF
        pdf_data = generar_pdf_bytes(df_mostrar, filtro_anio, filtro_semestre)
        st.download_button(
            label="📄 Exportar PDF con Firmas",
            data=pdf_data,
            file_name=f"Reporte_Megado_Motores_{datetime.date.today()}.pdf",
            mime="application/pdf",
            use_container_width=True
        )
    else:
        st.info("Aún no hay mediciones o motores registrados.")
