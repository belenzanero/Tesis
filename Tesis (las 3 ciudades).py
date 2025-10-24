# -*- coding: utf-8 -*-
"""
Created on Tue Sep  2 13:29:37 2025

@author: bzane
"""

import requests
import base64
import pandas as pd
import numpy as np
import folium
import polyline
import time

# --- CLAVES API ---
IDEALISTA_API_KEY = "rd99ggm2lpi3jakfai2f8agtihxf87g6".strip()
IDEALISTA_API_SECRET = " rRpq0cYQ3I3Y".strip()
GOOGLE_API_KEY = "AIzaSyDQfubUQ1qx78OHV-5qYS4TnMKdFTM-FD0"

# --- DATOS DE CIUDADES Y UNIVERSIDADES ---
ciudades = {
    "madrid": {
        "centro": (40.4203, -3.7058),  # Gran Vía
        "universidades": [
            {"nombre": "Universidad Autónoma de Madrid", "lat": 40.5443, "lon": -3.6969},
            {"nombre": "Universidad Complutense de Madrid", "lat": 40.4469, "lon": -3.7289},
            {"nombre": "Universidad Politécnica de Madrid", "lat": 40.4521, "lon": -3.7286},
            {"nombre": "Universidad de Alcalá", "lat": 40.5112, "lon": -3.3495},
            {"nombre": "Universidad Rey Juan Carlos - Móstoles", "lat": 40.3333, "lon": -3.8653},
            {"nombre": "Universidad de Castilla-La Mancha (Madrid)", "lat": 40.4078, "lon": -3.6964},
            {"nombre": "Universidad de Navarra (Campus Madrid)", "lat": 40.4322, "lon": -3.6853},
            {"nombre": "Universidad Pontificia Comillas", "lat": 40.4339, "lon": -3.7147},
            {"nombre": "Universidad San Pablo CEU", "lat": 40.4463, "lon": -3.6885},
            {"nombre": "Universidad Europea de Madrid", "lat": 40.3936, "lon": -3.9197},
            {"nombre": "Universidad Francisco de Vitoria", "lat": 40.4194, "lon": -3.8903},
            {"nombre": "Universidad Antonio de Nebrija", "lat": 40.4301, "lon": -3.7176},
            {"nombre": "Universidad Camilo José Cela", "lat": 40.3958, "lon": -3.6525},
            {"nombre": "Universidad Villanueva", "lat": 40.4485, "lon": -3.6895},
            {"nombre": "Universidad a Distancia de Madrid (UDIMA)", "lat": 40.5764, "lon": -3.6331},
        ]
    },
    "barcelona": {
        "centro": (41.3870, 2.1701),
        "universidades": [
            {"nombre": "Universidad de Barcelona (UB)", "lat": 41.3859, "lon": 2.1687},
            {"nombre": "Universidad Autónoma de Barcelona (UAB)", "lat": 41.5005, "lon": 2.1072},
            {"nombre": "Universidad Politécnica de Cataluña (UPC)", "lat": 41.3878, "lon": 2.1136},
            {"nombre": "Universidad Pompeu Fabra (UPF)", "lat": 41.3890, "lon": 2.1900},
            {"nombre": "Universitat Oberta de Catalunya (UOC)", "lat": 41.4036, "lon": 2.1946},
            {"nombre": "Universidad Ramon Llull (URL)", "lat": 41.3993, "lon": 2.1475},
            {"nombre": "Universidad Internacional de Cataluña (UIC)", "lat": 41.4011, "lon": 2.1418},
            {"nombre": "Universidad Abat Oliba CEU (UAO CEU)", "lat": 41.4094, "lon": 2.1375},
            {"nombre": "Universidad de Vic - Universidad Central de Cataluña (UVic-UCC)", "lat": 41.9303, "lon": 2.2542},
        ]
    },
    "valencia": {
        "centro": (39.4699, -0.3763),
        "universidades": [
            {"nombre": "Universitat de València (UV)", "lat": 39.4780, "lon": -0.3416},
            {"nombre": "Universitat Politècnica de València (UPV)", "lat": 39.4811, "lon": -0.3455},
            {"nombre": "Universidad Católica de Valencia San Vicente Mártir (UCV)", "lat": 39.4713, "lon": -0.3799},
            {"nombre": "Universidad Cardenal Herrera CEU (CEU UCH)", "lat": 39.4284, "lon": -0.3843},
            {"nombre": "Universidad Europea de Valencia", "lat": 39.4721, "lon": -0.3776},
            {"nombre": "Universidad Internacional de Valencia (VIU)", "lat": 39.4719, "lon": -0.3762},
            {"nombre": "Florida Universitària", "lat": 39.3962, "lon": -0.4494},
            {"nombre": "EDEM Escuela de Empresarios", "lat": 39.4553, "lon": -0.3196},
        ]
    }
}


