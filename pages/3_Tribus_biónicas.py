import streamlit as st
import geopandas as gpd
import numpy as np
import pandas as pd
import plotly.express as px
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler

st.title("🤖 Desafío 3: Tribus biónicas — geografía + consumo")

st.info("Una tribu biónica es un grupo de colonias que están cerca en el mapa y además se parecen en su consumo por vivienda (PROMVIVCON). Para que geografía y consumo pesen igual, los ponemos en la misma escala y luego usamos DBSCAN en ese espacio combinado; así emergen grupos coherentes y dejamos como ruido (-1) lo que no encaja.")

st.write("""
Aquí combinamos geografía (lat, lon) y consumo (PROMVIVCON) en la misma escala (z-scores)
y aplicamos DBSCAN para encontrar tribus: colonias cercanas con patrones de consumo similares.
""")

# 1) Cargar datos
agua_cdmx = gpd.read_file("consumo_agua.json")

# Asegurar CRS WGS84
if agua_cdmx.crs is None:
    agua_cdmx = agua_cdmx.set_crs(epsg=4326)
elif agua_cdmx.crs.to_epsg() != 4326:
    agua_cdmx = agua_cdmx.to_crs(epsg=4326)

# Validaciones mínimas
if "PROMVIVCON" not in agua_cdmx.columns:
    st.error("No se encontró la columna 'PROMVIVCON' en el dataset.")
    st.stop()
if "colonia" not in agua_cdmx.columns:
    agua_cdmx["colonia"] = "(sin_nombre)"

# 2) Preparar variables (centroides para lat/lon y vector de consumo)
agua_cdmx["centroid"] = agua_cdmx.geometry.centroid
lat = agua_cdmx["centroid"].y.to_numpy()
lon = agua_cdmx["centroid"].x.to_numpy()
cons = agua_cdmx["PROMVIVCON"].astype(float).to_numpy()

# Matriz de características y estandarización (igual que el notebook 3D)
X = np.column_stack([lat, lon, cons])
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# 3) Un solo control: “nivel de agrupación”
st.markdown("---")
nivel = st.select_slider(
    "Nivel de agrupación",
    options=["Suave", "Medio", "Fuerte"],
    value="Medio",
    help="Controla qué tan compactas deben ser las tribus (ajusta internamente eps y min_samples en el espacio escalado)."
)

# Mapear niveles a parámetros en espacio escalado (z-scores)
# Ajusta estos valores si en tu notebook usaste otros específicos
if nivel == "Suave":
    eps_scaled, min_samples = 0.9, 4
elif nivel == "Fuerte":
    eps_scaled, min_samples = 0.45, 6
else:  # Medio
    eps_scaled, min_samples = 0.5, 5

st.caption(f"eps (z-scores)={eps_scaled}, min_samples={min_samples}")

# 4) DBSCAN en espacio combinado (euclídea sobre z-scores)
db = DBSCAN(eps=eps_scaled, min_samples=min_samples, metric="euclidean")
labels = db.fit_predict(X_scaled)
agua_cdmx["tribu_id"] = labels.astype(int)

# 5) Mapa principal
st.markdown("### 🗺️ Tribus biónicas (color = grupo)")
st.info("Cada color es una tribu: colonias cercanas con consumo parecido. -1 es ruido (sin tribu).")

fig = px.scatter_mapbox(
    agua_cdmx,
    lat=lat,
    lon=lon,
    color=agua_cdmx["tribu_id"].astype(str),
    hover_name="colonia",
    hover_data={"PROMVIVCON": ":.2f", "tribu_id": True},
    mapbox_style="carto-positron",
    zoom=10,
    center={"lat": 19.4326, "lon": -99.1332},
    opacity=0.88,
    title=f"Tribus (DBSCAN en espacio escalado) — Nivel: {nivel}"
)
fig.update_layout(margin=dict(l=0, r=0, t=40, b=0))
st.plotly_chart(fig, use_container_width=True)

# 6) Mini explorador
st.markdown("### 🔎 Explora una tribu")
tribus = sorted(agua_cdmx["tribu_id"].unique())
tribu_sel = st.selectbox("Elige una tribu:", tribus)

df_t = agua_cdmx[agua_cdmx["tribu_id"] == tribu_sel].copy()
n = len(df_t)

colA, colB = st.columns([2, 1])
with colA:
    st.write(f"Colonias en tribu {tribu_sel}: {n}")
    if n > 0:
        tabla = df_t[["colonia", "PROMVIVCON"]].sort_values("PROMVIVCON", ascending=False).reset_index(drop=True)
        st.dataframe(tabla, use_container_width=True)
    else:
        st.info("Esta tribu quedó vacía con el nivel seleccionado.")

with colB:
    if n > 0:
        st.metric("Mediana PROMVIVCON", f"{df_t['PROMVIVCON'].median():.2f}")
        st.metric("Máximo PROMVIVCON", f"{df_t['PROMVIVCON'].max():.2f}")

# 7) Insight corto y conclusión
st.markdown("### 🧠 Insight rápido")
tribus_sin_ruido = [t for t in tribus if t != -1]
n_tribus = len(tribus_sin_ruido)
n_ruido = int((agua_cdmx["tribu_id"] == -1).sum())

st.write(f"- Tribus encontradas (excluyendo ruido): {n_tribus}")
st.write(f"- Colonias en ruido (-1): {n_ruido}")

resumen = (
    agua_cdmx.groupby("tribu_id", dropna=False)["PROMVIVCON"]
    .median()
    .reset_index()
    .rename(columns={"PROMVIVCON": "mediana_PROMVIVCON"})
    .sort_values("mediana_PROMVIVCON", ascending=False)
    .reset_index(drop=True)
)
if len(resumen) > 0:
    top_row = resumen.iloc[0]
    st.write(f"- Tribus top por mediana de consumo: {int(top_row['tribu_id'])} (mediana={top_row['mediana_PROMVIVCON']:.2f}).")

st.markdown("### ✅ Conclusión")
st.success(
    "Tribus = cercanía + consumo similar en la misma escala (z-scores). "
    "Sirven para planear acciones zonales coherentes: colonias vecinas con hábitos parecidos. "
    "Son distintas de los hotspots (solo vecindario) y del Top 10 (campeones sueltos)."
)