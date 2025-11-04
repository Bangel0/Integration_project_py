import streamlit as st
import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
from contextlib import contextmanager

# Opcional: para el apartado de API (comentado por defecto)
# import requests

st.set_page_config(page_title="Gestor de Inventario", page_icon="📦", layout="wide")


# ===========================
# Capa de Datos (SQLite)
# ===========================
DB_PATH = "inventario.db"

@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
        CREATE TABLE IF NOT EXISTS proveedores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL UNIQUE,
            telefono TEXT,
            email TEXT,
            direccion TEXT,
            creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS productos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            categoria TEXT,
            precio REAL CHECK(precio >= 0),
            stock INTEGER DEFAULT 0 CHECK(stock >= 0),
            proveedor_id INTEGER,
            creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (proveedor_id) REFERENCES proveedores(id) ON DELETE SET NULL
        );
        """)
        conn.commit()

def dicts_from_rows(rows):
    return [dict(r) for r in rows]

# ----- Proveedores CRUD -----
def crear_proveedor(nombre, telefono, email, direccion):
    with get_conn() as conn:
        try:
            conn.execute("""
                INSERT INTO proveedores (nombre, telefono, email, direccion)
                VALUES (?, ?, ?, ?)
            """, (nombre.strip(), telefono.strip() if telefono else None, email.strip() if email else None, direccion.strip() if direccion else None))
            conn.commit()
            return True, "Proveedor creado correctamente."
        except sqlite3.IntegrityError as e:
            return False, f"Error: {str(e)}"

def listar_proveedores(buscar=None):
    with get_conn() as conn:
        if buscar:
            like = f"%{buscar.strip()}%"
            rows = conn.execute("""
                SELECT * FROM proveedores
                WHERE nombre LIKE ? OR email LIKE ? OR telefono LIKE ?
                ORDER BY id DESC
            """, (like, like, like)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM proveedores ORDER BY id DESC").fetchall()
    return pd.DataFrame(dicts_from_rows(rows))

def obtener_proveedor_por_id(pid):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM proveedores WHERE id = ?", (pid,)).fetchone()
    return dict(row) if row else None

def actualizar_proveedor(pid, nombre, telefono, email, direccion):
    with get_conn() as conn:
        try:
            conn.execute("""
                UPDATE proveedores
                SET nombre = ?, telefono = ?, email = ?, direccion = ?
                WHERE id = ?
            """, (nombre.strip(), telefono.strip() if telefono else None, email.strip() if email else None, direccion.strip() if direccion else None, pid))
            conn.commit()
            return True, "Proveedor actualizado."
        except sqlite3.IntegrityError as e:
            return False, f"Error: {str(e)}"

def eliminar_proveedor(pid):
    with get_conn() as conn:
        conn.execute("DELETE FROM proveedores WHERE id = ?", (pid,))
        conn.commit()
        return True, "Proveedor eliminado. Nota: los productos asociados quedarán con proveedor NULL."

# ----- Productos CRUD -----
def crear_producto(nombre, categoria, precio, stock, proveedor_id):
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO productos (nombre, categoria, precio, stock, proveedor_id)
            VALUES (?, ?, ?, ?, ?)
        """, (nombre.strip(), categoria.strip() if categoria else None, float(precio), int(stock), proveedor_id if proveedor_id else None))
        conn.commit()
    return True, "Producto creado correctamente."

def listar_productos(filtros: dict = None):
    filtros = filtros or {}
    query = """
        SELECT p.*, pr.nombre AS proveedor_nombre
        FROM productos p
        LEFT JOIN proveedores pr ON pr.id = p.proveedor_id
        WHERE 1=1
    """
    params = []
    if filtros.get("buscar"):
        like = f"%{filtros['buscar'].strip()}%"
        query += " AND (p.nombre LIKE ? OR p.categoria LIKE ?)"
        params += [like, like]
    if filtros.get("categoria"):
        query += " AND p.categoria = ?"
        params.append(filtros["categoria"])
    if filtros.get("proveedor_id") not in (None, "Todos"):
        query += " AND p.proveedor_id = ?"
        params.append(int(filtros["proveedor_id"]))
    if filtros.get("precio_min") is not None:
        query += " AND p.precio >= ?"
        params.append(float(filtros["precio_min"]))
    if filtros.get("precio_max") is not None:
        query += " AND p.precio <= ?"
        params.append(float(filtros["precio_max"]))
    if filtros.get("stock_min") is not None:
        query += " AND p.stock >= ?"
        params.append(int(filtros["stock_min"]))
    if filtros.get("stock_max") is not None:
        query += " AND p.stock <= ?"
        params.append(int(filtros["stock_max"]))

    query += " ORDER BY p.id DESC"

    with get_conn() as conn:
        rows = conn.execute(query, params).fetchall()
    return pd.DataFrame(dicts_from_rows(rows))

