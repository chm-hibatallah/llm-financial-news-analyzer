import requests
import pandas as pd
import time
from src.config import NEWS_API_KEY, RAW_DATA_PATH

# Try importing newspaper, but have fallbacks
try:
    from newspaper import Article
    NEWSPAPER_AVAILABLE = True
except ImportError:
    NEWSPAPER_AVAILABLE = False
    print("newspaper3k not fully installed. Using basic extraction.")
    # Fallback: try to use just requests and BeautifulSoup
    from bs4 import BeautifulSoup

def extract_article_text(url):
    """
    Extract article text using available method.
    """
    text = ""
    
    # Method 1: newspaper3k (if available)
    if NEWSPAPER_AVAILABLE:
        try:
            article = Article(url)
            article.download()
            article.parse()
            text = article.text
            if text and len(text) > 100:
                return text
        except Exception as e:
            print(f"Newspaper extraction failed for {url}: {e}")
    
    # Method 2: Basic BeautifulSoup fallback
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            # Get text
            text = soup.get_text()
            # Break into lines and remove leading/trailing space
            lines = (line.strip() for line in text.splitlines())
            # Break multi-headlines into a line each
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            # Drop blank lines
            text = ' '.join(chunk for chunk in chunks if chunk)
            return text
    except Exception as e:
        print(f"BeautifulSoup extraction failed for {url}: {e}")
    
    return ""

def fetch_news(query="finance", page_size=10):
    """
    Fetch news articles from NewsAPI.
    """
    print(f"Fetching {page_size} news articles about '{query}'...")
    
    url = f"https://newsapi.org/v2/everything?q={query}&language=en&pageSize={page_size}&apiKey={NEWS_API_KEY}"
    
    try:
        response = requests.get(url)
        data = response.json()
        
        if data.get('status') != 'ok':
            print(f"API Error: {data.get('message', 'Unknown error')}")
            return pd.DataFrame()
        
        articles = []
        for i, item in enumerate(data.get('articles', [])):
            print(f"Processing article {i+1}/{page_size}: {item['title'][:50]}...")
            
            # Extract full text
            text = extract_article_text(item['url'])
            
            # If extraction failed, use description as fallback
            if not text or len(text) < 50:
                text = item.get('description', '')
                print(f"  Using description fallback ({len(text)} chars)")
            
            articles.append({
                'title': item['title'],
                'published': item['publishedAt'],
                'source': item['source']['name'],
                'url': item['url'],
                'text': text,
                'description': item.get('description', '')
            })
            
            # Small delay to be respectful to servers
            time.sleep(1)
        
        df = pd.DataFrame(articles)
        df.to_csv(RAW_DATA_PATH, index=False)
        print(f"✅ Saved {len(df)} articles to {RAW_DATA_PATH}")
        return df
        
    except Exception as e:
        print(f"❌ Error fetching news: {e}")
        return pd.DataFrame()

if __name__ == "__main__":
    # Test the function
    df = fetch_news(page_size=3)
    if not df.empty:
        print("\nSample article:")
        print(f"Title: {df.iloc[0]['title']}")
        print(f"Text length: {len(df.iloc[0]['text'])} characters")