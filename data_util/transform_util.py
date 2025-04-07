import numpy as np
import pandas as pd
from copy import deepcopy as dc
from sklearn.decomposition import PCA
from sklearn.preprocessing import MinMaxScaler, StandardScaler, RobustScaler, QuantileTransformer
from sklearn.feature_selection import mutual_info_regression

class TransformUtil:
    @staticmethod
    def create_indicator(indicator_name, df, scaler="minmax", method="mean", explained_var=0.8, mi_threshold=None):
        if df.isnull().values.any():
            df = df.interpolate(method="time", limit_direction="both")

        # Skaliranje
        if scaler == "minmax":
            scaler_obj = MinMaxScaler()
        elif scaler == "standard":
            scaler_obj = StandardScaler()
        elif scaler == "robust":
            scaler_obj = RobustScaler()
        elif scaler == "quantile":
            scaler_obj = QuantileTransformer(output_distribution="normal")
        else:
            raise ValueError(f"Neveljaven scaler: {scaler}")

        df_scaled = pd.DataFrame(scaler_obj.fit_transform(df), index=df.index, columns=df.columns)

        # Če je samo ena značilka, jo vrnemo neposredno
        if df_scaled.shape[1] == 1:
            return df_scaled.rename(columns={df_scaled.columns[0]: indicator_name})

        # Mutual Information za izbor značilk med sabo in povprečjem po vrsticah - Sintetic indicator
        mi = mutual_info_regression(df_scaled, df_scaled.mean(axis=1))
        if np.all(mi == 0):
            print(f"[{indicator_name}] Opozorilo: Vse MI vrednosti so 0 – ne izvajamo selekcije.")
        else:
            if mi_threshold is not None:
                selected_cols = df.columns[mi > mi_threshold]
            else:
                selected_cols = df.columns[np.argsort(mi)[-int(len(mi) * 0.7):]]
            df_scaled = dc(df_scaled[selected_cols])
            print(f"[{indicator_name}] Izbranih {len(selected_cols)} / {df.shape[1]} značilk z MI.")

        # PCA
        pca = PCA()
        pca_transformed = pca.fit_transform(df_scaled)
        explained_variance_ratio = np.cumsum(pca.explained_variance_ratio_)
        n_components = np.argmax(explained_variance_ratio >= explained_var) + 1

        # Kombiniranje komponent v en kazalnik
        if method == "mean":
            pca_indicator = np.mean(pca_transformed[:, :n_components], axis=1)
        elif method == "sum":
            pca_indicator = np.sum(pca_transformed[:, :n_components], axis=1)
        elif method == "weighted":
            weights = pca.explained_variance_ratio_[:n_components]
            pca_indicator = np.dot(pca_transformed[:, :n_components], weights)
        else:
            raise ValueError(f"Neveljavna metoda: {method}")

        print(f"[{indicator_name}] Uporabljenih {n_components} PCA komponent (≥ {explained_var*100:.1f}% variance).")

        return pd.DataFrame(pca_indicator, index=df.index, columns=[indicator_name])