"""Today's trending searches from Google Trends (free, no key needed).
If the page can't be read, the story is simply invented from scratch."""

import re

import requests

FEED = "https://trends.google.com/trending/rss?geo={geo}"


def today(geo="US", limit=12):
    """A short list of what people are searching for right now."""
    try:
        r = requests.get(FEED.format(geo=geo), timeout=20,
                         headers={"User-Agent": "Mozilla/5.0 (brainrot-shorts)"})
        r.raise_for_status()
    except requests.RequestException as e:
        print(f"Couldn't read Google Trends ({e}); inventing a story instead.")
        return []
    titles = re.findall(r"<item>\s*<title>(.*?)</title>", r.text, flags=re.S)
    clean = [re.sub(r"<!\[CDATA\[|\]\]>", "", t).strip() for t in titles]
    return [t for t in clean if t][:limit]


def as_topic(trends):
    if not trends:
        return None
    return ("Today's trending searches (pick at most ONE that can inspire a fun, harmless fruit drama, "
            "or ignore them all): " + "; ".join(trends))
