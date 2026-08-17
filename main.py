import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Gestión de Megado", page_icon="⚡", layout="wide")

# --- CONEXIÓN BASE DE DATOS ---
def conectar_db():
    conn = sqlite3.connect("megado_motores.db")
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS motores (
            id_motor TEXT PRIMARY KEY,
            zona TEXT,
            nombre TEXT,
            tdf TEXT,
            hp REAL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS mediciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT,
            id_motor TEXT,
            l1 REAL,
            l2 REAL,
            l3 REAL,
            voltaje REAL,
            tecnico TEXT,
            estado TEXT,
            obs TEXT
        )
    ''')
    conn.commit()
    conn.close()

conectar_db()

st.title("⚡ Sistema de Registro de Megado de Motores")

tab1, tab2, tab3 = st.tabs(["📝 Registrar Motor", "📐 Registrar Medición", "📊 Historial"])

# --- TAB 1: REGISTRAR MOTOR ---
with tab1:
    st.subheader("Nuevo Motor")
    col1, col2 = st.columns(2)
    
    with col1:
        id_m = st.text_input("ID Motor *")
        zona = st.text_input("Zona / Área")
        nombre = st.text_input("Nombre del Equipo *")
    with col2:
        tdf = st.text_input("Ubicación TDF")
        hp = st.number_input("Potencia (HP)", min_value=0.0, step=0.5)
    
    if st.button("Guardar Motor", type="primary"):
        if id_m and nombre:
            try:
                conn = sqlite3.connect("megado_motores.db")
                c = conn.cursor()
                c.execute("INSERT INTO motores VALUES (?,?,?,?,?)", (id_m, zona, nombre, tdf, hp))
                conn.commit()
                conn.close()
                st.success(f"✅ Motor {id_m} registrado correctamente.")
            except sqlite3.IntegrityError:
                st.error("❌ El ID de este motor ya existe.")
        else:
            st.warning("⚠️ Completa los campos obligatorios (ID y Nombre).")

# --- TAB 2: REGISTRAR MEDICIÓN ---
with tab2:
    st.subheader("Nueva Medición de Aislamiento")
    
    conn = sqlite3.connect("megado_motores.db")
    motores = [r[0] for r in conn.cursor().execute("SELECT id_motor FROM motores").fetchall()]
    conn.close()
    
    if not motores:
        st.info("💡 Primero debes registrar al menos un motor en la pestaña 'Registrar Motor'.")
    else:
        c1, c2 = st.columns(2)
        with c1:
            motor_sel = st.selectbox("Seleccionar Motor *", motores)
            fecha = st.date_input("Fecha de Inspección", datetime.now())
            tec = st.text_input("Técnico Responsable")
            estado = st.selectbox("Estado del Aislamiento", ["Bueno", "Alerta", "Crítico"])
        
        with c2:
            l1 = st.number_input("L1 (MΩ)", min_value=0.0, step=1.0)
            l2 = st.number_input("L2 (MΩ)", min_value=0.0, step=1.0)
            l3 = st.number_input("L3 (MΩ)", min_value=0.0, step=1.0)
            volt = st.number_input("Voltaje del Megóhmetro (V)", min_value=0.0, step=100.0)
        
        obs = st.text_area("Observaciones del Ensayo")
        
        if st.button("Guardar Medición", type="primary"):
            if l1 > 0 and l2 > 0 and l3 > 0:
                conn = sqlite3.connect("megado_motores.db")
                c = conn.cursor()
                c.execute('''
                    INSERT INTO mediciones (fecha, id_motor, l1, l2, l3, voltaje, tecnico, estado, obs) 
                    VALUES (?,?,?,?,?,?,?,?,?)
                ''', (str(fecha), motor_sel, l1, l2, l3, volt, tec, estado, obs))
                conn.commit()
                conn.close()
                st.success("✅ Medición guardada exitosamente.")
            else:
                st.warning("⚠️ Ingresa los valores de aislamiento L1, L2 y L3.")

# --- TAB 3: HISTORIAL ---
with tab3:
    st.subheader("Historial General de Mediciones")
    conn = sqlite3.connect("megado_motores.db")
    df = pd.read_sql_query("SELECT * FROM mediciones ORDER BY id DESC", conn)
    conn.close()
    
    if not df.empty:
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No hay mediciones registradas aún.")