import requests
import pandas as pd
import re
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
from ..config import Config


class BEA:
    BASE_URL = "https://apps.bea.gov/api/data/"

    def __init__(self):
        self.api_key = Config.BEA_API_KEY
        self.session = requests.Session()
        retries = Retry(total=5, backoff_factor=1, status_forcelist=[500, 502, 503, 504], respect_retry_after_header=False )
        self.session.mount("https://", HTTPAdapter(max_retries=retries))

    def _get_response(self, url):
        response = self.session.get(url, verify=False)  # Disable SSL verification if needed
        if response.status_code != 200:
            raise ConnectionError(f"API request failed with status code {response.status_code}")
        return response.json()

    def get_tables(self, dataset_name="NIPA"):
        url = f"{self.BASE_URL}?UserID={self.api_key}&method=GetParameterValues&datasetname={dataset_name}&ParameterName=TableName&ResultFormat=json"
        response = self.session.get(url, verify=False)

        if response.status_code != 200:
            raise ConnectionError(f"API request failed with status code {response.status_code}")

        data = response.json()

        # DEBUG: Izpiši celoten API odgovor
        print("BEA API Response:", data)

        if "BEAAPI" not in data or "Results" not in data["BEAAPI"] or "ParamValue" not in data["BEAAPI"]["Results"]:
            raise ValueError("Invalid API response format.")

        return pd.DataFrame(data["BEAAPI"]["Results"]["ParamValue"]).rename(
            columns={"Key": "TableName", "Desc": "Description"}
        )


    @staticmethod
    def parse_date(date_str):
        """
        Parse date string into a pandas datetime or Period object.
        """
        if re.match(r"^\d{4}M\d{2}$", date_str):  # Format "YYYYMmm" (monthly)
            return pd.to_datetime(date_str, format="%YM%m")
        elif re.match(r"^\d{4}Q\d$", date_str):  # Format "YYYYQq" (quarterly)
            year, quarter = date_str[:4], date_str[5]
            return pd.Period(f"{year}Q{quarter}", freq="Q").to_timestamp()
        elif re.match(r"^\d{4}$", date_str):  # Format "YYYY" (annual)
            return pd.to_datetime(date_str, format="%Y")
        return pd.NaT  # Invalid value

    def fetch_data(self, table_name, dataset_name="NIPA", frequencies=["M", "Q", "A"], year="ALL", processed=True,
                   metric_filter=None):
        """
        Fetches data for a specific table from the BEA API with a fallback frequency mechanism.
        """
        for freq in frequencies:
            url = f"{self.BASE_URL}?UserID={self.api_key}&method=GetData&datasetname={dataset_name}&TableName={table_name}&Frequency={freq}&Year={year}&ResultFormat=json"
            data = self._get_response(url)

            if "BEAAPI" not in data or "Results" not in data["BEAAPI"] or "Data" not in data["BEAAPI"]["Results"]:
                continue  # Try the next frequency

            df = pd.DataFrame(data["BEAAPI"]["Results"]["Data"])

            if not processed:
                return df  # Return raw data

            # Process the data
            df = df[["TimePeriod", "LineDescription", "DataValue", "METRIC_NAME"]].rename(
                columns={"TimePeriod": "Date"}
            )
            df["Date"] = df["Date"].apply(self.parse_date)
            df["DataValue"] = df["DataValue"].str.replace(",", "").astype(float)

            # Pivot data so that each unique combination of LineDescription and METRIC_NAME becomes a column
            df_pivot = df.pivot_table(index="Date", columns=["LineDescription", "METRIC_NAME"], values="DataValue",
                                      aggfunc="mean")
            df_pivot.sort_index(inplace=True)

            # Filter only columns where METRIC_NAME == "Fisher Quantity Index"
            if metric_filter:
                df_pivot = df_pivot.xs(metric_filter, axis=1, level=1, drop_level=True)
            return df_pivot

        # If all frequency attempts fail
        print("All frequency attempts failed.")
        return None

    def get_datasets(self):
        """
        Fetches the list of available datasets from the BEA API.
        """
        url = f"{self.BASE_URL}?UserID={self.api_key}&method=GetDatasetList&ResultFormat=json"
        data = self._get_response(url)

        if "BEAAPI" not in data or "Results" not in data["BEAAPI"] or "Dataset" not in data["BEAAPI"]["Results"]:
            raise ValueError("Invalid API response format.")

        return pd.DataFrame(data["BEAAPI"]["Results"]["Dataset"]).rename(
            columns={"DatasetName": "Dataset", "DatasetDescription": "Description"}
        )