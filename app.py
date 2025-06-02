import numpy as np
from flask import Flask, render_template, jsonify, request, redirect
import pandas as pd
from pandas import CategoricalDtype

from data_processing import (process_bea_data,
                             process_bitcoin_data,
                             process_fred_data,
                             remove_fully_nan_rows,
                             get_today,
                             process_btc_etf_data,
                             generate_all_ta_features, clean_data_for_models)
from predict import load_model, create_dataloaders, run_prediction
from data_util import HolidayUtil, BTC, BEA, FRED
from datetime import datetime
import os
import threading
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__, static_folder="static", template_folder="templates")

FILE_PATH = "Data/daily_data.csv"
FILE_PATH_cleaned = "Data/daily_data_model_orig.feather"
FILE_PATH_log = "Data/data_fetching_log.csv"
SUBSET_PATH = "Data/Subsets/"
data_loading = False
data_lock = threading.Lock()


def get_data():
    print("Zagon funkcije get_data()")
    global data_loading
    print(f"CHECK: data_loading = {data_loading}")

    with data_lock:
        print(f"CHECK: data_lock = {data_lock}")

        if data_loading:

            print("Podatki se že nalagajo – izhod.")
            return
        print("Začenjam nalaganje podatkov.")
        data_loading = True

    try:
        skip_download = False
        print(f"CHECK: skip_download = {skip_download}")

        if os.path.exists(FILE_PATH):
            file_date = datetime.fromtimestamp(os.path.getmtime(FILE_PATH)).date()
            print(f"Obstoječa datoteka iz: {file_date}")
            if file_date == datetime.today().date():
                print("Podatki so že današnji – preskakujem nalaganje.")
                skip_download = True
        print(f"CHECK: skip_download2 = {skip_download}")

        if not skip_download:
            print("Priprava glavnega DataFrame...")

            os.makedirs(SUBSET_PATH, exist_ok=True)
            main_df = pd.DataFrame(index=pd.date_range(start="2000-01-01", end="2030-12-31", freq="D"))
            main_df.index.name = "Date"

            print("Pridobivanje BTC podatkov...")
            df_btc = BTC.get_crypto_data("BTC-USD")
            if df_btc is None or df_btc.empty:
                print("Napaka pri pridobivanju BTC podatkov.")
                return

            print("BTC podatki uspešno pridobljeni.")

            os.makedirs(SUBSET_PATH, exist_ok=True)
            main_df = pd.DataFrame(index=pd.date_range(start="2000-01-01", end="2030-12-31", freq="D"))
            main_df.index.name = "Date"

            print("Pridobivanje BTC podatkov...")
            df_btc = BTC.get_crypto_data("BTC-USD")
            if df_btc is None or df_btc.empty:
                print("Napaka pri pridobivanju BTC podatkov.")
                return None

            main_df = main_df.merge(df_btc, on="Date", how="left")
            bitcoin_df_indices = process_bitcoin_data(df_btc, explained_var=0.8)
            bitcoin_df = BTC.get_bitcoin_indices()
            main_df = main_df.merge(bitcoin_df_indices, on="Date", how="left")
            main_df = main_df.merge(bitcoin_df, on="Date", how="left")

            # generira TA
            main_df = generate_all_ta_features(main_df)

            remove_fully_nan_rows(df_btc.merge(bitcoin_df, on="Date", how="left")).to_csv(f"{SUBSET_PATH}btc.csv",
                                                                                          index=True)

            bitcoin_etf_df, btc_etf_indicator = process_btc_etf_data(df_btc, explained_var=0.8)
            bitcoin_df_indices = bitcoin_df_indices.merge(btc_etf_indicator, on="Date", how="left")

            main_df = main_df.merge(bitcoin_etf_df, on="Date", how="left")
            main_df = main_df.merge(btc_etf_indicator, on="Date", how="left")

            remove_fully_nan_rows(bitcoin_etf_df).to_csv(f"{SUBSET_PATH}btc-etf.csv", index=True)

            print("Obdelava BEA podatkov...")
            bea_indices_df, orig_bea_df = process_bea_data(bea=BEA(), df_btc=df_btc, explained_var=0.8,
                                                           nan_threshold=0.7, min_date=bitcoin_df.index.min())

            main_df = main_df.merge(bea_indices_df, on="Date", how="left")

            remove_fully_nan_rows(orig_bea_df).to_csv(f"{SUBSET_PATH}bea.csv", index=True)

            df_indices = bitcoin_df_indices.merge(bea_indices_df, on="Date", how="left")

            remove_fully_nan_rows(df_indices).to_csv(f"{SUBSET_PATH}indicators.csv", index=True)

            print("Obdelava FRED podatkov...")
            fred_df, orig_fred = process_fred_data(FRED(), df_btc)
            main_df = main_df.merge(fred_df, on="Date", how="left")
            remove_fully_nan_rows(orig_fred).to_csv(f"{SUBSET_PATH}fred.csv", index=True)

            main_df = remove_fully_nan_rows(main_df)

            print("Dodajanje praznikov...")
            holiday_df = HolidayUtil.generate_holiday_dataframe(df_btc.index.min(), main_df.index.max())
            main_df = main_df[main_df.index >= main_df['Close'].first_valid_index()]
            main_df = main_df.merge(holiday_df, on="Date", how="left")
            main_df["time_idx"] = np.arange(1, len(main_df) + 1)
            main_df.to_csv(FILE_PATH, index=True)
            log_entry = pd.DataFrame([[get_today(), "OK"]], columns=["Date", "Status"])
            log_entry.to_csv(FILE_PATH_log, mode='a', header=not os.path.exists(FILE_PATH_log), index=False)
            print("Podatki uspešno shranjeni.")
            clean_data_for_models(FILE_PATH, FILE_PATH_cleaned)

    except Exception as e:
        print(f"Napaka pri nalaganju podatkov: {e}")
        error_message = str(e)
        log_entry = pd.DataFrame([[get_today(), error_message]], columns=["Date", "Status"])
        log_entry.to_csv(FILE_PATH_log, mode='a', header=not os.path.exists(FILE_PATH_log), index=False)

    finally:
        with data_lock:
            print("Končujem nalaganje – nastavljam data_loading = False")
            data_loading = False

