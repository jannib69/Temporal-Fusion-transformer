import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler, MinMaxScaler, RobustScaler, QuantileTransformer
from statsmodels.tsa.stattools import grangercausalitytests
from copy import deepcopy as dc
from data_util import TransformUtil, BTC
from tqdm import tqdm
from datetime import datetime, timedelta
import time

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

        category_name = bea.get_category_name(category)

        # Nastavitve po kategoriji
        category_settings = {
            "Personal Income and Employment": dict(scaler="standard", method="weighted"),
            "GDP and National Income": dict(scaler="quantile", method="mean"),
            "Government and Public Sector": dict(scaler="robust", method="weighted"),
            "Trade and International Transactions": dict(scaler="quantile", method="mean"),
            "Industry Specific Accounts": dict(scaler="standard", method="weighted"),
            "Financial and Corporate Data": dict(scaler="robust", method="weighted"),
            "Fixed Assets and Investment": dict(scaler="standard", method="mean"),
        }

        settings = category_settings.get(category_name, dict(scaler="standard", method="mean"))

        df_tmp_pca_indicator = TransformUtil.create_indicator(
            category_name, df_tmp,
            scaler=settings["scaler"], method=settings["method"],
            explained_var=explained_var
        )

        if df_tmp_pca_indicator.empty:
            print(f"Preskakujem {category}: Vsi podatki po PCA so preveč manjkajoči!")
            continue  # Pojdi na naslednjo kategorijo

        df_tmp_pca_indicator = df_tmp_pca_indicator.asfreq("QS-OCT")
        best_lag = best_granger_lag(df_tmp_pca_indicator, df_btc, "Close")

        df_indices.loc[:, bea.get_category_name(category)] = df_tmp_pca_indicator
        df_indices.loc[:, bea.get_category_name(category)] = df_indices[bea.get_category_name(category)].shift(best_lag)

    df_indices = remove_fully_nan_rows(df_indices)
    df_indices = df_indices.resample("D").interpolate(method="time", limit_direction="both")
    print("All BEA categories processed successfully.")
    return df_indices, df_bea_orig

def drop_cols_with_nan(df, tresh=0.7):
    print(f"Number of cols before dropping NaNs: {len(df.columns)}")
    threshold = tresh * len(df)
    df = df.dropna(axis=1, thresh=threshold)
    print(f"Number of cols after dropping NaNs: {len(df.columns)}")
    return df

def best_granger_lag(df1, df_btc, target_col, max_lag=10):
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

    monthly_metrics = [
        "M2SL", "M1SL", "WALCL",  # denarna masa, bilanca FED
        "CPIAUCSL", "CPILFESL", "CUSR0000SA0L2",  # inflacija + energija
        "FEDFUNDS", "IRLTLT01JPM156N", "RIFLGFCY10NA",  # obresti (tudi bančne)

        "PAYEMS", "UNRATE", "CIVPART",  # trg dela
        "DSPIC96", "PCE", "PSAVERT",  # dohodki, potrošnja, stopnja varčevanja

        "GEPUCURRENT", "USEPUINDXD", "EPUMONETARY",  # politična negotovost
        "APU000072610", "CPIENGSL",  # cene hrane in energije

        "HOUST", "PERMIT",  # gradbeni trg (indikator zaupanja in kreditne rasti)
        "RECPROUSM156N"  # verjetnost recesije (smoothed recession probability)
    ]

    df_monthly = fred.fetch_data(monthly_metrics, frequency="m", end_date=end_date)

    daily_metrics = [
        "DTWEXBGS",  # USD indeks
        "DGS10", "DGS2", "DGS30",  # donosnost obveznic (kriva donosnosti)
        "T10Y2Y", "T10Y3M", "T10YIE",  # spreadi + inflacijska pričakovanja
        "DFF", "FEDFUNDS",  # obrestna mera

        "SP500", "VIXCLS", "NASDAQCOM", "RIFSPFFNA"  # tržni sentiment
        "TEDRATE", "BAA10Y",  # kreditno tveganje

        "DCOILWTICO",  # cena nafte (inflacija, globalni šok)

        "WLEMUINDXD",  # EU politična negotovost
        "IRLTLT01JPM156N",  # Japonska dolgoročne obresti (globalna likvidnost)
        "T5YIFR"  # 5-year breakeven inflation rate (inflacijska pričakovanja)
    ]

    df_daily = fred.fetch_data(daily_metrics, frequency="d", end_date=end_date)

    df_fred_orig = df_monthly.merge(df_daily, on="Date", how="outer")

    if df_monthly.empty or df_daily.empty:
        print("Warning: Some FRED data is missing! Skipping processing.")
        return pd.DataFrame()

    df_fred_indices = pd.DataFrame(index=pd.date_range(start=df_monthly.index.min(), end="2026-12-31", freq="D"))
    df_fred_indices.index.name = "Date"

    btc_monthly = df_btc.resample("MS").mean().dropna()

    for col in df_monthly.columns:
        df_fred_indices[col] = df_monthly[col]

    for col in df_daily.columns:
        df_fred_indices[col] = df_daily[col]

    print("FRED Indices Before Cleaning:", df_fred_indices.tail())

    df_fred_indices = remove_fully_nan_rows(df_fred_indices)
    print("FRED Indices After Cleaning:", df_fred_indices.tail())

    df_fred_indices = df_fred_indices.interpolate(method="time", limit_direction="both")
    print("FRED Indices After Interpolation:", df_fred_indices.tail())

    return df_fred_indices, df_fred_orig

