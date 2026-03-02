"""
Financial News Collector
Collects news from NewsAPI and RSS feeds and saves raw data
"""

import requests
import pandas as pd
import feedparser
import time
from datetime import datetime
import os
from src.config import (
    NEWS_API_KEY, 
    RAW_DATA_PATH, 
    RSS_FEEDS, 
    NEWSAPI_QUERIES,
    MAX_ARTICLES_PER_NEWSAPI_QUERY,
    MAX_ARTICLES_PER_RSS_FEED
)

class FinancialNewsCollector:
    """
    A class to collect financial news from multiple sources
    """
    
    def __init__(self):
        self.all_articles = []
        self.newsapi_articles = []
        self.rss_articles = []
        
    def collect_from_newsapi(self, query, max_articles):
        """
        Collect news from NewsAPI for a specific query
        
        Args:
            query: Search term
            max_articles: Maximum number of articles to collect
            
        Returns:
            List of article dictionaries
        """
        print(f"      Query: '{query}'", end="", flush=True)
        
        if not NEWS_API_KEY or NEWS_API_KEY == "your_key_here":
            print(" - Skipping (no API key)")
            return []
        
        articles = []
        
        url = "https://newsapi.org/v2/everything"
        
        params = {
            "q": query,
            "language": "en",
            "sortBy": "publishedAt",
            "pageSize": min(max_articles, 100),
            "apiKey": NEWS_API_KEY
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            
            if data.get("status") != "ok":
                print(f" - Error: {data.get('message', 'Unknown error')}")
                return []
            
            for item in data.get("articles", []):
                article = {
                    "title": item.get("title", ""),
                    "published": item.get("publishedAt", ""),
                    "source": item.get("source", {}).get("name", "Unknown"),
                    "url": item.get("url", ""),
                    "text": item.get("content", "") or item.get("description", ""),
                    "description": item.get("description", ""),
                    "collection_method": "newsapi",
                    "collection_query": query,
                    "collected_at": datetime.now().isoformat()
                }
                articles.append(article)
            
            print(f" - {len(articles)} articles")
            
        except requests.exceptions.RequestException as e:
            print(f" - Connection error: {e}")
        except Exception as e:
            print(f" - Unexpected error: {e}")
        
        return articles
    
    def collect_all_newsapi(self):
        """
        Collect news from NewsAPI for all configured queries
        """
        print("\n  Collecting from NewsAPI...")
        
        if not NEWS_API_KEY or NEWS_API_KEY == "your_key_here":
            print("    No valid NewsAPI key found. Skipping NewsAPI collection.")
            print("    Get a free key at: https://newsapi.org/")
            return []
        
        all_articles = []
        
        for query in NEWSAPI_QUERIES:
            articles = self.collect_from_newsapi(query, MAX_ARTICLES_PER_NEWSAPI_QUERY)
            all_articles.extend(articles)
            time.sleep(1)  # Avoid rate limiting
        
        print(f"    Total NewsAPI articles: {len(all_articles)}")
        
        self.newsapi_articles = all_articles
        return all_articles
    
    def collect_from_rss_feed(self, feed):
        """
        Collect news from a single RSS feed
        
        Args:
            feed: Dictionary with feed name and url
            
        Returns:
            List of article dictionaries
        """
        name = feed["name"]
        url = feed["url"]
        
        print(f"      {name}...", end="", flush=True)
        
        articles = []
        
        try:
            parsed_feed = feedparser.parse(url)
            
            for entry in parsed_feed.entries[:MAX_ARTICLES_PER_RSS_FEED]:
                text = ""
                
                if hasattr(entry, "content") and entry.content:
                    text = entry.content[0].value
                elif hasattr(entry, "summary"):
                    text = entry.summary
                elif hasattr(entry, "description"):
                    text = entry.description
                
                if text:
                    text = text.replace("<p>", " ").replace("</p>", " ")
                    text = text.replace("<br>", " ").replace("<br/>", " ")
                
                article = {
                    "title": entry.get("title", ""),
                    "published": entry.get("published", entry.get("updated", "")),
                    "source": name,
                    "url": entry.get("link", ""),
                    "text": text,
                    "description": entry.get("summary", ""),
                    "collection_method": "rss",
                    "collection_source": name,
                    "collected_at": datetime.now().isoformat()
                }
                articles.append(article)
            
            print(f" {len(articles)} articles")
            
        except Exception as e:
            print(f" Error: {e}")
        
        return articles
    
    def collect_all_rss(self):
        """
        Collect news from all configured RSS feeds
        """
        print("\n  Collecting from RSS feeds...")
        
        all_articles = []
        
        for feed in RSS_FEEDS:
            articles = self.collect_from_rss_feed(feed)
            all_articles.extend(articles)
            time.sleep(1)
        
        print(f"    Total RSS articles: {len(all_articles)}")
        
        self.rss_articles = all_articles
        return all_articles
    
    def save_articles(self, articles, filepath):
        """
        Save articles to CSV file
        
        Args:
            articles: List of article dictionaries
            filepath: Path to save the CSV file
            
        Returns:
            Boolean indicating success
        """
        if not articles:
            print("    No articles to save")
            return False
        
        df = pd.DataFrame(articles)
        
        if "url" in df.columns:
            df = df.drop_duplicates(subset=["url"], keep="first")
        elif "title" in df.columns:
            df = df.drop_duplicates(subset=["title"], keep="first")
        
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        try:
            df.to_csv(filepath, index=False)
            print(f"    Saved {len(df)} articles to: {filepath}")
            return True
        except Exception as e:
            print(f"    Error saving file: {e}")
            return False
    
    def collect_all(self):
        """
        Run the complete collection process
        """
        print("\n" + "="*60)
        print("FINANCIAL NEWS COLLECTOR")
        print("="*60)
        
        self.collect_all_newsapi()
        self.collect_all_rss()
        
        self.all_articles = self.newsapi_articles + self.rss_articles
        
        print("\n" + "-"*60)
        print("COLLECTION SUMMARY")
        print("-"*60)
        print(f"  Total articles: {len(self.all_articles)}")
        print(f"  NewsAPI articles: {len(self.newsapi_articles)}")
        print(f"  RSS articles: {len(self.rss_articles)}")
        
        if self.all_articles:
            sources = set()
            for article in self.all_articles:
                if "source" in article:
                    sources.add(article["source"])
            print(f"  Unique sources: {len(sources)}")
        
        return self.all_articles
    
    def save_all(self):
        """
        Save all collected articles to the configured path
        """
        print("\n" + "-"*60)
        print("SAVING DATA")
        print("-"*60)
        
        if not self.all_articles:
            print("  No articles to save")
            return False
        
        success = self.save_articles(self.all_articles, RAW_DATA_PATH)
        
        if success:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"data/raw/financial_news_backup_{timestamp}.csv"
            self.save_articles(self.all_articles, backup_path)
            
            if self.newsapi_articles:
                newsapi_path = f"data/raw/newsapi_{timestamp}.csv"
                self.save_articles(self.newsapi_articles, newsapi_path)
            
            if self.rss_articles:
                rss_path = f"data/raw/rss_news_{timestamp}.csv"
                self.save_articles(self.rss_articles, rss_path)
        
        return success
    
    def show_sample(self, n=3):
        """
        Show sample articles
        
        Args:
            n: Number of sample articles to show
        """
        if not self.all_articles:
            print("\nNo articles to show")
            return
        
        print("\n" + "-"*60)
        print(f"SAMPLE ARTICLES (first {n})")
        print("-"*60)
        
        for i, article in enumerate(self.all_articles[:n]):
            print(f"\nArticle {i+1}:")
            print(f"  Title: {article.get('title', 'N/A')[:100]}...")
            print(f"  Source: {article.get('source', 'N/A')}")
            print(f"  Published: {article.get('published', 'N/A')}")
            print(f"  Method: {article.get('collection_method', 'N/A')}")
            print(f"  Text length: {len(article.get('text', ''))} characters")

def main():
    """
    Main function to run the collector
    """
    collector = FinancialNewsCollector()
    
    collector.collect_all()
    collector.save_all()
    collector.show_sample(3)
    
    print("\n" + "="*60)
    print("COLLECTION COMPLETE")
    print("="*60)
    print(f"\nMain data file: {RAW_DATA_PATH}")
    print("\nYou can now use this data for preprocessing and analysis.")

if __name__ == "__main__":
    main()