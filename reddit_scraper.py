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
if 'comment_threads' not in st.session_state:
    st.session_state.comment_threads = []
if 'scraped' not in st.session_state:
    st.session_state.scraped = False

# --- Functions ---
def extract_comments_from_urls(urls, limit):
    reddit = praw.Reddit(client_id=client_id, client_secret=client_secret, user_agent=user_agent)
    all_comments = []
    thread_titles = []
    for url in urls:
        try:
            submission = reddit.submission(url=url.strip())
            thread_titles.append(submission.title)
            submission.comments.replace_more(limit=0)
            comments = submission.comments[:limit]
            for comment in comments:
                all_comments.append({
                    "thread_title": submission.title,
                    "thread_url": url,
                    "username": comment.author.name if comment.author else "[deleted]",
                    "comment_text": comment.body,
                    "upvotes": comment.score,
                    "permalink": f"https://reddit.com{comment.permalink}"
                })
        except Exception as e:
            st.error(f"Failed to fetch from {url.strip()}: {e}")
    return pd.DataFrame(all_comments), thread_titles

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
        st.session_state.comments_df, st.session_state.comment_threads = extract_comments_from_urls(urls, limit)
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
        st.text_area("Game context (for reference):", value=st.session_state.game_context, height=400)
        game_txt = st.session_state.game_context.encode('utf-8')
        st.download_button("Download Game Context TXT", game_txt, "game_context.txt", "text/plain")

    if st.button("Generate Prompt"):
        thread_titles_text = "\n- " + "\n- ".join(st.session_state.comment_threads)

        prompt = f"""Hi ChatGPT — you are helping a sports journalist write a fan reaction article based on Reddit commentary and a separate game context file.

Here is what you’re working with:

1. Fan Commentary (CSV):
You have a CSV file named comments.csv. Each row represents a top-level Reddit comment. The columns include:
- thread_title: the title of the Reddit post (game or topic related)
- username: the Redditor's handle
- comment_text: their full comment
- upvotes: how many upvotes the comment received
- permalink: the full Reddit link to the comment

These comments came from the following Reddit threads:
{thread_titles_text}

2. Game Context (TXT):
You have a file named game_context.txt. It contains a text summary of the game from a Reddit post thread. Use this as the factual basis for game flow, player stats, and team performance. Do not fabricate any game events or results.

3. Optional Images:
The user may upload relevant images — including memes, screenshots, or visual reactions from Reddit — into this prompt thread. If so, examine these images to infer tone, sentiment, or context that complements the written comments.

Your task is to write a 400–500 word article titled:
**From the Stands: [TEAM] Fans React to [EVENT]**

Tone & Voice:
- Conversational and editorial
- Capture the mood and emotional vibe of the fans
- Use select direct quotes (attribute naturally, like “One fan wrote...”)
- Don’t overexplain or repeat what’s already obvious from the data

Structure:
- Start with a short, energetic intro paragraph summarizing how fans felt after the game
- Then build out 2–3 sections:
  - What themes or takeaways came up repeatedly?
  - How did fans react to key players or moments?
  - Was there praise, concern, frustration, optimism?
- End with a conclusion paragraph reflecting how the fanbase is feeling going forward

When you are done, return the article as plain text and format it for download as a .txt file."""

        st.subheader("Generated AI Prompt")
        st.text_area("Copy this prompt into ChatGPT:", value=prompt, height=700)
