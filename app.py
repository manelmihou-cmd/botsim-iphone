
import streamlit as st
import pandas as pd
import requests
from datetime import datetime
from zoneinfo import ZoneInfo

st.set_page_config(page_title="BotSim", page_icon="📈", layout="centered")

CAPITAL = 500.0
DEADLINE = datetime(2026, 11, 3, 18, 0, tzinfo=ZoneInfo("Europe/Paris"))
API = "https://data-api.binance.vision/api/v3/klines"

st.title("📈 BotSim")
st.caption("Simulation uniquement — BTC/EUR")

if "cash" not in st.session_state:
    st.session_state.cash = CAPITAL
    st.session_state.btc = 0.0
    st.session_state.transactions = []
    st.session_state.signal = "Aucun signal"
    st.session_state.last_candle = None

now = datetime.now(ZoneInfo("Europe/Paris"))

st.info("Capital virtuel de départ : 500 €. Aucun ordre réel.")
st.write("Arrêt prévu le 3 novembre 2026 à 18 h, heure de Paris.")

if now >= DEADLINE:
    st.error("La période de simulation est terminée.")
    st.stop()

@st.cache_data(ttl=60)
def get_data():
    r = requests.get(
        API,
        params={"symbol": "BTCEUR", "interval": "5m", "limit": 100},
        timeout=15,
    )
    r.raise_for_status()
    rows = r.json()
    df = pd.DataFrame(rows, columns=[
        "time", "open", "high", "low", "close", "volume",
        "close_time", "quote_volume", "trades",
        "taker_buy_base", "taker_buy_quote", "ignore"
    ])
    df["close"] = pd.to_numeric(df["close"])
    return df

try:
    df = get_data()
    df["SMA20"] = df["close"].rolling(20).mean()
    df["SMA50"] = df["close"].rolling(50).mean()
    price = float(df["close"].iloc[-1])

    prev = df.iloc[-2]
    last = df.iloc[-1]
    candle_time = int(last["time"])

    if (
        pd.notna(prev["SMA20"]) and pd.notna(prev["SMA50"])
        and pd.notna(last["SMA20"]) and pd.notna(last["SMA50"])
        and candle_time != st.session_state.last_candle
    ):
        if prev["SMA20"] <= prev["SMA50"] and last["SMA20"] > last["SMA50"]:
            if st.session_state.cash > 0:
                amount = st.session_state.cash
                st.session_state.btc += amount / price
                st.session_state.cash = 0.0
                st.session_state.signal = "ACHAT simulé"
                st.session_state.transactions.append({
                    "Heure": now.strftime("%d/%m %H:%M"),
                    "Action": "ACHAT",
                    "Prix BTC (€)": round(price, 2),
                    "Montant (€)": round(amount, 2),
                })

        elif prev["SMA20"] >= prev["SMA50"] and last["SMA20"] < last["SMA50"]:
            if st.session_state.btc > 0:
                amount = st.session_state.btc * price
                st.session_state.cash += amount
                st.session_state.btc = 0.0
                st.session_state.signal = "VENTE simulée"
                st.session_state.transactions.append({
                    "Heure": now.strftime("%d/%m %H:%M"),
                    "Action": "VENTE",
                    "Prix BTC (€)": round(price, 2),
                    "Montant (€)": round(amount, 2),
                })

        st.session_state.last_candle = candle_time

    total = st.session_state.cash + st.session_state.btc * price

    st.metric("Prix BTC/EUR", f"{price:,.2f} €")
    st.metric("Portefeuille simulé", f"{total:,.2f} €", f"{total-CAPITAL:+,.2f} €")
    st.metric("Solde en euros", f"{st.session_state.cash:,.2f} €")
    st.metric("BTC détenus", f"{st.session_state.btc:.8f}")
    st.write("Dernier signal :", st.session_state.signal)
    st.line_chart(df.set_index("time")["close"])

    st.subheader("Transactions")
    if st.session_state.transactions:
        st.dataframe(pd.DataFrame(st.session_state.transactions))
    else:
        st.write("Aucune transaction pour le moment.")

    if st.button("Actualiser"):
        st.cache_data.clear()
        st.rerun()

except Exception as e:
    st.error("Données de marché indisponibles. Réessaie plus tard.")
    st.caption(str(e))
