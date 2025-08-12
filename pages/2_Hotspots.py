import streamlit as st
import geopandas as gpd
import numpy as np
import plotly.express as px
from sklearn.cluster import DBSCAN

st.title("💥 Desafío 2: Hotspots densos — ¿Vecindario igual a consumo?")
st.subheader("Exploremos juntos los hotspots urbanos")

st.write("""
Primero vemos **vecindarios densos por cercanía** (DBSCAN geográfico, sin consumo).
Luego revelamos el **consumo por vivienda (PROMVIVCON)** para contrastar el hallazgo.
""")

# Cargar datos

agua_cdmx = gpd.read_file("consumo_agua.json")

# Asegurar CRS WGS84 (lat/lon)
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

# Centroides y coords

agua_cdmx["centroid"] = agua_cdmx.geometry.centroid
lats = agua_cdmx["centroid"].y.to_numpy()
lons = agua_cdmx["centroid"].x.to_numpy()
coords = np.column_stack([lats, lons])  


# Parámetros (mismos del notebook)

st.caption("Parámetros recomendados: eps≈0.8 km, min_samples=5 (ajústalos si lo deseas).")
col1, col2 = st.columns(2)
with col1:
    eps_km = st.slider("Radio DBSCAN (km)", 0.2, 2.0, 0.8, 0.1)
with col2:
    min_samples = st.slider("Mínimo de colonias por hotspot", 3, 12, 5, 1)

# DBSCAN geográfico (haversine: coords y eps en radianes)
coords_rad = np.radians(coords)
eps_rad = eps_km / 6371.0
db = DBSCAN(eps=eps_rad, min_samples=min_samples, metric="haversine").fit(coords_rad)
agua_cdmx["cluster_geo"] = db.labels_.astype(int)

# Mapa 1: Densidad pura (sin consumo)

st.markdown("### 📍 Mapa de densidad geográfica (sin consumo)")
st.info("Este mapa NO usa consumo. Cada color es un grupo por cercanía; -1 = ruido (sin grupo).")

fig_cluster = px.scatter_mapbox(
    agua_cdmx,
    lat=lats,
    lon=lons,
    color=agua_cdmx["cluster_geo"].astype(str),
    hover_name="colonia",
    hover_data={"cluster_geo": True},
    mapbox_style="carto-positron",
    zoom=10,
    center={"lat": 19.4326, "lon": -99.1332},
    opacity=0.75,
    title="Hotspots densos (DBSCAN geográfico)"
)
fig_cluster.update_layout(margin=dict(l=0, r=0, t=40, b=0))
st.plotly_chart(fig_cluster, use_container_width=True)

# =======================
# Botón: Revelar consumo + insight corto
# =======================
st.markdown("---")
if st.button("🔍 Revelar consumo"):
    st.markdown("### 💡 Mapa de consumo por vivienda (PROMVIVCON)")
    st.info("Ahora sí usamos PROMVIVCON: color y tamaño indican mayor consumo por vivienda.")

    fig_consumo = px.scatter_mapbox(
        agua_cdmx,
        lat=lats,
        lon=lons,
        size="PROMVIVCON",
        color="PROMVIVCON",
        color_continuous_scale="Blues",
        size_max=18,
        hover_name="colonia",
        hover_data={"PROMVIVCON": ":.2f", "cluster_geo": True},
        mapbox_style="carto-positron",
        zoom=10,
        center={"lat": 19.4326, "lon": -99.1332},
        opacity=0.85,
        title="Consumo por vivienda (PROMVIVCON)"
    )
    fig_consumo.update_layout(margin=dict(l=0, r=0, t=40, b=0))
    st.plotly_chart(fig_consumo, use_container_width=True)

    # Insight breve alineado al notebook: mediana del cluster más grande vs ruido
    cluster_counts = agua_cdmx["cluster_geo"].value_counts()
    # Excluir ruido para identificar el cluster "más grande"
    if -1 in cluster_counts.index:
        cluster_counts_no_noise = cluster_counts[cluster_counts.index != -1]
    else:
        cluster_counts_no_noise = cluster_counts

    cluster_mas_grande = int(cluster_counts_no_noise.idxmax()) if len(cluster_counts_no_noise) > 0 else None
    mediana_cluster_grande = float(
        agua_cdmx.loc[agua_cdmx["cluster_geo"] == cluster_mas_grande, "PROMVIVCON"].median()
    ) if cluster_mas_grande is not None else np.nan

    mediana_ruido = float(
        agua_cdmx.loc[agua_cdmx["cluster_geo"] == -1, "PROMVIVCON"].median()
    ) if (-1 in agua_cdmx["cluster_geo"].values) else np.nan

    st.markdown("#### 🧠 Insight rápido")
    if cluster_mas_grande is not None and not np.isnan(mediana_cluster_grande):
        st.write(f"- Cluster más grande (por nº de colonias): {cluster_mas_grande} | Mediana PROMVIVCON: {mediana_cluster_grande:.2f}.")
    else:
        st.write("- No se formó un cluster ‘grande’ (todos o casi todos quedaron como ruido). Ajusta eps/min_samples.")

    if not np.isnan(mediana_ruido):
        st.write(f"- Ruido (-1): Mediana consumo por vivienda: {mediana_ruido:.2f}.")
        if mediana_ruido >= mediana_cluster_grande:
            st.warning("Plot twist: el consumo mediano fuera de clusters (ruido) es comparable o mayor que en el cluster más grande.")
        else:
            st.info("El cluster más grande supera al ruido en mediana, pero observa en el mapa que los picos altos pueden estar aislados.")
    else:
        st.caption("Con esta configuración no hubo ruido (-1). Aun así, los máximos de consumo no necesariamente coinciden con los vecindarios más densos.")

    # =======================
    # Conclusión clara y breve
    # =======================
    st.markdown("### ✅ Conclusión: ¿Por qué estos son “hotspots”?")
    st.success(
        "Aquí ‘hotspot’ significa vecindario denso por cercanía (DBSCAN), no consumo alto. "
        "eps define qué tan cerca deben estar las colonias (radio en km) y min_samples cuántas se requieren para formar el grupo. "
        "Por eso puedes ver clusters en zonas muy juntas aunque su consumo no sea extraordinario. "
        "Al revelar consumo promedio por vivienda, el giro es evidente: los picos de consumo no siempre caen dentro de esos vecindarios densos. "
        "Densidad explica ‘dónde hay vecindarios’; consumo explica ‘dónde está la sed’. En el siguiente nivel unimos ambas."
    )