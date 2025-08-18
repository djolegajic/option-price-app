import streamlit as st
import pandas as pd
import yfinance as yf
from io import BytesIO

st.set_page_config(page_title="Pronalazač cena opcija", layout="centered")
st.title("📈 Pronalazač cena opcija")
st.write("Otpremite CSV ili Excel fajl sa kolonama (redosled): **simbol / istek / strike / vrsta**")

# --------- Pomoćna funkcija ---------
def get_option_price(symbol: str, expiry: str, cp: str, strike: float):
    try:
        t = yf.Ticker(symbol)
        expiries = t.options or []
        if expiry not in expiries:
            return None

        chain = t.option_chain(expiry)
        cp_norm = str(cp).strip().lower()
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

# --------- Učitavanje fajla ---------
uploaded = st.file_uploader("Otpremite fajl", type=["csv", "xlsx"])

if uploaded:
    # Čitanje CSV ili XLSX
    if uploaded.name.lower().endswith(".csv"):
        df_in = pd.read_csv(uploaded)
    else:
        df_in = pd.read_excel(uploaded)

    # Čišćenje i mapiranje kolona
    df_in.columns = df_in.columns.str.strip()
    rename_map = {}
    for c in df_in.columns:
        lc = c.strip().lower()
        if lc == "simbol":
            rename_map[c] = "simbol"
        elif lc == "istek":
            rename_map[c] = "istek"
        elif lc == "strike":
            rename_map[c] = "strike"
        elif lc == "vrsta":
            rename_map[c] = "vrsta"
    df_in = df_in.rename(columns=rename_map)

    required = ["simbol", "istek", "strike", "vrsta"]
    missing = [c for c in required if c not in df_in.columns]
    if missing:
        st.error(f"Nedostaju kolone: {missing}. Očekivano: {required}")
        st.stop()

    df_in = df_in[required].copy()

    # Pretvaranje 'istek' u pravi datum (bez formatiranja u tekst)
    if pd.api.types.is_numeric_dtype(df_in["istek"]):
        # Excel serijski broj -> datetime
        df_in["istek"] = pd.to_datetime(df_in["istek"], unit="d", origin="1899-12-30")
    else:
        df_in["istek"] = pd.to_datetime(df_in["istek"], errors="coerce")

    # Strike u broj
    df_in["strike"] = pd.to_numeric(df_in["strike"], errors="coerce")

    # --------- Preuzimanje cena ---------
    out_rows = []
    with st.spinner("Preuzimanje cena opcija..."):
        for _, r in df_in.iterrows():
            simbol = str(r["simbol"]).strip()
            expiry_dt = r["istek"]
            cp = str(r["vrsta"]).strip()
            strike_val = float(r["strike"]) if pd.notnull(r["strike"]) else None

            # Za yfinance expiry mora biti 'YYYY-MM-DD'
            expiry_str = pd.to_datetime(expiry_dt).strftime("%Y-%m-%d") if pd.notnull(expiry_dt) else None

            quote = None
            if simbol and expiry_str and strike_val is not None and cp:
                quote = get_option_price(simbol, expiry_str, cp, strike_val)

            out_rows.append({
                "simbol": simbol,
                "istek": expiry_dt,   # ostaje datetime64[ns] zbog Excel formata
                "strike": strike_val,
                "vrsta": cp,
                "last": quote["last"] if quote else None,
                "bid": quote["bid"] if quote else None,
                "ask": quote["ask"] if quote else None,
            })

    df_out = pd.DataFrame(out_rows, columns=["simbol","istek","strike","vrsta","last","bid","ask"])

    st.success("✅ Gotovo! Rezultat:")
    st.dataframe(df_out, use_container_width=True)

    # Export u XLSX (sa pravim Excel formatom za kolonu 'istek')
    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter", datetime_format="yyyy-mm-dd") as writer:
        df_out.to_excel(writer, index=False, sheet_name="Opcije")
        workbook  = writer.book
        worksheet = writer.sheets["Opcije"]

        # Primeni format datuma na kolonu 'istek'
        date_fmt = workbook.add_format({"num_format": "yyyy-mm-dd"})
        istek_col_idx = df_out.columns.get_loc("istek")
        worksheet.set_column(istek_col_idx, istek_col_idx, 12, date_fmt)

    xlsx_data = output.getvalue()

    st.download_button(
        label="📥 Preuzmi cene opcija",
        data=xlsx_data,
        file_name="opcije_sa_cenama.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
