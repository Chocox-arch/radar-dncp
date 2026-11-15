import streamlit as st
import pandas as pd
from pyvis.network import Network
import streamlit.components.v1 as components

st.set_page_config(page_title="Radar DNCP - Paraguay", layout="wide")

st.title("🕸️ Radar de Redes y Vínculos - DNCP Paraguay")
st.markdown("Visualización de redes empresariales vinculadas por contactos telefónicos compartidos.")

@st.cache_data
def cargar_datos():
    df = pd.read_csv('parties.csv', low_memory=False)
    df['tel_limpio'] = df['contactPoint_telephone'].astype(str).str.replace(r'\D', '', regex=True)
    return df

with st.spinner("Cargando base de datos..."):
    df_parties = cargar_datos()

proveedores = df_parties[df_parties['roles'].str.contains('supplier|tenderer', case=False, na=False)].copy()

# Controles en la barra lateral
st.sidebar.header("🛠️ Configuración del Grafo")
min_empresas = st.sidebar.slider("Mínimo de empresas por teléfono:", min_value=2, max_value=6, value=2)

tel_validos = proveedores[(proveedores['tel_limpio'].str.len() >= 6) & (proveedores['tel_limpio'] != 'nan')]
duplicados_tel = tel_validos[tel_validos.duplicated(subset=['tel_limpio'], keep=False)]

# Filtramos los grupos según el slider
resumen_alertas = duplicados_tel.groupby('tel_limpio').agg(
    cantidad_empresas=('identifier_id', 'count'),
    nombres_empresas=('name', lambda x: list(x.unique())),
    ejemplo_direccion=('address_streetAddress', 'first')
).reset_index()

resumen_filtrado = resumen_alertas[resumen_filtrado_cond := (resumen_alertas['cantidad_empresas'] >= min_empresas)]

st.metric("Clusters de Riesgo Detectados", len(resumen_filtrado))

st.markdown("---")
st.subheader("🌐 Mapa Interactivo de Conexiones (Nodos)")
st.markdown("Cada círculo central (rojo) representa un **número de teléfono compartido**, y los círculos secundarios (azules) son las **empresas** vinculadas a él. ¡Podés mover los nodos con el mouse!")

# Generamos el Grafo con PyVis
net = Network(height="600px", width="100%", bgcolor="#0e1117", font_color="white")
net.barnes_hut() # Algoritmo de física para que los nodos se acomoden solos

# Construimos la red visual
for index, row in resumen_filtrado.iterrows():
    tel = str(row['tel_limpio'])
    nodo_tel_id = f"TEL: {tel}"
    
    # Nodo central del teléfono (Rojo)
    net.add_node(nodo_tel_id, label=f"Tel: {tel}", color="#ff4b4b", size=25)
    
    # Nodos de las empresas vinculadas (Azul)
    for empresa in row['nombres_empresas']:
        net.add_node(empresa, label=empresa[:25] + "...", title=empresa, color="#1f77b4", size=15)
        # Conectamos el teléfono con la empresa
        net.add_edge(nodo_tel_id, empresa, color="#ffffff", width=1)

# Guardamos el grafo en un archivo HTML temporal para renderizarlo en Streamlit
try:
    net.save_graph("grafo_cluster.html")
    with open("grafo_cluster.html", 'r', encoding='utf-8') as f:
        html_code = f.read()
    components.html(html_code, height=620)
except Exception as e:
    st.error(f"Error al generar el grafo visual: {e}")

st.markdown("---")
st.subheader("📋 Detalle de Datos Tabulares")
st.dataframe(resumen_filtrado[['tel_limpio', 'cantidad_empresas', 'ejemplo_direccion']].assign(
    empresas=resumen_filtrado['nombres_empresas'].apply(lambda x: " | ".join(x))
), use_container_width=True, hide_index=True)
