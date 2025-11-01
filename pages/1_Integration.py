# app.py
# Streamlit + requests + pandas + plotly
# CRUD de Productos y Proveedores, tablas con filtros y gráficos básicos.
# Ajusta los endpoints y campos a tu API (Spring Boot, etc.). No usa st.secrets.

import json
import time
from datetime import datetime, date, timedelta
from typing import Any, Dict, List, Optional, Tuple

import requests
import pandas as pd
import streamlit as st
import plotly.express as px

# =========================
# Configuración principal
# =========================
st.set_page_config(page_title="Streamlit + API: Productos y Proveedores", layout="wide")

# Define tu API aquí (sin st.secrets)
API_URL = "http://localhost:8080/api/v1"   # <- incluye /v1
PRODUCTS_ENDPOINT  = "/products"
SUPPLIERS_ENDPOINT = "/proveedor"
SALES_ENDPOINT     = "/None"  # si no tienes ventas, puedes dejarlo None o comentar su uso

# Modo demo (True permite datos sintéticos si la API no responde)
USE_DEMO_IF_API_FAILS = True

REQUEST_TIMEOUT = 15
DEFAULT_HEADERS = {"Accept": "application/json", "Content-Type": "application/json"}

# =========================
# Helpers de red y cache
# =========================
def build_url(path: str) -> str:
    if path.startswith("http://") or path.startswith("https://"):
        return path
    base = API_URL.rstrip("/")
    path = path if path.startswith("/") else f"/{path}"
    return f"{base}{path}"

def api_request(method: str, path: str, params=None, json_body=None):
    url = build_url(path)
    try:
        resp = requests.request(
            method=method.upper(),
            url=url,
            headers={"Accept":"application/json","Content-Type":"application/json"},
            params=params,
            json=json_body,
            timeout=15,
        )
        if resp.status_code >= 400:
            try:
                detail = resp.json()
            except Exception:
                detail = resp.text
            st.error(f"Error {resp.status_code} {method} {url}: {detail}")
            return None
        return resp.json() if resp.content else None
    except requests.exceptions.RequestException as e:
        st.error(f"No se pudo conectar a {url}. Detalle: {e}")
        return None
    
    

# =========================
# Normalización de datos
# =========================
def normalize_products(df: pd.DataFrame) -> pd.DataFrame:
    # Columnas esperadas: ajusta a tu API
    expected = ["id", "name", "category", "price", "stock", "supplierId", "createdAt"]
    for c in expected:
        if c not in df.columns:
            df[c] = None
    df["price"] = pd.to_numeric(df["price"], errors="coerce")
    df["stock"] = pd.to_numeric(df["stock"], errors="coerce").fillna(0).astype("Int64")
    # fechas si existen
    if "createdAt" in df.columns:
        df["createdAt"] = pd.to_datetime(df["createdAt"], errors="coerce")
    return df[expected]

def normalize_suppliers(df: pd.DataFrame) -> pd.DataFrame:
    expected = ["id", "name", "email", "phone", "address", "createdAt"]
    for c in expected:
        if c not in df.columns:
            df[c] = None
    if "createdAt" in df.columns:
        df["createdAt"] = pd.to_datetime(df["createdAt"], errors="coerce")
    return df[expected]

def normalize_sales(df: pd.DataFrame) -> pd.DataFrame:
    expected = ["saleId", "productId", "productName", "category", "supplierId", "timestamp", "quantity", "total"]
    for c in expected:
        if c not in df.columns:
            df[c] = None
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce").fillna(0)
    df["total"] = pd.to_numeric(df["total"], errors="coerce").fillna(0.0)
    return df[expected]

# =========================
# Fetchers (cacheados)
# =========================
@st.cache_data(ttl=60)
def fetch_products() -> pd.DataFrame:
    data = api_request("GET", PRODUCTS_ENDPOINT)
    if data is None and USE_DEMO_IF_API_FAILS:
        return demo_products()
    df = pd.DataFrame(data or [])
    return normalize_products(df)

