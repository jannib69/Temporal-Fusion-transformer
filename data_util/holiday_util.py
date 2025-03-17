import pandas as pd
from datetime import datetime
import holidays

class HolidayUtil:
    @staticmethod
    def generate_holiday_dataframe(start_date="2000-01-01", end_date=None, countries=None, halving_dates=None):
        if end_date is None:
            end_date = datetime.today().strftime('%Y-%m-%d')

        if countries is None:
            countries = {"US": "US", "UK": "GB", "Japan": "JP", "China": "CN"}

        if halving_dates is None:
            halving_dates = [
                "2012-11-28",
                "2016-07-09",
                "2020-05-11",
                "2024-04-19",
                "2028-03-28",
            ]

        date_range = pd.date_range(start=start_date, end=end_date, freq="D")
        df_holidays = pd.DataFrame(index=date_range)
        df_holidays.index.name = "Date"

        for country_name, country_code in countries.items():
            holiday_calendar = holidays.country_holidays(country_code)
            df_holidays[country_name] = df_holidays.index.map(lambda x: holiday_calendar.get(x, "-"))

        df_holidays["day"] = df_holidays.index.day
        df_holidays["month"] = df_holidays.index.month
        df_holidays["time_idx"] = (df_holidays.index - df_holidays.index.min()).days

        df_holidays["is_weekend"] = (df_holidays.index.weekday >= 5).astype(int)

        halving_dates = pd.to_datetime(halving_dates)
        df_holidays["Halving"] = df_holidays.index.isin(halving_dates).astype(int)

        return df_holidays
