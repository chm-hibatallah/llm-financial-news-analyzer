"""
Simple preprocessing pipeline that updates existing files
No new files created - just updates the ones you have
"""

import pandas as pd
import re
import os
from datetime import datetime

def clean_text(text):
    """Simple text cleaning function"""
    if not isinstance(text, str):
        return ""
    
    # Convert to string and lowercase
    text = str(text).lower()
    
    # Remove HTML tags
    text = re.sub(r'<.*?>', '', text)
    
    # Remove URLs
    text = re.sub(r'http\S+|www\S+', '', text)
    
    # Remove special characters (keep letters, numbers, spaces, and basic punctuation)
    text = re.sub(r'[^a-zA-Z0-9\s\.\,\!\?\-\$\%]', '', text)
    
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    
    return text.strip()

def add_missing_columns(df):
    """Add any missing columns that our pipeline needs"""
    
    # Define default columns and their values
    default_columns = {
        'cleaned_text': '',  # Will be filled
        'word_count': 0,
        'char_count': 0,
        'has_financial_terms': False,
        'money_mentions': 0,
        'percentage_mentions': 0,
        'processing_date': datetime.now().strftime('%Y-%m-%d'),
        'processed_version': '1.0'
    }
    
    for col, default_value in default_columns.items():
        if col not in df.columns:
            df[col] = default_value
            print(f"   ➕ Added column: {col}")
    
    return df

def extract_financial_indicators(text):
    """Extract financial indicators from text"""
    money = len(re.findall(r'\$\d+(?:\.\d+)?(?:\s?(?:million|billion|trillion|M|B|T))?', text.lower()))
    percentage = len(re.findall(r'\d+(?:\.\d+)?%', text))
    return money, percentage

def has_financial_terms(text):
    """Check if text contains financial terms"""
    financial_terms = [
        'stock', 'market', 'share', 'invest', 'trading', 'bond', 
        'etf', 'dividend', 'earnings', 'revenue', 'profit', 'loss',
        'ceo', 'company', 'bank', 'economy', 'fed', 'interest', 'rate',
        'inflation', 'gdp', 'ipo', 'merger', 'acquisition'
    ]
    text_lower = text.lower()
    return any(term in text_lower for term in financial_terms)

def process_file(file_path):
    """
    Process a single CSV file and update it in place
    """
    print(f"\n📂 Processing: {os.path.basename(file_path)}")
    
    # Check if file exists
    if not os.path.exists(file_path):
        print(f"   ❌ File not found: {file_path}")
        return False
    
    # Load the CSV
    try:
        df = pd.read_csv(file_path)
        print(f"   📊 Loaded {len(df)} rows")
        print(f"   📋 Existing columns: {list(df.columns)}")
    except Exception as e:
        print(f"   ❌ Error loading file: {e}")
        return False
    
    # Add any missing columns
    df = add_missing_columns(df)
    
    # Track changes
    changes_made = 0
    
    # Process each row
    for idx, row in df.iterrows():
        row_changed = False
        
        # Get the text to process (check multiple possible text columns)
        text = ''
        for text_col in ['text', 'content', 'description', 'summary']:
            if text_col in df.columns and pd.notna(row.get(text_col)):
                text = str(row[text_col])
                break
        
        if not text:
            continue
        
        # 1. Clean text if not already cleaned or if empty
        if pd.isna(row.get('cleaned_text')) or row['cleaned_text'] == '':
            df.at[idx, 'cleaned_text'] = clean_text(text)
            row_changed = True
        
        # 2. Update word count
        cleaned = df.at[idx, 'cleaned_text']
        if pd.notna(cleaned):
            word_count = len(cleaned.split())
            if df.at[idx, 'word_count'] != word_count:
                df.at[idx, 'word_count'] = word_count
                row_changed = True
            
            # 3. Update character count
            char_count = len(cleaned)
            if df.at[idx, 'char_count'] != char_count:
                df.at[idx, 'char_count'] = char_count
                row_changed = True
            
            # 4. Check for financial terms
            financial = has_financial_terms(cleaned)
            if df.at[idx, 'has_financial_terms'] != financial:
                df.at[idx, 'has_financial_terms'] = financial
                row_changed = True
            
            # 5. Extract money and percentage mentions
            money, percentage = extract_financial_indicators(cleaned)
            if df.at[idx, 'money_mentions'] != money:
                df.at[idx, 'money_mentions'] = money
                row_changed = True
            if df.at[idx, 'percentage_mentions'] != percentage:
                df.at[idx, 'percentage_mentions'] = percentage
                row_changed = True
        
        if row_changed:
            changes_made += 1
    
    # Update processing date
    df['processing_date'] = datetime.now().strftime('%Y-%m-%d')
    
    # Save the updated file (overwrite original)
    try:
        df.to_csv(file_path, index=False)
        print(f"   ✅ Updated {changes_made} rows")
        print(f"   💾 Saved to original file: {os.path.basename(file_path)}")
        
        # Show final columns
        print(f"   📋 Final columns: {list(df.columns)}")
        
        return True
    except Exception as e:
        print(f"   ❌ Error saving file: {e}")
        return False

def main():
    """
    Main function to process all CSV files
    """
    print("\n" + "="*50)
    print("🔄 SIMPLE PREPROCESSING PIPELINE")
    print("="*50)
    print("This will update your existing CSV files in place")
    print("No new files will be created")
    
    # Define your CSV files
    csv_files = [
        "data/raw/financial_news_20260228_161838.csv",
        "data/raw/rss_news_20260228_162449.csv",
        "data/raw/combined_raw_quick.csv"  # Add any other files you have
    ]
    
    # Also look for any CSV files in the raw directory
    raw_dir = "data/raw/"
    if os.path.exists(raw_dir):
        for file in os.listdir(raw_dir):
            if file.endswith('.csv') and file not in [os.path.basename(f) for f in csv_files]:
                csv_files.append(os.path.join(raw_dir, file))
    
    # Process each file
    successful = 0
    for file_path in csv_files:
        if process_file(file_path):
            successful += 1
    
    # Summary
    print("\n" + "="*50)
    print("📊 PROCESSING SUMMARY")
    print("="*50)
    print(f"✅ Successfully processed: {successful}/{len(csv_files)} files")
    print("\n📁 All files updated in place:")
    for file_path in csv_files:
        if os.path.exists(file_path):
            size = os.path.getsize(file_path) / 1024  # KB
            print(f"   • {os.path.basename(file_path)} ({size:.1f} KB)")
    
    print("\n✨ Done! Your CSV files now have additional columns:")
    print("   • cleaned_text - Cleaned version of the article text")
    print("   • word_count - Number of words")
    print("   • char_count - Number of characters")
    print("   • has_financial_terms - Whether article contains financial terms")
    print("   • money_mentions - Count of money amounts mentioned")
    print("   • percentage_mentions - Count of percentages mentioned")
    print("   • processing_date - When this was processed")

if __name__ == "__main__":
    main()