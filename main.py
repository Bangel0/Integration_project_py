# home.py
import streamlit as st

st.set_page_config(
    page_title="SysMarket - Gestor de Inventario",
    page_icon="🛒",
    layout="centered"
)

# Encabezado
st.title("SysMarket")
st.caption("Gestor de Inventario • Simple, rápido y claro")

st.write(
    "Bienvenido a SysMarket, tu herramienta ligera para controlar existencias, entradas, "
    "salidas en tu negocio."
)

# Indicadores rápidos (placeholders)
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Productos", "—")
with col2:
    st.metric("Stock total", "—")


st.divider()

# Sección breve: ¿Qué es?
st.subheader("¿Qué es SysMarket?")
st.write(
    "Una aplicación sencilla para registrar productos, actualizar inventario y monitorear "
    "niveles de stock con total claridad."
)

# Funcionalidades básicas (mínimas)
st.subheader("Funciones básicas")
st.markdown(
    "- Registro y edición de productos\n"
    "- Entradas y salidas de inventario\n"
    "- Búsqueda rápida"
)

st.divider()

# Llamados a la acción (simples; sin navegación real)
st.subheader("Acciones rápidas")
cols = st.columns(3)
with cols[0]:
    st.button("➕ Ingresar productos")
with cols[1]:
    st.button("📦 Ver inventario")
with cols[2]:
    st.button("📊 Reportes")

# Barra lateral mínima
with st.sidebar:
    st.header("SysMarket")
    st.write("Gestor de inventario minimalista.")
    st.write("Versión: 0.1.0")

# Pie de página
st.markdown(
    "<br><center style='color:grey'>© 2025 SysMarket — Gestión de inventario sencilla</center>",
    unsafe_allow_html=True
)