import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# Importaciones para generación de PDF
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

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

LISTA_TODOS_LOS_MOTORES = []

# ==========================================
# 2. FUNCIONES DE LÓGICA Y REGISTRO
# ==========================================
def cargar_motores_combobox():
    global LISTA_TODOS_LOS_MOTORES
    conexion = sqlite3.connect("megado_motores.db")
    cursor = conexion.cursor()
    cursor.execute("SELECT id, zona, nombre FROM motores ORDER BY id ASC")
    motores = cursor.fetchall()
    conexion.close()

    LISTA_TODOS_LOS_MOTORES = [f"{m[0]} - {m[1]} ({m[2]})" for m in motores]
    combo_motor["values"] = LISTA_TODOS_LOS_MOTORES

def filtrar_motores_al_escribir(event):
    if event.keysym in ["Up", "Down", "Return", "Right", "Left", "Escape", "Tab", "Shift_L", "Shift_R"]:
        return

    texto_ingresado = combo_motor.get().strip().lower()

    if not texto_ingresado:
        combo_motor["values"] = LISTA_TODOS_LOS_MOTORES
    else:
        coincidencias = [m for m in LISTA_TODOS_LOS_MOTORES if texto_ingresado in m.lower()]
        combo_motor["values"] = coincidencias

    combo_motor.event_generate("<Down>")

def cargar_tecnicos_combobox():
    conexion = sqlite3.connect("megado_motores.db")
    cursor = conexion.cursor()
    cursor.execute("SELECT nombre FROM tecnicos ORDER BY nombre ASC")
    tecnicos = cursor.fetchall()
    conexion.close()

    lista_tecnicos = [t[0] for t in tecnicos]
    combo_tecnico["values"] = lista_tecnicos

def agregar_nuevo_tecnico():
    def guardar():
        nuevo_nombre = entry_nuevo.get().strip().upper()
        if not nuevo_nombre:
            messagebox.showwarning("Atención", "Ingresa el nombre del técnico.", parent=win_tec)
            return
        try:
            conexion = sqlite3.connect("megado_motores.db")
            cursor = conexion.cursor()
            cursor.execute("INSERT INTO tecnicos (nombre) VALUES (?)", (nuevo_nombre,))
            conexion.commit()
            conexion.close()

            messagebox.showinfo("Éxito", f"Técnico '{nuevo_nombre}' agregado.", parent=win_tec)
            cargar_tecnicos_combobox()
            combo_tecnico.set(nuevo_nombre)
            win_tec.destroy()
        except sqlite3.IntegrityError:
            messagebox.showerror("Error", "Este técnico ya existe en la lista.", parent=win_tec)

    win_tec = tk.Toplevel(ventana)
    win_tec.title("Agregar Técnico")
    win_tec.geometry("320x150")
    win_tec.grab_set()

    ttk.Label(win_tec, text="Nombre del Técnico:", font=("Arial", 10, "bold")).pack(pady=10)
    entry_nuevo = ttk.Entry(win_tec, width=28)
    entry_nuevo.pack(pady=5)
    entry_nuevo.focus()

    btn_g = tk.Button(win_tec, text="Guardar", bg="#4CAF50", fg="white", command=guardar)
    btn_g.pack(pady=10)

def registrar_motor():
    zona = entry_zona.get().strip()
    nombre = entry_nombre.get().strip()
    ubicacion_tdf = entry_ubicacion_tdf.get().strip()
    potencia = entry_potencia.get().strip()

    if not zona or not nombre:
        messagebox.showwarning("Atención", "La Zona y el Nombre del motor son obligatorios.")
        return

    try:
        conexion = sqlite3.connect("megado_motores.db")
        cursor = conexion.cursor()
        cursor.execute("""
            INSERT INTO motores (zona, nombre, ubicacion_tdf, potencia_hp)
            VALUES (?, ?, ?, ?)
        """, (zona, nombre, ubicacion_tdf, float(potencia) if potencia else None))
        conexion.commit()
        conexion.close()

        messagebox.showinfo("Éxito", f"Motor '{nombre}' guardado correctamente.")
        entry_zona.delete(0, tk.END)
        entry_nombre.delete(0, tk.END)
        entry_ubicacion_tdf.delete(0, tk.END)
        entry_potencia.delete(0, tk.END)
        cargar_motores_combobox()
    except Exception as e:
        messagebox.showerror("Error", f"Error inesperado: {e}")

