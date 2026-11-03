
import streamlit as st
import pandas as pd
import plotly.express as px
import folium
from streamlit_folium import st_folium
from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.units import cm
from html import escape


# =====================================================
# 1. CONFIGURACIÓN
# =====================================================

st.set_page_config(
    page_title="Observatorio Vial",
    page_icon="🚦",
    layout="wide"
)


# =====================================================
# 2. ESTILOS
# =====================================================

st.markdown("""
<style>
.stApp {
    background-color: #f3f6fa;
}
[data-testid="stSidebar"] {
    background-color: #17365D;
}
[data-testid="stSidebar"] * {
    color: white;
}
div[data-testid="stMetric"] {
    background-color: white;
    padding: 18px;
    border-radius: 12px;
    border: 1px solid #dce3eb;
}
h1, h2, h3 {
    color: #17365D;
}
</style>
""", unsafe_allow_html=True)


# =====================================================
# 3. ENCABEZADO
# =====================================================

st.title("🚦 OBSERVATORIO VIAL")

st.subheader(
    "Sistema de análisis, visualización y priorización de siniestros viales"
)

st.caption(
    "HERRAMIENTA DE APOYO PARA LA SEGURIDAD VIAL"
)

st.divider()


# =====================================================
# 4. CARGA DE DATOS
# =====================================================

@st.cache_data
def cargar_datos():
    df = pd.read_csv("dataset_final.csv")

    df.columns = df.columns.str.strip()

    df["clasificacion_gravedad"] = (
        df["clasificacion_gravedad"]
        .astype(str)
        .str.strip()
        .str.lower()
    )

    df["zona"] = df["zona"].fillna("Sin zona")

    df["momento_exacto"] = pd.to_datetime(
        df["momento_exacto"],
        errors="coerce"
    )

    df["latitud"] = pd.to_numeric(
        df["latitud"], errors="coerce"
    )

    df["longitud"] = pd.to_numeric(
        df["longitud"], errors="coerce"
    )

    return df


try:
    df = cargar_datos()
except Exception as e:
    st.error(f"No se pudo cargar el archivo dataset_final.csv: {e}")
    st.stop()


# =====================================================
# 5. FILTROS
# =====================================================

st.sidebar.title("🔎 FILTROS")

zonas_disponibles = sorted(
    df["zona"].dropna().unique().tolist()
)

gravedades_disponibles = sorted(
    df["clasificacion_gravedad"].dropna().unique().tolist()
)

zonas_seleccionadas = st.sidebar.multiselect(
    "Seleccionar zonas",
    zonas_disponibles,
    default=zonas_disponibles
)

gravedades_seleccionadas = st.sidebar.multiselect(
    "Seleccionar gravedad",
    gravedades_disponibles,
    default=gravedades_disponibles
)

df_filtrado = df[
    df["zona"].isin(zonas_seleccionadas)
    & df["clasificacion_gravedad"].isin(gravedades_seleccionadas)
].copy()


# =====================================================
# 6. INDICADORES GENERALES
# =====================================================

st.header("📊 Indicadores generales")

total = len(df_filtrado)

fatales = (
    df_filtrado["clasificacion_gravedad"] == "fatal"
).sum()

heridos = (
    df_filtrado["clasificacion_gravedad"] == "con heridos"
).sum()

danos = (
    df_filtrado["clasificacion_gravedad"] == "solo daños"
).sum()

cantidad_zonas = df_filtrado["zona"].nunique()

col1, col2, col3, col4, col5 = st.columns(5)

col1.metric("Total de siniestros", total)
col2.metric("Fatales", int(fatales))
col3.metric("Con heridos", int(heridos))
col4.metric("Solo daños", int(danos))
col5.metric("Zonas registradas", cantidad_zonas)

st.divider()


# =====================================================
# 7. GRÁFICO DE GRAVEDAD
# =====================================================

st.header("📈 Distribución por gravedad")

if not df_filtrado.empty:
    conteo_gravedad = (
        df_filtrado["clasificacion_gravedad"]
        .value_counts()
        .reset_index()
    )

    conteo_gravedad.columns = ["Gravedad", "Cantidad"]

    fig_gravedad = px.pie(
        conteo_gravedad,
        names="Gravedad",
        values="Cantidad",
        hole=0.45,
        title="Clasificación de los siniestros"
    )

    st.plotly_chart(fig_gravedad, use_container_width=True)
else:
    st.info("No hay datos para mostrar con los filtros seleccionados.")


# =====================================================
# 8. ZONAS CON MAYOR CANTIDAD DE SINIESTROS
# =====================================================

st.header("📍 Zonas con mayor cantidad de siniestros")

if not df_filtrado.empty:
    top_zonas = (
        df_filtrado["zona"]
        .value_counts()
        .head(10)
        .reset_index()
    )

    top_zonas.columns = ["Zona", "Cantidad"]

    fig_zonas = px.bar(
        top_zonas,
        x="Cantidad",
        y="Zona",
        orientation="h",
        text="Cantidad",
        title="Las 10 zonas con más siniestros"
    )

    fig_zonas.update_layout(
        yaxis={"categoryorder": "total ascending"}
    )

    st.plotly_chart(fig_zonas, use_container_width=True)


