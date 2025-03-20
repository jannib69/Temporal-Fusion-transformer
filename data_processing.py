import pandas as pd
from statsmodels.tsa.stattools import grangercausalitytests
from copy import deepcopy as dc
from data_util import TransformUtil, BTC
from tqdm import tqdm
from datetime import datetime
import time

# Definicija kategorij
bea_category_names = {
    "T1": "GDP and National Income",
    "T2": "Personal Income and Employment",
    "T3": "Industry Specific Accounts",
    "T4": "Fixed Assets and Investment",
    "T5": "Trade and International Transactions",
    "T6": "Prices and Inflation",
    "T7": "Government and Public Sector",
    "T8": "Financial and Corporate Data"
}

def process_bea_data(bea, df_btc, min_date="2015-01-01", explained_var=0.9, nan_threshold=0.7):
    df_indices = pd.DataFrame(index=pd.date_range(start="2000-01-01", end="2030-12-31", freq="QS"))
    df_indices.index.name = "Date"
    df_bea_orig = pd.DataFrame(index=pd.date_range(start="2000-01-01", end="2030-12-31", freq="D"))
    df_bea_orig.index.name = "Date"

    significant_features_df = pd.read_csv("Data/BEA/significant_features_BEA_cleaned.csv")
    category_results = {}

    for (category, table), group in tqdm(significant_features_df.groupby(["Category", "Table"]),
                                         desc="Processing BEA Data"):
        try:
            df = bea.fetch_data(table)
            time.sleep(5)

            df = df[df.index >= min_date]
            if df.empty:
                print(f"Warning: No data found for {table}. Skipping...")
                continue

            unique_metrics = group["Metric"].unique()
            table_results = []

            for metric in unique_metrics:
                if metric in df.columns.get_level_values(1):
                    df_pivot = df.xs(metric, axis=1, level=1, drop_level=True)
                else:
                    print(f"Warning: Metric '{metric}' not found in {table}. Skipping...")
                    continue

                relevant_columns = group[group["Metric"] == metric]["Column"].tolist()
                df_filtered = df_pivot[relevant_columns] if all(
                    col in df_pivot.columns for col in relevant_columns) else df_pivot

                for col in df_filtered.columns:
                    best_lag = group[group["Column"] == col]["Best Lag"].values[0]
                    df_filtered.loc[:, col] = df_filtered[col].shift(int(best_lag))
                    df_bea_orig.loc[df_filtered.index, col] = df_pivot[col]

                table_results.append(df_filtered)

            if table_results:
                final_table_df = pd.concat(table_results, axis=1)
                category_results[category] = pd.concat([category_results[category], final_table_df], axis=1) \
                    if category in category_results else final_table_df

        except Exception as e:
            print(f"Error processing {table}: {e}")

    for category, final_df in category_results.items():
        print(f"Processing category: {category}")

        category_results[category] = final_df.loc[:, ~final_df.columns.duplicated()]
        df_tmp = dc(category_results[category])
        df_tmp = drop_cols_with_nan(df_tmp, nan_threshold)

        if df_tmp.empty:
            print(f"Preskakujem {category}: Vsi podatki so preveč manjkajoči!")
            continue  # Pojdi na naslednjo kategorijo

        df_tmp_pca_indicator = TransformUtil.create_indicator(
            bea_category_names[category], df_tmp, scaler="standard", method="mean", explained_var=explained_var
        )
        if df_tmp_pca_indicator.empty:
            print(f"Preskakujem {category}: Vsi podatki po PCA so preveč manjkajoči!")
            continue  # Pojdi na naslednjo kategorijo

        df_tmp_pca_indicator = df_tmp_pca_indicator.asfreq("QS-OCT")
        best_lag = best_granger_lag(df_tmp_pca_indicator, df_btc, "Close")

        df_indices.loc[:, bea_category_names[category]] = df_tmp_pca_indicator
        df_indices.loc[:, bea_category_names[category]] = df_indices[bea_category_names[category]].shift(best_lag)

    df_indices = remove_fully_nan_rows(df_indices)
    df_indices = df_indices.resample("D").interpolate(method="linear", limit_direction="both")
    print("All BEA categories processed successfully.")
    return df_indices, df_bea_orig

def drop_cols_with_nan(df, tresh=0.7):
    print(f"Number of cols before dropping NaNs: {len(df.columns)}")
    threshold = tresh * len(df)
    df = df.dropna(axis=1, thresh=threshold)
    print(f"Number of cols after dropping NaNs: {len(df.columns)}")
    return df