# --- TOKEN IDEALISTA ROBUSTO ---
def _request_token(base_url, api_key, api_secret):
    cred = f"{api_key}:{api_secret}"
    b64 = base64.b64encode(cred.encode()).decode()
    headers = {
        "Authorization": f"Basic {b64}",
        "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
        "Accept": "application/json",
    }
    data = {"grant_type": "client_credentials", "scope": "read"}
    url = f"{base_url}/oauth/token"
    try:
        r = requests.post(url, headers=headers, data=data, timeout=25)
    except requests.RequestException as e:
        return None, f"network_error: {e}"

    try:
        payload = r.json()
    except ValueError:
        payload = {"non_json_body": r.text[:600]}

    if r.status_code == 200 and isinstance(payload, dict) and payload.get("access_token"):
        return payload["access_token"], None

    return None, {"status": r.status_code, "payload": payload}

def get_token(api_key, api_secret):
    # 1) SANDBOX
    token, err = _request_token("https://api-sandbox.idealista.com", api_key, api_secret)
    if token:
        print("🔑 Token OK (SANDBOX)")
        return token, "sandbox"

    # 2) PRODUCCIÓN
    token_prod, err_prod = _request_token("https://api.idealista.com", api_key, api_secret)
    if token_prod:
        print("🔑 Token OK (PRODUCCIÓN)")
        return token_prod, "prod"

    raise SystemExit(f"❌ No se pudo obtener token Idealista.\nÚltimo error: {err_prod}")


def obtener_tiempo_google(orig, dest, modo):
    url = "https://maps.googleapis.com/maps/api/distancematrix/json"
    params = {"origins": orig, "destinations": dest, "mode": modo, "key": GOOGLE_API_KEY}
    try:
        r = requests.get(url, params=params, timeout=25)
        r.raise_for_status()
        return r.json()["rows"][0]["elements"][0]["duration"]["value"] / 60
    except Exception:
        return float("inf")

def obtener_ruta_directions(origen, destino, modo, api_key):
    url = "https://maps.googleapis.com/maps/api/directions/json"
    params = {"origin": origen, "destination": destino, "mode": modo, "key": api_key}
    try:
        r = requests.get(url, params=params, timeout=25)
        if r.status_code == 200:
            data = r.json()
            if data.get("routes"):
                puntos_codificados = data["routes"][0]["overview_polyline"]["points"]
                return polyline.decode(puntos_codificados)
    except Exception:
        pass
    return []

def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    phi1, phi2 = np.radians(lat1), np.radians(lat2)
    dphi = np.radians(lat2 - lat1)
    dlambda = np.radians(lon2 - lon1)
    a = np.sin(dphi/2)**2 + np.cos(phi1)*np.cos(phi2)*np.sin(dlambda/2)**2
    return R * (2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a)))

def generar_link_maps(lat_origen, lon_origen, lat_destino, lon_destino, modo):
    return f"https://www.google.com/maps/dir/?api=1&origin={lat_origen},{lon_origen}&destination={lat_destino},{lon_destino}&travelmode={modo}"

def buscar_idealista(token, lat, lon, presupuesto, max_items=50, num_page=1):
    url = f"{base_search}/3.5/es/search"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
    }
    # Idealista espera strings en form-urlencoded
    data = {
        "center": f"{lat},{lon}",
        "distance": "5000",             # metros
        "propertyType": "homes",
        "operation": "rent",
        "maxPrice": str(presupuesto),
        "maxItems": str(max_items),
        "numPage": str(num_page),
    }

    try:
        r = requests.post(url, headers=headers, data=data, timeout=25)
    except requests.RequestException as e:
        raise SystemExit(f"❌ Error de red llamando a Idealista: {e}")

    try:
        payload = r.json()
    except ValueError:
        raise SystemExit(f"❌ Respuesta no-JSON de Idealista (status {r.status_code}): {r.text[:500]}")

    if r.status_code == 401 or payload.get("error") in {"invalid_token", "invalid_client"}:
        raise SystemExit(f"❌ Autenticación fallida en Idealista: {payload}")

    if r.status_code == 400:
        raise SystemExit(f"❌ Parámetros inválidos (400): {payload}")

    if "elementList" not in payload:
        raise SystemExit(f"❌ La respuesta no trae 'elementList'. Detalle: {payload}")

    elementos = payload.get("elementList", [])
    if not elementos:
        print("ℹ️ Búsqueda sin resultados en Idealista para esos filtros.")
        return pd.DataFrame()

    return pd.DataFrame(elementos)

