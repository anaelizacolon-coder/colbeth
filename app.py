import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# 1. CONEXIÓN Y ESTRUCTURA
def get_connection():
    return sqlite3.connect('muebles_negocio.db', check_same_thread=False)

conn = get_connection()
c = conn.cursor()

c.execute('''CREATE TABLE IF NOT EXISTS proyectos 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha_creacion TEXT, cliente TEXT, 
              mueble TEXT, suplidor TEXT, precio_venta REAL, costo_fabrica REAL, 
              adelanto_cliente REAL, adelanto_suplidor REAL, estado TEXT)''')

c.execute('''CREATE TABLE IF NOT EXISTS historial_pagos 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, proyecto_id INTEGER, fecha TEXT, 
              tipo_movimiento TEXT, monto REAL, detalle TEXT)''')

c.execute('''CREATE TABLE IF NOT EXISTS gastos_varios 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, concepto TEXT, monto REAL)''')
conn.commit()

st.set_page_config(page_title="Control Mueblería Pro", layout="wide")

# --- MENÚ LATERAL ---
st.sidebar.title("🛠️ Gestión de Negocio")
menu = ["Nuevo Proyecto", "Ver / Gestionar Proyectos", "Pagos y Abonos", "✏️ Corregir Datos", "Gastos Varios", "Reportes y Respaldo"]
choice = st.sidebar.selectbox("Seleccione una opción", menu)

# --- OPCIÓN 1: NUEVO PROYECTO ---
if choice == "Nuevo Proyecto":
    st.header("📝 Registrar Nuevo Proyecto")
    with st.form("form_nuevo", clear_on_submit=True):
        col1, col2 = st.columns(2)
        cliente = col1.text_input("Nombre del Cliente").upper()
        suplidor = col2.text_input("Nombre del Suplidor (Fábrica)").upper()
        mueble = st.text_area("Descripción del Mueble / Materiales")
        c1, c2 = st.columns(2)
        p_venta = c1.number_input("Precio de Venta ($)", min_value=0.0)
        c_fabrica = c2.number_input("Costo de Fábrica ($)", min_value=0.0)
        if st.form_submit_button("Guardar Proyecto"):
            if cliente and suplidor:
                fecha_hoy = datetime.now().strftime("%Y-%m-%d")
                c.execute("INSERT INTO proyectos (fecha_creacion, cliente, mueble, suplidor, precio_venta, costo_fabrica, adelanto_cliente, adelanto_suplidor, estado) VALUES (?,?,?,?,?,?,?,?,?)",
                          (fecha_hoy, cliente, mueble, suplidor, p_venta, c_fabrica, 0.0, 0.0, "En Proceso"))
                conn.commit()
                st.success(f"✅ Proyecto creado.")

# --- OPCIÓN 2: VER / GESTIONAR ---
elif choice == "Ver / Gestionar Proyectos":
    st.header("📋 Todos los Proyectos")
    df_p = pd.read_sql("SELECT * FROM proyectos", conn)
    if not df_p.empty:
        st.dataframe(df_p, use_container_width=True)
    else:
        st.info("No hay proyectos.")

# --- OPCIÓN 3: PAGOS Y ABONOS ---
elif choice == "Pagos y Abonos":
    st.header("💰 Registrar Abono")
    df = pd.read_sql("SELECT id, cliente, mueble FROM proyectos WHERE estado != 'Entregado'", conn)
    if not df.empty:
        opciones = [f"ID {row['id']} - {row['cliente']}" for _, row in df.iterrows()]
        selec = st.selectbox("Proyecto:", opciones)
        id_p = int(selec.split(" ")[1])
        tipo = st.radio("Tipo:", ["Cobro a Cliente", "Pago a Fábrica"])
        monto = st.number_input("Monto ($)", min_value=0.0)
        if st.button("Guardar"):
            campo = "adelanto_cliente" if "Cliente" in tipo else "adelanto_suplidor"
            c.execute(f"UPDATE proyectos SET {campo} = {campo} + ? WHERE id = ?", (monto, id_p))
            c.execute("INSERT INTO historial_pagos (proyecto_id, fecha, tipo_movimiento, monto) VALUES (?,?,?,?)",
                      (id_p, datetime.now().strftime("%Y-%m-%d"), tipo, monto))
            conn.commit()
            st.success("✅ Registrado.")