def obtener_producto_por_id(pid):
    with get_conn() as conn:
        row = conn.execute("""
            SELECT p.*, pr.nombre AS proveedor_nombre
            FROM productos p
            LEFT JOIN proveedores pr ON pr.id = p.proveedor_id
            WHERE p.id = ?
        """, (pid,)).fetchone()
    return dict(row) if row else None

def actualizar_producto(pid, nombre, categoria, precio, stock, proveedor_id):
    with get_conn() as conn:
        conn.execute("""
            UPDATE productos
            SET nombre = ?, categoria = ?, precio = ?, stock = ?, proveedor_id = ?
            WHERE id = ?
        """, (nombre.strip(), categoria.strip() if categoria else None, float(precio), int(stock), proveedor_id if proveedor_id else None, pid))
        conn.commit()
    return True, "Producto actualizado."

def eliminar_producto(pid):
    with get_conn() as conn:
        conn.execute("DELETE FROM productos WHERE id = ?", (pid,))
        conn.commit()
    return True, "Producto eliminado."


# ===========================
# Utilidades UI
# ===========================
def safe_rerun():
    try:
        st.rerun()
    except Exception:
        pass

def proveedores_options(df_prov):
    """
    Devuelve lista de opciones formato 'ID - Nombre' y un dict id->label
    """
    options = []
    id_to_label = {}
    for _, r in df_prov.sort_values("id").iterrows():
        label = f"{int(r['id'])} - {r['nombre']}"
        options.append(label)
        id_to_label[int(r['id'])] = label
    return options, id_to_label

def parse_id_from_option(option_label):
    # option_label esperado: "ID - Nombre"
    if not option_label:
        return None
    try:
        return int(option_label.split(" - ")[0])
    except:
        return None


# ===========================
# Interfaz
# ===========================
init_db()

st.title("📦 Gestor de Inventario (Streamlit + SQLite)")
st.caption("CRUD completo de Proveedores y Productos, conectados. Incluye filtros y análisis (torta, barra, línea).")

tab_proveedores, tab_productos, tab_analisis = st.tabs(["Proveedores", "Productos", "Análisis"])

