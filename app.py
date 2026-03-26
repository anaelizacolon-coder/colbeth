import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# 1. CONFIGURACIÓN DE BASE DE DATOS
conn = sqlite3.connect('muebles_negocio.db', check_same_thread=False)
c = conn.cursor()

c.execute('''CREATE TABLE IF NOT EXISTS proyectos 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, 
              cliente TEXT, 
              mueble TEXT, 
              suplidor TEXT, 
              precio_venta REAL, 
              costo_fabrica REAL, 
              adelanto_cliente REAL, 
              adelanto_suplidor REAL, 
              estado TEXT)''')
conn.commit()

# 2. INTERFAZ LATERAL
st.set_page_config(page_title="Control de Muebles", layout="wide")
st.sidebar.title("🛠️ Menú Principal")
menu = ["Nuevo Proyecto", "Ver Proyectos", "Pagos y Abonos", "Reportes y Respaldo"]
choice = st.sidebar.selectbox("Seleccione una opción", menu)

# --- OPCIÓN 1: NUEVO PROYECTO ---
if choice == "Nuevo Proyecto":
    st.header("📝 Registrar Nuevo Proyecto")
    with st.form("form_nuevo"):
        col1, col2 = st.columns(2)
        cliente = col1.text_input("Nombre del Cliente")
        suplidor = col2.text_input("Nombre del Suplidor (Fábrica)")
        mueble = st.text_area("Descripción del Mueble y Materiales")
        
        c1, c2 = st.columns(2)
        p_venta = c1.number_input("Precio de Venta al Cliente ($)", min_value=0.0)
        c_fabrica = c2.number_input("Costo de Fábrica ($)", min_value=0.0)
        
        if st.form_submit_button("Guardar Proyecto"):
            if cliente and suplidor:
                c.execute("INSERT INTO proyectos (cliente, mueble, suplidor, precio_venta, costo_fabrica, adelanto_cliente, adelanto_suplidor, estado) VALUES (?,?,?,?,?,?,?,?)",
                          (cliente, mueble, suplidor, p_venta, c_fabrica, 0.0, 0.0, "En Proceso"))
                conn.commit()
                st.success(f"✅ Proyecto de {cliente} guardado correctamente.")
            else:
                st.error("Por favor rellena los nombres de Cliente y Suplidor.")

# --- OPCIÓN 2: VER PROYECTOS ---
elif choice == "Ver Proyectos":
    st.header("📋 Listado General de Proyectos")
    df = pd.read_sql("SELECT * FROM proyectos", conn)
    if not df.empty:
        busqueda = st.text_input("🔍 Buscar cliente o mueble:")
        if busqueda:
            df = df[df['cliente'].str.contains(busqueda, case=False) | df['mueble'].str.contains(busqueda, case=False)]
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No hay proyectos registrados aún.")

# --- OPCIÓN 3: PAGOS Y ABONOS ---
elif choice == "Pagos y Abonos":
    st.header("💰 Registro de Pagos (Adelantos y Abonos)")
    df = pd.read_sql("SELECT id, cliente, mueble, suplidor FROM proyectos", conn)
    
    if not df.empty:
        # Seleccionar proyecto por ID y Nombre
        opciones = [f"ID {row['id']} - {row['cliente']} ({row['mueble'][:20]}...)" for index, row in df.iterrows()]
        seleccion = st.selectbox("Seleccione el Proyecto:", opciones)
        id_proy = int(seleccion.split(" ")[1])
        
        tipo_pago = st.radio("¿Quién realiza/recibe el pago?", ["Cliente (Me pagan a mí)", "Suplidor (Yo pago a fábrica)"])
        monto = st.number_input("Monto del Pago ($)", min_value=0.0)
        
        if st.button("Registrar Pago"):
            campo = "adelanto_cliente" if "Cliente" in tipo_pago else "adelanto_suplidor"
            c.execute(f"UPDATE proyectos SET {campo} = {campo} + ? WHERE id = ?", (monto, id_proy))
            conn.commit()
            st.success("💸 Pago registrado y saldo actualizado.")
    else:
        st.warning("Debe crear un proyecto primero.")

# --- OPCIÓN 4: REPORTES Y RESPALDO ---
elif choice == "Reportes y Respaldo":
    st.header("📊 Análisis Financiero")
    df = pd.read_sql("SELECT * FROM proyectos", conn)
    
    if not df.empty:
        # Cálculos de saldos
        df['Por Cobrar (Cliente)'] = df['precio_venta'] - df['adelanto_cliente']
        df['Por Pagar (Suplidor)'] = df['costo_fabrica'] - df['adelanto_suplidor']
        
        tab1, tab2, tab3 = st.tabs(["💵 Cuentas por Cobrar", "🏭 Cuentas por Pagar", "📈 Beneficios Totales"])
        
        with tab1:
            st.subheader("Saldos pendientes de Clientes")
            cobros = df[df['Por Cobrar (Cliente)'] > 0][['cliente', 'mueble', 'precio_venta', 'adelanto_cliente', 'Por Cobrar (Cliente)']]
            st.table(cobros)
            st.metric("Total por Cobrar", f"${cobros['Por Cobrar (Cliente)'].sum():,.2f}")

        with tab2:
            st.subheader("Deudas pendientes con Suplidores")
            pagos = df[df['Por Pagar (Suplidor)'] > 0][['suplidor', 'mueble', 'costo_fabrica', 'adelanto_suplidor', 'Por Pagar (Suplidor)']]
            st.table(pagos)
            st.metric("Total por Pagar", f"${pagos['Por Pagar (Suplidor)'].sum():,.2f}")
            
        with tab3:
            total_v = df['precio_venta'].sum()
            total_c = df['costo_fabrica'].sum()
            st.metric("Ventas Totales", f"${total_v:,.2f}")
            st.metric("Costo Total Fábrica", f"${total_c:,.2f}")
            st.metric("Beneficio Bruto Estimado", f"${(total_v - total_c):,.2f}", delta_color="normal")

        st.write("---")
        st.subheader("💾 Copia de Seguridad")
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Descargar todo a Excel (CSV)",
            data=csv,
            file_name=f'respaldo_negocio_{datetime.now().strftime("%Y-%m-%d")}.csv',
            mime='text/csv',
        )
    else:
        st.info("No hay datos para generar reportes.")