# --- OPCIÓN 4: CORREGIR DATOS ---
elif choice == "✏️ Corregir Datos":
    st.header("✏️ Corregir Montos")
    df = pd.read_sql("SELECT * FROM proyectos", conn)
    if not df.empty:
        opciones = [f"ID {row['id']} - {row['cliente']}" for _, row in df.iterrows()]
        selec = st.selectbox("Proyecto:", opciones)
        id_p = int(selec.split(" ")[1])
        p = df[df['id'] == id_p].iloc[0]
        with st.form("edit"):
            n_pv = st.number_input("Precio Venta", value=float(p['precio_venta']))
            n_cf = st.number_input("Costo Fábrica", value=float(p['costo_fabrica']))
            n_ac = st.number_input("Adelanto Cliente", value=float(p['adelanto_cliente']))
            n_as = st.number_input("Pago Fábrica", value=float(p['adelanto_suplidor']))
            if st.form_submit_button("Actualizar"):
                c.execute("UPDATE proyectos SET precio_venta=?, costo_fabrica=?, adelanto_cliente=?, adelanto_suplidor=? WHERE id=?",
                          (n_pv, n_cf, n_ac, n_as, id_p))
                conn.commit()
                st.success("Corregido.")

# --- OPCIÓN 5: GASTOS VARIOS ---
elif choice == "Gastos Varios":
    st.header("⛽ Gastos Extras")
    with st.form("g"):
        con = st.text_input("Concepto")
        mon = st.number_input("Monto", min_value=0.0)
        if st.form_submit_button("Guardar"):
            c.execute("INSERT INTO gastos_varios (fecha, concepto, monto) VALUES (?,?,?)", (datetime.now().strftime("%Y-%m-%d"), con, mon))
            conn.commit()
            st.success("Gasto guardado.")

# --- OPCIÓN 6: REPORTES SUMARIZADOS ---
elif choice == "Reportes y Respaldo":
    st.header("📊 Resumen de Cuentas Sumarizadas")
    
    # Filtro de fecha
    col_f1, col_f2 = st.columns(2)
    f_inicio = col_f1.date_input("Desde:", datetime(datetime.now().year, datetime.now().month, 1))
    f_fin = col_f2.date_input("Hasta:", datetime.now())

    df_p = pd.read_sql(f"SELECT * FROM proyectos", conn)
    
    if not df_p.empty:
        # Cálculos individuales de saldos
        df_p['Saldo Cliente'] = df_p['precio_venta'] - df_p['adelanto_cliente']
        df_p['Saldo Suplidor'] = df_p['costo_fabrica'] - df_p['adelanto_suplidor']
        
        tab1, tab2, tab3 = st.tabs(["👥 Cuentas por Cobrar (Clientes)", "🏭 Cuentas por Pagar (Suplidores)", "📦 Respaldo"])
        
        with tab1:
            st.subheader("Total por Cobrar agrupado por Cliente")
            # Agrupar y sumarizar
            resumen_c = df_p.groupby('cliente')['Saldo Cliente'].sum().reset_index()
            resumen_c = resumen_c[resumen_c['Saldo Cliente'] > 0] # Solo los que deben
            st.table(resumen_c.style.format({"Saldo Cliente": "${:,.2f}"}))
            st.metric("DEUDA TOTAL DE CLIENTES", f"${resumen_c['Saldo Cliente'].sum():,.2f}")

        with tab2:
            st.subheader("Total por Pagar agrupado por Suplidor")
            # Agrupar y sumarizar
            resumen_s = df_p.groupby('suplidor')['Saldo Suplidor'].sum().reset_index()
            resumen_s = resumen_s[resumen_s['Saldo Suplidor'] > 0] # Solo deudas reales
            st.table(resumen_s.style.format({"Saldo Suplidor": "${:,.2f}"}))
            st.metric("DEUDA TOTAL CON FÁBRICAS", f"${resumen_s['Saldo Suplidor'].sum():,.2f}")
            
        with tab3:
            st.download_button("Descargar Excel (CSV)", df_p.to_csv(index=False).encode('utf-8'), "respaldo.csv")
    else:
        st.info("No hay datos para mostrar.")
