import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.preprocessing import MinMaxScaler, StandardScaler

class TransformUtil:
    @staticmethod
    def create_indicator(indicator_name, df, scaler="minmax", method="mean", explained_var=0.8):
        if df.isnull().values.any():
            df = df.interpolate(method="linear", limit_direction="both")

        scaler = MinMaxScaler() if scaler == "minmax" else StandardScaler()
        df_scaled = pd.DataFrame(scaler.fit_transform(df), index=df.index, columns=df.columns)

        if df_scaled.shape[1] == 1:
            return df_scaled.rename(columns={df_scaled.columns[0]: "PCA_Indicator"})

        pca = PCA()
        pca_transformed = pca.fit_transform(df_scaled)
        explained_variance_ratio = np.cumsum(pca.explained_variance_ratio_)
        n_components = np.argmax(explained_variance_ratio >= explained_var) + 1

        pca_indicator = np.mean(pca_transformed[:, :n_components], axis=1) if method == "mean" else np.sum(pca_transformed[:, :n_components], axis=1)
        print(f"Processed with {n_components} PCA components explaining ≥ {explained_var*100:.1f}% variance.")

        return pd.DataFrame(pca_indicator, index=df.index, columns=[indicator_name])