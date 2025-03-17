import requests
import pandas as pd
from ..config import Config

class BLS:
    BASE_URL = "https://api.bls.gov/publicAPI/v2/timeseries/data/"

    def __init__(self):
        self.api_key = Config.BLS_API_KEY


    def fetch_data(self, series_ids, start_year, end_year, processed=True):
        headers = {"Content-Type": "application/json"}
        payload = {
            "seriesid": series_ids,
            "startyear": str(start_year),
            "endyear": str(end_year),
            "registrationkey": self.api_key
        }

        response = requests.post(self.BASE_URL, json=payload, headers=headers)

        if response.status_code != 200:
            raise ConnectionError(f"API request failed with status code {response.status_code}")

        data = response.json()
        if "Results" not in data or "series" not in data["Results"]:
            raise ValueError("Invalid API response format.")

        all_series_data = []
        for series in data["Results"]["series"]:
            series_id = series["seriesID"]
            for entry in series["data"]:
                value = float(entry["value"].replace(',', '')) if entry["value"] != "-" else None
                all_series_data.append({
                    "SeriesID": series_id,
                    "Date": pd.to_datetime(f"{entry['year']}-{entry['period'][1:]}-01"),
                    "Value": value
                })

        df = pd.DataFrame(all_series_data)

        if not processed:
            return df

        df_pivot = df.pivot_table(index="Date", columns="SeriesID", values="Value", aggfunc="mean")
        df_pivot.sort_index(inplace=True)

        return df_pivot