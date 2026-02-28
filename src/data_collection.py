import requests
import pandas as pd
import time
from datetime import datetime, timedelta
from src.config import NEWS_API_KEY, RAW_DATA_PATH

# Try importing newspaper, but have fallbacks
try:
    from newspaper import Article
    NEWSPAPER_AVAILABLE = True
except ImportError:
    NEWSPAPER_AVAILABLE = False
    print("newspaper3k not fully installed. Using basic extraction.")
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
            for script in soup(["script", "style", "nav", "header", "footer"]):
                script.decompose()
            text = soup.get_text()
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = ' '.join(chunk for chunk in chunks if chunk)
            return text
    except Exception as e:
        print(f"BeautifulSoup extraction failed for {url}: {e}")
    
    return ""

def fetch_news_paginated(query="finance", total_articles=50, days_back=7):
    """
    Fetch multiple pages of news articles.
    
    Args:
        query: Search query
        total_articles: Desired number of articles (max 100 due to API limit)
        days_back: How many days back to search
    """
    print(f"Fetching up to {total_articles} news articles about '{query}'...")
    
    all_articles = []
    page = 1
    page_size = min(100, total_articles)  # API max is 100 per request
    
    # Calculate date range
    to_date = datetime.now()
    from_date = to_date - timedelta(days=days_back)
    
    while len(all_articles) < total_articles:
        print(f"\nFetching page {page}...")
        
        # Build URL with pagination and date range
        url = (f"https://newsapi.org/v2/everything?"
               f"q={query}"
               f"&from={from_date.strftime('%Y-%m-%d')}"
               f"&to={to_date.strftime('%Y-%m-%d')}"
               f"&language=en"
               f"&pageSize={page_size}"
               f"&page={page}"
               f"&sortBy=publishedAt"
               f"&apiKey={NEWS_API_KEY}")
        
        try:
            response = requests.get(url)
            data = response.json()
            
            if data.get('status') != 'ok':
                print(f"API Error: {data.get('message', 'Unknown error')}")
                break
            
            articles_batch = data.get('articles', [])
            if not articles_batch:
                print("No more articles available.")
                break
            
            print(f"Got {len(articles_batch)} articles on page {page}")
            
            # Process each article
            for i, item in enumerate(articles_batch):
                if len(all_articles) >= total_articles:
                    break
                    
                print(f"  Processing article {i+1}/{len(articles_batch)}: {item['title'][:50]}...")
                
                # Extract full text
                text = extract_article_text(item['url'])
                
                # If extraction failed, use description as fallback
                if not text or len(text) < 50:
                    text = item.get('description', '')
                    print(f"    Using description fallback ({len(text)} chars)")
                
                all_articles.append({
                    'title': item['title'],
                    'published': item['publishedAt'],
                    'source': item['source']['name'],
                    'url': item['url'],
                    'text': text,
                    'description': item.get('description', '')
                })
                
                # Small delay to be respectful to servers
                time.sleep(1)
            
            page += 1
            
            # Check if we've reached the total results available
            if page > (data.get('totalResults', 0) // page_size) + 1:
                print("Reached the last available page.")
                break
                
        except Exception as e:
            print(f" Error on page {page}: {e}")
            break
    
    # Save to CSV
    if all_articles:
        df = pd.DataFrame(all_articles)
        # Add timestamp to filename to avoid overwriting
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = RAW_DATA_PATH.replace('.csv', f'_{timestamp}.csv')
        df.to_csv(filename, index=False)
        print(f"\n Saved {len(df)} articles to {filename}")
        
        # Also save as latest
        df.to_csv(RAW_DATA_PATH, index=False)
        print(f" Also saved as latest to {RAW_DATA_PATH}")
        
        return df
    else:
        print(" No articles collected.")
        return pd.DataFrame()

def fetch_news_multiple_queries(queries=None, articles_per_query=20):
    """
    Fetch news for multiple different queries to get more variety.
    """
    if queries is None:
        queries = [
            "stock market",
            "interest rates", 
            "inflation",
            "banking",
            "cryptocurrency",
            "real estate",
            "economy",
            "investing",
            "federal reserve",
            "earnings"
        ]
    
    all_articles = []
    
    for query in queries:
        print(f"\n{'='*50}")
        print(f"Fetching news for: '{query}'")
        print('='*50)
        
        df = fetch_news_paginated(query=query, total_articles=articles_per_query, days_back=3)
        
        if not df.empty:
            all_articles.append(df)
        
        # Wait between different queries to avoid rate limiting
        time.sleep(5)
    
    if all_articles:
        # Combine all dataframes
        final_df = pd.concat(all_articles, ignore_index=True)
        # Remove duplicates based on URL
        final_df = final_df.drop_duplicates(subset=['url'])
        
        # Save combined dataset
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"data/raw/financial_news_comprehensive_{timestamp}.csv"
        final_df.to_csv(filename, index=False)
        
        print(f"\n{'='*50}")
        print(f"  Collected {len(final_df)} unique articles")
        print(f" Saved to {filename}")
        print('='*50)
        
        return final_df
    else:
        print(" No articles collected from any query.")
        return pd.DataFrame()

def fetch_news_simple(query="finance", page_size=10):
    """
    Simple version for quick tests (original function)
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
            
            text = extract_article_text(item['url'])
            
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
            
            time.sleep(1)
        
        df = pd.DataFrame(articles)
        df.to_csv(RAW_DATA_PATH, index=False)
        print(f" Saved {len(df)} articles to {RAW_DATA_PATH}")
        return df
        
    except Exception as e:
        print(f" Error fetching news: {e}")
        return pd.DataFrame()

if __name__ == "__main__":
    print("Choose collection method:")
    print("1. Simple (10 articles)")
    print("2. Paginated (up to 100 articles)")
    print("3. Multiple queries (comprehensive)")
    
    choice = input("Enter choice (1-3): ").strip()
    
    if choice == "1":
        # Simple test
        df = fetch_news_simple(page_size=10)
        
    elif choice == "2":
        # Get up to 100 articles
        num = input("How many articles? (max 100): ").strip()
        num = int(num) if num.isdigit() else 50
        num = min(num, 100)
        df = fetch_news_paginated(total_articles=num, days_back=7)
        
    elif choice == "3":
        # Comprehensive - multiple queries
        df = fetch_news_multiple_queries(articles_per_query=15)
        
    else:
        print("Invalid choice")
        df = fetch_news_simple()
    
    # Show summary
    if not df.empty:
        print("\n" + "="*50)
        print("COLLECTION SUMMARY:")
        print("="*50)
        print(f"Total articles: {len(df)}")
        print(f"Date range: {df['published'].min()} to {df['published'].max()}")
        print(f"Sources: {df['source'].nunique()} unique sources")
        print("\nTop sources:")
        print(df['source'].value_counts().head(10))
        
        # Show sample
        print("\nSample article:")
        print(f"Title: {df.iloc[0]['title']}")
        print(f"Source: {df.iloc[0]['source']}")
        print(f"Published: {df.iloc[0]['published']}")
        print(f"Text length: {len(df.iloc[0]['text'])} characters")