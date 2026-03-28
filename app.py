import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, date
import io

def get_connection():
    return sqlite3.connect('muebles_negocio.db', check_same_thread=False)

conn = get_connection()
c = conn.cursor()

# Estructura de Base de Datos
c.execute('CREATE TABLE IF NOT EXISTS proyectos (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha_creacion TEXT, cliente TEXT, mueble TEXT, suplidor TEXT, precio_venta REAL, costo_fabrica REAL, adelanto_cliente REAL, adelanto_suplidor REAL, estado TEXT)')
c.execute('CREATE TABLE IF NOT EXISTS historial_pagos (id INTEGER PRIMARY KEY AUTOINCREMENT, proyecto_id INTEGER, fecha TEXT, tipo_movimiento TEXT, monto REAL)')
c.execute('CREATE TABLE IF NOT EXISTS gastos_varios (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, concepto TEXT, monto REAL)')
conn.commit()

st.set_page_config(page_title="Mueblería Pro v30", layout="wide")
menu = ["Nuevo Proyecto", "Ver / Gestionar Proyectos", "Pagos y Abonos", "✏️ Corregir Datos", "Gastos Varios", "Reportes y Respaldo"]
choice = st.sidebar.selectbox("Menú", menu)

# --- 1. NUEVO PROYECTO ---
if choice == "Nuevo Proyecto":
    st.header("📝 Nuevo Proyecto")
    df_ex = pd.read_sql("SELECT DISTINCT cliente, suplidor FROM proyectos", conn)
    op_cli = ["+ Nuevo Cliente"] + sorted(df_ex['cliente'].unique().tolist())
    op_sup = ["+ Nuevo Suplidor"] + sorted(df_ex['suplidor'].unique().tolist())
    with st.form("f_n"):
        f = st.date_input("Fecha", date.today())
        c1, c2 = st.columns(2)
        cl_s = c1.selectbox("Cliente", op_cli)
        cl_f = c1.text_input("Nombre Cliente").upper() if cl_s == "+ Nuevo Cliente" else cl_s
        su_s = c2.selectbox("Suplidor", op_sup)
        su_f = c2.text_input("Nombre Suplidor").upper() if su_s == "+ Nuevo Suplidor" else su_s
        mu = st.text_area("Descripción")
        p_v = st.number_input("Venta $", min_value=0.0)
        c_f = st.number_input("Costo $", min_value=0.0)
        if st.form_submit_button("Guardar"):
            c.execute("INSERT INTO proyectos (fecha_creacion, cliente, mueble, suplidor, precio_venta, costo_fabrica, adelanto_cliente, adelanto_suplidor, estado) VALUES (?,?,?,?,?,?,?,?,?)",
                      (f.strftime("%Y-%m-%d"), cl_f, mu, su_f, p_v, c_f, 0.0, 0.0, "En Proceso"))
            conn.commit()
            st.rerun()

# --- 2. VER PROYECTOS ---
elif choice == "Ver / Gestionar Proyectos":
    st.header("📋 Listado de Proyectos")
    df = pd.read_sql("SELECT * FROM proyectos", conn)
    if not df.empty:
        st.dataframe(df.style.format({"precio_venta": "${:,.2f}", "costo_fabrica": "${:,.2f}", "adelanto_cliente": "${:,.2f}", "adelanto_suplidor": "${:,.2f}"}), use_container_width=True)
    else:
        st.info("No hay proyectos registrados.")

# --- 3. PAGOS Y ABONOS ---
elif choice == "Pagos y Abonos":
    st.header("💰 Cobros y Pagos")
    df_p = pd.read_sql("SELECT id, cliente, mueble, suplidor FROM proyectos WHERE estado != 'Entregado'", conn)
    if not df_p.empty:
        with st.form("f_p"):
            sel = st.selectbox("Proyecto", [f"ID {r['id']} | {r['cliente']} | {r['mueble'][:15]} | {r['suplidor']}" for _, r in df_p.iterrows()])
            id_p = int(sel.split(" ")[1])
            t = st.radio("Tipo", ["Cobro a Cliente", "Pago a Fábrica"])
            f = st.date_input("Fecha", date.today())
            m = st.number_input("Monto $", min_value=0.1)
            if st.form_submit_button("Registrar"):
                campo = "adelanto_cliente" if "Cliente" in t else "adelanto_suplidor"
                c.execute(f"UPDATE proyectos SET {campo} = {campo} + ? WHERE id = ?", (m, id_p))
                c.execute("INSERT INTO historial_pagos (proyecto_id, fecha, tipo_movimiento, monto) VALUES (?,?,?,?)", (id_p, f.strftime("%Y-%m-%d"), t, m))
                conn.commit()
                st.rerun()

