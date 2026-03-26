import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# 1. CONEXIÓN SEGURA A BASE DE DATOS
def get_connection():
    return sqlite3.connect('muebles_negocio.db', check_same_thread=False)

conn = get_connection()
c = conn.cursor()

# Crear tablas con nombres limpios
c.execute('''CREATE TABLE IF NOT EXISTS proyectos 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, cliente TEXT, mueble TEXT, 
              suplidor TEXT, precio_venta REAL, costo_fabrica REAL, 
              adelanto_cliente REAL, adelanto_suplidor REAL, estado TEXT)''')

c.execute('''CREATE TABLE IF NOT EXISTS gastos_varios 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, concepto TEXT, monto REAL)''')
conn.commit()

st.set_page_config(page_title="Muebles Pro v4", layout="wide")

# --- MENÚ LATERAL ---
st.sidebar.title("🛠️ Panel de Control")
menu = ["Nuevo Proyecto", "Ver / Gestionar Proyectos", "Pagos y Abonos", "Gastos Varios", "Reportes y Respaldo"]
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
                c.execute("INSERT INTO proyectos (cliente, mueble, suplidor, precio_venta, costo_fabrica, adelanto_cliente, adelanto_suplidor, estado) VALUES (?,?,?,?,?,?,?,?)",
                          (cliente, mueble, suplidor, p_venta, c_fabrica, 0.0, 0.0, "En Proceso"))
                conn.commit()
                st.success("✅ Proyecto guardado.")
            else:
                st.error("Error: Cliente y Suplidor son obligatorios.")

# --- OPCIÓN 2: VER / GESTIONAR (CON ESCUDO DE ERRORES) ---
elif choice == "Ver / Gestionar Proyectos":
    st.header("📋 Gestión de Proyectos")
    
    try:
        # Forzar lectura fresca de la base de datos
        df_proyectos = pd.read_sql("SELECT * FROM proyectos", conn)
        
        if not df_proyectos.empty:
            st.subheader("⚠️ Acciones sobre Proyectos")
            col_id, col_acc, col_btn = st.columns([1, 2, 1])
            id_target = col_id.number_input("ID del Proyecto:", min_value=1, step=1)
            accion_tipo = col_acc.selectbox("Seleccione Acción:", ["---", "Marcar como ENTREGADO", "ELIMINAR PERMANENTE"])
            
            if col_btn.button("EJECUTAR", use_container_width=True):
                if accion_tipo == "Marcar como ENTREGADO":
                    c.execute("UPDATE proyectos SET estado = 'Entregado' WHERE id = ?", (id_target,))
                elif accion_tipo == "ELIMINAR PERMANENTE":
                    c.execute("DELETE FROM proyectos WHERE id = ?", (id_target,))
                conn.commit()
                st.success("Acción realizada. Por favor, cambie de pestaña y vuelva para ver los cambios.")

            st.divider()
            st.subheader("Tabla de Proyectos Registrados")
            st.dataframe(df_proyectos, use_container_width=True)
        else:
            st.info("No hay proyectos en la base de datos. Use la pestaña 'Nuevo Proyecto'.")
            
    except Exception as e:
        st.error(f"Ocurrió un error al cargar la tabla: {e}")
        st.write("Es posible que necesites borrar el archivo .db y empezar de cero si la estructura se dañó.")

# --- OPCIÓN 3: PAGOS Y ABONOS ---
elif choice == "Pagos y Abonos":
    st.header("💰 Registro de Abonos")
    df = pd.read_sql("SELECT id, cliente, mueble FROM proyectos WHERE estado != 'Entregado'", conn)
    if not df.empty:
        opciones = [f"ID {row['id']} - {row['cliente']}" for _, row in df.iterrows()]
        selec = st.selectbox("Seleccione Proyecto:", opciones)
        id_p = int(selec.split(" ")[1])
        tipo = st.radio("Movimiento:", ["Cobro a Cliente", "Pago a Fábrica"])
        monto = st.number_input("Monto ($)", min_value=0.0)
        
        if st.button("Guardar Pago"):
            campo = "adelanto_cliente" if "Cliente" in tipo else "adelanto_suplidor"
            c.execute(f"UPDATE proyectos SET {campo} = {campo} + ? WHERE id = ?", (monto, id_p))
            conn.commit()
            st.success("Saldo actualizado.")
    else:
        st.warning("No hay proyectos activos (En Proceso).")

# --- OPCIÓN 4: GASTOS VARIOS ---
elif choice == "Gastos Varios":
    st.header("⛽ Gastos de Operación")
    with st.form("form_gastos"):
        concepto = st.text_input("Concepto")
        monto_g = st.number_input("Monto ($)", min_value=0.0)
        if st.form_submit_button("Registrar Gasto"):
            fecha_hoy = datetime.now().strftime("%Y-%m-%d")
            c.execute("INSERT INTO gastos_varios (fecha, concepto, monto) VALUES (?,?,?)", (fecha_hoy, concepto, monto_g))
            conn.commit()
            st.success("Gasto registrado.")
    df_g = pd.read_sql("SELECT * FROM gastos_varios", conn)
    st.dataframe(df_g, use_container_width=True)

# --- OPCIÓN 5: REPORTES ---
elif choice == "Reportes y Respaldo":
    st.header("📊 Resumen Financiero")
    df = pd.read_sql("SELECT * FROM proyectos", conn)
    df_g = pd.read_sql("SELECT * FROM gastos_varios", conn)
    
    if not df.empty:
        df['Cobro Pendiente'] = df['precio_venta'] - df['adelanto_cliente']
        df['Pago Pendiente'] = df['costo_fabrica'] - df['adelanto_suplidor']
        
        t1, t2, t3 = st.tabs(["👥 Deudas Clientes", "🏭 Deudas Fábricas", "📉 Balance Final"])
        with t1:
            res_c = df.groupby('cliente')['Cobro Pendiente'].sum().reset_index()
            st.table(res_c[res_c['Cobro Pendiente'] > 0])
        with t2:
            res_s = df.groupby('suplidor')['Pago Pendiente'].sum().reset_index()
            st.table(res_s[res_s['Pago Pendiente'] > 0])
        with t3:
            utilidad = df['precio_venta'].sum() - df['costo_fabrica'].sum()
            gastos = df_g['monto'].sum() if not df_g.empty else 0
            st.metric("Utilidad Neta Actual", f"${utilidad - gastos:,.2f}")

        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Descargar Respaldo", csv, "respaldo.csv")
