import pandas as pd
import time
from datetime import timedelta
from pytrends.request import TrendReq


class TrendsUtil:
    def __init__(self):
        self.pytrends = TrendReq(hl="en-US", tz=360)

    def get_google_trends(self, start_date, end_date, keywords=["Bitcoin", "Crypto"]):
        start_date = pd.to_datetime(start_date)
        end_date = pd.to_datetime(end_date)
        delta = timedelta(days=270)

        all_data = []
        current_start = start_date
        while current_start < end_date:
            current_end = min(current_start + delta, end_date)
            time_range = f"{current_start.strftime('%Y-%m-%d')} {current_end.strftime('%Y-%m-%d')}"

            self.pytrends.build_payload(kw_list=keywords, timeframe=time_range, geo="", gprop="")
            df_trends = self.pytrends.interest_over_time()

            if "isPartial" in df_trends.columns:
                df_trends.drop(columns=["isPartial"], inplace=True)

            all_data.append(df_trends)
            current_start = current_end
            time.sleep(2)

        return pd.concat(all_data) if all_data else None