@st.cache_data(ttl=60)
def fetch_suppliers() -> pd.DataFrame:
    data = api_request("GET", SUPPLIERS_ENDPOINT)
    if data is None and USE_DEMO_IF_API_FAILS:
        return demo_suppliers()
    df = pd.DataFrame(data or [])
    return normalize_suppliers(df)

@st.cache_data(ttl=120)
def fetch_sales() -> pd.DataFrame:
    data = api_request("GET", SALES_ENDPOINT)
    if data is None and USE_DEMO_IF_API_FAILS:
        return demo_sales()
    df = pd.DataFrame(data or [])
    return normalize_sales(df)

# =========================
# CRUD wrappers
# =========================
def create_product(payload: dict) -> bool:
    res = api_request("POST", PRODUCTS_ENDPOINT, json_body=payload)
    if res is not None:
        fetch_products.clear()
        return True
    return False

def update_product(product_id: Any, payload: dict) -> bool:
    res = api_request("PUT", f"{PRODUCTS_ENDPOINT}/{product_id}", json_body=payload)
    if res is not None:
        fetch_products.clear()
        return True
    return False

def delete_product(product_id: Any) -> bool:
    res = api_request("DELETE", f"{PRODUCTS_ENDPOINT}/{product_id}")
    if res is not None:
        fetch_products.clear()
        return True
    return False

def create_supplier(payload: dict) -> bool:
    res = api_request("POST", SUPPLIERS_ENDPOINT, json_body=payload)
    if res is not None:
        fetch_suppliers.clear()
        return True
    return False

def update_supplier(supplier_id: Any, payload: dict) -> bool:
    res = api_request("PUT", f"{SUPPLIERS_ENDPOINT}/{supplier_id}", json_body=payload)
    if res is not None:
        fetch_suppliers.clear()
        return True
    return False

def delete_supplier(supplier_id: Any) -> bool:
    res = api_request("DELETE", f"{SUPPLIERS_ENDPOINT}/{supplier_id}")
    if res is not None:
        fetch_suppliers.clear()
        return True
    return False

# =========================
# Demo data (opcional)
# =========================
def demo_suppliers() -> pd.DataFrame:
    demo = [
        {"id": 1, "name": "Proveedor Andino", "email": "contacto@andino.com", "phone": "3001234567", "address": "Calle 1", "createdAt": datetime.now()},
        {"id": 2, "name": "Distribuciones Norte", "email": "ventas@norte.com", "phone": "3019876543", "address": "Carrera 2", "createdAt": datetime.now()},
        {"id": 3, "name": "La Bodega", "email": "info@bodega.com", "phone": "3025555555", "address": "Av 3", "createdAt": datetime.now()},
        {"":4,"":"","":"","":"","":""}
    ]
    return normalize_suppliers(pd.DataFrame(demo))

def demo_products() -> pd.DataFrame:
    demo = [
        {"id": 101, "name": "Leche entera", "category": "Lácteos", "price": 3.5, "stock": 120, "supplierId": 1, "createdAt": datetime.now()},
        {"id": 102, "name": "Yogur natural", "category": "Lácteos", "price": 2.0, "stock": 90, "supplierId": 1, "createdAt": datetime.now()},
        {"id": 103, "name": "Pan integral", "category": "Panadería", "price": 1.8, "stock": 75, "supplierId": 2, "createdAt": datetime.now()},
        {"id": 104, "name": "Café molido", "category": "Bebidas", "price": 5.5, "stock": 50, "supplierId": 3, "createdAt": datetime.now()},
        {"id": 105, "name": "Queso fresco", "category": "Lácteos", "price": 4.8, "stock": 65, "supplierId": 1, "createdAt": datetime.now()},
    ]
    return normalize_products(pd.DataFrame(demo))

