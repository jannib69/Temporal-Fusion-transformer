import requests
import pandas as pd
from requests.adapters import HTTPAdapter, Retry
from ..config import Config

class FRED:
    BASE_URL = "https://api.stlouisfed.org/fred/series/observations"

    def __init__(self):
        self.api_key = Config.FRED_API_KEY

    def fetch_data(self, series_ids, start_date="2000-01-01", end_date="2025-01-01", frequency="m"):
        all_data = []

        for series_id in series_ids:
            url = f"{self.BASE_URL}?series_id={series_id}&api_key={self.api_key}&file_type=json&frequency={frequency}&observation_start={start_date}&observation_end={end_date}"

            session = requests.Session()
            retries = Retry(total=5, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
            session.mount("https://", HTTPAdapter(max_retries=retries))

            response = session.get(url)
            if response.status_code != 200:
                continue

            data = response.json()
            df = pd.DataFrame(data["observations"])
            df["date"] = pd.to_datetime(df["date"])
            df["value"] = pd.to_numeric(df["value"], errors="coerce")

            df = df.rename(columns={"value": series_id}).set_index("date")
            df.index.name = "Date"

            df.drop(columns=["realtime_start", "realtime_end"], errors="ignore", inplace=True)

            all_data.append(df)

        return pd.concat(all_data, axis=1)