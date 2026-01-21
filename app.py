import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import date, timedelta
import io

# --------------------------------------------------
# CONFIG
# --------------------------------------------------
st.set_page_config(
    page_title="Bollinger Breakout Scanner",
    page_icon="📈",
    layout="wide"
)

st.title("📊 Bollinger Bands Breakout Scanner (Daily)")
st.markdown("**Segnali basati ESCLUSIVAMENTE sulla candela di ieri (chiusa)**")

# --------------------------------------------------
# SIDEBAR
# --------------------------------------------------
st.sidebar.header("⚙️ Configurazione")

DEFAULT_SYMBOLS = [
    "AAPL","MSFT","NVDA","META","GOOGL","AMZN","TSLA","NFLX",
    "AMD","INTC","CRM","ORCL","ADBE","JPM","BAC","GS","XOM",
    "CVX","KO","PEP","DIS","WMT","COST","SPY","QQQ","IWM"
]

uploaded_file = st.sidebar.file_uploader(
    "📁 Carica file TXT con simboli",
    type=["txt"]
)

if uploaded_file:
    symbols = uploaded_file.read().decode("utf-8").replace(",", "\n").split()
    symbols = [s.strip().upper() for s in symbols if s.strip()]
else:
    symbols = DEFAULT_SYMBOLS

st.sidebar.divider()

bb_period = st.sidebar.number_input("Periodo Bollinger", 10, 50, 20)
bb_std = st.sidebar.number_input("Deviazioni Standard", 1.0, 3.0, 2.0, step=0.1)

st.sidebar.info("📌 Il segnale è valido SOLO se la candela di IERI ha chiuso fuori banda")

# --------------------------------------------------
# DATA FETCH
# --------------------------------------------------
@st.cache_data
def fetch_data(symbol):
    end = date.today() + timedelta(days=1)
    start = end - timedelta(days=180)
    data = yf.download(symbol, start=start, end=end, progress=False)
    return data if not data.empty else None

# --------------------------------------------------
# ANALYSIS
# --------------------------------------------------
def analyze_stock(symbol):
    data = fetch_data(symbol)
    if data is None or len(data) < bb_period + 2:
        return None

    data = data.dropna()

    data["MA"] = data["Close"].rolling(bb_period).mean()
    data["STD"] = data["Close"].rolling(bb_period).std()
    data["Upper"] = data["MA"] + bb_std * data["STD"]
    data["Lower"] = data["MA"] - bb_std * data["STD"]

    # 👉 Candela di IERI
    candle = data.iloc[-2]

    close = candle["Close"]
    upper = candle["Upper"]
    lower = candle["Lower"]
    signal_date = candle.name

    if close > upper:
        signal = "🟢 Breakout Rialzista"
    elif close < lower:
        signal = "🔴 Breakout Ribassista"
    else:
        return None

    return {
        "Symbol": symbol,
        "Segnale": signal,
        "Close": close,
        "Upper": upper,
        "Lower": lower,
        "Data": signal_date,
        "DataFrame": data
    }

# --------------------------------------------------
# RUN SCAN
# --------------------------------------------------
if symbols:
    with st.spinner(f"Analisi di {len(symbols)} titoli..."):
        results = []
        for s in symbols:
            r = analyze_stock(s)
            if r:
                results.append(r)

    bullish = [r for r in results if "Rialzista" in r["Segnale"]]
    bearish = [r for r in results if "Ribassista" in r["Segnale"]]

    # --------------------------------------------------
    # RIALZISTI
    # --------------------------------------------------
    st.subheader("🟢 BREAKOUT RIALZISTI (Close > Banda Superiore – IERI)")

    if bullish:
        df_bull = pd.DataFrame([{
            "Simbolo": r["Symbol"],
            "Close": round(r["Close"], 2),
            "Banda Superiore": round(r["Upper"], 2),
            "Data Segnale": r["Data"].strftime("%d/%m/%Y")
        } for r in bullish])

        st.dataframe(df_bull, use_container_width=True)

    else:
        st.info("Nessun breakout rialzista trovato")

    # --------------------------------------------------
    # RIBASSISTI
    # --------------------------------------------------
    st.subheader("🔴 BREAKOUT RIBASSISTI (Close < Banda Inferiore – IERI)")

    if bearish:
        df_bear = pd.DataFrame([{
            "Simbolo": r["Symbol"],
            "Close": round(r["Close"], 2),
            "Banda Inferiore": round(r["Lower"], 2),
            "Data Segnale": r["Data"].strftime("%d/%m/%Y")
        } for r in bearish])

        st.dataframe(df_bear, use_container_width=True)

    else:
        st.info("Nessun breakout ribassista trovato")

    # --------------------------------------------------
    # GRAFICO
    # --------------------------------------------------
    st.divider()
    st.subheader("📈 Grafico Dettagliato con Bollinger")

    selectable = bullish + bearish
    if selectable:
        selected = st.selectbox(
            "Seleziona un titolo",
            [r["Symbol"] for r in selectable]
        )

        sel = next(r for r in selectable if r["Symbol"] == selected)
        d = sel["DataFrame"]

        fig = go.Figure()

        fig.add_trace(go.Candlestick(
            x=d.index,
            open=d["Open"],
            high=d["High"],
            low=d["Low"],
            close=d["Close"],
            name="Prezzo"
        ))

        fig.add_trace(go.Scatter(x=d.index, y=d["Upper"], name="Banda Superiore", line=dict(dash="dash")))
        fig.add_trace(go.Scatter(x=d.index, y=d["Lower"], name="Banda Inferiore", line=dict(dash="dash")))
        fig.add_trace(go.Scatter(x=d.index, y=d["MA"], name="Media", line=dict(color="gray")))

        fig.add_vline(x=sel["Data"], line_color="orange", line_dash="dot")

        fig.update_layout(
            title=f"{selected} – {sel['Segnale']} ({sel['Data'].strftime('%d/%m/%Y')})",
            xaxis_title="Data",
            yaxis_title="Prezzo",
            height=600
        )

        st.plotly_chart(fig, use_container_width=True)

# --------------------------------------------------
# INFO
# --------------------------------------------------
with st.expander("ℹ️ Logica del Segnale"):
    st.markdown("""
    **Breakout Rialzista**
    - Close di **IERI** > Banda Superiore

    **Breakout Ribassista**
    - Close di **IERI** < Banda Inferiore

    **Bollinger Bands**
    - Media mobile semplice
    - Periodo e deviazioni configurabili
    - Nessun utilizzo di dati intraday
    """)
