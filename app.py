import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# 1. CONEXIÓN Y ESTRUCTURA DE TABLAS
def get_connection():
    return sqlite3.connect('muebles_negocio.db', check_same_thread=False)

conn = get_connection()
c = conn.cursor()

# Tabla de Proyectos (con fecha de creación)
c.execute('''CREATE TABLE IF NOT EXISTS proyectos 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha_creacion TEXT, cliente TEXT, 
              mueble TEXT, suplidor TEXT, precio_venta REAL, costo_fabrica REAL, 
              adelanto_cliente REAL, adelanto_suplidor REAL, estado TEXT)''')

# Nueva Tabla de Historial de Transacciones para ver fechas de cada abono
c.execute('''CREATE TABLE IF NOT EXISTS historial_pagos 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, proyecto_id INTEGER, fecha TEXT, 
              tipo_movimiento TEXT, monto REAL, detalle TEXT)''')

c.execute('''CREATE TABLE IF NOT EXISTS gastos_varios 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, concepto TEXT, monto REAL)''')
conn.commit()

st.set_page_config(page_title="Muebles Pro v6", layout="wide")

# --- MENÚ LATERAL ---
st.sidebar.title("🛠️ Panel de Control")
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
                fecha_hoy = datetime.now().strftime("%Y-%m-%d %H:%M")
                c.execute("INSERT INTO proyectos (fecha_creacion, cliente, mueble, suplidor, precio_venta, costo_fabrica, adelanto_cliente, adelanto_suplidor, estado) VALUES (?,?,?,?,?,?,?,?,?)",
                          (fecha_hoy, cliente, mueble, suplidor, p_venta, c_fabrica, 0.0, 0.0, "En Proceso"))
                conn.commit()
                st.success(f"✅ Proyecto creado el {fecha_hoy}")

# --- OPCIÓN 2: VER / GESTIONAR ---
elif choice == "Ver / Gestionar Proyectos":
    st.header("📋 Gestión de Proyectos")
    df_proyectos = pd.read_sql("SELECT * FROM proyectos", conn)
    if not df_proyectos.empty:
        with st.expander("⚙️ ACCIONES RÁPIDAS (Eliminar/Entregar)"):
            col_id, col_acc, col_btn = st.columns([1, 2, 1])
            id_target = col_id.number_input("ID Proyecto:", min_value=1, step=1)
            accion_tipo = col_acc.selectbox("Acción:", ["---", "Marcar como ENTREGADO", "ELIMINAR PERMANENTE"])
            if col_btn.button("EJECUTAR"):
                if accion_tipo == "Marcar como ENTREGADO":
                    c.execute("UPDATE proyectos SET estado = 'Entregado' WHERE id = ?", (id_target,))
                elif accion_tipo == "ELIMINAR PERMANENTE":
                    c.execute("DELETE FROM proyectos WHERE id = ?", (id_target,))
                conn.commit()
                st.rerun()
        st.dataframe(df_proyectos, use_container_width=True)
    else:
        st.info("No hay proyectos.")

# --- OPCIÓN 3: PAGOS Y ABONOS (Con fecha automática) ---
elif choice == "Pagos y Abonos":
    st.header("💰 Registro de Abonos con Fecha")
    df = pd.read_sql("SELECT id, cliente, mueble FROM proyectos WHERE estado != 'Entregado'", conn)
    if not df.empty:
        opciones = [f"ID {row['id']} - {row['cliente']}" for _, row in df.iterrows()]
        selec = st.selectbox("Seleccione Proyecto:", opciones)
        id_p = int(selec.split(" ")[1])
        
        col_t, col_f = st.columns(2)
        tipo = col_t.radio("Movimiento:", ["Cobro a Cliente", "Pago a Fábrica"])
        fecha_pago = col_f.date_input("Fecha del pago:", datetime.now())
        
        monto = st.number_input("Monto ($)", min_value=0.0)
        detalle = st.text_input("Nota opcional (ej: Transferencia Banco X, Efectivo)")
        
        if st.button("Guardar Transacción"):
            # 1. Actualizar el acumulado en la tabla proyectos
            campo = "adelanto_cliente" if "Cliente" in tipo else "adelanto_suplidor"
            c.execute(f"UPDATE proyectos SET {campo} = {campo} + ? WHERE id = ?", (monto, id_p))
            
            # 2. Guardar en el historial con fecha
            c.execute("INSERT INTO historial_pagos (proyecto_id, fecha, tipo_movimiento, monto, detalle) VALUES (?,?,?,?,?)",
                      (id_p, fecha_pago.strftime("%Y-%m-%d"), tipo, monto, detalle))
            
            conn.commit()
            st.success(f"✅ {tipo} de ${monto} registrado el {fecha_pago}")
    else:
        st.warning("No hay proyectos activos.")

