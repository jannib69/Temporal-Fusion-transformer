import cloudscraper
import pandas as pd
import yfinance as yf

class BTC:
    @staticmethod
    def get_etf_flows():
        url = 'https://farside.co.uk/bitcoin-etf-flow-all-data/?t'
        scraper = cloudscraper.create_scraper()
        response = scraper.get(url)
        response.raise_for_status()

        df = pd.read_html(response.text, attrs={"class": "etf"})[0]
        df.columns = ["Datum", "IBIT", "FBTC", "BITB", "ARKB", "BTCO", "EZBC", "BRRR", "HODL", "BTCW", "GBTC", "BTC", "Skupaj"]
        df["Datum"] = pd.to_datetime(df["Datum"], format="%d %b %Y", errors="coerce")
        df = df.dropna(subset=["Datum"]).set_index("Datum")

        df = df.apply(lambda x: x.astype(str).str.replace(r"\((.*?)\)", r"-\1", regex=True))
        df = df.apply(pd.to_numeric, errors="coerce")
        df.fillna(0.0, inplace=True)
        df["Skupaj"] = df.iloc[:, :-1].sum(axis=1)

        return df

    @staticmethod
    def get_crypto_data(ticker="BTC-USD", period="max", interval="1d"):
        try:
            df_btc = yf.download(ticker, period=period, interval=interval, auto_adjust=True)
            df_btc.index = df_btc.index.tz_localize(None)
            df_btc = df_btc[["Close", "High", "Low", "Open", "Volume"]]
            df_btc.dropna(inplace=True)
            return df_btc
        except Exception as e:
            print(f"Error fetching data for {ticker}: {e}")
            return None