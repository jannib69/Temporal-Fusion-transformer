import pandas as pd
import torch
from pytorch_forecasting import TemporalFusionTransformer
from pytorch_forecasting.data.encoders import GroupNormalizer
from pytorch_forecasting.data.timeseries import TimeSeriesDataSet
from pytorch_lightning import Trainer


class Predictor:
    def __init__(self, model_path, data_path, target="Close", max_encoder_length=31, max_prediction_length=31):
        """
        Inicializacija modela in nastavitev parametrov za napoved.
        """
        self.model_path = model_path
        self.data_path = data_path
        self.target = target
        self.max_encoder_length = max_encoder_length
        self.max_prediction_length = max_prediction_length

        # Naloži model
        self.model = TemporalFusionTransformer.load_from_checkpoint(self.model_path)

    def prepare_data(self):
        """
        Naloži in pripravi podatke za napoved.
        """
        df = pd.read_csv(self.data_path, parse_dates=["date"])
        df = df.sort_values("date")  # Poskrbi, da so podatki urejeni

        # Pridobi zadnji znani datum
        last_known_date = df["date"].max()

        # Ustvari prihodnjih 31 dni za napoved
        future_dates = pd.date_range(start=last_known_date + pd.Timedelta(days=1), periods=self.max_prediction_length,
                                     freq="D")

        # Ustvari prihodnje vrstice za napoved
        df_future = pd.DataFrame({"date": future_dates})
        df_future[self.target] = None  # Vrednosti, ki jih napovemo

        # Združi obstoječe podatke z napovednimi vrsticami
        df = pd.concat([df, df_future], ignore_index=True)

        # Ustvari TimeSeriesDataSet
        dataset = TimeSeriesDataSet(
            df,
            time_idx="date",
            target=self.target,
            group_ids=["BTC"],  # Če imaš več časovnih vrstic
            time_varying_known_reals=["date"],  # Datum je znan vnaprej
            max_encoder_length=self.max_encoder_length,
            max_prediction_length=self.max_prediction_length,
            target_normalizer=GroupNormalizer(groups=["BTC"])  # Normalizacija
        )

        return dataset, future_dates

    def predict(self):
        """
        Napove prihodnje vrednosti BTC cene.
        """
        dataset, future_dates = self.prepare_data()

        # Inicializacija PyTorch Lightning Trainer
        trainer = Trainer(accelerator="cpu", logger=False, enable_checkpointing=False)

        # Izvedba napovedi
        predictions = trainer.predict(self.model, dataset, return_index=True)

        # Oblikovanje rezultatov
        df_preds = pd.DataFrame({
            "date": future_dates,
            "predicted_Close": predictions.numpy().flatten()
        })

        return df_preds

    def save_predictions(self, output_path):
        """
        Shrani napovedi v CSV datoteko.
        """
        predictions = self.predict()
        predictions.to_csv(output_path, index=False)
        print(f"Napovedi shranjene v: {output_path}")


# --- Primer uporabe ---
if __name__ == "__main__":
    model_file = "/mnt/data/TFT_Model_5.ckpt"
    data_file = "/mnt/data/daily_data.csv"
    output_file = "/mnt/data/BTC_predictions.csv"

    predictor = Predictor(model_file, data_file)
    predictor.save_predictions(output_file)