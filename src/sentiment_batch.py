

import pandas as pd
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import time
from datetime import datetime
import os
import matplotlib.pyplot as plt

print("=" * 60)
print("SENTIMENT ANALYSIS ON FILTERED ARTICLES")
print("=" * 60)

# ============================================
# STEP 1: Load the filtered data from EDA
# ============================================

print("\n📂 Loading filtered articles from EDA...")

filtered_file = "data/processed/eda_filtered_articles.csv"

if not os.path.exists(filtered_file):
    print(f"❌ File not found: {filtered_file}")
    print("   Please run your EDA notebook first and save the filtered data")
    exit()

df = pd.read_csv(filtered_file)
print(f"✅ Loaded {len(df)} articles that passed EDA filters")
print(f"   Columns: {list(df.columns)}")

# ============================================
# STEP 2: Find the text column
# ============================================

# Which column has the cleaned text?
text_column = None
for col in ['cleaned_text', 'text', 'content']:
    if col in df.columns:
        text_column = col
        print(f"📝 Using text column: '{col}'")
        break

if text_column is None:
    print("❌ No text column found!")
    exit()

# ============================================
# STEP 3: Load FinBERT
# ============================================

print("\n🔄 Loading FinBERT model...")
start_load = time.time()

model_name = "ProsusAI/finbert"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForSequenceClassification.from_pretrained(model_name)

print(f"✅ Model loaded in {time.time()-start_load:.1f} seconds")
print(f"   Model can classify into: {model.config.id2label}")

# ============================================
# STEP 4: Define sentiment function
# ============================================

def get_sentiment(text):
    """
    Get sentiment for a single article
    Returns: sentiment label and all scores
    """
    if not isinstance(text, str) or len(text) < 20:
        return "NEUTRAL", 0.33, 0.33, 0.34, 0.5
    
    # Tokenize
    inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
    
    # Predict
    with torch.no_grad():
        outputs = model(**inputs)
        probs = torch.nn.functional.softmax(outputs.logits, dim=-1)
    
    # Get scores (0=positive, 1=negative, 2=neutral)
    pos = probs[0][0].item()
    neg = probs[0][1].item()
    neu = probs[0][2].item()
    
    # Determine sentiment
    if pos > neg and pos > neu:
        sentiment = "POSITIVE"
        conf = pos
    elif neg > pos and neg > neu:
        sentiment = "NEGATIVE"
        conf = neg
    else:
        sentiment = "NEUTRAL"
        conf = neu
    
    return sentiment, pos, neg, neu, conf

# ============================================
# STEP 5: Process all filtered articles
# ============================================

print("\n" + "=" * 60)
print(f"🔍 Analyzing {len(df)} filtered articles")
print("=" * 60)

# Lists to store results
sentiments = []
pos_scores = []
neg_scores = []
neu_scores = []
confidences = []

total = len(df)
start_time = time.time()

for idx, row in df.iterrows():
    # Get text
    text = row.get(text_column, "")
    
    # Get sentiment
    sentiment, pos, neg, neu, conf = get_sentiment(text)
    
    # Store
    sentiments.append(sentiment)
    pos_scores.append(pos)
    neg_scores.append(neg)
    neu_scores.append(neu)
    confidences.append(conf)
    
    # Show progress every 50 articles
    if (idx + 1) % 50 == 0:
        elapsed = time.time() - start_time
        remaining = (elapsed / (idx + 1)) * (total - (idx + 1))
        print(f"   Processed {idx + 1}/{total} articles ({elapsed:.1f}s elapsed, ~{remaining:.1f}s remaining)")

# Add results to dataframe
df['sentiment'] = sentiments
df['pos_score'] = pos_scores
df['neg_score'] = neg_scores
df['neu_score'] = neu_scores
df['confidence'] = confidences

total_time = time.time() - start_time
print(f"\n✅ Completed in {total_time:.1f} seconds")
print(f"   Average: {total_time/total:.2f} seconds per article")

# ============================================
# STEP 6: Show results
# ============================================

print("\n" + "=" * 60)
print("📊 SENTIMENT RESULTS")
print("=" * 60)

