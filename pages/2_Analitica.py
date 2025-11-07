import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import matplotlib.pyplot as plt

st.set_page_config(page_title="Analítica Aeropuerto", page_icon="✈️", layout="wide")

st.title("📊 Analítica de Datos del Aeropuerto")
st.write("Sube un archivo CSV del aeropuerto (vuelos, pasajeros, aviones, etc.) para generar un análisis automático con visualizaciones interactivas.")

uploaded_file = st.file_uploader("📂 Selecciona tu archivo CSV", type=["csv"])

# --- Función para detectar columnas clave ---
COLUMN_HINTS = {
    'date': ['fecha', 'date', 'flight_date', 'departure_date'],
    'airline': ['aerolinea', 'airline', 'operator'],
    'origin': ['origen', 'origin', 'from'],
    'destination': ['destino', 'destination', 'to'],
    'flight': ['vuelo', 'flight'],
    'passengers': ['pasajeros', 'passengers', 'pax'],
    'delay': ['retraso', 'delay', 'delay_minutes']
}

def find_col(df, candidates):
    for c in candidates:
        for col in df.columns:
            if c.lower() in col.lower():
                return col
    return None

if uploaded_file:
    try:
        df = pd.read_csv(uploaded_file)
        st.success("✅ Archivo cargado correctamente")

        st.subheader("🧾 Información general")
        st.write(f"**Columnas:** {list(df.columns)}")
        st.write(f"**Número de filas:** {len(df)}")

        st.subheader("🗂️ Vista previa de los datos")
        st.dataframe(df.head())

        st.subheader("📈 Estadísticas descriptivas")
        st.dataframe(df.describe(include='all'))

        # Detectar columnas
        cols = {k: find_col(df, v) for k, v in COLUMN_HINTS.items()}

        # Detectar tipo de archivo
        tipo = "Desconocido"
        columnas = [col.lower() for col in df.columns]
        if "vuelo" in columnas or "origen" in columnas or "destino" in columnas:
            tipo = "Vuelos"
        elif "pasajero" in columnas or "edad" in columnas:
            tipo = "Pasajeros"
        elif "avion" in columnas or "modelo" in columnas:
            tipo = "Aviones"

        st.info(f"📂 Tipo de archivo detectado: **{tipo}**")

        st.divider()
        st.subheader("✈️ Visualizaciones Interactivas")

        # PIE CHART - Aerolíneas
        if cols['airline']:
            st.markdown("#### 🥧 Distribución de vuelos por aerolínea")
            top_airlines = df[cols['airline']].value_counts().nlargest(10)
            fig = px.pie(values=top_airlines.values, names=top_airlines.index, title="Top Aerolíneas")
            st.plotly_chart(fig, use_container_width=True)

        # DONUT - Destinos
        if cols['destination']:
            st.markdown("#### 🍩 Principales destinos")
            top_dest = df[cols['destination']].value_counts().nlargest(8)
            fig = px.pie(values=top_dest.values, names=top_dest.index, hole=0.45, title="Top Destinos")
            st.plotly_chart(fig, use_container_width=True)

        # TIME SERIES - Actividad mensual
        if cols['date']:
            try:
                df[cols['date']] = pd.to_datetime(df[cols['date']], errors='coerce')
                st.markdown("#### 📅 Actividad mensual")
                serie = df.groupby(df[cols['date']].dt.to_period("M")).size().reset_index(name="count")
                serie[cols['date']] = serie[cols['date']].dt.to_timestamp()
                fig = px.line(serie, x=cols['date'], y='count', markers=True, title="Vuelos por mes")
                st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.warning(f"No se pudo generar la serie temporal: {e}")

        # SCATTER - Retraso vs Pasajeros
        if cols['delay'] and cols['passengers']:
            st.markdown("#### 🎯 Relación entre retraso y número de pasajeros")
            fig = px.scatter(df, x=cols['passengers'], y=cols['delay'], color=cols['airline'],
                             title="Retraso vs Pasajeros", trendline="ols")
            st.plotly_chart(fig, use_container_width=True)

        # POLAR - Retraso promedio por día de la semana
        if cols['date'] and cols['delay']:
            st.markdown("#### 🌀 Retraso promedio por día de la semana")
            df['weekday'] = pd.to_datetime(df[cols['date']], errors='coerce').dt.day_name()
            delay_week = df.groupby('weekday')[cols['delay']].mean().dropna()
            delay_week = delay_week.reindex(['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday'])
            fig = px.line_polar(r=delay_week.values, theta=delay_week.index, line_close=True, title="Retraso promedio semanal")
            st.plotly_chart(fig, use_container_width=True)

        # VIOLIN - Distribución de retrasos por aerolínea
        if cols['delay'] and cols['airline']:
            st.markdown("#### 🎻 Distribución de retrasos por aerolínea")
            fig = px.violin(df, x=cols['airline'], y=cols['delay'], box=True, points="outliers")
            st.plotly_chart(fig, use_container_width=True)

        # TREEMAP - Rutas por aerolínea
        if cols['origin'] and cols['destination'] and cols['airline']:
            st.markdown("#### 🌳 Rutas por aerolínea (Treemap)")
            df['route'] = df[cols['origin']].astype(str) + " → " + df[cols['destination']].astype(str)
            agg = df.groupby(['route', cols['airline']]).size().reset_index(name='count')
            fig = px.treemap(agg, path=['route', cols['airline']], values='count', title="Treemap de rutas por aerolínea")
            st.plotly_chart(fig, use_container_width=True)

        st.success("✅ Análisis completado. Disfruta de tus visualizaciones.")
    
    except Exception as e:
        st.error(f"❌ Error al procesar el archivo: {e}")
else:
    st.info("Sube un archivo CSV para comenzar el análisis.")
=======
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

st.title("📊 Analítica de Datos del Aeropuerto")

st.write("Sube un archivo CSV del aeropuerto (vuelos, pasajeros, aviones, etc.) para analizarlo.")

uploaded_file = st.file_uploader("Selecciona tu archivo CSV", type=["csv"])

if uploaded_file:
    try:
        df = pd.read_csv(uploaded_file)

        st.success("✅ Archivo cargado correctamente")

        st.write("### 🧾 Información general")
        st.write(f"**Columnas:** {list(df.columns)}")
        st.write(f"**Número de filas:** {len(df)}")

        st.write("### 🗂️ Vista previa de los datos")
        st.dataframe(df.head())

        st.write("### 📈 Estadísticas descriptivas")
        st.dataframe(df.describe(include='all'))

        columnas = [col.lower() for col in df.columns]
        tipo = "Desconocido"

        if "vuelo" in columnas or "origen" in columnas or "destino" in columnas:
            tipo = "Vuelos"
        elif "pasajero" in columnas or "edad" in columnas:
            tipo = "Pasajeros"
        elif "avion" in columnas or "modelo" in columnas:
            tipo = "Aviones"

        st.info(f"📂 Tipo de archivo detectado: **{tipo}**")

        st.write("### ✈️ Visualización rápida")
        col_numericas = df.select_dtypes(include=['int64', 'float64']).columns

        if len(col_numericas) > 0:
            col_x = st.selectbox("Selecciona una columna numérica para graficar:", col_numericas)
            fig, ax = plt.subplots()
            ax.hist(df[col_x], bins=10)
            st.pyplot(fig)
        else:
            st.warning("No se encontraron columnas numéricas para graficar.")

    except Exception as e:
        st.error(f"❌ Error al leer el archivo: {e}")
