import re
import pandas as pd
from src.config import RAW_DATA_PATH, PROCESSED_DATA_PATH

def clean_text(text):
    if not isinstance(text, str):
        return ""
    # Remove extra whitespace, URLs, HTML entities
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'http\S+', '', text)
    text = re.sub(r'&[a-z]+;', '', text)  # simple HTML entities
    return text.strip()

def preprocess_data(input_path=RAW_DATA_PATH, output_path=PROCESSED_DATA_PATH):
    df = pd.read_csv(input_path)
    # Clean the text column
    df['clean_text'] = df['text'].apply(clean_text)
    # Drop rows with very short text
    df = df[df['clean_text'].str.len() > 100]
    # Save intermediate cleaned data
    df.to_csv(output_path, index=False)
    print(f"Preprocessed data saved to {output_path}")
    return df

if __name__ == "__main__":
    preprocess_data()