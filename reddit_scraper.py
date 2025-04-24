import streamlit as st
import praw
import pandas as pd

# --- Streamlit UI ---
st.set_page_config(page_title="Reddit Comment Scraper", layout="centered")
st.title("Reddit Comment Scraper")

# --- Reddit API Credentials ---
client_id = st.secrets["client_id"]
client_secret = st.secrets["client_secret"]
user_agent = "fan-scraper by u/yourusername"

# --- Input for Reddit URLs ---
urls_input = st.text_area("Reddit thread URLs (one per line)", key="urls")
game_thread_url = st.text_input("Reddit Game Thread URL", key="game_thread")
limit = st.slider("Number of top-level comments to extract per thread", 5, 100, 25)

# --- Initialize session state ---
if 'comments_df' not in st.session_state:
    st.session_state.comments_df = pd.DataFrame()
if 'game_context' not in st.session_state:
    st.session_state.game_context = ""
if 'scraped' not in st.session_state:
    st.session_state.scraped = False

# --- Functions ---
def extract_comments_from_urls(urls, limit):
    reddit = praw.Reddit(client_id=client_id, client_secret=client_secret, user_agent=user_agent)
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

def fetch_game_context(url):
    try:
        reddit = praw.Reddit(client_id=client_id, client_secret=client_secret, user_agent=user_agent)
        submission = reddit.submission(url=url.strip())
        return submission.selftext
    except Exception as e:
        st.error(f"Failed to fetch game thread: {e}")
        return ""

# --- Unified Scrape Button ---
if urls_input.strip() and game_thread_url.strip():
    if st.button("Scrape Reddit"):
        urls = urls_input.strip().splitlines()
        st.session_state.comments_df = extract_comments_from_urls(urls, limit)
        st.session_state.game_context = fetch_game_context(game_thread_url)
        st.session_state.scraped = True

# --- Show Results ---
if st.session_state.scraped:
    if not st.session_state.comments_df.empty:
        st.subheader("Fan Comments")
        st.dataframe(st.session_state.comments_df)
        csv = st.session_state.comments_df.to_csv(index=False).encode('utf-8')
        st.download_button("Download Comments CSV", csv, "comments.csv", "text/csv")

    if st.session_state.game_context:
        st.subheader("Game Context")
        st.text_area("This text can be pasted into your AI prompt for game context:", value=st.session_state.game_context, height=400)

    if st.button("Generate Prompt"):
        comments_sample = st.session_state.comments_df[['username', 'comment_text']].head(5).to_csv(index=False) if not st.session_state.comments_df.empty else "(No comments)"
        context_sample = st.session_state.game_context or "(No game context)"

        prompt = f"""Hi ChatGPT — you are helping a sports journalist write a fan reaction story powered by real Reddit comments and post-game thread data.

1. Game Context:
{context_sample}

2. Fan Quotes Preview:
{comments_sample}

Write a 400–500 word article capturing fan sentiment and key game reactions. Title it: 'From the Stands: [TEAM] Fans React to [EVENT]'. Use direct quotes and highlight standout themes or performances. Maintain a lively, editorial tone."""

        st.subheader("Generated AI Prompt")
        st.text_area("Copy this prompt into ChatGPT:", value=prompt, height=600)
