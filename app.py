import streamlit as st
import pandas as pd
import yfinance as yf

st.set_page_config(page_title="Pronalazač cena opcija", layout="centered")
st.title("📈 Pronalazač cena opcija")
st.write("Otpremite CSV ili Excel fajl sa kolonama (redosled): **Simbol / istek / strike / vrsta**")


# --------- Core helper ---------
def get_option_price(symbol: str, expiry: str, cp: str, strike: float):
    """
    Returns dict with last, bid, ask for a single option, or None if no match.
    """
    try:
        t = yf.Ticker(symbol)
        expiries = t.options or []
        if expiry not in expiries:
            return None

        chain = t.option_chain(expiry)
        # Normalize cp
        cp_norm = str(cp).strip().lower()
        # accept a few shorthands
        if cp_norm in ("c", "call", "kup", "kupovina"):
            df = chain.calls
        else:
            df = chain.puts

        match = df[df["strike"] == float(strike)]
        if match.empty:
            return None

        row = match.iloc[0]
        return {
            "last": row.get("lastPrice"),
            "bid": row.get("bid"),
            "ask": row.get("ask"),
        }
    except Exception:
        return None

# --------- Upload ---------
uploaded = st.file_uploader("Upload file", type=["csv", "xlsx"])

if uploaded:
    # Read file
    if uploaded.name.lower().endswith(".csv"):
        df_in = pd.read_csv(uploaded)
    else:
        df_in = pd.read_excel(uploaded)

    # Clean headers and enforce expected names
    df_in.columns = df_in.columns.str.strip()
    # We accept any case but expect these logical names:
    rename_map = {}
    for c in df_in.columns:
        lc = c.strip().lower()
        if lc == "simbol":
            rename_map[c] = "Simbol"
        elif lc == "istek":
            rename_map[c] = "istek"
        elif lc == "strike":
            rename_map[c] = "strike"
        elif lc == "vrsta":
            rename_map[c] = "vrsta"
    df_in = df_in.rename(columns=rename_map)

    # Minimal validation
    required = ["Simbol", "istek", "strike", "vrsta"]
    missing = [c for c in required if c not in df_in.columns]
    if missing:
        st.error(f"Nedostaju kolone: {missing}. Očekivano: {required}")
        st.stop()

    # Reorder and trim to only expected input cols
    df_in = df_in[required].copy()

    # Convert 'istek' to 'YYYY-MM-DD'
    # - if Excel serial (numeric), convert from 1899-12-30 origin
    # - else parse as date string
    if pd.api.types.is_numeric_dtype(df_in["istek"]):
        df_in["istek"] = pd.to_datetime(
            df_in["istek"], unit="d", origin="1899-12-30"
        ).dt.strftime("%Y-%m-%d")
    else:
        df_in["istek"] = pd.to_datetime(df_in["istek"]).dt.strftime("%Y-%m-%d")

    # Ensure strike is float
    df_in["strike"] = pd.to_numeric(df_in["strike"], errors="coerce")

    # --------- Fetch prices ---------
    out_rows = []
    with st.spinner("Preuzimanje cena opcija..."):
        for _, r in df_in.iterrows():
            symbol = str(r["Simbol"]).strip()
            expiry = str(r["istek"]).strip()
            cp = str(r["vrsta"]).strip()
            strike = float(r["strike"]) if pd.notnull(r["strike"]) else None

            quote = None
            if symbol and expiry and strike is not None and cp:
                quote = get_option_price(symbol, expiry, cp, strike)

            out_rows.append({
                "Simbol": symbol,
                "istek": expiry,
                "strike": strike,
                "vrsta": cp,
                "last": quote["last"] if quote else None,
                "bid": quote["bid"] if quote else None,
                "ask": quote["ask"] if quote else None,
            })

    df_out = pd.DataFrame(out_rows, columns=["Simbol","istek","strike","vrsta","last","bid","ask"])

    st.success("✅ Gotovo. Rezultat:")
    st.dataframe(df_out, use_container_width=True)

    csv_bytes = df_out.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📥 Preuzmi cene opcija",
        data=csv_bytes,
        file_name="options_with_prices.csv",
        mime="text/csv",
    )