def process_bitcoin_data(df_btc, explained_var=0.9):
    df_btc_indices_tmp = BTC.generate_bitcoin_indicators(explained_var)
    df_btc_indices_tmp = df_btc_indices_tmp.interpolate(method="time", limit_direction="both")
    df_btc_indices_tmp.index.name = "Date"

    df_btc_indices = pd.DataFrame(index=pd.date_range(start=df_btc_indices_tmp.index.min(), end="2026-12-31", freq="D"))
    df_btc_indices.index.name = "Date"

    for col in df_btc_indices_tmp.columns:
        best_lag = best_granger_lag(df_btc_indices_tmp[[col]], df_btc, "Close")

        if best_lag is not None:
            df_btc_indices[col] = df_btc_indices_tmp[col].shift(best_lag)
        else:
            df_btc_indices[col] = df_btc_indices_tmp[col]

    df_btc_indices = remove_fully_nan_rows(df_btc_indices)
    df_btc_indices = df_btc_indices.interpolate(method="time", limit_direction="both")

    return df_btc_indices

def get_today():
    return datetime.today().strftime('%Y-%m-%d')

def process_btc_etf_data(df_btc, explained_var=0.9):
    bitcoin_etf_df_orig = BTC.get_etf_flows()

    df_tmp_pca_indicator = TransformUtil.create_indicator(
        "BTC_etf", bitcoin_etf_df_orig, scaler="quantile", method="weighted", explained_var=explained_var
    )

    full_index = pd.date_range(start=df_tmp_pca_indicator.index.min(), end="2026-12-31", freq="D")
    df_tmp_pca_indicator = df_tmp_pca_indicator.reindex(full_index)
    df_tmp_pca_indicator.index.name = "Date"

    shifted_df = pd.DataFrame(index=df_tmp_pca_indicator.index)

    best_lag = best_granger_lag(df_tmp_pca_indicator, df_btc, "Close")
    if best_lag is not None:
        shifted_df = df_tmp_pca_indicator.shift(best_lag)
    else:
        shifted_df = df_tmp_pca_indicator

    shifted_df = remove_fully_nan_rows(shifted_df)

    return bitcoin_etf_df_orig, shifted_df

