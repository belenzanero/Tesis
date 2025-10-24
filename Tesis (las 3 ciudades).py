import streamlit as st
import folium
from streamlit_folium import st_folium

st.title("Buscador de Alojamiento - Proyecto Tesis")

# Selección de ciudad
ciudad = st.selectbox("Seleccioná una ciudad", ["Madrid", "Barcelona", "Valencia"])

# Ingreso de universidad (opcional)
universidad = st.text_input("Ingresá el nombre de la universidad (opcional)")

# Filtros de búsqueda
precio_max = st.number_input("Precio máximo (€)", min_value=0, step=100)
tipos_disponibles = ["chalet", "duplex", "flat", "penthouse", "studio"]
tipos = st.multiselect("Tipos de propiedad", tipos_disponibles)
preferencia = st.radio("¿Qué preferís priorizar?", ["Precio", "Ubicación", "Ambas"])

st.write("Buscando alojamientos en:", ciudad)
if universidad:
    st.write("Cerca de la universidad:", universidad)

# Mostrar mapa base
if ciudad == "Madrid":
    coords = [40.4168, -3.7038]
elif ciudad == "Barcelona":
    coords = [41.3874, 2.1686]
else:
    coords = [39.4699, -0.3763]

m = folium.Map(location=coords, zoom_start=12)
folium.Marker(coords, popup=f"{ciudad} centro").add_to(m)

st_data = st_folium(m, width=800, height=500)

