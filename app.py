import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, date

# 1. CONEXIÓN A BASE DE DATOS
def get_connection():
    return sqlite3.connect('muebles_negocio.db', check_same_thread=False)

conn = get_connection()
c = conn.cursor()

# ASEGURAR TABLAS
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

st.set_page_config(page_title="Mueblería Pro v18 - Seguridad", layout="wide")

menu = ["Nuevo Proyecto", "Ver / Gestionar Proyectos", "Pagos y Abonos", "✏️ Corregir Datos", "Gastos Varios", "Reportes y Respaldo"]
choice = st.sidebar.selectbox("Menú Principal", menu)

# --- 1. NUEVO PROYECTO ---
if choice == "Nuevo Proyecto":
    st.header("📝 Registrar Nuevo Proyecto")
    with st.form("form_nuevo_proy", clear_on_submit=True):
        f_p = st.date_input("Fecha:", date.today())
        col1, col2 = st.columns(2)
        cli = col1.text_input("Nombre del Cliente").upper()
        sup = col2.text_input("Nombre del Suplidor (Fábrica)").upper()
        mue = st.text_area("Descripción del Producto")
        c1, c2 = st.columns(2)
        p_v = c1.number_input("Precio Venta ($)", min_value=0.0, step=100.0)
        c_f = c2.number_input("Costo Fábrica ($)", min_value=0.0, step=100.0)
        
        if st.form_submit_button("Guardar Proyecto"):
            if cli and sup and p_v > 0:
                c.execute("INSERT INTO proyectos (fecha_creacion, cliente, mueble, suplidor, precio_venta, costo_fabrica, adelanto_cliente, adelanto_suplidor, estado) VALUES (?,?,?,?,?,?,?,?,?)",
                          (f_p.strftime("%Y-%m-%d"), cli, mue, sup, p_v, c_f, 0.0, 0.0, "En Proceso"))
                conn.commit()
                st.success("✅ Proyecto guardado y formulario limpio.")
                st.rerun()
            else:
                st.error("Por favor completa los nombres y asegúrate que el precio sea mayor a 0.")

# --- 3. PAGOS Y ABONOS (MEJORADO CON LIMPIEZA Y VALIDACIÓN) ---
elif choice == "Pagos y Abonos":
    st.header("💰 Registro de Cobros y Pagos")
    st.write("Selecciona el proyecto y el monto real que entró o salió de caja.")
    
    df_act = pd.read_sql("SELECT id, cliente, mueble, suplidor FROM proyectos WHERE estado != 'Entregado'", conn)
    
    if not df_act.empty:
        # Formulario con clear_on_submit para evitar duplicados al refrescar
        with st.form("form_pagos", clear_on_submit=True):
            opc = [f"ID {r['id']} | {r['cliente']} | {r['mueble'][:20]}... (Fábrica: {r['suplidor']})" for _, r in df_act.iterrows()]
            sel = st.selectbox("Seleccione el Proyecto Específico:", opc)
            id_p = int(sel.split(" ")[1])
            
            col_t, col_f = st.columns(2)
            tipo = col_t.radio("Tipo de Movimiento:", ["Cobro a Cliente", "Pago a Fábrica"])
            fecha_m = col_f.date_input("Fecha:", date.today())
            
            monto = st.number_input("Monto Real ($)", min_value=0.0, step=100.0, help="Debe ser mayor a 0")
            
            submitted = st.form_submit_button("✅ REGISTRAR MOVIMIENTO")
            
            if submitted:
                if monto > 0:
                    campo = "adelanto_cliente" if "Cliente" in tipo else "adelanto_suplidor"
                    # 1. Actualizar balance en tabla proyectos
                    c.execute(f"UPDATE proyectos SET {campo} = {campo} + ? WHERE id = ?", (monto, id_p))
                    # 2. Insertar en historial para el Estado de Resultados
                    c.execute("INSERT INTO historial_pagos (proyecto_id, fecha, tipo_movimiento, monto) VALUES (?,?,?,?)",
                              (id_p, fecha_m.strftime("%Y-%m-%d"), tipo, monto))
                    conn.commit()
                    st.success(f"Dinero Registrado con Éxito. Pantalla limpia para el siguiente registro.")
                    # st.rerun() ayuda a limpiar visualmente cualquier residuo
                else:
                    st.warning("⚠️ El monto debe ser mayor a cero para poder registrarse.")
    else:
        st.warning("No hay proyectos activos para procesar pagos.")

# --- 4. CORREGIR DATOS (PARA BORRAR EL PAGO DUPLICADO) ---
elif choice == "✏️ Corregir Datos":
    st.header("✏️ Editor Maestro")
    st.info("Si duplicaste un pago por error, ajusta los montos de 'Cobrado' o 'Pagado Fábrica' aquí.")
    
    df_e = pd.read_sql("SELECT * FROM proyectos", conn)
    if not df_e.empty:
        opc = [f"ID {r['id']} - {r['cliente']}" for _, r in df_e.iterrows()]
        sel = st.selectbox("Seleccione el proyecto:", opc)
        id_p = int(sel.split(" ")[1])
        p = df_e[df_e['id'] == id_p].iloc[0]
        
        with st.form("e_m"):
            n_fecha = st.date_input("Fecha Creación:", value=datetime.strptime(p['fecha_creacion'], "%Y-%m-%d").date())
            n_c = st.text_input("Cliente", p['cliente'])
            n_s = st.text_input("Suplidor", p['suplidor'])
            col_a, col_b = st.columns(2)
            n_pv = col_a.number_input("Precio Venta", value=float(p['precio_venta']))
            n_cf = col_b.number_input("Costo Fábrica", value=float(p['costo_fabrica']))
            
            st.write("---")
            st.write("**Ajuste de Balances (Corrige aquí si duplicaste un pago)**")
            col_c, col_d = st.columns(2)
            n_ac = col_c.number_input("Total Cobrado Cliente", value=float(p['adelanto_cliente']))
            n_as = col_d.number_input("Total Pagado a Fábrica", value=float(p['adelanto_suplidor']))
            
            if st.form_submit_button("💾 GUARDAR CORRECCIONES"):
                c.execute('''UPDATE proyectos SET fecha_creacion=?, cliente=?, suplidor=?, 
                             precio_venta=?, costo_fabrica=?, adelanto_cliente=?, 
                             adelanto_suplidor=? WHERE id=?''',
                          (n_fecha.strftime("%Y-%m-%d"), n_c.upper(), n_s.upper(), 
                           n_pv, n_cf, n_ac, n_as, id_p))
                conn.commit()
                st.success("Corregido.")
                st.rerun()

# (Se mantienen iguales Ver Proyectos, Gastos y Reportes de la v17)
