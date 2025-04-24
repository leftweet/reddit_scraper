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

        prompt = f"""Hi ChatGPT — you are helping a sports journalist write a fan reaction article using only the supplied CSV and game context file.

You have three sources of information:

1. comments.csv
This file contains Reddit fan comments. Each row includes:
- thread_title
- username
- comment_text (the full fan comment)
- upvotes
- permalink

These are the ONLY fan quotes you are allowed to use.
You may:
- Use them verbatim
- Paraphrase them conservatively (the meaning must remain exactly the same)
You may NOT:
- Create new quotes
- Invent phrasing that does not exist in the comment_text
- Imply sentiment beyond what the comment actually says

If you want to include a quote in the article, it must come directly from a row in the CSV.

2. game_context.txt
This is a factual summary of the game. It includes score, player stats, and game flow. You may ONLY refer to players, events, or stats mentioned in this file.

3. Optional Images
You may have uploaded memes or Reddit screenshots. Use these only to support tone or sentiment, not as factual sources. Do not extract or invent text from them.

Your task is to write a 400–500 word article titled:
**From the Stands: [TEAM] Fans React to [EVENT]**

Instructions:
- Start with a 1-paragraph fan reaction summary
- Then create 2–3 sections (reactions to players, moments, coaching)
- End with a conclusion about how fans feel going forward

Tone:
- Conversational, polished, and journalistic
- Quote fans naturally (e.g. “One user commented…”)
- Use quotes for flavor, not filler
- Do not exaggerate sentiment or speculate

Return the article as a plain text .txt file."""

        st.subheader("Generated AI Prompt")
        st.text_area("Copy this prompt into ChatGPT:", value=prompt, height=700)
