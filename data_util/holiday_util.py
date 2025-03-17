import holidays
import pandas as pd
from datetime import datetime

class HolidayUtil:
    @staticmethod
    def generate_holiday_dataframe(start_date="2000-01-01", end_date=None):
        if end_date is None:
            end_date = datetime.today().strftime('%Y-%m-%d')

        df_holidays = pd.DataFrame(index=pd.date_range(start=start_date, end=end_date, freq="D"))
        df_holidays.index.name = "Date"

        holiday_calendars = {
            "US": holidays.country_holidays("US"),
            "UK": holidays.country_holidays("GB"),
            "Japan": holidays.country_holidays("JP"),
            "China": holidays.country_holidays("CN")
        }

        for country, holiday_calendar in holiday_calendars.items():
            df_holidays[country] = df_holidays.index.to_series().apply(lambda x: holiday_calendar.get(x, None))

        return df_holidays