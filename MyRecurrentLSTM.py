import torch
from pytorch_forecasting.models import RecurrentNetwork
from pytorch_optimizer import Ranger
import warnings
warnings.filterwarnings("ignore")


class MyRecurrentLSTM(RecurrentNetwork):
    def __init__(self, beta1=0.9, beta2=0.95, alpha=0.5, k=6, lr_factor=0.65, lr_patience=3, min_lr=1e-9, **kwargs):
        self.save_hyperparameters(ignore=["loss", "logging_metrics"])
        super().__init__(**kwargs)
        self.training_time = None

    def configure_optimizers(self):
        optimizer = Ranger(
            self.parameters(),
            lr=self.hparams.learning_rate,
            betas=(self.hparams.beta1, self.hparams.beta2),
            weight_decay=self.hparams.weight_decay,
             eps=1e-8,
            k=self.hparams.k,
            alpha=self.hparams.alpha
        )
        scheduler = {
            "scheduler": torch.optim.lr_scheduler.ReduceLROnPlateau(
                optimizer,
                mode="min",
                factor=self.hparams.lr_factor,
                patience=self.hparams.lr_patience,
                min_lr=self.hparams.min_lr,
                verbose=True
            ),
            "monitor": "val_loss",
            "interval": "epoch",
            "frequency": 1
        }
        return {"optimizer": optimizer, "lr_scheduler": scheduler}