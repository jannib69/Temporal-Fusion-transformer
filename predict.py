import numpy as np
import torch
import pandas as pd
from pytorch_forecasting.models.temporal_fusion_transformer import TemporalFusionTransformer
torch.set_float32_matmul_precision('high')


MODEL_PATH = "Models/TFT_Model_3.ckpt"

def load_model():
    """Load the trained TFT model from disk"""
    best_tft = TemporalFusionTransformer.load_from_checkpoint(MODEL_PATH, map_location=torch.device("cpu"))
    best_tft.eval()
    return best_tft

def run_tft_prediction(model, data, max_prediction_length):
    """Runs inference on TFT and ensures predictions are extracted correctly with print logging."""

    print("Starting TFT prediction...")

    new_raw_predictions = model.predict(
        data,
        mode="quantiles",
        return_x=True,
        return_y=True,
        trainer_kwargs={"accelerator": "gpu"},
    )

    if new_raw_predictions is None or len(new_raw_predictions[0]) == 0:
        print("Error: Model returned no predictions.")
        return pd.DataFrame()  # Return empty DataFrame if no predictions

    print("TFT prediction completed successfully.")

    # Extract quantiles
    predicted_quantiles = new_raw_predictions[0]

    print(f"Shape of raw predictions: {predicted_quantiles.shape}")

    quantile_05 = predicted_quantiles[:, :, 0].detach().cpu().numpy().squeeze()
    quantile_50 = predicted_quantiles[:, :, 1].detach().cpu().numpy().squeeze()
    quantile_85 = predicted_quantiles[:, :, 2].detach().cpu().numpy().squeeze()


    print(
        f"Extracted quantiles - Median shape: {quantile_50.shape}, Lower bound: {quantile_05.shape}, Upper bound: {quantile_85.shape}")

    if len(quantile_50) == 0:
        print("Error: No valid predictions returned.")
        return pd.DataFrame()

    time_idx = data["time_idx"].values[-max_prediction_length:]

    print(f"Time indices for predictions: {time_idx}")

    predictions_df = pd.DataFrame({
        "time_idx": time_idx,
        "Predicted_Median": quantile_50,
        "Lower_Bound": quantile_05,
        "Upper_Bound": quantile_85
    })

    data = data.reset_index()  # prenese Date iz indexa v stolpec


    predictions_df = data[["time_idx", "Date", "Close"]].merge(
        predictions_df,
        on="time_idx",
        how="left"
    )

    predictions_df.loc[
        predictions_df.time_idx >= predictions_df.time_idx.max() - max_prediction_length,
        "Close"
    ] = np.nan

    print("Predictions DataFrame after merging with dates:")
    return predictions_df