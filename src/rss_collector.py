import feedparser
import pandas as pd
import time
from datetime import datetime
import requests
from bs4 import BeautifulSoup

def fetch_from_rss(feeds=None, max_per_feed=20):
    """
    Fetch news from RSS feeds (completely free, no API limits)
    """
    if feeds is None:
        feeds = [
            # Yahoo Finance RSS
            'https://finance.yahoo.com/news/rssindex',
            # Reuters Business
            'http://feeds.reuters.com/reuters/businessNews',
            # CNBC
            'https://www.cnbc.com/id/10001147/device/rss/rss.html',
            # Bloomberg (might need specific feeds)
            'https://feeds.bloomberg.com/markets/news.rss',
            # Financial Times
            'https://www.ft.com/?format=rss',
            # WSJ
            'https://feeds.a.dj.com/rss/RSSMarketsMain.xml',
        ]
    
    all_articles = []
    
    for feed_url in feeds:
        print(f"\nFetching from RSS: {feed_url}")
        
        try:
            feed = feedparser.parse(feed_url)
            
            for entry in feed.entries[:max_per_feed]:
                article = {
                    'title': entry.get('title', ''),
                    'published': entry.get('published', datetime.now()),
                    'source': feed.feed.get('title', 'Unknown'),
                    'url': entry.get('link', ''),
                    'text': '',  # Will fill later
                    'description': entry.get('description', ''),
                    'summary': entry.get('summary', '')
                }
                
                # Try to get full text
                try:
                    response = requests.get(entry.link, timeout=10)
                    soup = BeautifulSoup(response.content, 'html.parser')
                    # Remove script/style
                    for script in soup(["script", "style"]):
                        script.decompose()
                    text = soup.get_text()
                    # Clean up
                    lines = (line.strip() for line in text.splitlines())
                    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                    text = ' '.join(chunk for chunk in chunks if chunk)
                    article['text'] = text[:10000]  # Limit length
                except:
                    article['text'] = article['description']
                
                all_articles.append(article)
                
            time.sleep(2)  # Be respectful
            
        except Exception as e:
            print(f"Error with feed {feed_url}: {e}")
    
    # Create DataFrame
    df = pd.DataFrame(all_articles)
    
    # Save
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"data/raw/rss_news_{timestamp}.csv"
    df.to_csv(filename, index=False)
    
    print(f"\n Saved {len(df)} articles from RSS feeds to {filename}")
    return df

if __name__ == "__main__":
    df = fetch_from_rss(max_per_feed=10)
    print(f"Collected {len(df)} articles")