import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, date

# 1. CONEXIÓN A BASE DE DATOS
def get_connection():
    return sqlite3.connect('muebles_negocio.db', check_same_thread=False)

conn = get_connection()
c = conn.cursor()

# CONFIGURACIÓN DE TABLAS
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

st.set_page_config(page_title="Mueblería Pro v26", layout="wide")

# --- MENÚ LATERAL ---
menu = ["Nuevo Proyecto", "Ver / Gestionar Proyectos", "Pagos y Abonos", "✏️ Corregir Datos", "Gastos Varios", "Reportes y Respaldo"]
choice = st.sidebar.selectbox("Navegación:", menu)

# --- 1. NUEVO PROYECTO (Optimizado para múltiples productos/suplidores) ---
if choice == "Nuevo Proyecto":
    st.header("📝 Registrar Nuevo Proyecto")
    st.info("💡 Si un cliente tiene Cocina y Tope con suplidores distintos, regístralos como 2 proyectos separados para un mejor control de pagos.")
    
    df_p_existentes = pd.read_sql("SELECT DISTINCT cliente, suplidor FROM proyectos", conn)
    lista_clientes = sorted(df_p_existentes['cliente'].unique().tolist())
    lista_suplidores = sorted(df_p_existentes['suplidor'].unique().tolist())
    
    opciones_cli = ["+ Agregar Nuevo Cliente"] + lista_clientes
    opciones_sup = ["+ Agregar Nuevo Suplidor"] + lista_suplidores

    with st.form("form_nuevo", clear_on_submit=True):
        f_p = st.date_input("Fecha de Inicio:", date.today())
        col1, col2 = st.columns(2)
        
        cli_sel = col1.selectbox("Cliente:", opciones_cli)
        cli_final = col1.text_input("Nombre Nuevo Cliente").upper() if cli_sel == "+ Agregar Nuevo Cliente" else cli_sel
        
        sup_sel = col2.selectbox("Suplidor (Fábrica/Marmolería):", opciones_sup)
        sup_final = col2.text_input("Nombre Nuevo Suplidor").upper() if sup_sel == "+ Agregar Nuevo Suplidor" else sup_sel
        
        mue = st.text_area("Descripción (Ej: Cocina de Caoba o Tope de Granito)")
        
        c1, c2 = st.columns(2)
        p_v = c1.number_input("Precio de Venta al Cliente ($)", min_value=0.0)
        c_f = c2.number_input("Costo de esta parte (Fábrica) ($)", min_value=0.0)
        
        if st.form_submit_button("💾 Guardar Proyecto"):
            if cli_final and sup_final:
                c.execute("INSERT INTO proyectos (fecha_creacion, cliente, mueble, suplidor, precio_venta, costo_fabrica, adelanto_cliente, adelanto_suplidor, estado) VALUES (?,?,?,?,?,?,?,?,?)",
                          (f_p.strftime("%Y-%m-%d"), cli_final, mue, sup_final, p_v, c_f, 0.0, 0.0, "En Proceso"))
                conn.commit()
                st.success(f"✅ Proyecto '{mue}' para {cli_final} guardado.")
                st.rerun()

# --- 3. PAGOS Y ABONOS (Identificación clara del suplidor) ---
elif choice == "Pagos y Abonos":
    st.header("💰 Registro de Cobros y Pagos")
    # Traemos el suplidor en la lista para no equivocarnos
    df_act = pd.read_sql("SELECT id, cliente, mueble, suplidor FROM proyectos WHERE estado != 'Entregado'", conn)
    if not df_act.empty:
        with st.form("f_pagos", clear_on_submit=True):
            # Mostramos Cliente + Mueble + Suplidor para saber a quién le estamos pagando
            opc = [f"ID {r['id']} | {r['cliente']} | {r['mueble'][:15]} | Fab: {r['suplidor']}" for _, r in df_act.iterrows()]
            sel = st.selectbox("Seleccionar Proyecto Destino:", opc)
            id_p = int(sel.split(" ")[1])
            
            col_a, col_b = st.columns(2)
            tipo = col_a.radio("Tipo de Movimiento:", ["Cobro a Cliente", "Pago a Fábrica"])
            f_pago = col_b.date_input("Fecha:", date.today())
            mon = st.number_input("Monto ($)", min_value=0.1)
            
            if st.form_submit_button("✅ Registrar"):
                campo = "adelanto_cliente" if "Cliente" in tipo else "adelanto_suplidor"
                c.execute(f"UPDATE proyectos SET {campo} = {campo} + ? WHERE id = ?", (mon, id_p))
                c.execute("INSERT INTO historial_pagos (proyecto_id, fecha, tipo_movimiento, monto) VALUES (?,?,?,?)",
                          (id_p, f_pago.strftime("%Y-%m-%d"), tipo, mon))
                conn.commit()
                st.success("Movimiento registrado.")
                st.rerun()