def preprocess_for_tft(df, min_date="1.1.2016", max_prediction_lenght=14):
    df = dc(df)

    df.index = pd.to_datetime(df.index)
    df = df.sort_index()
    df["Volume_weekly"] = df["Volume"].resample("W").mean()
    df["Volume_monthly"] = df["Volume"].resample("ME").mean()

    df["MA7"] = df["Close"].rolling(7, min_periods=1).mean()
    df["MA111"] = df["Close"].rolling(111, min_periods=1).mean()
    df["MA200"] = df["Close"].rolling(200, min_periods=1).mean()

    df["Close_delta_1"] = df["Close"].diff(1)
    df["Close_delta_7"] = df["Close"].diff(7)

    if "time_idx" not in df.columns:
        df = df.sort_index()
        df["time_idx"] = np.arange(len(df))

    df["group"] = "BTC"

    cat_cols = ['US', 'UK', 'Japan', 'China', 'day', 'month', 'day_of_week', 'week_of_year', 'year', 'quarter',
                'is_weekend', 'is_month_end', 'time_idx', 'Halving', "group"]

    df[cat_cols] = df[cat_cols].astype(str).astype("category")

    cutoff_date = pd.Timestamp(pd.Timestamp(datetime.today()) + pd.Timedelta(days=max_prediction_lenght)).normalize()

    df_clipped = df[
        (df.index >= pd.Timestamp(min_date)) &
        (df.index <= cutoff_date)
        ].copy()

    num_cols = df_clipped.select_dtypes(exclude=["object", "category"]).columns

    df_clipped[num_cols] = df_clipped[num_cols].interpolate(method="time", limit_direction="both")

    df_all_transformed = apply_minmax_to_all_except_cat_and_target(df_clipped)

    df_all_transformed["time_idx"] = df_all_transformed["time_idx"].astype(int)

    return df_all_transformed

def apply_quantile_to_all_except_cat_and_target(df, target_col="Close"):
    transformed_df = df.copy()
    transformers = {}

    numeric_cols = df.select_dtypes(include=["number"]).columns
    cols_to_transform = [col for col in numeric_cols if col != target_col]

    for col in cols_to_transform:
        if df[col].isnull().all():
            continue  # preskoči prazne

        qt = QuantileTransformer(output_distribution="uniform", random_state=42)
        transformed_col = qt.fit_transform(df[[col]])
        transformed_df[col] = transformed_col
        transformers[col] = qt

    return transformed_df, transformers

def apply_minmax_to_all_except_cat_and_target(df, target_col="Close"):
    transformed_df = df.copy()
    num_cols = df.select_dtypes(exclude=["object", "category"]).columns
    cols_to_transform = [col for col in num_cols if col != target_col]

    scaler = MinMaxScaler()
    transformed_df[cols_to_transform] = scaler.fit_transform(transformed_df[cols_to_transform])

    return transformed_df


def generate_all_ta_features(df):
    df_feat = df.copy()

    for col in ["Open", "High", "Low", "Close", "Volume"]:
        if col not in df_feat.columns:
            raise ValueError(f"Manjka stolpec '{col}'")

    close = df_feat["Close"]
    high = df_feat["High"]
    low = df_feat["Low"]
    volume = df_feat["Volume"]

    # EMA / SMA
    for p in [10, 20, 50, 100, 200]:
        df_feat[f"EMA_{p}"] = close.ewm(span=p, adjust=False).mean()
        df_feat[f"SMA_{p}"] = close.rolling(window=p).mean()

    # RSI
    for p in [14, 21]:
        delta = close.diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.rolling(window=p).mean()
        avg_loss = loss.rolling(window=p).mean()
        rs = avg_gain / avg_loss
        df_feat[f"RSI_{p}"] = 100 - (100 / (1 + rs))

    # MACD
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    signal = macd.ewm(span=9, adjust=False).mean()
    df_feat["MACD"] = macd
    df_feat["MACD_signal"] = signal

    # Bollinger Bands
    ma20 = close.rolling(window=20).mean()
    std20 = close.rolling(window=20).std()
    df_feat["BB_upper"] = ma20 + 2 * std20
    df_feat["BB_lower"] = ma20 - 2 * std20

    # Volatility (rolling std)
    df_feat["Volatility_20"] = close.rolling(window=20).std()

    # ATR (Average True Range)
    tr = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low - close.shift()).abs()
    ], axis=1).max(axis=1)
    df_feat["ATR_14"] = tr.rolling(window=14).mean()

    # ROC (Rate of Change)
    df_feat["ROC_10"] = close.pct_change(periods=10)

    # Stochastic Oscillator
    low_14 = low.rolling(window=14).min()
    high_14 = high.rolling(window=14).max()
    df_feat["Stoch_K"] = 100 * (close - low_14) / (high_14 - low_14)
    df_feat["Stoch_D"] = df_feat["Stoch_K"].rolling(window=3).mean()

    # OBV (On-Balance Volume)
    obv = volume.copy()
    obv[close.diff() < 0] *= -1
    df_feat["OBV"] = obv.cumsum()

    return df_feat
