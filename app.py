import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import date, timedelta

# --------------------------------------------------
# PAGE CONFIG
# --------------------------------------------------
st.set_page_config(
    page_title="Bollinger Breakout Scanner",
    page_icon="📈",
    layout="wide"
)

st.title("📊 Bollinger Bands Exit Band Scanner")
st.markdown("**Segnali basati ESCLUSIVAMENTE sulla candela DAILY di IERI (chiusa)**")

# --------------------------------------------------
# SIDEBAR
# --------------------------------------------------
st.sidebar.header("⚙️ Configurazione")

DEFAULT_SYMBOLS = [
    "NQ=F", "ES=F", "YM=F", "RTY=F",
    "^GDAXI", "^STOXX50E",
    "CL=F", "RB=F", "NG=F", "GC=F", "SI=F", "HG=F", "PL=F", "PA=F",
    "ZC=F", "ZS=F", "ZW=F", "ZO=F", "ZR=F", "KC=F", "CC=F", "CT=F",
    "SB=F", "OJ=F",
    "6E=F", "6B=F", "6A=F", "6N=F", "6S=F", "6J=F", "6M=F",
    "DX-Y.NYB", "BTC=F", "ETH=F", "ZB=F"
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

# --------------------------------------------------
# DATA FETCH (FIX MULTIINDEX)
# --------------------------------------------------
@st.cache_data
def fetch_data(symbol):
    end = date.today() + timedelta(days=1)
    start = end - timedelta(days=200)

    df = yf.download(
        symbol,
        start=start,
        end=end,
        group_by="column",
        auto_adjust=False,
        progress=False
    )

    if df is None or df.empty:
        return None

    # 🔥 FIX MULTIINDEX
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df = df.rename(columns={
        "Open": "Open",
        "High": "High",
        "Low": "Low",
        "Close": "Close",
        "Volume": "Volume"
    })

    df = df[["Open", "High", "Low", "Close", "Volume"]]
    df = df.dropna()

    # 🔒 Forza tipi corretti
    for col in ["Open", "High", "Low", "Close"]:
        df[col] = df[col].astype(float)

    df.index = pd.to_datetime(df.index)

    return df

# --------------------------------------------------
# ANALYSIS
# --------------------------------------------------
def analyze_stock(symbol):
    data = fetch_data(symbol)
    if data is None or len(data) < bb_period + 2:
        return None

    data["MA"] = data["Close"].rolling(bb_period).mean()
    data["STD"] = data["Close"].rolling(bb_period).std()
    data["Upper"] = data["MA"] + bb_std * data["STD"]
    data["Lower"] = data["MA"] - bb_std * data["STD"]

    # Candela di IERI
    candle = data.iloc[-2]

    close = float(candle["Close"])
    upper = float(candle["Upper"])
    lower = float(candle["Lower"])
    signal_date = candle.name

    if np.isnan(close) or np.isnan(upper) or np.isnan(lower):
        return None

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
# RUN SCANNER
# --------------------------------------------------
results = []
with st.spinner("Analisi in corso..."):
    for s in symbols:
        r = analyze_stock(s)
        if r:
            results.append(r)

bullish = [r for r in results if "Rialzista" in r["Segnale"]]
bearish = [r for r in results if "Ribassista" in r["Segnale"]]

# --------------------------------------------------
# TABLES (date senza orario)
# --------------------------------------------------
st.subheader("🟢 Breakout Rialzisti")
if bullish:
    df_bull = pd.DataFrame(bullish)[["Symbol","Close","Upper","Data"]].copy()
    df_bull["Data"] = df_bull["Data"].dt.strftime("%d/%m/%Y")
    st.dataframe(df_bull, use_container_width=True)
else:
    st.info("Nessun breakout rialzista")

st.subheader("🔴 Breakout Ribassisti")
if bearish:
    df_bear = pd.DataFrame(bearish)[["Symbol","Close","Lower","Data"]].copy()
    df_bear["Data"] = df_bear["Data"].dt.strftime("%d/%m/%Y")
    st.dataframe(df_bear, use_container_width=True)
else:
    st.info("Nessun breakout ribassista")

# --------------------------------------------------
# CHART (CANDELE GARANTITE)
# --------------------------------------------------
st.divider()
st.subheader("📈 Grafico con Candele e Bollinger")

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
        open=d["Open"].to_numpy(),
        high=d["High"].to_numpy(),
        low=d["Low"].to_numpy(),
        close=d["Close"].to_numpy(),
        name="Prezzo"
    ))

    fig.add_trace(go.Scatter(
        x=d.index,
        y=d["Upper"].to_numpy(),
        name="Banda Superiore",
        line=dict(dash="dash")
    ))

    fig.add_trace(go.Scatter(
        x=d.index,
        y=d["Lower"].to_numpy(),
        name="Banda Inferiore",
        line=dict(dash="dash")
    ))

    fig.add_trace(go.Scatter(
        x=d.index,
        y=d["MA"].to_numpy(),
        name="Media",
        line=dict(color="gray")
    ))

    fig.add_vline(
        x=sel["Data"],
        line_dash="dot",
        line_color="orange"
    )

    fig.update_layout(
        title=f"{selected} – {sel['Segnale']} ({sel['Data'].strftime('%d/%m/%Y')})",
        xaxis_title="Data",
        yaxis_title="Prezzo",
        height=600,
        xaxis_rangeslider_visible=False
    )

    st.plotly_chart(fig, use_container_width=True)