# --- OPCIÓN 4: CORREGIR DATOS ---
elif choice == "✏️ Corregir Datos":
    st.header("✏️ Modificar Datos")
    df = pd.read_sql("SELECT * FROM proyectos", conn)
    if not df.empty:
        opciones = [f"ID {row['id']} - {row['cliente']}" for _, row in df.iterrows()]
        selec = st.selectbox("Proyecto a editar:", opciones)
        id_p = int(selec.split(" ")[1])
        p = df[df['id'] == id_p].iloc[0]
        
        with st.form("edit_form"):
            c1, c2 = st.columns(2)
            n_pv = c1.number_input("Precio Venta", value=float(p['precio_venta']))
            n_cf = c2.number_input("Costo Fábrica", value=float(p['costo_fabrica']))
            n_ac = c1.number_input("Total Adelantos Cliente", value=float(p['adelanto_cliente']))
            n_as = c2.number_input("Total Pagado a Fábrica", value=float(p['adelanto_suplidor']))
            n_est = st.selectbox("Estado", ["En Proceso", "Entregado"], index=0 if p['estado']=="En Proceso" else 1)
            
            if st.form_submit_button("Actualizar"):
                c.execute("UPDATE proyectos SET precio_venta=?, costo_fabrica=?, adelanto_cliente=?, adelanto_suplidor=?, estado=? WHERE id=?",
                          (n_pv, n_cf, n_ac, n_as, n_est, id_p))
                conn.commit()
                st.success("Datos actualizados.")

# --- OPCIÓN 5: GASTOS VARIOS ---
elif choice == "Gastos Varios":
    st.header("⛽ Gastos Extras")
    with st.form("g"):
        con = st.text_input("Concepto")
        mon = st.number_input("Monto", min_value=0.0)
        fec = st.date_input("Fecha", datetime.now())
        if st.form_submit_button("Guardar"):
            c.execute("INSERT INTO gastos_varios (fecha, concepto, monto) VALUES (?,?,?)", (fec.strftime("%Y-%m-%d"), con, mon))
            conn.commit()
            st.success("Gasto guardado.")
    st.dataframe(pd.read_sql("SELECT * FROM gastos_varios", conn), use_container_width=True)

# --- OPCIÓN 6: REPORTES ---
elif choice == "Reportes y Respaldo":
    st.header("📊 Resumen y Fechas")
    df = pd.read_sql("SELECT * FROM proyectos", conn)
    df_h = pd.read_sql("SELECT * FROM historial_pagos", conn)
    
    t1, t2, t3 = st.tabs(["💰 Deudas", "📅 Historial de Pagos", "📉 Balance"])
    
    with t1:
        if not df.empty:
            df['Pendiente'] = df['precio_venta'] - df['adelanto_cliente']
            st.subheader("Por Cobrar")
            st.table(df[df['Pendiente']>0][['cliente', 'Pendiente']])
        
    with t2:
        st.subheader("Registro cronológico de entradas y salidas")
        if not df_h.empty:
            st.dataframe(df_h.sort_values(by="fecha", ascending=False), use_container_width=True)
        else:
            st.info("No hay pagos registrados aún.")
            
    with t3:
        if not df.empty:
            ventas = df['precio_venta'].sum()
            costos = df['costo_fabrica'].sum()
            gastos = pd.read_sql("SELECT SUM(monto) FROM gastos_varios", conn).iloc[0,0] or 0
            st.metric("Utilidad Neta Actual", f"${ventas - costos - gastos:,.2f}")
            st.download_button("Descargar Todo (CSV)", df.to_csv(index=False).encode('utf-8'), "respaldo.csv")