# --- 4. CORREGIR DATOS (Sincronización Reforzada) ---
elif choice == "✏️ Corregir Datos":
    st.header("✏️ Editor Maestro")
    t1, t2 = st.tabs(["📋 Editar Proyectos", "💸 Editar/Anular Pagos"])
    with t1:
        df_pro = pd.read_sql("SELECT * FROM proyectos", conn)
        if not df_pro.empty:
            sel_p = st.selectbox("Editar Proyecto:", [f"ID {r['id']} - {r['cliente']}" for _, r in df_pro.iterrows()])
            id_p = int(sel_p.split(" ")[1])
            p = df_pro[df_pro['id'] == id_p].iloc[0]
            with st.form("e_pro"):
                nf = st.date_input("Fecha", datetime.strptime(p['fecha_creacion'], "%Y-%m-%d").date())
                nc = st.text_input("Cliente", p['cliente'])
                ns = st.text_input("Suplidor", p['suplidor'])
                nm = st.text_area("Mueble", p['mueble'])
                nv = st.number_input("Venta", value=float(p['precio_venta']))
                ncost = st.number_input("Costo", value=float(p['costo_fabrica']))
                nest = st.selectbox("Estado", ["En Proceso", "Entregado"], index=0 if p['estado']=="En Proceso" else 1)
                c_s, c_d = st.columns(2)
                if c_s.form_submit_button("💾 ACTUALIZAR"):
                    c.execute("UPDATE proyectos SET fecha_creacion=?, cliente=?, suplidor=?, mueble=?, precio_venta=?, costo_fabrica=?, estado=? WHERE id=?", (nf.strftime("%Y-%m-%d"), nc.upper(), ns.upper(), nm, nv, ncost, nest, id_p))
                    conn.commit()
                    st.rerun()
                if c_d.form_submit_button("🗑️ ELIMINAR"):
                    if st.checkbox("Confirmar borrar proyecto e historial"):
                        c.execute("DELETE FROM proyectos WHERE id=?", (id_p,))
                        c.execute("DELETE FROM historial_pagos WHERE proyecto_id=?", (id_p,))
                        conn.commit()
                        st.rerun()
    with t2:
        df_hi = pd.read_sql("SELECT h.id, h.proyecto_id, h.fecha, p.cliente, h.tipo_movimiento, h.monto FROM historial_pagos h JOIN proyectos p ON h.proyecto_id = p.id ORDER BY h.id DESC", conn)
        if not df_hi.empty:
            sel_h = st.selectbox("Seleccionar Pago:", [f"ID {r['id']} | {r['cliente']} | {r['tipo_movimiento']} | ${r['monto']}" for _, r in df_hi.iterrows()])
            id_h = int(sel_h.split(" ")[1])
            h = df_hi[df_hi['id'] == id_h].iloc[0]
            with st.form("e_pag"):
                fn = st.date_input("Fecha", datetime.strptime(h['fecha'], "%Y-%m-%d").date())
                mn = st.number_input("Monto", value=float(h['monto']))
                cs, ca = st.columns(2)
                if cs.form_submit_button("💾 GUARDAR"):
                    campo = "adelanto_cliente" if "Cliente" in h['tipo_movimiento'] else "adelanto_suplidor"
                    # Corregimos el total en la tabla PROYECTOS y luego en el historial
                    c.execute(f"UPDATE proyectos SET {campo} = {campo} - ? + ? WHERE id = ?", (h['monto'], mn, h['proyecto_id']))
                    c.execute("UPDATE historial_pagos SET fecha=?, monto=? WHERE id=?", (fn.strftime("%Y-%m-%d"), mn, id_h))
                    conn.commit()
                    st.rerun()
                if ca.form_submit_button("🚫 ANULAR"):
                    if st.checkbox("Confirmar anulación"):
                        campo = "adelanto_cliente" if "Cliente" in h['tipo_movimiento'] else "adelanto_suplidor"
                        c.execute(f"UPDATE proyectos SET {campo} = {campo} - ? WHERE id = ?", (h['monto'], h['proyecto_id']))
                        c.execute("DELETE FROM historial_pagos WHERE id=?", (id_h,))
                        conn.commit()
                        st.rerun()

