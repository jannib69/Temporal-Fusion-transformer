import pandas as pd
import time
from datetime import timedelta
from pytrends.request import TrendReq


class TRENDS:
    pytrends = TrendReq(hl="en-US", tz=360)

    @staticmethod
    def get_google_trends(start_date, end_date, keywords=None):
        if keywords is None:
            keywords = ["Bitcoin", "Crypto", "BTC"]
        return TRENDS._fetch_trends(start_date, end_date, keywords, gprop="")

    @staticmethod
    def get_youtube_trends(start_date, end_date, keywords=None):
        if keywords is None:
            keywords = ["Bitcoin", "Crypto", "BTC"]
        return TRENDS._fetch_trends(start_date, end_date, keywords, gprop="youtube")

    @staticmethod
    def _fetch_trends(start_date, end_date, keywords, gprop):
        start_date = pd.to_datetime(start_date)
        end_date = pd.to_datetime(end_date)
        delta = timedelta(days=180)  # Manjši interval za stabilnost

        all_data = []
        current_start = start_date
        while current_start < end_date:
            current_end = min(current_start + delta, end_date)
            time_range = f"{current_start.strftime('%Y-%m-%d')} {current_end.strftime('%Y-%m-%d')}"

            TRENDS.pytrends.build_payload(kw_list=keywords, timeframe=time_range, geo="", gprop=gprop)
            df_trends = TRENDS.pytrends.interest_over_time()

            if not df_trends.empty and "isPartial" in df_trends.columns:
                df_trends.drop(columns=["isPartial"], inplace=True)

            all_data.append(df_trends)
            current_start = current_end
            time.sleep(2)  # Da ne pride do blokade

        return pd.concat(all_data) if all_data else None