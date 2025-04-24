import streamlit as st
import praw
import pandas as pd
import requests
from bs4 import BeautifulSoup

# --- Streamlit UI ---
st.set_page_config(page_title="Reddit Comment Scraper", layout="centered")
st.title("Reddit Comment + Box Score Scraper")
st.write("Paste in Reddit thread URLs and optionally a PlainTextSports game URL. Extract comments and box score data for sports AI workflows.")

# --- Reddit API Credentials ---
client_id = st.secrets["client_id"]
client_secret = st.secrets["client_secret"]
user_agent = "fan-scraper by u/yourusername"  # Replace with your Reddit username

# --- Input for Reddit URLs ---
urls_input = st.text_area("Reddit thread URLs (one per line)")
limit = st.slider("Number of top-level comments to extract per thread", 5, 100, 25)

# --- Input for PlainTextSports URL ---
box_url = st.text_input("PlainTextSports game page URL (optional)")

# --- Reddit Comment Scraper ---
def extract_comments_from_urls(urls, limit):
    reddit = praw.Reddit(
        client_id=client_id,
        client_secret=client_secret,
        user_agent=user_agent
    )
    
    all_comments = []
    for url in urls:
        try:
            submission = reddit.submission(url=url.strip())
            submission.comments.replace_more(limit=0)
            comments = submission.comments[:limit]

            for comment in comments:
                all_comments.append({
                    "thread_url": url,
                    "username": comment.author.name if comment.author else "[deleted]",
                    "comment_text": comment.body,
                    "upvotes": comment.score,
                    "permalink": f"https://reddit.com{comment.permalink}"
                })
        except Exception as e:
            st.error(f"Failed to fetch from {url.strip()}: {e}")

    return pd.DataFrame(all_comments)

# --- Box Score Scraper ---
def scrape_box_score(url):
    try:
        res = requests.get(url)
        soup = BeautifulSoup(res.text, "html.parser")
        lines = soup.find_all("td", class_="line-content")
        box_score_lines = [line.get_text(strip=True) for line in lines if "MIN" in line.get_text() or "LAL" in line.get_text()]

        structured_data = []
        for line in box_score_lines:
            tokens = line.replace("LAL", "LAL ").replace("MIN", "MIN ").split()
            if len(tokens) >= 6:
                team = tokens[0]
                scores = tokens[1:5]
                total = tokens[5]
                structured_data.append({
                    "team": team,
                    "Q1": scores[0],
                    "Q2": scores[1],
                    "Q3": scores[2],
                    "Q4": scores[3],
                    "Total": total
                })

        return pd.DataFrame(structured_data)
    except Exception as e:
        st.error(f"Box score scrape failed: {e}")
        return pd.DataFrame()

# --- Scrape Comments Button ---
if urls_input and st.button("Scrape Reddit Comments"):
    urls = urls_input.strip().splitlines()
    df = extract_comments_from_urls(urls, limit)
    if not df.empty:
        st.success(f"Extracted {len(df)} comments from {len(urls)} thread(s)!")
        st.dataframe(df)
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("Download Comments CSV", csv, "comments.csv", "text/csv")
    else:
        st.warning("No comments were extracted. Please check the URLs.")

# --- Scrape Box Score Button ---
if box_url and st.button("Scrape Box Score"):
    box_df = scrape_box_score(box_url)
    if not box_df.empty:
        st.success("Box score extracted successfully!")
        st.dataframe(box_df)
        box_csv = box_df.to_csv(index=False).encode('utf-8')
        st.download_button("Download Box Score CSV", box_csv, "box_score.csv", "text/csv")
    else:
        st.warning("Box score not found or failed to parse.")