def schedule_data_check():
    """Preveri in osveži podatke vsakih 10 minut."""
    global data_loading
    file_exists = os.path.exists(FILE_PATH)
    file_updated_today = file_exists and datetime.fromtimestamp(os.path.getmtime(FILE_PATH)).date() == datetime.today().date()
    print("checking data")
    if not file_updated_today:
        with data_lock:
            if data_loading:
                print("Podatki se že nalagajo, čakam...")
                return
            print("Samodejna posodobitev podatkov...")
        threading.Thread(target=get_data, daemon=True).start()

scheduler = BackgroundScheduler()
scheduler.add_job(schedule_data_check, "interval", minutes=0.1)
scheduler.start()

@app.route("/")
def redirect_home():
    return redirect("/home")

@app.route("/home")
def index():
    return render_template("index.html")

@app.route("/navbar")
def navbar():
    return render_template("navbar.html")

@app.route("/footer")
def footer():
    return render_template("footer.html")

@app.route("/data")
def data_page():
    return render_template("data.html")

@app.route("/modeli")
def modeli_page():
    return render_template("modeli.html")

@app.route("/get_metrics/<category>")
def get_metrics(category):
    file_path = f"{SUBSET_PATH}{category}.csv"
    if not os.path.exists(file_path):
        return jsonify({"error": "File not found"}), 404

    df = pd.read_csv(file_path, index_col="Date", parse_dates=True)
    metrics = list(df.columns)
    return jsonify({"metrics": metrics})

@app.route("/get_chart_data")
def get_chart_data():
    category = request.args.get("category")
    metric = request.args.get("metric")
    file_path = f"{SUBSET_PATH}{category}.csv"

    if not os.path.exists(file_path):
        return jsonify({"error": "File not found"}), 404

    df = pd.read_csv(file_path, index_col="Date", parse_dates=True)
    if metric not in df.columns:
        return jsonify({"error": "Metric not found"}), 404

    df = df.dropna(subset=[metric])

    return jsonify({
        "dates": df.index.strftime("%Y-%m-%d").tolist(),
        "values": df[metric].tolist()
    })

@app.route("/predict_and_plot", methods=["GET"])
def predict_and_plot():
    if not os.path.exists(FILE_PATH_cleaned):
        return jsonify({"error": "Cleaned data file not found"}), 404

    max_encoder_length = 64
    max_prediction_length = 7

    # Pripravi podatke in dataloader
    dataset, predict_dataloader, df = create_dataloaders(
        FILE_PATH_cleaned,
        max_encoder_length=max_encoder_length,
        max_prediction_length=max_prediction_length
    )

    # Naloži modele in napovedi
    models = {name: load_model(name) for name in ["tft", "lstm", "gru"]}
    merged = None
    for name, model in models.items():
        preds_df = run_prediction(model, predict_dataloader, name)
        preds_df = preds_df.rename(columns={"Predicted": name.upper()})
        merged = preds_df if merged is None else merged.merge(preds_df, on="time_idx", how="outer")

    df = df.reset_index()
    df["Date"] = pd.to_datetime(df["Date"])
    today = get_today()

    # Zgodovina
    historical = df[df["Date"] < today].copy().tail(max_encoder_length)
    historical = historical[["time_idx", "Date", "Close"]]
    historical["TFT"] = None
    historical["LSTM"] = None
    historical["GRU"] = None

    # Napovedi
    future_dates = pd.date_range(start=today, periods=max_prediction_length, freq="D")
    future_time_idx = merged["time_idx"].iloc[-max_prediction_length:].values
    predicted = merged.tail(max_prediction_length).copy()
    predicted["Date"] = future_dates
    predicted["Close"] = None
    predicted = predicted[["time_idx", "Date", "Close", "TFT", "LSTM", "GRU"]]

    # JSON kompatibilno
    historical = historical.replace({np.nan: None})
    predicted = predicted.replace({np.nan: None})

    return jsonify({
        "historical": historical.to_dict(orient="records"),
        "predicted": predicted.to_dict(orient="records")
    })


@app.errorhandler(404)
def page_not_found(e):
    return jsonify({"error": "Page not found"}), 404

if __name__ == "__main__":
    app.run(debug=True)