import streamlit as st
import praw
import pandas as pd

# --- Streamlit UI ---
st.set_page_config(page_title="Reddit Comment Scraper", layout="centered")
st.title("Reddit Thread Comment Scraper")
st.write("Paste in one or more Reddit thread URLs below (separated by newlines). This tool will extract the top-level comments and export them as a CSV.")

# --- Reddit API Credentials ---
client_id = st.secrets["client_id"]
client_secret = st.secrets["client_secret"]
user_agent = "fan-scraper by u/yourusername"  # Replace with your Reddit username

# --- Input field for Reddit URLs ---
urls_input = st.text_area("Reddit thread URLs (one per line)")
limit = st.slider("Number of top-level comments to extract per thread", 5, 100, 25)

# --- Function to extract comments ---
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

# --- Button to trigger scraping ---
if urls_input and st.button("Scrape Comments"):
    urls = urls_input.strip().splitlines()
    df = extract_comments_from_urls(urls, limit)
    if not df.empty:
        st.success(f"Extracted {len(df)} comments from {len(urls)} thread(s)!")
        st.dataframe(df)

        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("Download CSV", csv, "comments.csv", "text/csv")
    else:
        st.warning("No comments were extracted. Please check the URLs.")
