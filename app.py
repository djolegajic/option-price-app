import streamlit as st
import pandas as pd
import yfinance as yf

def get_option_price(symbol: str, expiry: str, cp: str, strike: float):
    try:
        ticker = yf.Ticker(symbol)
        expiries = ticker.options

        if expiry not in expiries:
            return None

        chain = ticker.option_chain(expiry)
        df = chain.calls if cp.lower() == 'call' else chain.puts

        match = df[df['strike'] == strike]
        if match.empty:
            return None

        row = match.iloc[0]
        return {
            'symbol': symbol,
            'expiry': expiry,
            'type': cp.lower(),
            'strike': row['strike'],
            'lastPrice': row['lastPrice'],
            'bid': row['bid'],
            'ask': row['ask'],

        }

    except Exception as e:
        return None

# Streamlit UI
st.title("📈 Option Price Fetcher")
st.write("Upload a CSV or Excel file with columns: `symbol`, `expiry` (date or Excel date), `cp` (call/put), and `strike`")

uploaded_file = st.file_uploader("Upload your options file", type=["csv", "xlsx"])

if uploaded_file:
    # Read CSV or Excel automatically
    if uploaded_file.name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)

    df.columns = df.columns.str.strip()  # Clean headers

    # Convert expiry column to proper YYYY-MM-DD string
    if pd.api.types.is_numeric_dtype(df["expiry"]):
        # Excel serial number to datetime
        df["expiry"] = pd.to_datetime(df["expiry"], unit='d', origin='1899-12-30').dt.strftime('%Y-%m-%d')
    else:
        # Already a date string or datetime
        df["expiry"] = pd.to_datetime(df["expiry"]).dt.strftime('%Y-%m-%d')

    results = []

    with st.spinner("Fetching option prices..."):
        for _, row in df.iterrows():
            symbol = row["symbol"]
            expiry = row["expiry"]
            cp = row["cp"]
            try:
                strike = float(row["strike"])
                result = get_option_price(symbol, expiry, cp, strike)

                if result:
                    result["status"] = "✅ Success"
                    results.append(result)
                else:
                    results.append({
                        'symbol': symbol,
                        'expiry': expiry,
                        'type': cp,
                        'strike': strike,
                        'lastPrice': None,
                        'bid': None,
                        'ask': None,
                        'status': '⚠️ No match or invalid input'
                    })
            except Exception as e:
                results.append({
                    'symbol': symbol,
                    'expiry': expiry,
                    'type': cp,
                    'strike': row.get("strike"),
                    'lastPrice': None,
                    'bid': None,
                    'ask': None,
                    'status': f'❌ Error: {str(e)}'
                })

    output_df = pd.DataFrame(results)
    st.success("✅ Done! Preview and download below.")
    st.dataframe(output_df)

    csv = output_df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Download CSV with Prices",
        data=csv,
        file_name='options_with_prices.csv',
        mime='text/csv',
    )



