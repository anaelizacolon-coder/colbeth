import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, date

def get_connection():
    return sqlite3.connect('muebles_negocio.db', check_same_thread=False)

conn = get_connection()
c = conn.cursor()

# --- INICIALIZACIÓN ---
c.execute('''CREATE TABLE IF NOT EXISTS proyectos 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha_creacion TEXT, cliente TEXT, 
              mueble TEXT, suplidor TEXT, precio_venta REAL, costo_fabrica REAL, 
              adelanto_cliente REAL, adelanto_suplidor REAL, estado TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS historial_pagos 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, proyecto_id INTEGER, fecha TEXT, 
              tipo_movimiento TEXT, monto REAL)''')
c.execute('''CREATE TABLE IF NOT EXISTS gastos_varios 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, concepto TEXT, monto REAL)''')
conn.commit()

st.set_page_config(page_title="Mueblería Pro v16", layout="wide")

menu = ["Nuevo Proyecto", "Ver / Gestionar Proyectos", "Pagos y Abonos", "✏️ Corregir Datos", "Gastos Varios", "Reportes y Respaldo"]
choice = st.sidebar.selectbox("Menú Principal", menu)

# --- MÓDULOS DE REGISTRO (Resumidos para brevedad, mantienen tu lógica) ---
if choice == "Nuevo Proyecto":
    st.header("📝 Nuevo Proyecto")
    with st.form("f_n", clear_on_submit=True):
        f_p = st.date_input("Fecha:", date.today())
        cli = st.text_input("Cliente").upper()
        sup = st.text_input("Suplidor").upper()
        mue = st.text_area("Descripción")
        p_v = st.number_input("Precio Venta", min_value=0.0)
        c_f = st.number_input("Costo Fábrica", min_value=0.0)
        if st.form_submit_button("Guardar"):
            c.execute("INSERT INTO proyectos (fecha_creacion, cliente, mueble, suplidor, precio_venta, costo_fabrica, adelanto_cliente, adelanto_suplidor, estado) VALUES (?,?,?,?,?,?,?,?,?)",
                      (f_p.strftime("%Y-%m-%d"), cli, mue, sup, p_v, c_f, 0.0, 0.0, "En Proceso"))
            conn.commit()
            st.success("Guardado.")

elif choice == "Pagos y Abonos":
    st.header("💰 Registrar Movimiento Real de Efectivo")
    st.info("Nota: Los montos registrados aquí son los que aparecen en el Estado de Resultados.")
    df_act = pd.read_sql("SELECT id, cliente FROM proyectos", conn)
    if not df_act.empty:
        opc = [f"ID {r['id']} - {r['cliente']}" for _, r in df_act.iterrows()]
        sel = st.selectbox("Proyecto:", opc)
        id_p = int(sel.split(" ")[1])
        t_m = st.radio("Movimiento:", ["Cobro a Cliente", "Pago a Fábrica"])
        f_m = st.date_input("Fecha:", date.today())
        mon = st.number_input("Monto", min_value=0.0)
        if st.button("Registrar Transacción"):
            campo = "adelanto_cliente" if "Cliente" in t_m else "adelanto_suplidor"
            c.execute(f"UPDATE proyectos SET {campo} = {campo} + ? WHERE id = ?", (mon, id_p))
            c.execute("INSERT INTO historial_pagos (proyecto_id, fecha, tipo_movimiento, monto) VALUES (?,?,?,?)",
                      (id_p, f_m.strftime("%Y-%m-%d"), t_m, mon))
            conn.commit()
            st.success("¡Dinero registrado!")

# --- REPORTE CORREGIDO ---
elif choice == "Reportes y Respaldo":
    st.header("📊 Inteligencia Financiera")
    
    # Filtros en la barra lateral
    st.sidebar.subheader("Rango del Reporte")
    f_ini = st.sidebar.date_input("Desde", date(2026, 1, 1)) # Ampliado por defecto a inicio de año
    f_fin = st.sidebar.date_input("Hasta", date.today())
    
    s_ini, s_fin = f_ini.strftime("%Y-%m-%d"), f_fin.strftime("%Y-%m-%d")

    # CARGA DE DATOS
    df_h = pd.read_sql(f"SELECT * FROM historial_pagos WHERE fecha >= '{s_ini}' AND fecha <= '{s_fin}'", conn)
    df_g = pd.read_sql(f"SELECT * FROM gastos_varios WHERE fecha >= '{s_ini}' AND fecha <= '{s_fin}'", conn)

    # CÁLCULOS
    ing = df_h[df_h['tipo_movimiento'] == 'Cobro a Cliente']['monto'].sum() or 0.0
    p_f = df_h[df_h['tipo_movimiento'] == 'Pago a Fábrica']['monto'].sum() or 0.0
    gas = df_g['monto'].sum() or 0.0
    neto = ing - p_f - gas

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("INGRESOS", f"${ing:,.2f}")
    col2.metric("A FÁBRICA", f"${p_f:,.2f}")
    col3.metric("GASTOS", f"${gas:,.2f}")
    col4.metric("UTILIDAD", f"${neto:,.2f}")

    if df_h.empty and df_g.empty:
        st.warning("⚠️ No hay transacciones de dinero en este rango de fechas. Registra un cobro en 'Pagos y Abonos' para ver datos aquí.")

# (El resto de las funciones: Ver proyectos, Corregir y Gastos se mantienen igual que la v15)