def best_granger_lag(df1, df_btc, target_col, max_lag=5):
    if df1.index.name != "Date" or df_btc.index.name != "Date":
        raise ValueError("Both df1 and df_btc must have 'Date' as index")

    merged_df = df_btc[[target_col]].merge(df1, on="Date", how="inner")
    merged_df.replace([float("inf"), float("-inf")], float("nan"), inplace=True)
    merged_df.dropna(inplace=True)

    if len(merged_df) < max_lag + 1:
        return None

    feature_col = df1.columns[0]

    # Grangerjev test
    best_lag, best_p_value = None, 1.0
    test_results = grangercausalitytests(merged_df[[feature_col, target_col]], max_lag, verbose=False)

    for lag, results in test_results.items():
        p_value = results[0]['ssr_chi2test'][1]
        if p_value < best_p_value:
            best_p_value = p_value
            best_lag = lag

    return best_lag

def remove_fully_nan_rows(df):
    first_valid_index = df.notna().any(axis=1).idxmax()
    last_valid_index = df.loc[::-1].notna().any(axis=1).idxmax()

    df = df.loc[first_valid_index:last_valid_index]

    return df

def process_fred_data(fred, df_btc):
    end_date = datetime.today().strftime('%Y-%m-%d')

    monthly_metrics = ["M2SL", "FEDFUNDS", "IRLTLT01JPM156N", "CPIAUCSL", "PAYEMS", "GEPUCURRENT", "USEPUINDXD",
                       "EPUMONETARY", "APU000072610"]
    df_monthly = fred.fetch_data(monthly_metrics, frequency="m", end_date=end_date)

    daily_metrics = ["DTWEXBGS", "DGS10", "DGS2", "DFF", "VIXCLS", "USEPUINDXD", "WLEMUINDXD", "T10Y2Y", "T10Y3M", "T10YIE"]
    df_daily = fred.fetch_data(daily_metrics, frequency="d", end_date=end_date)

    df_fred_orig = df_monthly.merge(df_daily, on="Date", how="outer")

    if df_monthly.empty or df_daily.empty:
        print("Warning: Some FRED data is missing! Skipping processing.")
        return pd.DataFrame()

    df_fred_indices = pd.DataFrame(index=pd.date_range(start=df_monthly.index.min(), end="2026-12-31", freq="D"))
    df_fred_indices.index.name = "Date"

    btc_monthly = df_btc.resample("MS").mean().dropna()

    for col in df_monthly.columns:
        best_lag = best_granger_lag(df_monthly[[col]], btc_monthly, "Close")
        print(f"Monthly Lag: {best_lag} | Column: {col}")
        df_fred_indices[col] = df_monthly[col].shift(best_lag)

    for col in df_daily.columns:
        best_lag = best_granger_lag(df_daily[[col]], df_btc, "Close")
        print(f"Daily Lag: {best_lag} | Column: {col}")
        df_fred_indices[col] = df_daily[col].shift(best_lag)

    print("FRED Indices Before Cleaning:", df_fred_indices.tail())

    df_fred_indices = remove_fully_nan_rows(df_fred_indices)
    print("FRED Indices After Cleaning:", df_fred_indices.tail())

    df_fred_indices = df_fred_indices.interpolate(method="linear", limit_direction="both")
    print("FRED Indices After Interpolation:", df_fred_indices.tail())

    return df_fred_indices, df_fred_orig


def process_bitcoin_data(df_btc, explained_var=0.9):
    df_btc_indices_tmp = BTC.generate_bitcoin_indicators(explained_var)
    df_btc_indices_tmp = df_btc_indices_tmp.interpolate(method="linear", limit_direction="both")
    df_btc_indices_tmp.index.name = "Date"

    df_btc_indices = pd.DataFrame(index=pd.date_range(start=df_btc_indices_tmp.index.min(), end="2026-12-31", freq="D"))
    df_btc_indices.index.name = "Date"

    for col in df_btc_indices_tmp.columns:
        best_lag = best_granger_lag(df_btc_indices_tmp[[col]], df_btc, "Close")

        if best_lag is not None:
            df_btc_indices[col] = df_btc_indices_tmp[col].shift(best_lag)
    df_btc_indices = remove_fully_nan_rows(df_btc_indices)
    df_btc_indices = df_btc_indices.interpolate(method="linear", limit_direction="both")

    return df_btc_indices

def get_today():
    return datetime.today().strftime('%Y-%m-%d')