import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf

st.set_page_config(
    page_title="Peso colombiano vs Dólar",
    page_icon="💵",
    layout="wide",
)

# ---------- Estilos ----------
st.markdown(
    """
    <style>
    .titulo {font-size: 2.2rem; font-weight: 800; margin-bottom: 0;}
    .subtitulo {color: #888; margin-top: 0;}
    </style>
    """,
    unsafe_allow_html=True,
)
st.markdown('<p class="titulo">🇨🇴 Peso colombiano vs 🇺🇸 Dólar</p>', unsafe_allow_html=True)
st.markdown(
    '<p class="subtitulo">Gráfica de cajas en tiempo real (cuántos pesos cuesta 1 dólar)</p>',
    unsafe_allow_html=True,
)

# ---------- Controles ----------
with st.sidebar:
    st.header("⚙️ Opciones")
    periodo = st.selectbox(
        "¿Cuánto tiempo atrás quieres ver?",
        ["5 días", "1 mes", "3 meses"],
        index=1,
    )
    agrupar = st.radio(
        "Una caja por...",
        ["Día", "Semana", "Hora del día"],
        help="Cada caja resume los precios que hubo en ese grupo.",
    )
    mostrar_puntos = st.checkbox("Mostrar todos los puntos", value=False)
    st.caption("Los datos se actualizan solos cada minuto.")
    st.caption("Fuente: Yahoo Finance (COP=X). El mercado cierra los fines de semana.")

CONFIG = {
    "5 días": ("5d", "15m"),
    "1 mes": ("1mo", "1h"),
    "3 meses": ("3mo", "1h"),
}


@st.cache_data(ttl=60)
def cargar_datos(periodo_yf: str, intervalo: str) -> pd.DataFrame:
    df = yf.Ticker("COP=X").history(period=periodo_yf, interval=intervalo)
    if df.empty:
        return df
    df.index = df.index.tz_convert("America/Bogota")
    return df[["Close"]].rename(columns={"Close": "precio"})


def etiquetar(df: pd.DataFrame, modo: str) -> pd.Series:
    if modo == "Día":
        return pd.Series(df.index.strftime("%d/%m"), index=df.index)
    if modo == "Semana":
        semana = df.index.isocalendar().week
        return pd.Series("Sem " + semana.astype(str).values, index=df.index)
    return pd.Series(df.index.hour.astype(str).values + ":00", index=df.index)


# Se refresca solo cada 60 segundos, sin recargar toda la página
@st.fragment(run_every=60)
def mostrar_grafica(periodo_txt: str, modo: str, puntos: bool):
    periodo_yf, intervalo = CONFIG[periodo_txt]
    try:
        df = cargar_datos(periodo_yf, intervalo)
    except Exception as e:
        st.error(f"No se pudieron traer los datos: {e}")
        return

    if df.empty:
        st.warning("No llegaron datos. Intenta de nuevo en un momento.")
        return

    # --- Métricas ---
    actual = df["precio"].iloc[-1]
    inicial = df["precio"].iloc[0]
    cambio = actual - inicial
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Precio actual", f"${actual:,.2f}", f"{cambio:+,.2f} en el periodo")
    c2.metric("Mínimo", f"${df['precio'].min():,.2f}")
    c3.metric("Máximo", f"${df['precio'].max():,.2f}")
    c4.metric("Promedio", f"${df['precio'].mean():,.2f}")

    # --- Box plot ---
    df = df.copy()
    df["grupo"] = etiquetar(df, modo)
    orden = list(dict.fromkeys(df["grupo"]))
    if modo == "Hora del día":
        orden = sorted(orden, key=lambda x: int(x.split(":")[0]))

    colores = [
        f"hsl({int(200 + 60 * i / max(len(orden) - 1, 1))}, 70%, 55%)"
        for i in range(len(orden))
    ]

    fig = go.Figure()
    for grupo, color in zip(orden, colores):
        datos = df.loc[df["grupo"] == grupo, "precio"]
        fig.add_trace(
            go.Box(
                y=datos,
                name=grupo,
                boxmean=True,  # la línea punteada es el promedio
                boxpoints="all" if puntos else "outliers",
                marker_color=color,
                line=dict(width=1.5),
                hovertemplate="%{y:,.2f}<extra>" + grupo + "</extra>",
            )
        )

    fig.update_layout(
        title=f"Precio del dólar en pesos colombianos (una caja por {modo.lower()})",
        yaxis_title="Pesos por dólar (COP)",
        xaxis_title=modo,
        showlegend=False,
        height=550,
        template="plotly_white",
        margin=dict(l=20, r=20, t=60, b=20),
    )
    fig.update_yaxes(tickformat=",.0f", gridcolor="rgba(150,150,150,0.25)")
    fig.update_xaxes(categoryorder="array", categoryarray=orden)

    st.plotly_chart(fig, use_container_width=True)
    ultima = df.index[-1].strftime("%d/%m/%Y %H:%M")
    st.caption(f"Último dato: {ultima} (hora de Colombia)")

    with st.expander("📖 ¿Cómo leer esta gráfica?"):
        st.markdown(
            """
- **La caja** muestra dónde estuvo la mitad de los precios (del cuartil 1 al cuartil 3).
- **La línea del medio** es la mediana.
- **La línea punteada** es el promedio.
- **Los bigotes** (las rayitas) muestran el rango normal de precios.
- **Los puntos sueltos** son valores raros (outliers), días con saltos fuertes.
            """
        )


mostrar_grafica(periodo, agrupar, mostrar_puntos)
