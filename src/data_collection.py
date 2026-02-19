import requests
import pandas as pd
from newspaper import Article
from src.config import NEWS_API_KEY, RAW_DATA_PATH

def fetch_news(query="finance", page_size=10):
    """
    Fetch news articles from NewsAPI.
    """
    url = f"https://newsapi.org/v2/everything?q={query}&language=en&pageSize={page_size}&apiKey={NEWS_API_KEY}"
    response = requests.get(url)
    data = response.json()
    
    articles = []
    for item in data.get('articles', []):
        # Use newspaper3k to extract full text
        try:
            article = Article(item['url'])
            article.download()
            article.parse()
            text = article.text
        except Exception as e:
            print(f"Error downloading {item['url']}: {e}")
            text = item.get('description', '')
        
        articles.append({
            'title': item['title'],
            'published': item['publishedAt'],
            'source': item['source']['name'],
            'url': item['url'],
            'text': text
        })
    
    df = pd.DataFrame(articles)
    df.to_csv(RAW_DATA_PATH, index=False)
    print(f"Saved {len(df)} articles to {RAW_DATA_PATH}")
    return df

if __name__ == "__main__":
    fetch_news()