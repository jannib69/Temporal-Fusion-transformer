import os
from dotenv import load_dotenv

# Naloži spremenljivke iz .env
load_dotenv()

class Config:
    FRED_API_KEY = os.getenv("FRED_API_KEY")
    BEA_API_KEY = os.getenv("BEA_API_KEY")
    BLS_API_KEY = os.getenv("BLS_API_KEY")
    YFINANCE_API_KEY = os.getenv("YFINANCE_API_KEY")