# Count by sentiment
print("\nSentiment Distribution:")
sent_counts = df['sentiment'].value_counts()
for sentiment in ['POSITIVE', 'NEGATIVE', 'NEUTRAL']:
    count = sent_counts.get(sentiment, 0)
    pct = (count / total) * 100
    print(f"   {sentiment}: {count} articles ({pct:.1f}%)")

# Confidence stats
print(f"\nConfidence Scores:")
print(f"   Average: {df['confidence'].mean():.3f}")
print(f"   Median: {df['confidence'].median():.3f}")
print(f"   High (>0.8): {(df['confidence'] > 0.8).sum()} articles")

# Show examples
print("\n" + "=" * 60)
print("📰 EXAMPLE ARTICLES")
print("=" * 60)

for i in range(min(5, len(df))):
    print(f"\nArticle {i+1}:")
    print(f"   Title: {df.iloc[i]['title'][:80]}...")
    print(f"   Sentiment: {df.iloc[i]['sentiment']} (conf: {df.iloc[i]['confidence']:.2f})")
    print(f"   Scores: P={df.iloc[i]['pos_score']:.2f}, N={df.iloc[i]['neg_score']:.2f}, Neu={df.iloc[i]['neu_score']:.2f}")

# ============================================
# STEP 7: Simple visualization
# ============================================

print("\n📊 Creating simple visualization...")

fig, axes = plt.subplots(2, 2, figsize=(12, 10))

# 1. Sentiment bar chart
axes[0, 0].bar(sent_counts.index, sent_counts.values, 
               color=['green', 'red', 'gray'])
axes[0, 0].set_title('Sentiment Distribution')
axes[0, 0].set_xlabel('Sentiment')
axes[0, 0].set_ylabel('Number of Articles')
for i, v in enumerate(sent_counts.values):
    axes[0, 0].text(i, v + 5, str(v), ha='center')

# 2. Sentiment pie chart
axes[0, 1].pie(sent_counts.values, labels=sent_counts.index, 
               autopct='%1.1f%%', colors=['green', 'red', 'gray'])
axes[0, 1].set_title('Sentiment Percentage')

# 3. Confidence distribution
axes[1, 0].hist(df['confidence'], bins=20, edgecolor='black', alpha=0.7)
axes[1, 0].axvline(df['confidence'].mean(), color='red', 
                    linestyle='--', label=f"Mean: {df['confidence'].mean():.2f}")
axes[1, 0].set_xlabel('Confidence')
axes[1, 0].set_ylabel('Frequency')
axes[1, 0].set_title('Confidence Distribution')
axes[1, 0].legend()

# 4. Score distributions
axes[1, 1].hist(df['pos_score'], alpha=0.5, label='Positive', bins=20, color='green')
axes[1, 1].hist(df['neg_score'], alpha=0.5, label='Negative', bins=20, color='red')
axes[1, 1].hist(df['neu_score'], alpha=0.5, label='Neutral', bins=20, color='gray')
axes[1, 1].set_xlabel('Score')
axes[1, 1].set_ylabel('Frequency')
axes[1, 1].set_title('Score Distributions')
axes[1, 1].legend()

plt.tight_layout()
plt.savefig('reports/filtered_sentiment_results.png', dpi=150, bbox_inches='tight')
plt.show()
print("✅ Chart saved to: reports/filtered_sentiment_results.png")

# ============================================
# STEP 8: Save results
# ============================================

print("\n💾 Saving results...")

# Save with timestamp
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
output_file = f"data/processed/sentiment_filtered_{timestamp}.csv"
df.to_csv(output_file, index=False)
print(f"✅ Saved to: {output_file}")

# Also save as main file for easy access
main_file = "data/processed/final_sentiment_results.csv"
df.to_csv(main_file, index=False)
print(f"✅ Saved to: {main_file}")

print("\n" + "=" * 60)
print("✨ SENTIMENT ANALYSIS COMPLETE!")
print("=" * 60)
print(f"\n📈 Final dataset: {len(df)} articles with sentiment")
print(f"📁 Files saved:")
print(f"   - {output_file}")
print(f"   - {main_file}")
print(f"   - reports/filtered_sentiment_results.png")