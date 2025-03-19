from flask import Flask, render_template, Response, request, jsonify
import pandas as pd
from data_processing import process_bea_data, process_bitcoin_data, process_fred_data, remove_fully_nan_rows
from data_util import HolidayUtil, BTC, BEA, FRED
from datetime import datetime
import os

app = Flask(__name__, static_folder="static", template_folder="templates")

FILE_PATH = "Data/daily_data.csv"
SUBSET_PATH = "Data/Subsets/"

def get_data():
    os.makedirs(SUBSET_PATH, exist_ok=True)

    if os.path.exists(FILE_PATH):
        file_date = datetime.fromtimestamp(os.path.getmtime(FILE_PATH)).date()
        today = datetime.today().date()
        if file_date == today:
            df = pd.read_csv(FILE_PATH, parse_dates=["Date"], index_col="Date")
            return df if not df.empty else None

    main_df = pd.DataFrame(index=pd.date_range(start="2000-01-01", end="2030-12-31", freq="D"))
    main_df.index.name = "Date"

    print(f"Processing BTC")
    df_btc = BTC.get_crypto_data("BTC-USD")
    main_df = main_df.merge(df_btc, on="Date", how="left")

    bitcoin_df_indices = process_bitcoin_data(df_btc, explained_var=0.8)
    bitcoin_df = BTC.get_bitcoin_indices()

    main_df = main_df.merge(bitcoin_df_indices, on="Date", how="left")
    main_df = main_df.merge(bitcoin_df, on="Date", how="left")
    btc_df_tmp = df_btc.merge(bitcoin_df, on="Date", how="left")
    remove_fully_nan_rows(btc_df_tmp).to_csv(f"{SUBSET_PATH}btc.csv", index=True)

    bitcoin_etf_df = BTC.get_etf_flows()
    main_df = main_df.merge(bitcoin_etf_df, on="Date", how="left")
    remove_fully_nan_rows(bitcoin_etf_df).to_csv(f"{SUBSET_PATH}btc-etf.csv", index=True)

    print(f"Processing BEA")
    bea_indices_df, orig_bea_df = process_bea_data(bea=BEA(), df_btc=df_btc, explained_var=0.8, nan_threshold=0.7, min_date=bitcoin_df.index.min())
    main_df = main_df.merge(bea_indices_df, on="Date", how="left")
    remove_fully_nan_rows(orig_bea_df).to_csv(f"{SUBSET_PATH}bea.csv", index=True)

    df_indices = bitcoin_df_indices.merge(bea_indices_df, on="Date", how="left")
    remove_fully_nan_rows(df_indices).to_csv(f"{SUBSET_PATH}indicators.csv", index=True)

    print(f"Processing FRED")
    fred_df, orig_fred = process_fred_data(FRED(), df_btc)
    main_df = main_df.merge(fred_df, on="Date", how="left")
    remove_fully_nan_rows(orig_fred).to_csv(f"{SUBSET_PATH}fred.csv", index=True)

    main_df = remove_fully_nan_rows(main_df)

    print(f"Processing Holidays")
    holiday_df = HolidayUtil.generate_holiday_dataframe(main_df.index.min(), main_df.index.max())
    main_df = main_df[main_df.index >= main_df['Close'].first_valid_index()]
    main_df = main_df.merge(holiday_df, on="Date", how="left")

    main_df.to_csv(FILE_PATH, index=True)
    return main_df

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/load_data")
def load_data():
    file_exists = os.path.exists(FILE_PATH)
    file_updated_today = file_exists and datetime.fromtimestamp(os.path.getmtime(FILE_PATH)).date() == datetime.today().date()

    if file_updated_today:
        return jsonify({"status": "ready"})
    else:
        return jsonify({"status": "update_required"})

@app.route("/update_data", methods=['POST'])
def update_data():
    get_data()
    return jsonify({"status": "completed"})


@app.route("/navbar")
def navbar():
    return render_template("navbar.html")

@app.route("/footer")
def footer():
    return render_template("footer.html")

@app.route("/data")
def data_page():
    return render_template("data.html")

@app.route("/get_metrics/<category>")
def get_metrics(category):
    file_path = f"{SUBSET_PATH}{category}.csv"
    if not os.path.exists(file_path):
        return jsonify({"error": "File not found"}), 404

    df = pd.read_csv(file_path, index_col="Date", parse_dates=True)
    metrics = list(df.columns)
    print(f"Metrics for {category}: {metrics}")  # Debug log
    return jsonify({"metrics": metrics})

@app.route("/get_chart_data")
def get_chart_data():
    category = request.args.get("category")
    metric = request.args.get("metric")
    file_path = f"{SUBSET_PATH}{category}.csv"

    # Debug logs
    print(f"Requested category: {category}, metric: {metric}")
    print(f"Checking file path: {file_path}")

    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return jsonify({"error": "File not found"}), 404

    df = pd.read_csv(file_path, index_col="Date", parse_dates=True)
    if metric not in df.columns:
        print(f"Metric not found: {metric}")
        return jsonify({"error": "Metric not found"}), 404

    df = df.dropna(subset=[metric])
    print(f"Chart data for {metric}: {df.head()}")  # Debug log

    return jsonify({
        "dates": df.index.strftime("%Y-%m-%d").tolist(),
        "values": df[metric].tolist()
    })




@app.errorhandler(404)
def page_not_found(e):
    return jsonify({"error": "Page not found"}), 404


if __name__ == "__main__":
    app.run(debug=True)