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

st.title("📊 Bollinger Bands Breakout Scanner")
st.markdown("**Segnali basati ESCLUSIVAMENTE sulla candela DAILY di IERI (chiusa)**")

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

# --------------------------------------------------
# DATA FETCH
# --------------------------------------------------
@st.cache_data
def fetch_data(symbol):
    end = date.today() + timedelta(days=1)
    start = end - timedelta(days=180)

    df = yf.download(
        symbol,
        start=start,
        end=end,
        auto_adjust=False,
        progress=False
    )

    if df is None or df.empty:
        return None

    # 🔒 FIX CRITICO: forza OHLC a float
    df = df.copy()
    df.index = pd.to_datetime(df.index)

    for col in ["Open", "High", "Low", "Close"]:
        df[col] = df[col].astype(float)

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
# TABLES
# --------------------------------------------------
st.subheader("🟢 Breakout Rialzisti")
st.dataframe(pd.DataFrame(bullish)[["Symbol","Close","Upper","Data"]], use_container_width=True)

st.subheader("🔴 Breakout Ribassisti")
st.dataframe(pd.DataFrame(bearish)[["Symbol","Close","Lower","Data"]], use_container_width=True)

# --------------------------------------------------
# CHART (CANDELE FIXATE)
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

    # 🔥 CANDELE (FIX DEFINITIVO)
    fig.add_trace(go.Candlestick(
        x=d.index,
        open=d["Open"].values,
        high=d["High"].values,
        low=d["Low"].values,
        close=d["Close"].values,
        name="Prezzo"
    ))

    fig.add_trace(go.Scatter(
        x=d.index,
        y=d["Upper"].values,
        name="Banda Superiore",
        line=dict(dash="dash")
    ))

    fig.add_trace(go.Scatter(
        x=d.index,
        y=d["Lower"].values,
        name="Banda Inferiore",
        line=dict(dash="dash")
    ))

    fig.add_trace(go.Scatter(
        x=d.index,
        y=d["MA"].values,
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
