import requests
import pandas as pd
import re
from ..config import Config


class BEA:
    BASE_URL = "https://apps.bea.gov/api/data/"

    def __init__(self):
        self.api_key = Config.BEA_API_KEY

    def get_datasets(self):
        url = f"{self.BASE_URL}?UserID={self.api_key}&method=GetDatasetList&ResultFormat=json"
        response = requests.get(url)

        if response.status_code != 200:
            raise ConnectionError(f"API request failed with status code {response.status_code}")

        data = response.json()
        if "BEAAPI" not in data or "Results" not in data["BEAAPI"] or "Dataset" not in data["BEAAPI"]["Results"]:
            raise ValueError("Invalid API response format.")

        return pd.DataFrame(data["BEAAPI"]["Results"]["Dataset"]).rename(columns={"DatasetName": "Dataset", "DatasetDescription": "Description"})

    @staticmethod
    def parse_date(date_str):
        if re.match(r"^\d{4}M\d{2}$", date_str):
            return pd.to_datetime(date_str, format="%YM%m")
        elif re.match(r"^\d{4}Q\d$", date_str):
            year, quarter = date_str[:4], date_str[5]
            return pd.Period(f"{year}Q{quarter}", freq="Q").to_timestamp()
        elif re.match(r"^\d{4}$", date_str):
            return pd.to_datetime(date_str, format="%Y")
        return pd.NaT