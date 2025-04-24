import streamlit as st
import praw
import pandas as pd

# --- Streamlit UI ---
st.set_page_config(page_title="Reddit Comment Scraper", layout="centered")
st.title("Reddit Comment Scraper")
st.write("Paste in Reddit thread URLs below to extract top-level comments and export as a CSV.")

# --- Reddit API Credentials ---
client_id = st.secrets["client_id"]
client_secret = st.secrets["client_secret"]
user_agent = "fan-scraper by u/yourusername"

# --- Input for Reddit URLs ---
urls_input = st.text_area("Reddit thread URLs (one per line)")
limit = st.slider("Number of top-level comments to extract per thread", 5, 100, 25)

# --- Input for Game Thread URL ---
game_thread_url = st.text_input("Reddit Game Thread URL (optional)")

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

# --- Fetch Game Context from Game Thread ---
def fetch_game_context(url):
    try:
        reddit = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            user_agent=user_agent
        )
        submission = reddit.submission(url=url.strip())
        return submission.selftext
    except Exception as e:
        st.error(f"Failed to fetch game thread: {e}")
        return ""

if game_thread_url and st.button("Fetch Game Context"):
    context_text = fetch_game_context(game_thread_url)
    if context_text:
        st.subheader("Game Context")
        st.text_area("This text can be pasted into your AI prompt for game context:", value=context_text, height=400)
