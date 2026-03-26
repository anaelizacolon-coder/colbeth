import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# 1. CONFIGURACIÓN DE BASE DE DATOS
conn = sqlite3.connect('muebles_negocio.db', check_same_thread=False)
c = conn.cursor()

# Tablas para Proyectos y Gastos
c.execute('''CREATE TABLE IF NOT EXISTS proyectos 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, cliente TEXT, mueble TEXT, 
              suplidor TEXT, precio_venta REAL, costo_fabrica REAL, 
              adelanto_cliente REAL, adelanto_suplidor REAL, estado TEXT)''')

c.execute('''CREATE TABLE IF NOT EXISTS gastos_varios 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, concepto TEXT, monto REAL)''')
conn.commit()

st.set_page_config(page_title="Muebles Pro v2", layout="wide")
st.sidebar.title("🛠️ Panel de Control")
menu = ["Nuevo Proyecto", "Ver / Gestionar Proyectos", "Pagos y Abonos", "Gastos Varios", "Reportes y Respaldo"]
choice = st.sidebar.selectbox("Seleccione una opción", menu)

# --- OPCIÓN 1: NUEVO PROYECTO ---
if choice == "Nuevo Proyecto":
    st.header("📝 Registrar Nuevo Proyecto")
    with st.form("form_nuevo"):
        col1, col2 = st.columns(2)
        cliente = col1.text_input("Nombre del Cliente").upper()
        suplidor = col2.text_input("Nombre del Suplidor (Fábrica)").upper()
        mueble = st.text_area("Descripción del Mueble / Materiales")
        
        c1, c2 = st.columns(2)
        p_venta = c1.number_input("Precio de Venta ($)", min_value=0.0)
        c_fabrica = c2.number_input("Costo de Fábrica ($)", min_value=0.0)
        
        if st.form_submit_button("Guardar Proyecto"):
            if cliente and suplidor:
                c.execute("INSERT INTO proyectos (cliente, mueble, suplidor, precio_venta, costo_fabrica, adelanto_cliente, adelanto_suplidor, estado) VALUES (?,?,?,?,?,?,?,?)",
                          (cliente, mueble, suplidor, p_venta, c_fabrica, 0.0, 0.0, "En Proceso"))
                conn.commit()
                st.success("✅ Proyecto guardado.")
            else:
                st.error("Rellena Cliente y Suplidor.")

# --- OPCIÓN 2: VER / GESTIONAR (BOTONES ARRIBA) ---
elif choice == "Ver / Gestionar Proyectos":
    st.header("📋 Gestión de Proyectos")
    
    # ACCIONES RÁPIDAS (BOTONES)
    with st.expander("⚠️ PANEL DE ELIMINAR O EDITAR", expanded=True):
        col_id, col_acc, col_btn = st.columns([1, 2, 1])
        id_target = col_id.number_input("ID Proyecto:", min_value=1, step=1)
        accion_tipo = col_acc.selectbox("Acción:", ["Seleccionar...", "Marcar como ENTREGADO", "ELIMINAR PERMANENTE"])
        
        if col_btn.button("EJECUTAR ACCIÓN", use_container_width=True):
            if accion_tipo == "Marcar como ENTREGADO":
                c.execute("UPDATE proyectos SET estado = 'Entregado' WHERE id = ?", (id_target,))
                conn.commit()
                st.success(f"ID {id_target} actualizado.")
                st.rerun()
            elif accion_tipo == "ELIMINAR PERMANENTE":
                c.execute("DELETE FROM proyectos WHERE id = ?", (id_target,))
                conn.commit()
                st.warning(f"ID {id_target} eliminado.")
                st.rerun()

    st.write("---")
    df = pd.read_sql("SELECT * FROM proyectos", conn)
    if not df.empty:
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No hay proyectos.")

# --- OPCIÓN 3: PAGOS Y ABONOS ---
elif choice == "Pagos y Abonos":
    st.header("💰 Registro de Abonos")
    df = pd.read_sql("SELECT id, cliente, mueble FROM proyectos WHERE estado != 'Entregado'", conn)
    if not df.empty:
        opciones = [f"ID {row['id']} - {row['cliente']} ({row['mueble'][:15]}...)" for _, row in df.iterrows()]
        selec = st.selectbox("Proyecto:", opciones)
        id_p = int(selec.split(" ")[1])
        
        tipo = st.radio("Movimiento:", ["Cobro a Cliente", "Pago a Fábrica"])
        monto = st.number_input("Monto ($)", min_value=0.0)
        
        if st.button("Guardar Pago"):
            campo = "adelanto_cliente" if "Cliente" in tipo else "adelanto_suplidor"
            c.execute(f"UPDATE proyectos SET {campo} = {campo} + ? WHERE id = ?", (monto, id_p))
            conn.commit()
            st.success("Pago registrado.")
    else:
        st.warning("No hay proyectos activos.")

# --- OPCIÓN 4: GASTOS VARIOS ---
elif choice == "Gastos Varios":
    st.header("⛽ Gastos Extras (Gasolina, Herramientas, etc.)")
    with st.form("form_gastos"):
        concepto = st.text_input("Concepto del Gasto")
        monto_g = st.number_input("Monto del Gasto ($)", min_value=0.0)
        if st.form_submit_button("Registrar Gasto"):
            fecha_hoy = datetime.now().strftime("%Y-%m-%d")
            c.execute("INSERT INTO gastos_varios (fecha, concepto, monto) VALUES (?,?,?)", (fecha_hoy, concepto, monto_g))
            conn.commit()
            st.success("Gasto guardado.")
    
    st.write("### Historial de Gastos")
    df_g = pd.read_sql("SELECT * FROM gastos_varios", conn)
    st.table(df_g)

# --- OPCIÓN 5: REPORTES SUMARIZADOS ---
elif choice == "Reportes y Respaldo":
    st.header("📊 Resumen General")
    df = pd.read_sql("SELECT * FROM proyectos", conn)
    df_g = pd.read_sql("SELECT * FROM gastos_varios", conn)
    
    if not df.empty:
        df['D. Cliente'] = df['precio_venta'] - df['adelanto_cliente']
        df['D. Suplidor'] = df['costo_fabrica'] - df['adelanto_suplidor']
        
        t1, t2, t3 = st.tabs(["👥 Deudas Clientes", "🏭 Deudas Fábricas", "📉 Ganancia Real"])
        
        with t1:
            res_c = df.groupby('cliente')['D. Cliente'].sum().reset_index()
            st.table(res_c[res_c['D. Cliente'] > 0])
            st.metric("TOTAL POR COBRAR", f"${res_c['D. Cliente'].sum():,.2f}")

        with t2:
            res_s = df.groupby('suplidor')['D. Suplidor'].sum().reset_index()
            st.table(res_s[res_s['D. Suplidor'] > 0])
            st.metric("TOTAL POR PAGAR", f"${res_s['D. Suplidor'].sum():,.2f}")
            
        with t3:
            utilidad_proyectos = df['precio_venta'].sum() - df['costo_fabrica'].sum()
            total_gastos_varios = df_g['monto'].sum() if not df_g.empty else 0
            st.metric("Ventas Totales", f"${df['precio_venta'].sum():,.2f}")
            st.metric("Beneficio Proyectos", f"${utilidad_proyectos:,.2f}")
            st.metric("Gastos Varios", f"- ${total_gastos_varios:,.2f}")
            st.subheader(f"Ganancia Real Neta: ${utilidad_proyectos - total_gastos_varios:,.2f}")

        st.download_button("Descargar Respaldo CSV", df.to_csv(index=False).encode('utf-8'), "respaldo.csv")
