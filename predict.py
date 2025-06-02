import warnings

warnings.filterwarnings("ignore")
warnings.filterwarnings(
    "ignore",
    message="X does not have valid feature names, but StandardScaler was fitted with feature names"
)

import numpy as np
import pandas as pd
import torch
from pandas.api.types import CategoricalDtype
from pytorch_forecasting import TimeSeriesDataSet
from pytorch_forecasting.data.encoders import NaNLabelEncoder, EncoderNormalizer
from pytorch_lightning import seed_everything

from MyTFT import MyTFT
from MyRecurrentLSTM import MyRecurrentLSTM

torch.set_float32_matmul_precision("high")

MODEL_PATHS = {
    "tft": "Models/tft_v1.ckpt",
    "lstm": "Models/lstm_v3.ckpt",
    "gru": "Models/gru_v1.ckpt"
}

def load_model(model_type: str):
    if model_type == "tft":
        return MyTFT.load_from_checkpoint(MODEL_PATHS["tft"], map_location="cpu").eval()
    elif model_type in ["lstm", "gru"]:
        return MyRecurrentLSTM.load_from_checkpoint(MODEL_PATHS[model_type], map_location="cpu").eval()
    else:
        raise ValueError(f"Unknown model type: {model_type}")

def run_prediction(model, dataloader, model_type="model"):
    print(f"Running {model_type.upper()} prediction...")

    if model_type == "tft":
        preds_obj = model.predict(
            dataloader,
            mode="raw",
            return_x=True,
            return_y=False,
            trainer_kwargs={"accelerator": "cpu"},
        )
        preds = preds_obj.output[0].detach().cpu().numpy().reshape(-1)
        x = preds_obj.x
        time_idx = x["decoder_time_idx"][0].detach().cpu().numpy().reshape(-1)

    else:  # LSTM, GRU
        preds_obj = model.predict(
            dataloader,
            mode="prediction",
            return_x=True,
            return_y=False,
            trainer_kwargs={"accelerator": "cpu"},
        )

        if hasattr(preds_obj, "output") and hasattr(preds_obj, "x"):
            # V primeru, da model kljub vsemu vrne objekt (ne bi smel)
            preds = preds_obj.output[0].detach().cpu().numpy().reshape(-1)
            x = preds_obj.x
        elif isinstance(preds_obj, tuple) and len(preds_obj) == 2:
            raw_preds, x = preds_obj
            preds = raw_preds[0].detach().cpu().numpy().reshape(-1)
        else:
            raise ValueError("Nepodprt format izhoda pri modelu: pričakovan tuple ali objekt z .output in .x")

        time_idx = x["decoder_time_idx"][0].detach().cpu().numpy().reshape(-1)

    # --- Poravnava dolžin ---
    min_len = min(len(preds), len(time_idx))
    return pd.DataFrame({
        "time_idx": time_idx[:min_len],
        "Predicted": preds[:min_len]
    })

def create_dataloaders(
    file_path: str,
    batch_size=1000,
    max_encoder_length=64,
    max_prediction_length=7,
    target_lags=3,
    target_center=True,
    target_transformation="log",
):
    df = pd.read_feather(file_path)
    if "Date" not in df.columns and isinstance(df.index, pd.DatetimeIndex):
        df["Date"] = df.index


    # Današnji datum
    today = pd.to_datetime("today").normalize()

    # Loči na zgodovinske in prihodnje
    df_hist = df[df["Date"] <= today].copy()
    df_future = df[df["Date"] > today].copy()

    # Zadnjih X vrstic zgodovine
    required_hist = max_encoder_length + target_lags + target_center
    df_hist = df_hist.tail(required_hist)

    # Združi zgodovino s prihodnostjo (če obstaja)
    df = pd.concat([df_hist, df_future.tail(max_prediction_length)], ignore_index=True)

    # Dodeli time_idx
    df["time_idx"] = np.arange(len(df))

    # Značilke
    time_varying_known_reals = [
        "GDP and National Income", "Personal Income and Employment", "Industry Specific Accounts",
        "Fixed Assets and Investment", "Trade and International Transactions",
        "Government and Public Sector", "Financial and Corporate Data",
        "time_idx", "year"
    ]

    time_varying_known_categoricals = [
        'US', 'UK', 'Japan', 'China', 'day', 'month', 'day_of_week', 'week_of_year',
        'year', 'quarter', 'is_weekend', 'is_month_end', 'Halving', 'group'
    ]

    time_varying_unknown_reals = ["Close"]

    # Encoderji
    categorical_encoders = {col: NaNLabelEncoder(add_nan=True) for col in time_varying_known_categoricals}

    seed_everything(42, workers=True)
    df.reset_index(drop=True, inplace=True)
    dataset = TimeSeriesDataSet(
        df,
        time_idx="time_idx",
        target="Close",
        group_ids=["group"],
        max_encoder_length=max_encoder_length,
        max_prediction_length=max_prediction_length,
        static_categoricals=["group"],
        time_varying_known_categoricals=time_varying_known_categoricals,
        time_varying_known_reals=time_varying_known_reals,
        time_varying_unknown_reals=time_varying_unknown_reals,
        target_normalizer=EncoderNormalizer(transformation=target_transformation, center=target_center),
        add_relative_time_idx=True,
        add_target_scales=True,
        add_encoder_length=True,
        allow_missing_timesteps=True,
        categorical_encoders=categorical_encoders,
        lags={"Close": list(np.arange(1, target_lags))}
    )

    predict_dataloader = dataset.to_dataloader(train=False, batch_size=batch_size, num_workers=2)
    return dataset, predict_dataloader, df