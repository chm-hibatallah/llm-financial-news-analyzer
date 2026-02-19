import os
from dotenv import load_dotenv

load_dotenv()  # load variables from .env file

# NewsAPI
NEWS_API_KEY = os.getenv("NEWS_API_KEY", "3ebf5a2ef01b41e2aa4812ba8421f9b5")

# Paths
RAW_DATA_PATH = "data/raw/financial_news.csv"
PROCESSED_DATA_PATH = "data/processed/financial_news_with_sentiment.csv"