# ---------------------------
# Tab Proveedores
# ---------------------------
with tab_proveedores:
    st.subheader("Gestión de Proveedores")

    action = st.radio(
        "Acción",
        options=["Crear", "Leer", "Actualizar", "Eliminar"],
        horizontal=True,
        key="prov_action"
    )

    if action == "Crear":
        with st.form("form_crear_proveedor", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                nombre = st.text_input("Nombre del proveedor", placeholder="Ej: Suministros XYZ", max_chars=120)
                telefono = st.text_input("Teléfono", placeholder="Ej: +57 300 123 4567", max_chars=50)
            with col2:
                email = st.text_input("Email", placeholder="Ej: ventas@xyz.com", max_chars=120)
                direccion = st.text_input("Dirección", placeholder="Ej: Calle 123 #45-67", max_chars=200)
            submitted = st.form_submit_button("Crear proveedor")
        if submitted:
            if not nombre.strip():
                st.error("El nombre es obligatorio.")
            else:
                ok, msg = crear_proveedor(nombre, telefono, email, direccion)
                st.success(msg) if ok else st.error(msg)
                if ok:
                    safe_rerun()

    elif action == "Leer":
        buscar = st.text_input("Buscar (por nombre, email o teléfono)", placeholder="Ej: XYZ o @gmail.com")
        df = listar_proveedores(buscar=buscar)
        st.dataframe(df, use_container_width=True)

    elif action == "Actualizar":
        df = listar_proveedores()
        if df.empty:
            st.info("No hay proveedores. Crea uno primero.")
        else:
            opts, _ = proveedores_options(df)
            sel = st.selectbox("Selecciona proveedor por ID", opts)
            pid = parse_id_from_option(sel)
            datos = obtener_proveedor_por_id(pid) if pid else None

            if datos:
                with st.form("form_actualizar_proveedor"):
                    col1, col2 = st.columns(2)
                    with col1:
                        nombre = st.text_input("Nombre", value=datos["nombre"], max_chars=120)
                        telefono = st.text_input("Teléfono", value=datos["telefono"] or "", max_chars=50)
                    with col2:
                        email = st.text_input("Email", value=datos["email"] or "", max_chars=120)
                        direccion = st.text_input("Dirección", value=datos["direccion"] or "", max_chars=200)
                    submitted = st.form_submit_button("Actualizar")
                if submitted:
                    if not nombre.strip():
                        st.error("El nombre es obligatorio.")
                    else:
                        ok, msg = actualizar_proveedor(pid, nombre, telefono, email, direccion)
                        st.success(msg) if ok else st.error(msg)
                        if ok:
                            safe_rerun()

    elif action == "Eliminar":
        df = listar_proveedores()
        if df.empty:
            st.info("No hay proveedores para eliminar.")
        else:
            opts, _ = proveedores_options(df)
            sel = st.selectbox("Selecciona proveedor por ID a eliminar", opts)
            pid = parse_id_from_option(sel)
            st.warning("Al eliminar un proveedor, los productos asociados quedarán con proveedor NULL.")
            confirmar = st.checkbox("Confirmo que deseo eliminar este proveedor.")
            if st.button("Eliminar proveedor", type="primary", disabled=(not confirmar or pid is None)):
                ok, msg = eliminar_proveedor(pid)
                st.success(msg) if ok else st.error(msg)
                if ok:
                    safe_rerun()

# ---------------------------
# Tab Productos
# ---------------------------
with tab_productos:
    st.subheader("Gestión de Productos")

    action = st.radio(
        "Acción",
        options=["Crear", "Leer", "Actualizar", "Eliminar"],
        horizontal=True,
        key="prod_action"
    )

    df_prov = listar_proveedores()

    if action == "Crear":
        if df_prov.empty:
            st.info("Primero crea al menos un proveedor para poder asociarlo al producto.")
        with st.form("form_crear_producto", clear_on_submit=True):
            col1, col2, col3 = st.columns(3)
            with col1:
                nombre = st.text_input("Nombre del producto", placeholder="Ej: Teclado mecánico", max_chars=120)
                categoria = st.text_input("Categoría", placeholder="Ej: Periféricos", max_chars=100)
            with col2:
                precio = st.number_input("Precio", min_value=0.0, value=0.0, step=0.01, format="%.2f")
                stock = st.number_input("Stock", min_value=0, value=0, step=1)
            with col3:
                if not df_prov.empty:
                    opts, _ = proveedores_options(df_prov)
                    proveedor_opt = st.selectbox("Proveedor (ID - Nombre)", ["Ninguno"] + opts)
                else:
                    proveedor_opt = "Ninguno"
            submitted = st.form_submit_button("Crear producto")

        if submitted:
            if not nombre.strip():
                st.error("El nombre del producto es obligatorio.")
            else:
                proveedor_id = None if proveedor_opt == "Ninguno" else parse_id_from_option(proveedor_opt)
                ok, msg = crear_producto(nombre, categoria, precio, stock, proveedor_id)
                st.success(msg) if ok else st.error(msg)
                if ok:
                    safe_rerun()

    elif action == "Leer":
        with st.expander("Filtros", expanded=True):
            buscar = st.text_input("Buscar (nombre/categoría)", placeholder="Ej: teclado o periféricos")
            categoria_f = st.text_input("Filtrar por categoría exacta", placeholder="Dejar vacío para todas")
            prov_sel = "Todos"
            if not df_prov.empty:
                opts, _ = proveedores_options(df_prov)
                prov_sel = st.selectbox("Proveedor", ["Todos"] + opts)
            col1, col2 = st.columns(2)
            with col1:
                precio_min = st.number_input("Precio mínimo", min_value=0.0, value=0.0, step=0.01, format="%.2f")
                stock_min = st.number_input("Stock mínimo", min_value=0, value=0, step=1)
            with col2:
                precio_max = st.number_input("Precio máximo (0 = sin tope)", min_value=0.0, value=0.0, step=0.01, format="%.2f")
                stock_max = st.number_input("Stock máximo (0 = sin tope)", min_value=0, value=0, step=1)

        filtros = {
            "buscar": buscar if buscar else None,
            "categoria": categoria_f if categoria_f.strip() else None,
            "proveedor_id": prov_sel,
            "precio_min": precio_min if precio_min > 0 else None,
            "precio_max": precio_max if precio_max > 0 else None,
            "stock_min": stock_min if stock_min > 0 else None,
            "stock_max": stock_max if stock_max > 0 else None,
        }
        df = listar_productos(filtros)
        st.dataframe(df, use_container_width=True)

    elif action == "Actualizar":
        df = listar_productos()
        if df.empty:
            st.info("No hay productos. Crea uno primero.")
        else:
            # Selección por ID
            prod_ids = df["id"].astype(int).tolist()
            pid = st.selectbox("Selecciona producto por ID", prod_ids)
            datos = obtener_producto_por_id(pid)

            if datos:
                with st.form("form_actualizar_producto"):
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        nombre = st.text_input("Nombre", value=datos["nombre"], max_chars=120)
                        categoria = st.text_input("Categoría", value=datos["categoria"] or "", max_chars=100)
                    with col2:
                        precio = st.number_input("Precio", min_value=0.0, value=float(datos["precio"] or 0.0), step=0.01, format="%.2f")
                        stock = st.number_input("Stock", min_value=0, value=int(datos["stock"] or 0), step=1)
                    with col3:
                        if not df_prov.empty:
                            opts, id_to_label = proveedores_options(df_prov)
                            current_label = id_to_label.get(int(datos["proveedor_id"])) if datos.get("proveedor_id") else "Ninguno"
                            proveedor_opt = st.selectbox(
                                "Proveedor (ID - Nombre)",
                                ["Ninguno"] + opts,
                                index=(["Ninguno"] + opts).index(current_label) if current_label in (["Ninguno"] + opts) else 0
                            )
                        else:
                            proveedor_opt = "Ninguno"
                    submitted = st.form_submit_button("Actualizar")

                if submitted:
                    if not nombre.strip():
                        st.error("El nombre es obligatorio.")
                    else:
                        proveedor_id = None if proveedor_opt == "Ninguno" else parse_id_from_option(proveedor_opt)
                        ok, msg = actualizar_producto(pid, nombre, categoria, precio, stock, proveedor_id)
                        st.success(msg) if ok else st.error(msg)
                        if ok:
                            safe_rerun()

    elif action == "Eliminar":
        df = listar_productos()
        if df.empty:
            st.info("No hay productos para eliminar.")
        else:
            prod_ids = df["id"].astype(int).tolist()
            pid = st.selectbox("Selecciona producto por ID a eliminar", prod_ids)
            confirmar = st.checkbox("Confirmo que deseo eliminar este producto.")
            if st.button("Eliminar producto", type="primary", disabled=(not confirmar or pid is None)):
                ok, msg = eliminar_producto(pid)
                st.success(msg) if ok else st.error(msg)
                if ok:
                    safe_rerun()

# ---------------------------
# Tab Análisis
# ---------------------------
with tab_analisis:
    st.subheader("Análisis de Datos")

    df_prod = listar_productos()
    if df_prod.empty:
        st.info("No hay productos para analizar. Agrega algunos primero.")
    else:
        # Filtros de análisis
        left, mid, right = st.columns([1,1,2])
        with left:
            categorias = sorted([c for c in df_prod["categoria"].dropna().unique() if c != ""])
            cat_sel = st.multiselect("Categorías", categorias, default=categorias)
        with mid:
            # Proveedores list
            df_prov = listar_proveedores()
            prov_map = {int(r["id"]): r["nombre"] for _, r in df_prov.iterrows()} if not df_prov.empty else {}
            proveedores_op = ["Todos"] + [f"{pid} - {prov_map[pid]}" for pid in sorted(prov_map.keys())]
            prov_sel = st.selectbox("Proveedor", proveedores_op)
        with right:
            min_precio = float(df_prod["precio"].min() if pd.notna(df_prod["precio"]).any() else 0.0)
            max_precio = float(df_prod["precio"].max() if pd.notna(df_prod["precio"]).any() else 0.0)
            r_min, r_max = st.slider("Rango de precio", min_value=0.0, max_value=max(max_precio, 1.0), value=(min_precio, max_precio if max_precio > 0 else 1.0), step=0.5)

        df_fil = df_prod.copy()
        if categorias:
            df_fil = df_fil[df_fil["categoria"].isin(cat_sel)] if cat_sel else df_fil.iloc[0:0]
        # Filtrar por proveedor
        if prov_sel != "Todos":
            prov_id = parse_id_from_option(prov_sel)
            df_fil = df_fil[df_fil["proveedor_id"] == prov_id]
        # Filtrar por precio
        df_fil = df_fil[(df_fil["precio"] >= r_min) & (df_fil["precio"] <= r_max)]

        st.markdown("#### Datos filtrados")
        st.dataframe(df_fil, use_container_width=True, height=250)

        # 1) Diagrama de torta: distribución por categoría
        st.markdown("#### Distribución por categoría (Torta)")
        if df_fil.empty or df_fil["categoria"].dropna().empty:
            st.info("No hay datos suficientes para graficar la torta.")
        else:
            cat_counts = df_fil["categoria"].fillna("Sin categoría").value_counts()
            fig, ax = plt.subplots()
            ax.pie(cat_counts.values, labels=cat_counts.index, autopct="%1.1f%%", startangle=90)
            ax.axis('equal')
            st.pyplot(fig, use_container_width=True)

        # 2) Diagrama de barra: productos por proveedor
        st.markdown("#### Productos por proveedor (Barra)")
        if df_fil.empty:
            st.info("No hay datos para graficar la barra.")
        else:
            # Mostrar por nombre del proveedor si existe
            df_bar = df_fil.copy()
            df_bar["proveedor_nombre"] = df_bar["proveedor_nombre"].fillna("Sin proveedor")
            counts = df_bar["proveedor_nombre"].value_counts().rename_axis("Proveedor").to_frame("Cantidad")
            st.bar_chart(counts)

        # 3) Diagrama lineal: productos creados por día
        st.markdown("#### Productos creados por día (Línea)")
        if df_fil.empty or df_fil["creado_en"].dropna().empty:
            st.info("No hay datos para graficar la línea.")
        else:
            df_line = df_fil.copy()
            # Convertir a fecha
            df_line["fecha"] = pd.to_datetime(df_line["creado_en"]).dt.date
            series = df_line.groupby("fecha")["id"].count()
            st.line_chart(series)


# ============================================================
# APARTADO DE CÓDIGO: Consumo de API Spring Boot (requests)
# Este bloque no está integrado a la UI de arriba. Es un ejemplo
# para que lo adaptes a tu API real de Spring Boot.
# ============================================================
# """
# EJEMPLO DE ENDPOINTS ESPERADOS (ajusta según tu API):
# - GET    /api/proveedores
# - POST   /api/proveedores
# - PUT    /api/proveedores/{id}
# - DELETE /api/proveedores/{id}

# - GET    /api/productos
# - POST   /api/productos
# - PUT    /api/productos/{id}
# - DELETE /api/productos/{id}
# """

# Descomenta 'import requests' arriba para usar estas funciones.
# BASE_URL = "http://localhost:8080/api"

# def api_listar_proveedores():
#     url = f"{BASE_URL}/proveedores"
#     r = requests.get(url, timeout=10)
#     r.raise_for_status()
#     return r.json()  # Se espera lista de proveedores (JSON)

# def api_crear_proveedor(payload: dict):
#     """
#     payload ejemplo:
#     {
#       "nombre": "Suministros XYZ",
#       "telefono": "+57 300 123 4567",
#       "email": "ventas@xyz.com",
#       "direccion": "Calle 123 #45-67"
#     }
#     """
#     url = f"{BASE_URL}/proveedores"
#     r = requests.post(url, json=payload, timeout=10)
#     r.raise_for_status()
#     return r.json()

# def api_actualizar_proveedor(pid: int, payload: dict):
#     url = f"{BASE_URL}/proveedores/{pid}"
#     r = requests.put(url, json=payload, timeout=10)
#     r.raise_for_status()
#     return r.json()

# def api_eliminar_proveedor(pid: int):
#     url = f"{BASE_URL}/proveedores/{pid}"
#     r = requests.delete(url, timeout=10)
#     r.raise_for_status()
#     return {"status": "ok"}

# def api_listar_productos():
#     url = f"{BASE_URL}/productos"
#     r = requests.get(url, timeout=10)
#     r.raise_for_status()
#     return r.json()

# def api_crear_producto(payload: dict):
#     """
#     payload ejemplo:
#     {
#       "nombre": "Teclado mecánico",
#       "categoria": "Periféricos",
#       "precio": 250000.0,
#       "stock": 10,
#       "proveedorId": 1
#     }
#     """
#     url = f"{BASE_URL}/productos"
#     r = requests.post(url, json=payload, timeout=10)
#     r.raise_for_status()
#     return r.json()

# def api_actualizar_producto(pid: int, payload: dict):
#     url = f"{BASE_URL}/productos/{pid}"
#     r = requests.put(url, json=payload, timeout=10)
#     r.raise_for_status()
#     return r.json()

# def api_eliminar_producto(pid: int):
#     url = f"{BASE_URL}/productos/{pid}"
#     r = requests.delete(url, timeout=10)
#     r.raise_for_status()
#     return {"status": "ok"}


# ===========================
# Notas finales
# ===========================
# - Este archivo es autocontenido y usa SQLite para persistencia local.
# - Si deseas cambiar a API, adapta el flujo de la UI para usar las funciones "api_*" arriba.
# - Para sencillez, las gráficas usan Streamlit y Matplotlib.
# - Si eliminas un proveedor, los productos quedan sin proveedor (NULL).
# - Ajusta validaciones, campos y reglas según tu necesidad.