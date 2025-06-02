# Bitcoin Forecasting Web App

This project is an interactive Flask web application for visualizing 7-day forecasts of Bitcoin price using advanced deep learning models: Temporal Fusion Transformer (TFT), LSTM, and GRU. The predictions are based on real-time economic indicators retrieved automatically from public sources (BEA and others).

![image](https://github.com/user-attachments/assets/1113ef87-94f3-4451-9e97-b93faeaf81fd)

## Overview

The application allows users to:

- Automatically load and process the latest economic and macro data (updated **daily**),
- Visualize historical Bitcoin prices along with model predictions for the next 7 days,
- Compare forecasts across multiple models (TFT, LSTM, GRU),
- Explore each economic input variable using interactive time series plots,
- Use a clean and responsive web interface built with Flask and JavaScript.

---

## Project Structure

├── app.py                  # Flask backend serving routes and predictions
├── templates/              # HTML templates
├── static/                 # CSS and JavaScript files
├── predict.py              # Prediction logic and dataloader preparation
├── Models/                 # Trained model checkpoints (.ckpt files)
├── data/                   # Raw and cleaned input data
├── Training/               # Jupyter Notebooks with training and evaluation
└── README.md               # Project description

## Models

All models are trained using [PyTorch Forecasting](https://pytorch-forecasting.readthedocs.io/en/stable/) and include:
- Temporal Fusion Transformer (TFT) with quantile loss and attention mechanism,
- LSTM and GRU baselines with optimized hyperparameters,
- Custom feature engineering using macroeconomic time series and calendar features.

Model outputs are normalized, lagged, and re-scaled for realistic future prediction.

## Technologies

- Python, Flask, Pandas, PyTorch Lightning
- PyTorch Forecasting
- HTML/CSS + Vanilla JavaScript
- Jupyter Notebooks for training and evaluation

## Data Source

Source: Custom models trained on publicly available economic data from the Bureau of Economic Analysis (BEA) and cryptocurrency market data.

## Training & Evaluation

All training and evaluation notebooks are in the `Training/` directory, including:
- Feature selection and preprocessing,
- Model definition and tuning (Optuna),
- Metrics: MAE, RMSE, MAPE, SMAPE, AIC, BIC,
- Visualizations of attention weights and prediction intervals.

## Environment Setup

Before running the application, make sure to set up the required environment variables and install dependencies.

### 1. Create `.env` file

In the project root, create a `.env` file with the following contents:

FRED_API_KEY=your_fred_api_key_here

BEA_API_KEY=your_bea_api_key_here

BLS_API_KEY=your_bls_api_key_here

Replace `your_fred_api_key_here`, etc., with your actual API keys. These are required for automatic data collection from official sources like FRED, BEA, and BLS.

### 2. Install requirements

To install all required Python packages:

```bash
pip install -r requirements.txt


