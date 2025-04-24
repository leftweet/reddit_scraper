import streamlit as st
import praw
import pandas as pd

# --- Streamlit UI ---
st.set_page_config(page_title="Reddit Comment Scraper", layout="centered")
st.title("Reddit Thread Comment Scraper")
st.write("Paste in a Reddit thread URL below. This tool will extract the top-level comments and export them as a CSV.")

# --- Reddit API Credentials ---
client_id = st.secrets["client_id"]
client_secret = st.secrets["client_secret"]
user_agent = "fan-scraper by u/yourusername"  # Replace with your Reddit username

# --- Input field for Reddit URL ---
url = st.text_input("Reddit thread URL")
limit = st.slider("Number of top-level comments to extract", 5, 100, 25)

# --- Function to extract comments ---
def extract_comments_from_url(url, limit):
    reddit = praw.Reddit(
        client_id=client_id,
        client_secret=client_secret,
        user_agent=user_agent
    )
    
    submission = reddit.submission(url=url)
    submission.comments.replace_more(limit=0)
    comments = submission.comments[:limit]

    data = []
    for comment in comments:
        data.append({
            "username": comment.author.name if comment.author else "[deleted]",
            "comment_text": comment.body,
            "upvotes": comment.score,
            "permalink": f"https://reddit.com{comment.permalink}"
        })

    return pd.DataFrame(data)

# --- Button to trigger scraping ---
if url and st.button("Scrape Comments"):
    try:
        df = extract_comments_from_url(url, limit)
        st.success(f"Extracted {len(df)} comments!")
        st.dataframe(df)

        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("Download CSV", csv, "comments.csv", "text/csv")
    except Exception as e:
        st.error(f"Error: {e}")
