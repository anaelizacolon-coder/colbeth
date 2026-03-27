import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, date

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
              tipo_movimiento TEXT, monto REAL)''')

c.execute('''CREATE TABLE IF NOT EXISTS gastos_varios 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, concepto TEXT, monto REAL)''')
conn.commit()

st.set_page_config(page_title="Mueblería Pro - Gestión Total", layout="wide")

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
                st.success("✅ Proyecto creado exitosamente.")

# --- OPCIÓN 2: VER / GESTIONAR ---
elif choice == "Ver / Gestionar Proyectos":
    st.header("📋 Todos los Proyectos")
    df_p = pd.read_sql("SELECT * FROM proyectos", conn)
    if not df_p.empty:
        st.dataframe(df_p, use_container_width=True)
    else:
        st.info("No hay proyectos registrados.")

# --- OPCIÓN 4: CORREGIR DATOS (EDICIÓN Y ELIMINACIÓN) ---
elif choice == "✏️ Corregir Datos":
    st.header("✏️ Editor Maestro y Eliminación")
    df = pd.read_sql("SELECT * FROM proyectos", conn)
    if not df.empty:
        opciones = [f"ID {row['id']} - {row['cliente']}" for _, row in df.iterrows()]
        selec = st.selectbox("Seleccione registro para editar o eliminar:", opciones)
        id_p = int(selec.split(" ")[1])
        p = df[df['id'] == id_p].iloc[0]
        
        with st.form("edit_maestro"):
            n_cliente = st.text_input("Cliente", value=str(p['cliente']))
            n_mueble = st.text_area("Mueble", value=str(p['mueble']))
            n_suplidor = st.text_input("Suplidor", value=str(p['suplidor']))
            c1, c2 = st.columns(2)
            n_pv = c1.number_input("Precio Venta", value=float(p['precio_venta']))
            n_cf = c2.number_input("Costo Fábrica", value=float(p['costo_fabrica']))
            n_ac = c1.number_input("Adelantos Cliente", value=float(p['adelanto_cliente']))
            n_as = c2.number_input("Pagos Fábrica", value=float(p['adelanto_suplidor']))
            n_est = st.selectbox("Estado", ["En Proceso", "Entregado"], index=0 if p['estado']=="En Proceso" else 1)
            
            col_save, col_del = st.columns([1,1])
            save_btn = col_save.form_submit_button("💾 GUARDAR CAMBIOS")
            del_btn = col_del.form_submit_button("🗑️ ELIMINAR PROYECTO")
            
            if save_btn:
                c.execute('''UPDATE proyectos SET cliente=?, mueble=?, suplidor=?, precio_venta=?, 
                             costo_fabrica=?, adelanto_cliente=?, adelanto_suplidor=?, estado=? WHERE id=?''',
                          (n_cliente.upper(), n_mueble, n_suplidor.upper(), n_pv, n_cf, n_ac, n_as, n_est, id_p))
                conn.commit()
                st.success("✅ Registro actualizado.")
                st.rerun()

            if del_btn:
                c.execute("DELETE FROM proyectos WHERE id=?", (id_p,))
                c.execute("DELETE FROM historial_pagos WHERE proyecto_id=?", (id_p,))
                conn.commit()
                st.warning(f"⚠️ Proyecto {id_p} eliminado.")
                st.rerun()

# --- OPCIÓN 3: PAGOS Y ABONOS ---
elif choice == "Pagos y Abonos":
    st.header("💰 Registrar Movimiento de Dinero")
    df = pd.read_sql("SELECT id, cliente, mueble FROM proyectos WHERE estado != 'Entregado'", conn)
    if not df.empty:
        opciones = [f"ID {row['id']} - {row['cliente']}" for _, row in df.iterrows()]
        selec = st.selectbox("Seleccione Proyecto:", opciones)
        id_p = int(selec.split(" ")[1])
        col_t, col_f = st.columns(2)
        tipo = col_t.radio("Tipo:", ["Cobro a Cliente", "Pago a Fábrica"])
        fecha_mov = col_f.date_input("Fecha:", date.today())
        monto = st.number_input("Monto ($)", min_value=0.0)
        if st.button("Registrar"):
            campo = "adelanto_cliente" if "Cliente" in tipo else "adelanto_suplidor"
            c.execute(f"UPDATE proyectos SET {campo} = {campo} + ? WHERE id = ?", (monto, id_p))
            c.execute("INSERT INTO historial_pagos (proyecto_id, fecha, tipo_movimiento, monto) VALUES (?,?,?,?)",
                      (id_p, fecha_mov.strftime("%Y-%m-%d"), tipo, monto))
            conn.commit()
            st.success(f"✅ Registrado.")

# --- OPCIÓN 5: GASTOS VARIOS ---
elif choice == "Gastos Varios":
    st.header("⛽ Gastos Operativos")
    with st.form("g"):
        col_a, col_b = st.columns(2)
        con = col_a.text_input("Concepto")
        mon = col_b.number_input("Monto ($)", min_value=0.0)
        fec = st.date_input("Fecha:", date.today())
        if st.form_submit_button("Registrar Gasto"):
            c.execute("INSERT INTO gastos_varios (fecha, concepto, monto) VALUES (?,?,?)", (fec.strftime("%Y-%m-%d"), con, mon))
            conn.commit()
            st.success("Gasto guardado.")

# --- OPCIÓN 6: REPORTES Y ESTADO DE RESULTADOS (CORREGIDO DECIMALES) ---
elif choice == "Reportes y Respaldo":
    st.header("📊 Inteligencia Financiera")
    st.sidebar.divider()
    f_inicio = st.sidebar.date_input("Fecha Inicio", date(date.today().year, date.today().month, 1))
    f_fin = st.sidebar.date_input("Fecha Fin", date.today())
    
    str_ini, str_fin = f_inicio.strftime("%Y-%m-%d"), f_fin.strftime("%Y-%m-%d")

    df_proy = pd.read_sql("SELECT * FROM proyectos", conn)
    df_pagos = pd.read_sql(f"SELECT * FROM historial_pagos WHERE fecha BETWEEN '{str_ini}' AND '{str_fin}'", conn)
    df_gastos = pd.read_sql(f"SELECT * FROM gastos_varios WHERE fecha BETWEEN '{str_ini}' AND '{str_fin}'", conn)

    tab1, tab2, tab3 = st.tabs(["📈 Estado de Resultados", "👥 Saldos Pendientes", "📦 Respaldo"])

    with tab1:
        ingresos = df_pagos[df_pagos['tipo_movimiento'] == 'Cobro a Cliente']['monto'].sum()
        pagos_f = df_pagos[df_pagos['tipo_movimiento'] == 'Pago a Fábrica']['monto'].sum()
        gastos_v = df_gastos['monto'].sum()
        beneficio = ingresos - pagos_f - gastos_v
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("INGRESOS", f"${ingresos:,.2f}")
        m2.metric("PAGOS FÁBRICA", f"${pagos_f:,.2f}")
        m3.metric("GASTOS VARIOS", f"${gastos_v:,.2f}")
        m4.metric("BENEFICIO NETO", f"${beneficio:,.2f}")
        
        st.write("### Detalle de Gastos")
        if not df_gastos.empty:
            # Formateo de tabla a 2 decimales
            st.table(df_gastos.style.format({"monto": "${:,.2f}"}))
        else:
            st.info("Sin gastos en este periodo.")

    with tab2:
        if not df_proy.empty:
            df_proy['Saldo Cliente'] = df_proy['precio_venta'] - df_proy['adelanto_cliente']
            df_proy['Saldo Suplidor'] = df_proy['costo_fabrica'] - df_proy['adelanto_suplidor']
            
            # Agrupar por Cliente y Formatear
            c_cobrar = df_proy.groupby('cliente')['Saldo Cliente'].sum().reset_index()
            c_cobrar = c_cobrar[c_cobrar['Saldo Cliente'] > 0]
            
            # Agrupar por Suplidor y Formatear
            c_pagar = df_proy.groupby('suplidor')['Saldo Suplidor'].sum().reset_index()
            c_pagar = c_pagar[c_pagar['Saldo Suplidor'] > 0]
            
            st.subheader("Cuentas por Cobrar (Clientes)")
            if not c_cobrar.empty:
                st.table(c_cobrar.style.format({"Saldo Cliente": "${:,.2f}"}))
            else:
                st.success("✅ ¡No hay saldos pendientes de clientes!")

            st.subheader("Cuentas por Pagar (Fábricas)")
            if not c_pagar.empty:
                st.table(c_pagar.style.format({"Saldo Suplidor": "${:,.2f}"}))
            else:
                st.success("✅ ¡No debes nada a las fábricas!")
        
    with tab3:
        st.download_button("Descargar CSV", df_proy.to_csv(index=False).encode('utf-8'), "muebleria.csv")
