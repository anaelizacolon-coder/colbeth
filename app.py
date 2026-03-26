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

st.set_page_config(page_title="Gestión Muebles Pro", layout="wide")
st.sidebar.title("🛠️ Menú Principal")
menu = ["Nuevo Proyecto", "Ver / Editar Proyectos", "Pagos y Abonos", "Reportes y Respaldo"]
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
                          (cliente.upper(), mueble, suplidor.upper(), p_venta, c_fabrica, 0.0, 0.0, "En Proceso"))
                conn.commit()
                st.success(f"✅ Proyecto de {cliente} guardado.")
            else:
                st.error("Rellena los campos obligatorios.")

# --- OPCIÓN 2: VER / EDITAR / ELIMINAR ---
elif choice == "Ver / Editar Proyectos":
    st.header("📋 Gestión de Proyectos")
    df = pd.read_sql("SELECT * FROM proyectos", conn)
    
    if not df.empty:
        busqueda = st.text_input("🔍 Buscar por cliente o mueble:")
        if busqueda:
            df = df[df['cliente'].str.contains(busqueda, case=False) | df['mueble'].str.contains(busqueda, case=False)]
        
        st.dataframe(df, use_container_width=True)
        
        st.write("---")
        st.subheader("⚙️ Acciones de Proyecto")
        col_ed1, col_ed2 = st.columns(2)
        
        id_accion = col_ed1.number_input("Ingrese el ID del proyecto para modificar/eliminar:", min_value=1, step=1)
        accion = col_ed2.selectbox("Acción a realizar:", ["Seleccionar...", "Cambiar a Entregado", "Eliminar Proyecto"])
        
        if st.button("Ejecutar Acción"):
            if accion == "Cambiar a Entregado":
                c.execute("UPDATE proyectos SET estado = 'Entregado' WHERE id = ?", (id_accion,))
                conn.commit()
                st.success(f"Proyecto {id_accion} marcado como Entregado.")
                st.rerun()
            elif accion == "Eliminar Proyecto":
                c.execute("DELETE FROM proyectos WHERE id = ?", (id_accion,))
                conn.commit()
                st.warning(f"Proyecto {id_accion} eliminado permanentemente.")
                st.rerun()
    else:
        st.info("No hay proyectos.")

# --- OPCIÓN 3: PAGOS Y ABONOS ---
elif choice == "Pagos y Abonos":
    st.header("💰 Registro de Flujo de Caja")
    df = pd.read_sql("SELECT id, cliente, mueble FROM proyectos WHERE estado != 'Entregado'", conn)
    
    if not df.empty:
        opciones = [f"ID {row['id']} - {row['cliente']} ({row['mueble'][:20]}...)" for index, row in df.iterrows()]
        seleccion = st.selectbox("Seleccione el Proyecto Activo:", opciones)
        id_proy = int(seleccion.split(" ")[1])
        
        tipo_pago = st.radio("Tipo de movimiento:", ["Cobro a Cliente (Ingreso)", "Pago a Fábrica (Egreso)"])
        monto = st.number_input("Monto ($)", min_value=0.0)
        
        if st.button("Registrar Transacción"):
            campo = "adelanto_cliente" if "Cliente" in tipo_pago else "adelanto_suplidor"
            c.execute(f"UPDATE proyectos SET {campo} = {campo} + ? WHERE id = ?", (monto, id_proy))
            conn.commit()
            st.success("Saldo actualizado con éxito.")
    else:
        st.warning("No hay proyectos activos para cobrar/pagar.")

# --- OPCIÓN 4: REPORTES SUMARIZADOS ---
elif choice == "Reportes y Respaldo":
    st.header("📊 Resumen de Cuentas")
    df = pd.read_sql("SELECT * FROM proyectos", conn)
    
    if not df.empty:
        df['Deuda Cliente'] = df['precio_venta'] - df['adelanto_cliente']
        df['Deuda Suplidor'] = df['costo_fabrica'] - df['adelanto_suplidor']
        
        t1, t2, t3 = st.tabs(["👥 Resumen por Cliente", "🏭 Resumen por Suplidor", "📦 Respaldo"])
        
        with t1:
            st.subheader("¿Cuánto me debe cada cliente?")
            resumen_clientes = df.groupby('cliente')['Deuda Cliente'].sum().reset_index()
            resumen_clientes = resumen_clientes[resumen_clientes['Deuda Cliente'] > 0]
            st.table(resumen_clientes.style.format({"Deuda Cliente": "${:,.2f}"}))
            st.metric("TOTAL POR COBRAR", f"${resumen_clientes['Deuda Cliente'].sum():,.2f}")

        with t2:
            st.subheader("¿Cuánto le debo a cada fábrica?")
            resumen_suplidores = df.groupby('suplidor')['Deuda Suplidor'].sum().reset_index()
            resumen_suplidores = resumen_suplidores[resumen_suplidores['Deuda Suplidor'] > 0]
            st.table(resumen_suplidores.style.format({"Deuda Suplidor": "${:,.2f}"}))
            st.metric("TOTAL POR PAGAR", f"${resumen_suplidores['Deuda Suplidor'].sum():,.2f}")
            
        with t3:
            st.subheader("Exportar Datos")
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button("Descargar Excel (CSV)", csv, f"respaldo_{datetime.now().strftime('%Y-%m-%d')}.csv", "text/csv")
    else:
        st.info("Sin datos.")