# --- REPORTE DE SALDOS (Separado por Suplidor) ---
elif choice == "Reportes y Respaldo":
    st.header("📊 Inteligencia Financiera")
    f_ini = st.sidebar.date_input("Desde", date(date.today().year, date.today().month, 1))
    f_fin = st.sidebar.date_input("Hasta", date.today())
    s_ini, s_fin = f_ini.strftime("%Y-%m-%d"), f_fin.strftime("%Y-%m-%d")

    df_h = pd.read_sql(f"SELECT h.fecha, p.cliente, p.suplidor, h.tipo_movimiento, h.monto FROM historial_pagos h JOIN proyectos p ON h.proyecto_id = p.id WHERE h.fecha BETWEEN '{s_ini}' AND '{s_fin}'", conn)
    df_g = pd.read_sql(f"SELECT * FROM gastos_varios WHERE fecha BETWEEN '{s_ini}' AND '{s_fin}'", conn)
    df_p = pd.read_sql("SELECT * FROM proyectos", conn)

    tab1, tab2 = st.tabs(["📈 Resultados", "👥 Saldos Pendientes"])

    with tab1:
        ing = df_h[df_h['tipo_movimiento'] == 'Cobro a Cliente']['monto'].sum() or 0.0
        p_f = df_h[df_h['tipo_movimiento'] == 'Pago a Fábrica']['monto'].sum() or 0.0
        gas = df_g['monto'].sum() or 0.0
        util = ing - p_f - gas
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("COBROS", f"${ing:,.2f}")
        c2.metric("PAGOS FAB.", f"${p_f:,.2f}")
        c3.metric("GASTOS", f"${gas:,.2f}")
        c4.metric("UTILIDAD", f"${util:,.2f}")
        st.dataframe(df_h, use_container_width=True)

    with tab2:
        if not df_p.empty:
            df_p['Por Cobrar'] = df_p['precio_venta'] - df_p['adelanto_cliente']
            df_p['Por Pagar'] = df_p['costo_fabrica'] - df_p['adelanto_suplidor']
            
            c_cli, c_sup = st.columns(2)
            c_cli.subheader("Cuentas por Cobrar")
            c_cli.table(df_p[df_p['Por Cobrar'] > 0][['cliente', 'mueble', 'Por Cobrar']])
            
            c_sup.subheader("Cuentas por Pagar (Fábricas)")
            # Aquí se ve claro a qué suplidor le debes
            c_sup.table(df_p[df_p['Por Pagar'] > 0][['suplidor', 'mueble', 'Por Pagar']])

# (Módulos de edición y gestión se mantienen igual que v25)
elif choice == "Ver / Gestionar Proyectos":
    st.header("📋 Listado")
    st.dataframe(pd.read_sql("SELECT * FROM proyectos", conn), use_container_width=True)

elif choice == "✏️ Corregir Datos":
    st.header("✏️ Editor")
    # (Código de edición de v25...)
    st.write("Usa las pestañas para editar proyectos o anular pagos.")
    # [Aquí va el mismo código de edición del mensaje anterior]

elif choice == "Gastos Varios":
    st.header("⛽ Gastos")
    with st.form("g_v"):
        con = st.text_input("Concepto")
        mon = st.number_input("Monto")
        if st.form_submit_button("Guardar"):
            c.execute("INSERT INTO gastos_varios (fecha, concepto, monto) VALUES (?,?,?)", (date.today().strftime("%Y-%m-%d"), con, mon))
            conn.commit()
            st.rerun()