def registrar_medicion():
    seleccion = combo_motor.get().strip()
    r1 = entry_r1.get().strip()
    r2 = entry_r2.get().strip()
    r3 = entry_r3.get().strip()
    voltaje = entry_voltaje.get().strip()
    tecnico = combo_tecnico.get().strip()
    estado = combo_estado.get().strip()
    obs = entry_obs.get().strip()

    fecha_seleccionada = cal_fecha.get_date()
    hora_actual = datetime.datetime.now().strftime("%H:%M:%S")
    fecha_formateada = f"{fecha_seleccionada.strftime('%Y-%m-%d')} {hora_actual}"

    if not seleccion or not r1 or not r2 or not r3 or not voltaje or not tecnico or not estado:
        messagebox.showwarning("Atención", "Debes seleccionar Motor, 3 Fases, Voltaje, Técnico y Estado.")
        return

    try:
        if " - " not in seleccion:
            messagebox.showwarning("Atención", "Por favor selecciona un motor válido de la lista desplegable.")
            return

        motor_id = int(seleccion.split(" - ")[0])

        conexion = sqlite3.connect("megado_motores.db")
        cursor = conexion.cursor()
        cursor.execute("""
            INSERT INTO mediciones (motor_id, fecha, res_l1, res_l2, res_l3, voltaje_prueba, tecnico, estado, observacion)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (motor_id, fecha_formateada, float(r1), float(r2), float(r3), float(voltaje), tecnico, estado, obs))
        conexion.commit()
        conexion.close()

        messagebox.showinfo("Éxito", f"Medición registrada con fecha {fecha_seleccionada}.")

        entry_r1.delete(0, tk.END)
        entry_r2.delete(0, tk.END)
        entry_r3.delete(0, tk.END)
        entry_voltaje.delete(0, tk.END)
        combo_tecnico.set("")
        combo_estado.set("NORMAL")
        entry_obs.delete(0, tk.END)
        combo_motor.set("")
        cargar_motores_combobox()
        cal_fecha.set_date(datetime.date.today())

        cargar_anios_filtro()
        cargar_historial()
    except ValueError:
        messagebox.showerror("Error", "Las resistencias y el voltaje deben ser valores numéricos.")
    except Exception as e:
        messagebox.showerror("Error", f"Error al guardar medición: {e}")

# ==========================================
# 3. FUNCIONES DE HISTORIAL, EDICIÓN Y EXPORTACIÓN PDF
# ==========================================
def cargar_anios_filtro():
    conexion = sqlite3.connect("megado_motores.db")
    cursor = conexion.cursor()
    cursor.execute("SELECT DISTINCT strftime('%Y', fecha) FROM mediciones WHERE fecha IS NOT NULL AND fecha != '' ORDER BY fecha DESC")
    anios = [row[0] for row in cursor.fetchall() if row[0] is not None]
    conexion.close()

    anio_actual = str(datetime.datetime.now().year)
    if anio_actual not in anios:
        anios.insert(0, anio_actual)

    anios.insert(0, "TODOS")
    combo_filtro_anio["values"] = anios

    if combo_filtro_anio.get() not in anios or combo_filtro_anio.get() == "TODOS":
        combo_filtro_anio.set(anio_actual)

def cargar_historial():
    for row in tabla.get_children():
        tabla.delete(row)

    conexion = sqlite3.connect("megado_motores.db")
    cursor = conexion.cursor()

    query = """
        SELECT m.id, m.fecha, mot.zona, mot.nombre, mot.ubicacion_tdf, m.res_l1, m.res_l2, m.res_l3, m.voltaje_prueba, m.tecnico, m.estado, m.observacion
        FROM mediciones m
        JOIN motores mot ON m.motor_id = mot.id
        WHERE 1=1
    """
    params = []

    anio_sel = combo_filtro_anio.get().strip()
    semestre_sel = combo_filtro_semestre.get().strip()

    if anio_sel and anio_sel != "TODOS":
        query += " AND strftime('%Y', m.fecha) = ?"
        params.append(anio_sel)

    if semestre_sel == "I Semestre (Ene - Jun)":
        query += " AND strftime('%m', m.fecha) BETWEEN '01' AND '06'"
    elif semestre_sel == "II Semestre (Jul - Dic)":
        query += " AND strftime('%m', m.fecha) BETWEEN '07' AND '12'"

    query += " ORDER BY m.fecha DESC"

    cursor.execute(query, params)
    registros = cursor.fetchall()
    conexion.close()

    for reg in registros:
        med_id = reg[0]
        datos_visibles = reg[1:]
        estado = reg[10]

        if estado == "NORMAL":
            tag_estado = "normal"
        elif estado == "OBSERVADO":
            tag_estado = "observado"
        elif estado == "CRÍTICO":
            tag_estado = "critico"
        else:
            tag_estado = ""

        tabla.insert("", tk.END, iid=med_id, values=datos_visibles, tags=(tag_estado,))

def limpiar_filtros():
    combo_filtro_anio.set("TODOS")
    combo_filtro_semestre.set("TODOS")
    cargar_historial()

def editar_medicion_seleccionada():
    item_sel = tabla.selection()
    if not item_sel:
        messagebox.showwarning("Atención", "Por favor, selecciona un registro de la tabla para editar.")
        return

    med_id = item_sel[0]
    valores = tabla.item(med_id, "values")

    win_edit = tk.Toplevel(ventana)
    win_edit.title(f"Editar Medición (ID: {med_id})")
    win_edit.geometry("380x420")
    win_edit.grab_set()

    ttk.Label(win_edit, text="Fase 1 (MΩ):").grid(row=0, column=0, padx=10, pady=5, sticky="e")
    e_r1 = ttk.Entry(win_edit, width=15); e_r1.insert(0, valores[4]); e_r1.grid(row=0, column=1, padx=10, pady=5)

    ttk.Label(win_edit, text="Fase 2 (MΩ):").grid(row=1, column=0, padx=10, pady=5, sticky="e")
    e_r2 = ttk.Entry(win_edit, width=15); e_r2.insert(0, valores[5]); e_r2.grid(row=1, column=1, padx=10, pady=5)

    ttk.Label(win_edit, text="Fase 3 (MΩ):").grid(row=2, column=0, padx=10, pady=5, sticky="e")
    e_r3 = ttk.Entry(win_edit, width=15); e_r3.insert(0, valores[6]); e_r3.grid(row=2, column=1, padx=10, pady=5)

    ttk.Label(win_edit, text="Voltaje Prueba (V):").grid(row=3, column=0, padx=10, pady=5, sticky="e")
    e_volt = ttk.Entry(win_edit, width=15); e_volt.insert(0, valores[7]); e_volt.grid(row=3, column=1, padx=10, pady=5)

    ttk.Label(win_edit, text="Técnico:").grid(row=4, column=0, padx=10, pady=5, sticky="e")
    c_tec = ttk.Combobox(win_edit, values=combo_tecnico["values"], width=20, state="readonly")
    c_tec.set(valores[8]); c_tec.grid(row=4, column=1, padx=10, pady=5)

    ttk.Label(win_edit, text="Estado:").grid(row=5, column=0, padx=10, pady=5, sticky="e")
    c_est = ttk.Combobox(win_edit, values=["NORMAL", "OBSERVADO", "CRÍTICO"], width=20, state="readonly")
    c_est.set(valores[9]); c_est.grid(row=5, column=1, padx=10, pady=5)

    ttk.Label(win_edit, text="Observación:").grid(row=6, column=0, padx=10, pady=5, sticky="e")
    e_obs = ttk.Entry(win_edit, width=22); e_obs.insert(0, valores[10]); e_obs.grid(row=6, column=1, padx=10, pady=5)

    def guardar_cambios():
        try:
            conexion = sqlite3.connect("megado_motores.db")
            cursor = conexion.cursor()
            cursor.execute("""
                UPDATE mediciones 
                SET res_l1=?, res_l2=?, res_l3=?, voltaje_prueba=?, tecnico=?, estado=?, observacion=?
                WHERE id=?
            """, (float(e_r1.get()), float(e_r2.get()), float(e_r3.get()), float(e_volt.get()), c_tec.get(), c_est.get(), e_obs.get(), med_id))
            conexion.commit()
            conexion.close()

            messagebox.showinfo("Éxito", "Medición actualizada correctamente.", parent=win_edit)
            win_edit.destroy()
            cargar_historial()
        except ValueError:
            messagebox.showerror("Error", "Asegúrate de ingresar valores numéricos válidos en Fases y Voltaje.", parent=win_edit)

    tk.Button(win_edit, text="Guardar Cambios", bg="#4CAF50", fg="white", font=("Arial", 9, "bold"), command=guardar_cambios).grid(row=7, column=0, columnspan=2, pady=15)

def eliminar_medicion_seleccionada():
    item_sel = tabla.selection()
    if not item_sel:
        messagebox.showwarning("Atención", "Por favor, selecciona un registro de la tabla para eliminar.")
        return

    med_id = item_sel[0]
    confirmacion = messagebox.askyesno("Confirmar Eliminación", "¿Estás seguro de que deseas eliminar la medición seleccionada?\nEsta acción no se puede deshacer.")
    
    if confirmacion:
        conexion = sqlite3.connect("megado_motores.db")
        cursor = conexion.cursor()
        cursor.execute("DELETE FROM mediciones WHERE id=?", (med_id,))
        conexion.commit()
        conexion.close()

        messagebox.showinfo("Eliminado", "La medición ha sido eliminada del historial.")
        cargar_historial()

def exportar_pdf():
    filas = tabla.get_children()
    if not filas:
        messagebox.showwarning("Atención", "No hay datos en la tabla para exportar.")
        return

    archivo_pdf = filedialog.asksaveasfilename(
        defaultextension=".pdf",
        filetypes=[("Archivos PDF", "*.pdf")],
        title="Guardar Reporte de Mediciones como PDF",
        initialfile=f"Reporte_Megado_Motores_{datetime.date.today()}.pdf"
    )

    if not archivo_pdf:
        return

    try:
        doc = SimpleDocTemplate(
            archivo_pdf,
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

        anio_filtro = combo_filtro_anio.get()
        semestre_filtro = combo_filtro_semestre.get()
        
        elementos.append(Paragraph("REPORTE TÉCNICO DE MEGADO Y RESISTENCIA DE AISLAMIENTO EN MOTORES", style_title))
        elementos.append(Spacer(1, 4))
        elementos.append(Paragraph(f"Filtro Aplicado: Año: <b>{anio_filtro}</b> | Semestre: <b>{semestre_filtro}</b> — Generado el: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", style_sub))
        elementos.append(Spacer(1, 12))

        headers = ["Fecha / Hora", "Zona", "Motor", "Ubicación", "L1 (MΩ)", "L2 (MΩ)", "L3 (MΩ)", "Volt (V)", "Técnico", "Estado", "Observación"]
        data = [[Paragraph(h, style_header) for h in headers]]

        for item in filas:
            val = tabla.item(item, "values")
            data.append([Paragraph(str(v), style_cell) for v in val])

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

        # --- SECCIÓN DE FIRMAS ---
        elementos.append(Spacer(1, 45))  # Espacio previo para las firmas

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

        # Generar el archivo
        doc.build(elementos)

        resp = messagebox.askyesno("Éxito", "El reporte en PDF con firmas ha sido generado correctamente.\n\n¿Deseas abrirlo ahora para visualizarlo o imprimirlo?")
        if resp:
            os.startfile(archivo_pdf)

    except Exception as e:
        messagebox.showerror("Error", f"Ocurrió un error al generar el PDF: {e}")

def mostrar_menu_contextual(event):
    iid = tabla.identify_row(event.y)
    if iid:
        tabla.selection_set(iid)
        menu_contextual.post(event.x_root, event.y_root)

# ==========================================
# 4. INTERFAZ GRÁFICA (GUI)
# ==========================================
st.title("Sistema de Control de Megado de Motores Trifásicos")

notebook = ttk.Notebook(ventana)
notebook.pack(fill="both", expand=True, padx=10, pady=10)

pestaña1 = ttk.Frame(notebook)
pestaña2 = ttk.Frame(notebook)

notebook.add(pestaña1, text=" Registrar Datos ")
notebook.add(pestaña2, text=" Historial de Mediciones ")

# --- PESTAÑA 1: REGISTRO ---
frame_motor = ttk.LabelFrame(pestaña1, text=" Registro de Motor ")
frame_motor.pack(fill="x", padx=15, pady=10)

ttk.Label(frame_motor, text="Zona *:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
entry_zona = ttk.Entry(frame_motor, width=20)
entry_zona.grid(row=0, column=1, padx=5, pady=5)

ttk.Label(frame_motor, text="Nombre/Equipo *:").grid(row=0, column=2, padx=5, pady=5, sticky="e")
entry_nombre = ttk.Entry(frame_motor, width=20)
entry_nombre.grid(row=0, column=3, padx=5, pady=5)

ttk.Label(frame_motor, text="Ubicación (TDF):").grid(row=1, column=0, padx=5, pady=5, sticky="e")
entry_ubicacion_tdf = ttk.Entry(frame_motor, width=20)
entry_ubicacion_tdf.grid(row=1, column=1, padx=5, pady=5)

ttk.Label(frame_motor, text="Potencia (HP):").grid(row=1, column=2, padx=5, pady=5, sticky="e")
entry_potencia = ttk.Entry(frame_motor, width=20)
entry_potencia.grid(row=1, column=3, padx=5, pady=5)

btn_guardar_motor = tk.Button(frame_motor, text="Guardar Motor", bg="#2196F3", fg="white", command=registrar_motor)
btn_guardar_motor.grid(row=2, column=0, columnspan=4, pady=10)

frame_medicion = ttk.LabelFrame(pestaña1, text=" Nueva Medición de Megado (Aislamiento por Fase) ")
frame_medicion.pack(fill="x", padx=15, pady=10)

ttk.Label(frame_medicion, text="Fecha de Medición *:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
cal_fecha = DateEntry(frame_medicion, width=15, background="darkblue", foreground="white", date_pattern="yyyy-mm-dd")
cal_fecha.grid(row=0, column=1, padx=5, pady=5, sticky="w")

ttk.Label(frame_medicion, text="Seleccionar Motor *:").grid(row=0, column=2, padx=5, pady=5, sticky="e")
combo_motor = ttk.Combobox(frame_medicion, width=32, state="normal")
combo_motor.grid(row=0, column=3, padx=5, pady=5, sticky="w")
combo_motor.bind("<KeyRelease>", filtrar_motores_al_escribir)

ttk.Label(frame_medicion, text="FASE 1 (MΩ) *:").grid(row=1, column=0, padx=5, pady=5, sticky="e")
entry_r1 = ttk.Entry(frame_medicion, width=12)
entry_r1.grid(row=1, column=1, padx=5, pady=5, sticky="w")

ttk.Label(frame_medicion, text="FASE 2 (MΩ) *:").grid(row=1, column=2, padx=5, pady=5, sticky="e")
entry_r2 = ttk.Entry(frame_medicion, width=12)
entry_r2.grid(row=1, column=3, padx=5, pady=5, sticky="w")

ttk.Label(frame_medicion, text="FASE 3 (MΩ) *:").grid(row=2, column=0, padx=5, pady=5, sticky="e")
entry_r3 = ttk.Entry(frame_medicion, width=12)
entry_r3.grid(row=2, column=1, padx=5, pady=5, sticky="w")

ttk.Label(frame_medicion, text="Voltaje Prueba (V) *:").grid(row=2, column=2, padx=5, pady=5, sticky="e")
entry_voltaje = ttk.Entry(frame_medicion, width=12)
entry_voltaje.grid(row=2, column=3, padx=5, pady=5, sticky="w")

ttk.Label(frame_medicion, text="Técnico Responsable *:").grid(row=3, column=0, padx=5, pady=5, sticky="e")
frame_tec_combo = ttk.Frame(frame_medicion)
frame_tec_combo.grid(row=3, column=1, columnspan=3, sticky="w", padx=5, pady=5)

combo_tecnico = ttk.Combobox(frame_tec_combo, width=32, state="readonly")
combo_tecnico.pack(side="left")

btn_add_tec = tk.Button(frame_tec_combo, text="+ Agregar Nuevo", bg="#9C27B0", fg="white", font=("Arial", 8, "bold"), command=agregar_nuevo_tecnico)
btn_add_tec.pack(side="left", padx=8)

ttk.Label(frame_medicion, text="Estado del Motor *:").grid(row=4, column=0, padx=5, pady=5, sticky="e")
combo_estado = ttk.Combobox(frame_medicion, values=["NORMAL", "OBSERVADO", "CRÍTICO"], width=20, state="readonly")
combo_estado.grid(row=4, column=1, padx=5, pady=5, sticky="w")
combo_estado.set("NORMAL")

ttk.Label(frame_medicion, text="Observación:").grid(row=5, column=0, padx=5, pady=5, sticky="e")
entry_obs = ttk.Entry(frame_medicion, width=45)
entry_obs.grid(row=5, column=1, columnspan=3, padx=5, pady=5, sticky="w")

btn_guardar_medicion = tk.Button(frame_medicion, text="Guardar Medición", bg="#4CAF50", fg="white", command=registrar_medicion)
btn_guardar_medicion.grid(row=6, column=0, columnspan=4, pady=10)

cargar_motores_combobox()
cargar_tecnicos_combobox()

# --- PESTAÑA 2: HISTORIAL, FILTROS Y EXPORTACIÓN ---
frame_filtros = ttk.LabelFrame(pestaña2, text=" Filtros para Auditoría (Año / Semestre) ")
frame_filtros.pack(fill="x", padx=10, pady=5)

ttk.Label(frame_filtros, text="Año:", font=("Arial", 9, "bold")).pack(side="left", padx=(10, 2), pady=8)
combo_filtro_anio = ttk.Combobox(frame_filtros, width=10, state="readonly")
combo_filtro_anio.pack(side="left", padx=5, pady=8)

ttk.Label(frame_filtros, text="Semestre:", font=("Arial", 9, "bold")).pack(side="left", padx=(15, 2), pady=8)
combo_filtro_semestre = ttk.Combobox(frame_filtros, values=["TODOS", "I Semestre (Ene - Jun)", "II Semestre (Jul - Dic)"], width=22, state="readonly")
combo_filtro_semestre.pack(side="left", padx=5, pady=8)
combo_filtro_semestre.set("TODOS")

btn_filtrar = tk.Button(frame_filtros, text="Filtrar", bg="#2196F3", fg="white", font=("Arial", 9, "bold"), command=cargar_historial)
btn_filtrar.pack(side="left", padx=8, pady=8)

btn_limpiar = tk.Button(frame_filtros, text="Mostrar Todos", bg="#607D8B", fg="white", command=limpiar_filtros)
btn_limpiar.pack(side="left", padx=5, pady=8)

# Botones de Acción
btn_pdf = tk.Button(frame_filtros, text="📄 Exportar PDF / Imprimir", bg="#009688", fg="white", font=("Arial", 9, "bold"), command=exportar_pdf)
btn_pdf.pack(side="right", padx=10, pady=8)

btn_eliminar = tk.Button(frame_filtros, text="🗑️ Eliminar", bg="#F44336", fg="white", font=("Arial", 9, "bold"), command=eliminar_medicion_seleccionada)
btn_eliminar.pack(side="right", padx=5, pady=8)

btn_editar = tk.Button(frame_filtros, text="✏️ Editar", bg="#FFC107", font=("Arial", 9, "bold"), command=editar_medicion_seleccionada)
btn_editar.pack(side="right", padx=5, pady=8)

frame_historial = ttk.Frame(pestaña2)
frame_historial.pack(fill="both", expand=True, padx=10, pady=5)

columnas = ("Fecha", "Zona", "Motor", "Ubicación (TDF)", "FASE 1 (MΩ)", "FASE 2 (MΩ)", "FASE 3 (MΩ)", "Voltaje (V)", "Técnico", "Estado", "Obs.")
tabla = ttk.Treeview(frame_historial, columns=columnas, show="headings")

for col in columnas:
    tabla.heading(col, text=col)
    tabla.column(col, width=90, anchor="center")

tabla.column("Fecha", width=130)
tabla.column("Ubicación (TDF)", width=110)
tabla.column("Técnico", width=110)
tabla.column("Estado", width=100)
tabla.column("Obs.", width=100)

tabla.tag_configure("normal", foreground="#008000")
tabla.tag_configure("observado", foreground="#D97706")
tabla.tag_configure("critico", foreground="#DC2626")

scrollbar = ttk.Scrollbar(frame_historial, orient="vertical", command=tabla.yview)
tabla.configure(yscroll=scrollbar.set)

tabla.pack(side="left", fill="both", expand=True)
scrollbar.pack(side="right", fill="y")

# Menú contextual
menu_contextual = tk.Menu(ventana, tearoff=0)
menu_contextual.add_command(label="✏️ Editar Registro", command=editar_medicion_seleccionada)
menu_contextual.add_command(label="🗑️ Eliminar Registro", command=eliminar_medicion_seleccionada)

tabla.bind("<Button-3>", mostrar_menu_contextual)

cargar_anios_filtro()
cargar_historial()

ventana.mainloop()