def demo_sales() -> pd.DataFrame:
    # Ventas muy simples para gráficos
    prods = demo_products()
    rows = []
    now = datetime.now()
    for i, r in prods.iterrows():
        for d in range(14):
            ts = now - timedelta(days=d)
            rows.append({
                "saleId": 1000 + i*20 + d,
                "productId": r["id"],
                "productName": r["name"],
                "category": r["category"],
                "supplierId": r["supplierId"],
                "timestamp": ts,
                "quantity": (i + d) % 5 + 1,
                "total": ((i + d) % 5 + 1) * float(r["price"] or 0),
            })
    return normalize_sales(pd.DataFrame(rows))

# =========================
# Utilidades de UI
# =========================
def paginate_df(df: pd.DataFrame, page: int, page_size: int) -> Tuple[pd.DataFrame, int]:
    if df.empty:
        return df, 0
    total_pages = (len(df) - 1) // page_size + 1
    page = max(1, min(page, total_pages))
    start = (page - 1) * page_size
    end = start + page_size
    return df.iloc[start:end], total_pages

def text_search(df: pd.DataFrame, query: str) -> pd.DataFrame:
    if not query:
        return df
    q = str(query).strip().lower()
    mask = pd.Series(False, index=df.index)
    for c in df.columns:
        mask |= df[c].astype(str).str.lower().str.contains(q, na=False)
    return df[mask]