# --- 5. REPORTES Y RESPALDO ---
elif choice == "Reportes y Respaldo":
    st.header("📊 Inteligencia de Negocio")
    
    # BOTÓN DE RESPALDO EXCEL
    st.subheader("🛡️ Respaldo de Seguridad")
    if st.button("Generar Archivo de Respaldo (Excel)"):
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            pd.read_sql("SELECT * FROM proyectos", conn).to_excel(writer, sheet_name='Proyectos', index=False)
            pd.read_sql("SELECT * FROM historial_pagos", conn).to_excel(writer, sheet_name='Historial_Pagos', index=False)
            pd.read_sql("SELECT * FROM gastos_varios", conn).to_excel(writer, sheet_name='Gastos_Varios', index=False)
        st.download_button(label="📥 Descargar Respaldo.xlsx", data=output.getvalue(), file_name=f"Respaldo_Muebleria_{date.today()}.xlsx")

    st.divider()
    f1 = st.sidebar.date_input("Desde", date(date.today().year, date.today().month, 1))
    f2 = st.sidebar.date_input("Hasta", date.today())
    
    df_h = pd.read_sql(f"SELECT h.fecha, p.cliente, p.suplidor, h.tipo_movimiento, h.monto FROM historial_pagos h JOIN proyectos p ON h.proyecto_id = p.id WHERE h.fecha BETWEEN '{f1}' AND '{f2}'", conn)
    df_g = pd.read_sql(f"SELECT * FROM gastos_varios WHERE fecha BETWEEN '{f1}' AND '{f2}'", conn)
    df_p = pd.read_sql("SELECT * FROM proyectos", conn)

    t1, t2 = st.tabs(["📉 Resultados Periodo", "👥 Deudas y Pendientes"])
    with t1:
        ing = df_h[df_h['tipo_movimiento'] == 'Cobro a Cliente']['monto'].sum() or 0.0
        paf = df_h[df_h['tipo_movimiento'] == 'Pago a Fábrica']['monto'].sum() or 0.0
        gas = df_g['monto'].sum() or 0.0
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("COBROS", f"${ing:,.2f}"); c2.metric("PAGOS FAB", f"${paf:,.2f}"); c3.metric("GASTOS", f"${gas:,.2f}"); c4.metric("UTILIDAD", f"${(ing-paf-gas):,.2f}")
        st.dataframe(df_h.style.format({"monto": "${:,.2f}"}), use_container_width=True)

    with t2:
        if not df_p.empty:
            df_p['Por Cobrar'] = df_p['precio_venta'] - df_p['adelanto_cliente']
            df_p['Por Pagar'] = df_p['cost_fabrica'] - df_p['adelanto_suplidor']
            col_izq, col_der = st.columns(2)
            with col_izq:
                st.subheader("💰 Cuentas Clientes")
                st.table(df_p[df_p['Por Cobrar'] > 0][['cliente', 'mueble', 'Por Cobrar']].style.format("${:,.2f}"))
            with col_der:
                st.subheader("🏭 Cuentas Suplidores")
                st.table(df_p[df_p['Por Pagar'] > 0][['suplidor', 'mueble', 'Por Pagar']].style.format("${:,.2f}"))

elif choice == "Gastos Varios":
    st.header("⛽ Gastos Operativos")
    with st.form("g"):
        con = st.text_input("Concepto"); mon = st.number_input("Monto"); f = st.date_input("Fecha")
        if st.form_submit_button("Guardar"):
            c.execute("INSERT INTO gastos_varios (fecha, concepto, monto) VALUES (?,?,?)", (f.strftime("%Y-%m-%d"), con, mon))
            conn.commit(); st.rerun()