# --- SELECCIÓN DE CIUDAD ---
print("\n🏙️ Ciudades disponibles:")
for i, ciudad in enumerate(ciudades.keys(), 1):
    print(f"{i}. {ciudad.capitalize()}")

op_ciudad = int(input("📌 Ingresá el número de la ciudad donde buscás alojamiento: ").strip())
lista_ciudades = list(ciudades.keys())

if not 1 <= op_ciudad <= len(lista_ciudades):
    print("❌ Opción no válida.")
    raise SystemExit(1)

ciudad_seleccionada = lista_ciudades[op_ciudad - 1]
nombre_ciudad = ciudad_seleccionada
info_ciudad = ciudades[ciudad_seleccionada]

universidades = info_ciudad["universidades"]
centro_ciudad = info_ciudad["centro"]  # (lat, lon)
lat_centro, lon_centro = centro_ciudad

# Etiqueta del centro (Gran Vía solo en Madrid)
nombre_centro = "Gran Vía" if nombre_ciudad == "madrid" else f"Centro de {nombre_ciudad.capitalize()}"

# --- INPUT DEL USUARIO ---
print("\n🎓 Universidades disponibles:")
for i, u in enumerate(universidades, 1):
    print(f"{i}. {u['nombre']}")
op = int(input("📌 Ingresá el número de tu universidad: ").strip())
lat_uni, lon_uni = universidades[op-1]["lat"], universidades[op-1]["lon"]
nombre_uni = universidades[op-1]["nombre"]

presupuesto = float(input("💶 Precio máximo (€): "))
print(f"\n🏠 Tipos de propiedad disponibles en Idealista ({nombre_ciudad.capitalize()}):")
tipos_disponibles = ["chalet", "duplex", "flat", "penthouse", "studio"]
for i, tipo in enumerate(tipos_disponibles, 1):
    print(f"{i}. {tipo}")
opciones = input("📌 Ingresá los números que te interesan (separados por coma): ")
indices = [int(i.strip()) for i in opciones.split(",") if i.strip().isdigit()]
tipo_propiedad = [tipos_disponibles[i-1] for i in indices if 1 <= i <= len(tipos_disponibles)]

tamano_min = input("📏 Tamaño mínimo en m² (opcional): ").strip()
rooms_min = int(input("🛏️ Mínimo de habitaciones: "))
banos_min = int(input("🚿 Mínimo de baños: "))
exterior = input("🌞 ¿Querés que sea exterior? (si/no): ").strip().lower() == "si"

print("\n📊 ¿Qué preferís priorizar?")
print("1. Estar más cerca de la universidad")
print(f"2. Estar más cerca de {nombre_centro}")
print("3. Un equilibrio entre ambas")
preferencia = int(input("Elegí 1, 2 o 3: ").strip())
medio_transporte = input("\n🚶‍♂️ ¿Cómo te gustaría viajar? (driving / walking / transit): ").strip().lower()
tiempo_max = int(input("⏱ Tiempo máximo permitido (en minutos): "))

# --- CONSULTA A LA API ---
token, entorno = get_token(IDEALISTA_API_KEY, IDEALISTA_API_SECRET)
base_search = "https://api-sandbox.idealista.com" if entorno == "sandbox" else "https://api.idealista.com"

df = buscar_idealista(token, lat_uni, lon_uni, presupuesto, max_items=50, num_page=1)

if df.empty:
    raise SystemExit("⚠️ No se encontraron propiedades con esos criterios. Probá aumentar el presupuesto, la distancia o relajar filtros.")

# Validaciones mínimas
for c in ["latitude", "longitude"]:
    if c not in df.columns:
        raise SystemExit(f"❌ La API no devolvió la columna obligatoria '{c}'. Payload inesperado.")

df = df.dropna(subset=["latitude", "longitude"]).copy()

# Normalizar columnas que pueden faltar
defaults = {
    "rooms": 0,
    "bathrooms": 0,
    "size": 0,
    "exterior": False,
    "hasLift": False,
    "address": "No disponible",
    "url": "",
    "price": 0,
    "floor": "No disponible",
    "detailedType": "",
}
for c, default in defaults.items():
    if c not in df.columns:
        df[c] = default
    df[c] = df[c].fillna(default)

# detailedType puede venir como dict
def _tipo_str(x):
    if isinstance(x, dict):
        return (x.get("subTypology") or x.get("typology") or "").lower()
    return str(x).lower()

df["detailedType_str"] = df["detailedType"].apply(_tipo_str)

# Filtros del usuario
df = df[(df["rooms"] >= rooms_min) & (df["bathrooms"] >= banos_min)]
if tamano_min:
    try:
        df = df[df["size"] >= float(tamano_min)]
    except ValueError:
        pass