# =========================
# UI: Productos (CRUD + filtros)
# =========================
def ui_products():
    st.subheader("Productos")
    prods = fetch_products()
    sups = fetch_suppliers()

    # Mapeo supplierId -> nombre
    sup_map = dict(zip(sups["id"], sups["name"]))
    prods["supplierName"] = prods["supplierId"].map(sup_map)

    with st.expander("Filtros", expanded=True):
        cols = st.columns(4)
        categories = sorted([c for c in prods["category"].dropna().unique().tolist()])
        cat_sel = cols[0].multiselect("Categoría", categories, default=[])
        # Rango de precio
        pmin = float(prods["price"].min() if pd.notna(prods["price"].min()) else 0.0)
        pmax = float(prods["price"].max() if pd.notna(prods["price"].max()) else 0.0)
        price_range = cols[1].slider("Precio", min_value=0.0, max_value=max(0.01, pmax + 1.0), value=(pmin, pmax), step=0.1)
        sup_options = ["(Todos)"] + [f"{sid} - {sup_map.get(sid, '')}" for sid in sups["id"].dropna().tolist()]
        sup_choice = cols[2].selectbox("Proveedor", sup_options, index=0)
        # Rango fechas por createdAt
        if "createdAt" in prods.columns and prods["createdAt"].notna().any():
            dmin = prods["createdAt"].min().date()
            dmax = prods["createdAt"].max().date()
        else:
            dmin, dmax = date.today() - timedelta(days=30), date.today()
        date_from, date_to = cols[3].date_input("Rango de fechas (createdAt)", value=(dmin, dmax))

        q = st.text_input("Búsqueda global (cualquier columna)")

    # Aplicar filtros
    df = prods.copy()
    if cat_sel:
        df = df[df["category"].isin(cat_sel)]
    df = df[(df["price"].fillna(0) >= price_range[0]) & (df["price"].fillna(0) <= price_range[1])]
    if sup_choice != "(Todos)":
        sel_id = int(sup_choice.split(" - ")[0])
        df = df[df["supplierId"] == sel_id]
    if "createdAt" in df.columns and df["createdAt"].notna().any():
        df = df[(df["createdAt"].dt.date >= date_from) & (df["createdAt"].dt.date <= date_to)]
    df = text_search(df, q)

    # Tabla con paginación
    left, right = st.columns([3, 2], gap="large")
    with left:
        st.caption(f"{len(df)} registros filtrados")
        page_size = st.number_input("Registros por página", 5, 100, value=10, step=5, key="prod_ps")
        page = st.number_input("Página", 1, max(1, (len(df)-1)//int(page_size)+1), value=1, step=1, key="prod_pg")
        page_df, total_pages = paginate_df(df, int(page), int(page_size))
        st.caption(f"Página {page} de {total_pages}")
        show_cols = ["id", "name", "category", "price", "stock", "supplierId", "supplierName", "createdAt"]
        show_cols = [c for c in show_cols if c in page_df.columns]
        st.dataframe(page_df[show_cols], use_container_width=True, height=400)

        # Métricas simples
        k1, k2, k3 = st.columns(3)
        k1.metric("Total productos", f"{len(df):,}")
        k2.metric("Precio promedio", f"{df['price'].mean():.2f}" if not df["price"].dropna().empty else "—")
        k3.metric("Categorías únicas", f"{df['category'].nunique()}")

        # Gráficos
        cols_g = st.columns(2)
        if "category" in df.columns and not df.empty:
            cat_count = df.groupby("category", as_index=False)["id"].count().rename(columns={"id": "cantidad"})
            fig1 = px.bar(cat_count, x="category", y="cantidad", title="Productos por categoría")
            cols_g[0].plotly_chart(fig1, use_container_width=True)
            fig2 = px.pie(cat_count, names="category", values="cantidad", title="Distribución por categoría")
            cols_g[1].plotly_chart(fig2, use_container_width=True)

    # CRUD
    with right:
        st.markdown("### CRUD Productos")
        tabs = st.tabs(["Crear", "Editar", "Eliminar"])

        with tabs[0]:
            with st.form("create_product_form"):
                name = st.text_input("Nombre")
                category = st.text_input("Categoría")
                price = st.number_input("Precio", min_value=0.0, step=0.1)
                stock = st.number_input("Stock", min_value=0, step=1)
                sup_ids = sups["id"].dropna().astype(int).tolist()
                supplierId = st.selectbox("Proveedor ID", sup_ids if sup_ids else [0])
                submitted = st.form_submit_button("Crear")
            if submitted:
                payload = {"name": name, "category": category, "price": float(price), "stock": int(stock), "supplierId": int(supplierId)}
                if not name:
                    st.error("El nombre es obligatorio")
                else:
                    if create_product(payload):
                        st.success("Producto creado con éxito")
                        rerun_after()

        with tabs[1]:
            ids = prods["id"].dropna().tolist()
            if not ids:
                st.info("No hay productos para editar.")
            else:
                sel_id = st.selectbox("Selecciona ID para editar", ids, key="edit_prod_id")
                current = prods.loc[prods["id"] == sel_id].iloc[0]
                with st.form("edit_product_form"):
                    name = st.text_input("Nombre", value=str(current.get("name") or ""))
                    category = st.text_input("Categoría", value=str(current.get("category") or ""))
                    price = st.number_input("Precio", value=float(current.get("price") or 0.0), step=0.1)
                    stock = st.number_input("Stock", value=int(current.get("stock") or 0), step=1)
                    supplierId = st.selectbox("Proveedor ID", sups["id"].dropna().astype(int).tolist(), index=0)
                    submitted = st.form_submit_button("Guardar cambios")
                if submitted:
                    payload = {"name": name, "category": category, "price": float(price), "stock": int(stock), "supplierId": int(supplierId)}
                    if update_product(sel_id, payload):
                        st.success("Producto actualizado")
                        rerun_after()

        with tabs[2]:
            ids = prods["id"].dropna().tolist()
            if not ids:
                st.info("No hay productos para eliminar.")
            else:
                del_id = st.selectbox("Selecciona ID para eliminar", ids, key="del_prod_id")
                if st.button("Eliminar producto", type="primary"):
                    if delete_product(del_id):
                        st.success(f"Producto {del_id} eliminado")
                        rerun_after()

# =========================
# UI: Proveedores (CRUD + filtros)
# =========================
def ui_suppliers():
    st.subheader("Proveedores")
    sups = fetch_suppliers()

    with st.expander("Filtros", expanded=True):
        q = st.text_input("Búsqueda global (cualquier columna)", key="sup_query")
        # Fechas por createdAt si existen
        if "createdAt" in sups.columns and sups["createdAt"].notna().any():
            dmin = sups["createdAt"].min().date()
            dmax = sups["createdAt"].max().date()
        else:
            dmin, dmax = date.today() - timedelta(days=30), date.today()
        date_from, date_to = st.date_input("Rango de fechas (createdAt)", value=(dmin, dmax), key="sup_dates")

    df = sups.copy()
    if "createdAt" in df.columns and df["createdAt"].notna().any():
        df = df[(df["createdAt"].dt.date >= date_from) & (df["createdAt"].dt.date <= date_to)]
    df = text_search(df, q)

    left, right = st.columns([3, 2], gap="large")
    with left:
        st.caption(f"{len(df)} registros filtrados")
        ps = st.number_input("Registros por página", 5, 100, value=10, step=5, key="sup_ps")
        pg = st.number_input("Página", 1, max(1, (len(df)-1)//int(ps)+1), value=1, step=1, key="sup_pg")
        page_df, total_pages = paginate_df(df, int(pg), int(ps))
        st.caption(f"Página {pg} de {total_pages}")
        show_cols = ["id", "name", "email", "phone", "address", "createdAt"]
        show_cols = [c for c in show_cols if c in page_df.columns]
        st.dataframe(page_df[show_cols], use_container_width=True, height=400)

        # KPI básicos
        k1, k2 = st.columns(2)
        k1.metric("Total proveedores", f"{len(df):,}")
        k2.metric("Con email", f"{df['email'].notna().sum():,}" if "email" in df.columns else "—")

    with right:
        st.markdown("### CRUD Proveedores")
        tabs = st.tabs(["Crear", "Editar", "Eliminar"])

        with tabs[0]:
            with st.form("create_supplier_form"):
                name = st.text_input("Nombre")
                email = st.text_input("Email")
                phone = st.text_input("Teléfono")
                address = st.text_input("Dirección")
                submitted = st.form_submit_button("Crear")
            if submitted:
                payload = {"name": name, "email": email, "phone": phone, "address": address}
                if not name:
                    st.error("El nombre es obligatorio")
                else:
                    if create_supplier(payload):
                        st.success("Proveedor creado con éxito")
                        rerun_after()

        with tabs[1]:
            ids = sups["id"].dropna().tolist()
            if not ids:
                st.info("No hay proveedores para editar.")
            else:
                sel_id = st.selectbox("Selecciona ID para editar", ids, key="edit_sup_id")
                current = sups.loc[sups["id"] == sel_id].iloc[0]
                with st.form("edit_supplier_form"):
                    name = st.text_input("Nombre", value=str(current.get("name") or ""))
                    email = st.text_input("Email", value=str(current.get("email") or ""))
                    phone = st.text_input("Teléfono", value=str(current.get("phone") or ""))
                    address = st.text_input("Dirección", value=str(current.get("address") or ""))
                    submitted = st.form_submit_button("Guardar cambios")
                if submitted:
                    payload = {"name": name, "email": email, "phone": phone, "address": address}
                    if update_supplier(sel_id, payload):
                        st.success("Proveedor actualizado")
                        rerun_after()

        with tabs[2]:
            ids = sups["id"].dropna().tolist()
            if not ids:
                st.info("No hay proveedores para eliminar.")
            else:
                del_id = st.selectbox("Selecciona ID para eliminar", ids, key="del_sup_id")
                if st.button("Eliminar proveedor", type="primary"):
                    if delete_supplier(del_id):
                        st.success(f"Proveedor {del_id} eliminado")
                        rerun_after()

# =========================
# UI: Analítica básica
# =========================
def ui_analytics():
    st.subheader("Analítica básica")
    sales = fetch_sales()  # si no existe endpoint, se usan datos demo
    prods = fetch_products()
    sups = fetch_suppliers()
    sup_map = dict(zip(sups["id"], sups["name"]))

    with st.expander("Filtros de analítica", expanded=True):
        categories = sorted([c for c in sales["category"].dropna().unique().tolist()]) or sorted(prods["category"].dropna().unique().tolist())
        cat_sel = st.multiselect("Categoría", categories, default=[])
        # Fechas
        if "timestamp" in sales.columns and sales["timestamp"].notna().any():
            dmin = sales["timestamp"].min().date()
            dmax = sales["timestamp"].max().date()
        else:
            dmin, dmax = date.today() - timedelta(days=30), date.today()
        d_from, d_to = st.date_input("Rango de fechas (ventas)", value=(dmin, dmax))
        # Proveedor
        sup_options = ["(Todos)"] + [f"{sid} - {sup_map.get(sid, '')}" for sid in sups["id"].dropna().tolist()]
        sup_choice = st.selectbox("Proveedor", sup_options, index=0)
        # Horas
        hour_from, hour_to = st.slider("Rango de horas", 0, 23, (0, 23))

    df = sales.copy()
    if not df.empty:
        if cat_sel:
            df = df[df["category"].isin(cat_sel)]
        if "timestamp" in df.columns and df["timestamp"].notna().any():
            df = df[(df["timestamp"].dt.date >= d_from) & (df["timestamp"].dt.date <= d_to)]
            df["hour"] = df["timestamp"].dt.hour
            df = df[(df["hour"] >= hour_from) & (df["hour"] <= hour_to)]
        if sup_choice != "(Todos)":
            sel_id = int(sup_choice.split(" - ")[0])
            df = df[df["supplierId"] == sel_id]

    # KPIs
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Registros de venta", f"{len(df):,}")
    c2.metric("Unidades", f"{int(df['quantity'].sum() if 'quantity' in df else 0):,}")
    c3.metric("Ingresos", f"${float(df['total'].sum() if 'total' in df else 0):,.2f}")
    c4.metric("Productos distintos", df["productId"].nunique() if "productId" in df else 0)

    # Gráficos
    g1, g2 = st.columns(2)
    if not df.empty and "category" in df.columns:
        agg_cat = df.groupby("category", as_index=False)["quantity"].sum().sort_values("quantity", ascending=False)
        fig1 = px.bar(agg_cat, x="category", y="quantity", title="Unidades por categoría (filtrado)")
        g1.plotly_chart(fig1, use_container_width=True)

    if not df.empty and "timestamp" in df.columns:
        df_day = df.copy()
        df_day["date"] = df_day["timestamp"].dt.date
        agg_day = df_day.groupby("date", as_index=False)[["quantity", "total"]].sum()
        fig2 = px.line(agg_day, x="date", y=["quantity", "total"], markers=True, title="Tendencia: Unidades y Total por día")
        g2.plotly_chart(fig2, use_container_width=True)

    with st.expander("Detalle de ventas (max 1000 filas)"):
        if not df.empty:
            cols = [c for c in ["timestamp", "productName", "category", "quantity", "total", "supplierId"] if c in df.columns]
            st.dataframe(df[cols].sort_values("timestamp", ascending=False).head(1000), use_container_width=True, height=400)
        else:
            st.info("Sin datos (ajusta los filtros o verifica el endpoint /sales).")

# =========================
# Layout principal
# =========================
st.title("Proyecto base: Streamlit + API externa (Productos y Proveedores)")
st.caption("Incluye tablas, filtros, CRUD básico y analítica con pandas/plotly. Ajusta endpoints y campos a tu API.")

tabs = st.tabs(["Productos", "Proveedores", "Analítica"])
with tabs[0]:
    ui_products()
with tabs[1]:
    ui_suppliers()
# with tabs[2]:
#     ui_analytics()

# st.markdown(
#     unsafe_allow_html=True,
# )
if st.sidebar.button("Probar conexión API"):
    for ep in [PRODUCTS_ENDPOINT, SUPPLIERS_ENDPOINT]:
        data = api_request("GET", ep)
        st.sidebar.write(f"GET {ep} ->", "OK" if data is not None else "ERROR")