import streamlit as st
import pandas as pd
import yfinance as yf

yf.pdr_override()

def get_option_price(symbol: str, expiry: str, cp: str, strike: float):
    ticker = yf.Ticker(symbol)
    try:
        expiries = ticker.options
        if expiry not in expiries:
            return None
        df = ticker.option_chain(expiry).calls if cp.lower() == 'call' else ticker.option_chain(expiry).puts
        match = df[df['strike'] == strike]
        if match.empty:
            return None
        row = match.iloc[0]
        return {
            'symbol': symbol,
            'type': cp,
            'strike': row['strike'],
            'expiry': expiry,
            'lastPrice': row['lastPrice'],
            'bid': row['bid'],
            'ask': row['ask'],
            'impliedVolatility': row['impliedVolatility'],
            'volume': row['volume'],
            'openInterest': row['openInterest']
        }
    except Exception:
        return None

st.title("Option Price Fetcher")

uploaded_file = st.file_uploader("Upload your options_input.csv file", type="csv")

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    df.columns = df.columns.str.strip()

    results = []

    with st.spinner("Fetching option prices..."):
        for i, row in df.iterrows():
            symbol = row["symbol"]
            expiry = row["expiry"]
            cp = row["cp"]
            try:
                strike = float(row["strike"])
                result = get_option_price(symbol, expiry, cp, strike)

                if result:
                    result['status'] = '✅ success'
                    results.append(result)
                else:
                    results.append({
                        'symbol': symbol,
                        'type': cp,
                        'strike': strike,
                        'expiry': expiry,
                        'lastPrice': None,
                        'bid': None,
                        'ask': None,
                        'impliedVolatility': None,
                        'volume': None,
                        'openInterest': None,
                        'status': '⚠️ no match or invalid expiry/strike'
                    })
            except Exception as e:
                results.append({
                    'symbol': symbol,
                    'type': cp,
                    'strike': row.get("strike"),
                    'expiry': expiry,
                    'lastPrice': None,
                    'bid': None,
                    'ask': None,
                    'impliedVolatility': None,
                    'volume': None,
                    'openInterest': None,
                    'status': f'❌ error: {str(e)}'
                })

    output_df = pd.DataFrame(results)
    st.success("Done! Here is your file:")

    st.dataframe(output_df)

    csv = output_df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Download CSV",
        data=csv,
        file_name='options_with_prices.csv',
        mime='text/csv',
    )