# =====================================================
# 9. DISTRIBUCIÓN POR HORARIO
# =====================================================

st.header("🕒 Distribución de siniestros por horario")

if not df_filtrado.empty:
    df_horarios = df_filtrado.dropna(
        subset=["momento_exacto"]
    ).copy()

    if not df_horarios.empty:
        df_horarios["hora"] = (
            df_horarios["momento_exacto"].dt.hour
        )

        conteo_horas = (
            df_horarios["hora"]
            .value_counts()
            .sort_index()
            .reindex(range(24), fill_value=0)
            .reset_index()
        )

        conteo_horas.columns = ["Hora", "Cantidad"]

        fig_horas = px.bar(
            conteo_horas,
            x="Hora",
            y="Cantidad",
            title="Cantidad de siniestros por hora del día"
        )

        st.plotly_chart(fig_horas, use_container_width=True)
    else:
        st.info("No hay horarios válidos para mostrar.")


st.divider()


# =====================================================
# 10. MAPA INTERACTIVO
# =====================================================

st.header("🗺️ Mapa de siniestros viales")

df_mapa = df_filtrado.dropna(
    subset=["latitud", "longitud"]
).copy()

# Validar coordenadas dentro de rangos geográficos
df_mapa = df_mapa[
    df_mapa["latitud"].between(-90, 90)
    & df_mapa["longitud"].between(-180, 180)
]

if not df_mapa.empty:

    centro_lat = df_mapa["latitud"].mean()
    centro_lon = df_mapa["longitud"].mean()

    mapa = folium.Map(
        location=[centro_lat, centro_lon],
        zoom_start=12,
        tiles="OpenStreetMap"
    )

    for _, fila in df_mapa.iterrows():

        gravedad = fila["clasificacion_gravedad"]

        if gravedad == "fatal":
            color = "red"
        elif gravedad == "con heridos":
            color = "orange"
        else:
            color = "blue"

        direccion = escape(str(fila.get("direccion_completa", "")))
        zona = escape(str(fila.get("zona", "")))
        gravedad_segura = escape(str(gravedad))

        popup_texto = f"""
        <b>Dirección:</b> {direccion}<br>
        <b>Zona:</b> {zona}<br>
        <b>Gravedad:</b> {gravedad_segura}
        """

        folium.CircleMarker(
            location=[
                fila["latitud"],
                fila["longitud"]
            ],
            radius=7,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.7,
            popup=folium.Popup(popup_texto, max_width=300)
        ).add_to(mapa)

    mapa.fit_bounds(
        df_mapa[["latitud", "longitud"]].values.tolist()
    )

    st_folium(
        mapa,
        width=None,
        height=580,
        returned_objects=[]
    )

    st.caption(
        "Rojo: fatal | Naranja: con heridos | Azul: solo daños."
    )

else:
    st.warning("No hay coordenadas válidas para mostrar en el mapa.")


st.divider()


# =====================================================
# 11. PRIORIZACIÓN DE ZONAS
# =====================================================

st.header("🎯 Priorización de zonas críticas")

# Esta puntuación es un criterio orientativo del proyecto.
# No representa una probabilidad estadística de accidentes.

resumen_zonas = df.groupby("zona").agg(
    total_siniestros=("id_feu", "count"),

    accidentes_fatales=(
        "clasificacion_gravedad",
        lambda x: (x == "fatal").sum()
    ),

    accidentes_con_heridos=(
        "clasificacion_gravedad",
        lambda x: (x == "con heridos").sum()
    ),

    accidentes_solo_danos=(
        "clasificacion_gravedad",
        lambda x: (x == "solo daños").sum()
    )

).reset_index()


resumen_zonas["puntaje_prioridad"] = (
    resumen_zonas["accidentes_fatales"] * 5
    + resumen_zonas["accidentes_con_heridos"] * 2
    + resumen_zonas["accidentes_solo_danos"]
)


def determinar_nivel(puntaje):
    if puntaje >= 10:
        return "Alta"
    elif puntaje >= 4:
        return "Media"
    else:
        return "Baja"


resumen_zonas["nivel_prioridad"] = (
    resumen_zonas["puntaje_prioridad"]
    .apply(determinar_nivel)
)


resumen_zonas = resumen_zonas.sort_values(
    by="puntaje_prioridad",
    ascending=False
)


st.write(
    "El sistema asigna un puntaje orientativo a cada zona "
    "considerando la gravedad y cantidad de siniestros registrados."
)

st.dataframe(
    resumen_zonas,
    use_container_width=True,
    hide_index=True
)


# =====================================================
# 12. ZONA CON MAYOR PRIORIDAD
# =====================================================

st.header("🚨 Resultado de la priorización")