if tipo_propiedad:
    df = df[df["detailedType_str"].apply(lambda s: any(tp in s for tp in tipo_propiedad))]
if exterior:
    df = df[df["exterior"] == True]

if df.empty:
    raise SystemExit("⚠️ Después de aplicar filtros no quedó ninguna propiedad. Relajá los filtros.")

# Tiempos y distancias
df["tiempo_uni"] = df.apply(lambda row: obtener_tiempo_google(
    f"{row['latitude']},{row['longitude']}", f"{lat_uni},{lon_uni}", medio_transporte), axis=1)

# Centro de ciudad (Gran Vía para Madrid, centro para el resto)
lat_ref, lon_ref = lat_centro, lon_centro
modo_ref = "transit" if medio_transporte not in {"driving", "walking", "bicycling"} else medio_transporte

df["tiempo_centro"] = df.apply(lambda row: obtener_tiempo_google(
    f"{row['latitude']},{row['longitude']}", f"{lat_ref},{lon_ref}", modo_ref), axis=1)

df["distancia_km_uni"] = df.apply(lambda row: haversine(row["latitude"], row["longitude"], lat_uni, lon_uni), axis=1)
df["distancia_km_centro"] = df.apply(lambda row: haversine(row["latitude"], row["longitude"], lat_ref, lon_ref), axis=1)

# Orden según preferencia
if preferencia == 1:
    df = df[df["tiempo_uni"] <= tiempo_max].sort_values("tiempo_uni")
elif preferencia == 2:
    df = df.sort_values("tiempo_centro")
else:
    df = df[df["tiempo_uni"] <= tiempo_max].copy()
    df["ponderado"] = 0.5 * df["tiempo_uni"] + 0.5 * df["tiempo_centro"]
    df = df.sort_values("ponderado")

# Top 3
df = df.head(3).reset_index(drop=True)
df["id"] = df.index + 1

# --- RESULTADOS Y MAPA ---
print("\n📋 Opciones sugeridas:")
mapa = folium.Map(location=[lat_uni, lon_uni], zoom_start=13)
folium.Marker([lat_uni, lon_uni], popup=nombre_uni, icon=folium.Icon(color="blue")).add_to(mapa)
colores = ["red", "green", "purple"]

for i, fila in df.iterrows():
    # Elegir destino según preferencia
    if preferencia in [1, 3]:
        lat_destino = lat_uni
        lon_destino = lon_uni
    else:
        lat_destino = lat_ref
        lon_destino = lon_ref

    # Generar link de Google Maps
    link_maps = generar_link_maps(fila["latitude"], fila["longitude"], lat_destino, lon_destino, medio_transporte)

    print(f"\n🏠 #{fila['id']}")
    print(f"- Precio: €{fila['price']}")
    print(f"- Tamaño: {fila['size']} m2")
    print(f"- Habitaciones: {fila['rooms']}, Baños: {fila['bathrooms']}")
    print(f"- Dirección: {fila.get('address', 'No disponible')}")
    print(f"- Exterior: {'Sí' if fila.get('exterior') else 'No'}")
    print(f"- Ascensor: {'Sí' if fila.get('hasLift') else 'No'}")
    print(f"- Piso: {fila.get('floor', 'No disponible')}")
    print(f"- Tiempo a universidad: {fila['tiempo_uni']:.1f} min ({fila['distancia_km_uni']:.2f} km)")
    print(f"- Tiempo a {nombre_centro}: {fila['tiempo_centro']:.1f} min ({fila['distancia_km_centro']:.2f} km)")
    print(f"- Link: {fila['url']}")
    print(f"- Cómo llegar (Google Maps): {link_maps}")

    popup = f"#{fila['id']} - €{fila['price']}<br>{fila.get('address', '')}<br>{fila['tiempo_uni']:.1f} min"
    folium.Marker(
        [fila['latitude'], fila['longitude']],
        popup=popup,
        icon=folium.DivIcon(html=f"<div style='font-size: 10pt; color:{colores[i]}'>{fila['id']}</div>")
    ).add_to(mapa)

    # Trazo de ruta
    ruta = obtener_ruta_directions(
        f"{fila['latitude']},{fila['longitude']}",
        f"{lat_destino},{lon_destino}",
        medio_transporte,
        GOOGLE_API_KEY
    )
    if ruta:
        folium.PolyLine(locations=ruta, color=colores[i], weight=3, opacity=0.7).add_to(mapa)

mapa.save("mapa_recomendado.html")
print("\n🗺️ Mapa guardado como 'mapa_recomendado.html'")
