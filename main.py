import datetime
import io
import sqlite3
import pandas as pd
import streamlit as st

# Importaciones para generación de PDF
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

# Configuración de la página web
st.set_page_config(
    page_title="Control de Megado de Motores",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================
# 1. BASE DE DATOS
# ==========================================
def iniciar_db():
    conexion = sqlite3.connect("megado_motores.db")
    cursor = conexion.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS motores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            zona TEXT NOT NULL,
            nombre TEXT NOT NULL,
            ubicacion_tdf TEXT,
            potencia_hp REAL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tecnicos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT UNIQUE NOT NULL
        )
    """)

    cursor.execute("SELECT COUNT(*) FROM tecnicos")
    if cursor.fetchone()[0] == 0:
        compañeros = [
            ("ADRIANA PASSIURI",),
            ("ANTONY LIRA",),
            ("ELTON BEGAZO",),
            ("MARCO ALVITEZ",),
            ("MILTON HERRERA",),
        ]
        cursor.executemany("INSERT INTO tecnicos (nombre) VALUES (?)", compañeros)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS mediciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            motor_id INTEGER,
            fecha TEXT NOT NULL,
            res_l1 REAL NOT NULL,
            res_l2 REAL NOT NULL,
            res_l3 REAL NOT NULL,
            voltaje_prueba REAL NOT NULL,
            tecnico TEXT NOT NULL,
            estado TEXT NOT NULL DEFAULT 'NORMAL',
            observacion TEXT,
            FOREIGN KEY (motor_id) REFERENCES motores (id)
        )
    """)

    conexion.commit()
    conexion.close()

iniciar_db()

# ==========================================
# 2. FUNCIONES DE APOYO Y CONSULTAS
# ==========================================
def obtener_motores():
    conexion = sqlite3.connect("megado_motores.db")
    cursor = conexion.cursor()
    cursor.execute("SELECT id, zona, nombre FROM motores ORDER BY id ASC")
    motores = cursor.fetchall()
    conexion.close()
    return {f"{m[0]} - {m[1]} ({m[2]})": m[0] for m in motores}

def obtener_tecnicos():
    conexion = sqlite3.connect("megado_motores.db")
    cursor = conexion.cursor()
    cursor.execute("SELECT nombre FROM tecnicos ORDER BY nombre ASC")
    tecnicos = cursor.fetchall()
    conexion.close()
    return [t[0] for t in tecnicos]

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
            Paragraph(str(row['fecha']), style_cell),
            Paragraph(str(row['zona']), style_cell),
            Paragraph(str(row['nombre']), style_cell),
            Paragraph(str(row['ubicacion_tdf'] or ''), style_cell),
            Paragraph(str(row['res_l1']), style_cell),
            Paragraph(str(row['res_l2']), style_cell),
            Paragraph(str(row['res_l3']), style_cell),
            Paragraph(str(row['voltaje_prueba']), style_cell),
            Paragraph(str(row['tecnico']), style_cell),
            Paragraph(str(row['estado']), style_cell),
            Paragraph(str(row['observacion'] or ''), style_cell)
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

# ==========================================
# 3. INTERFAZ EN STREAMLIT
# ==========================================
st.title("⚡ Sistema de Control de Megado de Motores Trifásicos")

