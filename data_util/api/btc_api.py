import cloudscraper
import pandas as pd
import yfinance as yf
import requests
from tqdm import tqdm
from data_util.transform_util import TransformUtil

class BTC:
    @staticmethod
    def get_etf_flows():
        url = 'https://farside.co.uk/bitcoin-etf-flow-all-data/?t'
        scraper = cloudscraper.create_scraper()
        response = scraper.get(url)
        response.raise_for_status()

        df = pd.read_html(response.text, attrs={"class": "etf"})[0]

        df.columns = ["Date", "IBIT", "FBTC", "BITB", "ARKB", "BTCO",
                      "EZBC", "BRRR", "HODL", "BTCW", "GBTC", "BTC", "Total"]

        df["Date"] = pd.to_datetime(df["Date"], format="%d %b %Y", errors="coerce")
        df.dropna(subset=["Date"], inplace=True)
        df.set_index("Date", inplace=True)
        df.index.name = "Date"

        df = df.replace(r"\((.*?)\)", r"-\1", regex=True).apply(pd.to_numeric, errors="coerce")

        df.fillna(0.0, inplace=True)

        df["Total"] = df.iloc[:, :-1].sum(axis=1)

        return df

    @staticmethod
    def get_crypto_data(ticker="BTC-USD", period="max", interval="1d"):
        try:
            df_btc = yf.download(ticker, period=period, interval=interval, auto_adjust=True, progress=False, multi_level_index=False)
            df_btc.index = df_btc.index.tz_localize(None)
            df_btc = df_btc[["Close", "High", "Low", "Open", "Volume"]]
            df_btc.dropna(inplace=True)
            return df_btc
        except Exception as e:
            print(f"Error fetching data for {ticker}: {e}")
            return None

    @staticmethod
    def get_bitcoin_indices():
        endpoints = {
            "Unique Addresses Used": "https://api.blockchain.info/charts/n-unique-addresses?timespan=all&format=json",
            "Number of Transactions": "https://api.blockchain.info/charts/n-transactions?timespan=all&format=json",
            "Transactions Per Second": "https://api.blockchain.info/charts/transactions-per-second?timespan=all&format=json",
            "Output Volume": "https://api.blockchain.info/charts/output-volume?timespan=all&format=json",
            "Mempool Transaction Count": "https://api.blockchain.info/charts/mempool-count?timespan=all&format=json",
            "Mempool Size Growth": "https://api.blockchain.info/charts/mempool-growth?timespan=all&format=json",
            "Mempool Size (Bytes)": "https://api.blockchain.info/charts/mempool-size?timespan=all&format=json",
            "Transactions Excluding Popular Addresses": "https://api.blockchain.info/charts/n-transactions-excluding-popular?timespan=all&format=json",
            "Estimated Transaction Volume (BTC)": "https://api.blockchain.info/charts/estimated-transaction-volume?timespan=all&format=json",
            "Estimated Transaction Volume (USD)": "https://api.blockchain.info/charts/estimated-transaction-volume-usd?timespan=all&format=json",
            "Miners Revenue (USD)": "https://api.blockchain.info/charts/miners-revenue?timespan=all&format=json",
            "Transaction Fees (BTC)": "https://api.blockchain.info/charts/transaction-fees?timespan=all&format=json",
            "Transaction Fees (USD)": "https://api.blockchain.info/charts/transaction-fees-usd?timespan=all&format=json",
            "Cost per Transaction (%)": "https://api.blockchain.info/charts/cost-per-transaction-percent?timespan=all&format=json",
            "Cost per Transaction (USD)": "https://api.blockchain.info/charts/cost-per-transaction?timespan=all&format=json",
            "Network Difficulty": "https://api.blockchain.info/charts/difficulty?timespan=all&format=json",
            "Hash Rate (TH/s)": "https://api.blockchain.info/charts/hash-rate?timespan=all&format=json",
            "Block Size": "https://api.blockchain.info/charts/blocks-size?timespan=all&format=json",
            "Average Block Size": "https://api.blockchain.info/charts/avg-block-size?timespan=all&format=json",
            "Transactions per Block": "https://api.blockchain.info/charts/n-transactions-per-block?timespan=all&format=json",
            "Trade Volume": "https://api.blockchain.info/charts/trade-volume?timespan=all&format=json",
            "Total Bitcoins": "https://api.blockchain.info/charts/total-bitcoins?timespan=all&format=json",
            "Market Cap": "https://api.blockchain.info/charts/market-cap?timespan=all&format=json",
        }

        def fetch_data(session, url, column_name):
            try:
                response = session.get(url, timeout=10)
                response.raise_for_status()
                data = response.json()
                if 'values' not in data:
                    print(f"Warning: 'values' key not found in API response for {column_name}")
                    return pd.DataFrame()
                df = pd.DataFrame(data['values'])
                df.rename(columns={'x': 'Date'}, inplace=True)
                df['Date'] = pd.to_datetime(df['Date'], unit='s').dt.date
                df.set_index('Date', inplace=True)
                df.rename(columns={'y': column_name}, inplace=True)
                return df
            except requests.RequestException as e:
                print(f"Error fetching {column_name}: {e}")
                return pd.DataFrame()

        full_dates = pd.DataFrame(index=pd.date_range(start="2009-01-01", end="2026-12-31", freq="D"))
        full_dates.index.name = "Date"

        with requests.Session() as session:
            df_combined = full_dates.copy()
            for name, url in tqdm(endpoints.items(), desc="Fetching data", unit="endpoint"):
                df = fetch_data(session, url, name)
                if not df.empty:
                    df_combined = df_combined.join(df, how='left')

        df_combined = df_combined[~df_combined.index.duplicated(keep="first")].dropna(how="all")

        return df_combined

    @staticmethod
    def generate_bitcoin_indicators(explained_var=.9):
        df_tmp = BTC.get_bitcoin_indices()
        df_btc_indices = pd.DataFrame(index=pd.date_range(start=df_tmp.index.min(), end="2026-12-31", freq="D"))
        df_btc_indices.index.name = "Date"
        transaction_indicators = [
            "Unique Addresses Used", "Number of Transactions", "Transactions Per Second",
            "Output Volume", "Transactions Excluding Popular Addresses",
            "Estimated Transaction Volume (BTC)", "Estimated Transaction Volume (USD)",
            "Transactions per Block"
        ]

        mining_indicators = [
            "Miners Revenue (USD)", "Transaction Fees (BTC)", "Transaction Fees (USD)",
            "Cost per Transaction (%)", "Cost per Transaction (USD)",
            "Network Difficulty", "Hash Rate (TH/s)"
        ]

        network_indicators = [
            "Mempool Transaction Count", "Mempool Size Growth", "Mempool Size (Bytes)",
            "Block Size", "Average Block Size", "Trade Volume", "Total Bitcoins", "Market Cap"
        ]

        df_btc_indices["BTC_miners"] = TransformUtil.create_indicator("BTC_miners", df_tmp[mining_indicators],
                                                                        scaler="standard", method="mean",
                                                                        explained_var=explained_var)
        df_btc_indices["BTC_transactions"] = TransformUtil.create_indicator("BTC_transactions",
                                                                              df_tmp[transaction_indicators],
                                                                              scaler="standard", method="mean",
                                                                              explained_var=explained_var)
        df_btc_indices["BTC_network"] = TransformUtil.create_indicator("BTC_network", df_tmp[network_indicators],
                                                                         scaler="standard", method="mean",
                                                                         explained_var=explained_var)

        return df_btc_indices