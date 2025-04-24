import streamlit as st
import praw
import pandas as pd
import requests
from bs4 import BeautifulSoup

# --- Streamlit UI ---
st.set_page_config(page_title="Reddit Comment + Box Score Scraper", layout="centered")
st.title("Reddit Comment + Box Score Scraper")
st.write("Paste in Reddit thread URLs and optionally a Basketball-Reference box score URL. Extract comments and structured box score data.")

# --- Reddit API Credentials ---
client_id = st.secrets["client_id"]
client_secret = st.secrets["client_secret"]
user_agent = "fan-scraper by u/yourusername"  # Replace with your Reddit username

# --- Input for Reddit URLs ---
urls_input = st.text_area("Reddit thread URLs (one per line)")
limit = st.slider("Number of top-level comments to extract per thread", 5, 100, 25)

# --- Input for Basketball-Reference URL ---
box_url = st.text_input("Basketball-Reference box score URL (optional)")

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

# --- Basketball-Reference Box Score Scraper ---
def scrape_bref_box_score(url):
    try:
        res = requests.get(url)
        soup = BeautifulSoup(res.text, "html.parser")

        linescore_table = soup.find("table", id="line_score")
        rows = linescore_table.find_all("tr")

        structured_data = []
        for row in rows[1:]:
            cells = row.find_all("td")
            if len(cells) >= 6:
                team = row.find("a").text if row.find("a") else "Unknown"
                q_scores = [cell.text for cell in cells[:4]]
                total = cells[4].text
                structured_data.append({
                    "team": team,
                    "Q1": q_scores[0],
                    "Q2": q_scores[1],
                    "Q3": q_scores[2],
                    "Q4": q_scores[3],
                    "Total": total
                })

        return pd.DataFrame(structured_data)
    except Exception as e:
        st.error(f"Basketball-Reference scrape failed: {e}")
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
    box_df = scrape_bref_box_score(box_url)
    if not box_df.empty:
        st.success("Box score extracted successfully!")
        st.dataframe(box_df)
        box_csv = box_df.to_csv(index=False).encode('utf-8')
        st.download_button("Download Box Score CSV", box_csv, "box_score.csv", "text/csv")
    else:
        st.warning("Box score not found or failed to parse.")