pestaña1, pestaña2 = st.tabs(["📝 Registrar Datos", "📊 Historial de Mediciones"])

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
                    conexion = sqlite3.connect("megado_motores.db")
                    cursor = conexion.cursor()
                    cursor.execute("""
                        INSERT INTO motores (zona, nombre, ubicacion_tdf, potencia_hp)
                        VALUES (?, ?, ?, ?)
                    """, (zona, nombre, ubicacion_tdf, potencia if potencia > 0 else None))
                    conexion.commit()
                    conexion.close()
                    st.success(f"Motor '{nombre}' guardado correctamente.")
                except Exception as e:
                    st.error(f"Error al guardar motor: {e}")

    st.divider()

    # Agregar nuevo técnico
    with st.expander("➕ Agregar Nuevo Técnico Responsable"):
        with st.form("form_nuevo_tecnico", clear_on_submit=True):
            nuevo_tec = st.text_input("Nombre del Técnico")
            btn_add_tec = st.form_submit_button("Agregar Técnico")
            if btn_add_tec:
                if nuevo_tec.strip():
                    try:
                        conexion = sqlite3.connect("megado_motores.db")
                        cursor = conexion.cursor()
                        cursor.execute("INSERT INTO tecnicos (nombre) VALUES (?)", (nuevo_tec.strip().upper(),))
                        conexion.commit()
                        conexion.close()
                        st.success(f"Técnico '{nuevo_tec.upper()}' agregado.")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("Este técnico ya existe.")
                else:
                    st.warning("Ingresa un nombre válido.")

    st.header("2. Nueva Medición de Megado (Aislamiento por Fase)")
    
    dict_motores = obtener_motores()
    lista_tecnicos = obtener_tecnicos()

    if not dict_motores:
        st.warning("Primero debes registrar al menos un motor.")
    else:
        with st.form("form_medicion", clear_on_submit=True):
            col_m1, col_m2 = st.columns(2)
            with col_m1:
                fecha_sel = st.date_input("Fecha de Medición *", datetime.date.today())
                motor_sel_label = st.selectbox("Seleccionar Motor *", list(dict_motores.keys()))
            with col_m2:
                tecnico_sel = st.selectbox("Técnico Responsable *", lista_tecnicos)
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
                        motor_id = dict_motores[motor_sel_label]
                        hora_actual = datetime.datetime.now().strftime("%H:%M:%S")
                        fecha_formateada = f"{fecha_sel.strftime('%Y-%m-%d')} {hora_actual}"

                        conexion = sqlite3.connect("megado_motores.db")
                        cursor = conexion.cursor()
                        cursor.execute("""
                            INSERT INTO mediciones (motor_id, fecha, res_l1, res_l2, res_l3, voltaje_prueba, tecnico, estado, observacion)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (motor_id, fecha_formateada, res_l1, res_l2, res_l3, voltaje_p, tecnico_sel, estado_sel, observacion))
                        conexion.commit()
                        conexion.close()
                        st.success(f"Medición registrada correctamente para {fecha_sel}.")
                    except Exception as e:
                        st.error(f"Error al guardar medición: {e}")

# --- PESTAÑA 2: HISTORIAL Y ACCIONES ---
with pestaña2:
    st.header("Historial y Filtros para Auditoría")

    conexion = sqlite3.connect("megado_motores.db")
    cursor = conexion.cursor()
    cursor.execute("SELECT DISTINCT strftime('%Y', fecha) FROM mediciones WHERE fecha IS NOT NULL AND fecha != '' ORDER BY fecha DESC")
    anios_db = [row[0] for row in cursor.fetchall() if row[0] is not None]
    conexion.close()

    anio_actual = str(datetime.datetime.now().year)
    if anio_actual not in anios_db:
        anios_db.insert(0, anio_actual)
    anios_db.insert(0, "TODOS")

    f_col1, f_col2 = st.columns(2)
    with f_col1:
        filtro_anio = st.selectbox("Filtrar por Año", anios_db)
    with f_col2:
        filtro_semestre = st.selectbox("Filtrar por Semestre", ["TODOS", "I Semestre (Ene - Jun)", "II Semestre (Jul - Dic)"])

    # Consulta dinámica
    conexion = sqlite3.connect("megado_motores.db")
    query = """
        SELECT m.id, m.fecha, mot.zona, mot.nombre, mot.ubicacion_tdf, m.res_l1, m.res_l2, m.res_l3, m.voltaje_prueba, m.tecnico, m.estado, m.observacion
        FROM mediciones m
        JOIN motores mot ON m.motor_id = mot.id
        WHERE 1=1
    """
    params = []

    if filtro_anio != "TODOS":
        query += " AND strftime('%Y', m.fecha) = ?"
        params.append(filtro_anio)

    if filtro_semestre == "I Semestre (Ene - Jun)":
        query += " AND strftime('%m', m.fecha) BETWEEN '01' AND '06'"
    elif filtro_semestre == "II Semestre (Jul - Dic)":
        query += " AND strftime('%m', m.fecha) BETWEEN '07' AND '12'"

    query += " ORDER BY m.fecha DESC"

    df = pd.read_sql_query(query, conexion, params=params)
    conexion.close()

    if not df.empty:
        st.dataframe(df, use_container_width=True)

        # Botón PDF
        pdf_data = generar_pdf_bytes(df, filtro_anio, filtro_semestre)
        st.download_button(
            label="📄 Exportar PDF con Firmas",
            data=pdf_data,
            file_name=f"Reporte_Megado_Motores_{datetime.date.today()}.pdf",
            mime="application/pdf",
            use_container_width=True
        )

        st.divider()

        # Operaciones Editar y Eliminar
        st.subheader("🛠️ Administrar Medición")
        lista_ids = df['id'].tolist()
        id_seleccionado = st.selectbox("Selecciona el ID de la medición a Modificar o Eliminar", lista_ids)

        col_act1, col_act2 = st.columns(2)

        with col_act1:
            with st.expander("✏️ Editar Medición Seleccionada"):
                registro_actual = df[df['id'] == id_seleccionado].iloc[0]
                
                with st.form("form_editar"):
                    e_r1 = st.number_input("Fase 1 (MΩ)", value=float(registro_actual['res_l1']))
                    e_r2 = st.number_input("Fase 2 (MΩ)", value=float(registro_actual['res_l2']))
                    e_r3 = st.number_input("Fase 3 (MΩ)", value=float(registro_actual['res_l3']))
                    e_volt = st.number_input("Voltaje (V)", value=float(registro_actual['voltaje_prueba']))
                    e_tec = st.selectbox("Técnico", obtener_tecnicos(), index=obtener_tecnicos().index(registro_actual['tecnico']) if registro_actual['tecnico'] in obtener_tecnicos() else 0)
                    e_est = st.selectbox("Estado", ["NORMAL", "OBSERVADO", "CRÍTICO"], index=["NORMAL", "OBSERVADO", "CRÍTICO"].index(registro_actual['estado']))
                    e_obs = st.text_input("Observación", value=str(registro_actual['observacion'] or ''))

                    if st.form_submit_button("Guardar Cambios"):
                        conexion = sqlite3.connect("megado_motores.db")
                        cursor = conexion.cursor()
                        cursor.execute("""
                            UPDATE mediciones 
                            SET res_l1=?, res_l2=?, res_l3=?, voltaje_prueba=?, tecnico=?, estado=?, observacion=?
                            WHERE id=?
                        """, (e_r1, e_r2, e_r3, e_volt, e_tec, e_est, e_obs, id_seleccionado))
                        conexion.commit()
                        conexion.close()
                        st.success("Medición actualizada correctamente.")
                        st.rerun()

        with col_act2:
            with st.expander("🗑️ Eliminar Medición"):
                st.warning(f"¿Estás seguro de eliminar el registro ID #{id_seleccionado}?")
                if st.button("Confirmar Eliminación", type="primary"):
                    conexion = sqlite3.connect("megado_motores.db")
                    cursor = conexion.cursor()
                    cursor.execute("DELETE FROM mediciones WHERE id=?", (id_seleccionado,))
                    conexion.commit()
                    conexion.close()
                    st.success("Registro eliminado.")
                    st.rerun()
    else:
        st.info("No se encontraron registros con los filtros seleccionados.")
