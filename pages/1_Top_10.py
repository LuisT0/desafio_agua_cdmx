import streamlit as st
import pandas as pd
import plotly.express as px
import geopandas as gpd

# Cargar datos
agua_cdmx = gpd.read_file('consumo_agua.json')

# Título y narrativa
st.title("💧 Desafío 1: ¿Quién consume más agua?")
st.subheader("¡Hora de apostar! 💦")
st.write(
    """
    Bienvenido a nuestro primer reto del **Desafío del Agua en CDMX**.  
    Hoy jugamos a ser detectives hídricos. Antes de mostrarte el ranking real, 
    quiero que uses tu intuición:  
    **¿Qué colonia crees que es la campeona del gasto hídrico?** 🏆
    
    Este no es un simple ranking... es la oportunidad de poner a prueba cuánto conoces tu ciudad.
    """
)

# Preguntas motivadoras
st.markdown("**¿Te imaginas quién se lleva el oro?** 🌟")
st.markdown("**¿Será la más poblada... o la más lujosa?** 🤔")

# Selector de apuesta
colonias_unicas = agua_cdmx["colonia"].dropna().unique()
prediccion = st.selectbox("👉 Elige la colonia que crees que gana:", sorted(colonias_unicas))

# Botón para revelar el resultado
if st.button("🎯 ¡Hacer mi apuesta!"):
    # Filtrar Top 10
    top10 = agua_cdmx.sort_values(by="PROMVIVCON", ascending=False).head(10)
    campeona = top10.iloc[0]["colonia"]

    # Mensaje de resultado
    if prediccion == campeona:
        st.success(f"🎉 ¡Le atinaste! La colonia **{campeona}** es la campeona del consumo. 💦")
    elif prediccion in top10["colonia"].values:
        st.info(f"👌 Casi casi... **{prediccion}** está en el top 10, pero la ganadora es **{campeona}** 🏆")
    else:
        st.error(f"🙈 Ups!... **{prediccion}** no aparece en el top 10. La ganadora es **{campeona}** 🏆")

    # Visualización en barras
    fig = px.bar(
        top10,
        x="PROMVIVCON",
        y="colonia",
        orientation="h",
        title="Top 10 Colonias con Mayor Consumo de Agua",
        labels={"PROMVIVCON": "Consumo (m³)", "colonia": "Colonia"},
        text="PROMVIVCON"
    )
    fig.update_traces(texttemplate='%{text:.0f}', textposition='outside')
    fig.update_layout(yaxis=dict(categoryorder="total ascending"))
    st.plotly_chart(fig, use_container_width=True)

    # Mapa con la campeona resaltada
    top10["color"] = top10["colonia"].apply(
        lambda x: "Campeona" if x == campeona else "Top 10"
    )

    fig_map = px.choropleth_mapbox(
        top10,
        geojson=top10.geometry,
        locations=top10.index,
        color="color",
        color_discrete_map={"Campeona": "red", "Top 10": "lightblue"},
        hover_name="colonia",
        hover_data={"PROMVIVCON": True, "color": False},
        mapbox_style="carto-positron",
        zoom=10,
        center={"lat": 19.4326, "lon": -99.1332},  # Centro CDMX
        opacity=0.6,
    )

    fig_map.update_layout(
        title="Mapa Interactivo: Top 10 Colonias con Mayor Consumo de Agua",
        margin={"r":0, "t":40, "l":0, "b":0}
    )

    st.plotly_chart(fig_map, use_container_width=True)

    # Reflexión final
    st.success("💡 ¿Te sorprendió el resultado? Reflexiona... y prepárate para el siguiente desafío. 🚀")
