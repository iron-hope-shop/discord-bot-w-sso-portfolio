import feedparser

def fetch_rss_feed(url):
    feed = feedparser.parse(url)
    items = feed.entries
    return items