if not resumen_zonas.empty:

    zona_principal = resumen_zonas.iloc[0]

    zona_nombre = zona_principal["zona"]
    puntaje = int(zona_principal["puntaje_prioridad"])
    nivel = zona_principal["nivel_prioridad"]

    with st.container(border=True):

        st.caption("ZONA CON MAYOR PUNTAJE DE PRIORIDAD")

        st.subheader(f"📍 {zona_nombre}")

        col1, col2 = st.columns(2)

        col1.metric("Puntaje obtenido", puntaje)

        col2.metric("Nivel de prioridad", nivel)

    st.subheader("Aspectos a evaluar")

    st.write(
        "- Señalización vial y estado de las calles."
    )

    st.write(
        "- Iluminación y visibilidad."
    )

    st.write(
        "- Flujo vehicular y comportamiento de conductores."
    )

    st.write(
        "- Presencia de peatones y motociclistas."
    )

    st.subheader("Acciones preventivas sugeridas")

    st.write(
        "- Reforzar la señalización horizontal y vertical."
    )

    st.write(
        "- Evaluar la iluminación de la zona."
    )

    st.write(
        "- Realizar controles preventivos de tránsito."
    )

    st.write(
        "- Analizar la necesidad de reductores de velocidad."
    )

    st.caption(
        "Las acciones son propuestas iniciales que deben "
        "validarse mediante inspecciones en el lugar."
    )


st.divider()


# =====================================================
# 13. TABLA DE REGISTROS
# =====================================================

st.header("📋 Registros de siniestros")

st.dataframe(
    df_filtrado,
    use_container_width=True,
    hide_index=True
)


# =====================================================
# 14. GENERAR INFORME PDF
# =====================================================

def generar_pdf():

    buffer = BytesIO()

    documento = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm
    )

    estilos = getSampleStyleSheet()

    titulo = ParagraphStyle(
        "TituloPersonalizado",
        parent=estilos["Title"],
        alignment=TA_CENTER,
        textColor=colors.HexColor("#17365D"),
        fontSize=18
    )

    elementos = []

    elementos.append(
        Paragraph("OBSERVATORIO VIAL", titulo)
    )

    elementos.append(Spacer(1, 10))

    elementos.append(
        Paragraph(
            "Informe de análisis de siniestros viales",
            estilos["Heading2"]
        )
    )

    elementos.append(Spacer(1, 15))

    elementos.append(
        Paragraph(
            f"Total de siniestros registrados: {len(df)}",
            estilos["Normal"]
        )
    )

    elementos.append(
        Paragraph(
            f"Accidentes fatales: "
            f"{int((df['clasificacion_gravedad'] == 'fatal').sum())}",
            estilos["Normal"]
        )
    )

    elementos.append(
        Paragraph(
            f"Accidentes con heridos: "
            f"{int((df['clasificacion_gravedad'] == 'con heridos').sum())}",
            estilos["Normal"]
        )
    )

    elementos.append(
        Paragraph(
            f"Accidentes solo daños: "
            f"{int((df['clasificacion_gravedad'] == 'solo daños').sum())}",
            estilos["Normal"]
        )
    )

    elementos.append(Spacer(1, 20))

    elementos.append(
        Paragraph(
            "Zonas con mayor puntaje de prioridad",
            estilos["Heading2"]
        )
    )

    datos_tabla = [
        [
            "Zona",
            "Total",
            "Fatales",
            "Con heridos",
            "Puntaje",
            "Prioridad"
        ]
    ]

    for _, fila in resumen_zonas.head(10).iterrows():

        datos_tabla.append([
            str(fila["zona"]),
            str(int(fila["total_siniestros"])),
            str(int(fila["accidentes_fatales"])),
            str(int(fila["accidentes_con_heridos"])),
            str(int(fila["puntaje_prioridad"])),
            str(fila["nivel_prioridad"])
        ])

    tabla = Table(
        datos_tabla,
        repeatRows=1
    )

    tabla.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0),
             colors.HexColor("#17365D")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("FONTSIZE", (0, 0), (-1, -1), 7),
            ("ALIGN", (1, 1), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1),
             [colors.white, colors.HexColor("#EAF0F6")])
        ])
    )

    elementos.append(tabla)

    elementos.append(Spacer(1, 20))

    elementos.append(
        Paragraph(
            "Observatorio Vial - Proyecto de Práctica Profesionalizante III",
            estilos["Italic"]
        )
    )

    documento.build(elementos)

    buffer.seek(0)

    return buffer.getvalue()


# =====================================================
# 15. DESCARGA DEL INFORME
# =====================================================

st.header("📄 Descargar informe")

pdf = generar_pdf()

st.download_button(
    label="📥 Descargar informe en PDF",
    data=pdf,
    file_name="informe_observatorio_vial.pdf",
    mime="application/pdf"
)


# =====================================================
# 16. PIE DE PÁGINA
# =====================================================

st.divider()

st.markdown("### 🚦 OBSERVATORIO VIAL")

st.caption(
    "Proyecto de Práctica Profesionalizante III"
)

