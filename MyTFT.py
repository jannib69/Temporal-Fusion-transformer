import torch
from pytorch_forecasting.models import TemporalFusionTransformer
from pytorch_optimizer import Ranger
import warnings
warnings.filterwarnings("ignore")
warnings.filterwarnings(
    "ignore",
    message="X does not have valid feature names, but StandardScaler was fitted with feature names"
)

class MyTFT(TemporalFusionTransformer):
    def __init__(
        self,
        *args,
        beta1=0.9,
        beta2=0.999,
        weight_decay=0.0,
        alpha=0.5,
        k=6,
        lr_factor=0.67,
        lr_patience=10,
        min_lr=1e-9,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.save_hyperparameters(ignore=["loss", "logging_metrics"])
        self.training_time = None

    def configure_optimizers(self):
        optimizer = Ranger(
            self.parameters(),
            lr=self.hparams.learning_rate,
            alpha=self.hparams.alpha,
            k=self.hparams.k,
            betas=(self.hparams.beta1, self.hparams.beta2),
            eps=1e-8,
            weight_decay=self.hparams.weight_decay,
            use_gc=True,
            gc_conv_only=False,
            amsgrad=False
        )

        scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
            optimizer,
            mode="min",
            factor=self.hparams.lr_factor,
            patience=self.hparams.lr_patience,
            min_lr=self.hparams.min_lr,
            verbose=True
        )

        return {
            "optimizer": optimizer,
            "lr_scheduler": {
                "scheduler": scheduler,
                "monitor": "val_loss",
                "interval": "epoch",
                "frequency": 1
            }
        }

    def on_train_start(self):
        self.log("initial_lr", self.trainer.optimizers[0].param_groups[0]["lr"], prog_bar=False, logger=True)

    def on_train_epoch_end(self):
        current_lr = self.trainer.optimizers[0].param_groups[0]["lr"]
        self.log("lr", current_lr, prog_bar=True, logger=True)