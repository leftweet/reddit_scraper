import streamlit as st
import praw
import pandas as pd

# --- Streamlit UI ---
st.set_page_config(page_title="Reddit Fan Reaction Builder", layout="centered")
st.title("Fan Reaction Article Builder")

# --- Reddit API Credentials ---
client_id = st.secrets["client_id"]
client_secret = st.secrets["client_secret"]
user_agent = "fan-scraper by u/yourusername"

# --- Input for Reddit URLs ---
urls_input = st.text_area("Reddit thread URLs (one per line)", key="urls")
game_thread_url = st.text_input("Reddit Game Thread URL", key="game_thread")

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
def extract_top_comments_by_upvotes(urls, top_n=5):
    reddit = praw.Reddit(client_id=client_id, client_secret=client_secret, user_agent=user_agent)
    all_comments = []
    thread_titles = []
    for url in urls:
        try:
            submission = reddit.submission(url=url.strip())
            thread_titles.append(submission.title)
            submission.comments.replace_more(limit=0)
            comments = sorted(submission.comments, key=lambda x: x.score, reverse=True)[:top_n]
            for comment in comments:
                all_comments.append({
                    "thread_title": submission.title,
                    "comment_text": comment.body.strip()
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

# --- Scrape Button ---
if urls_input.strip() and game_thread_url.strip():
    if st.button("Scrape Reddit"):
        urls = urls_input.strip().splitlines()
        st.session_state.comments_df, st.session_state.comment_threads = extract_top_comments_by_upvotes(urls)
        st.session_state.game_context = fetch_game_context(game_thread_url)
        st.session_state.scraped = True

# --- Show Results ---
if st.session_state.scraped:
    if not st.session_state.comments_df.empty:
        st.subheader("Fan Comments")
        st.dataframe(st.session_state.comments_df)

    if st.session_state.game_context:
        st.subheader("Game Context")
        st.text_area("Fetched game context:", value=st.session_state.game_context, height=300)

    # Format fan quotes for both prompts
    formatted_quotes = ""
    for _, row in st.session_state.comments_df.iterrows():
        formatted_quotes += f'"{row["comment_text"]}" — from "{row["thread_title"]}"\n'

    # --- Article Generation Prompt ---
    if st.button("Generate Article Prompt"):
        article_prompt = f"""Hi ChatGPT — you are helping a sports journalist write a fan reaction article using ONLY the comments and game context below.

You must follow these strict editorial rules:

1. Fan Quotes:
Use ONLY the quotes provided below. Do not fabricate or paraphrase beyond recognition. If you use a quote, reference the thread title it came from. Do not invent quotes or assume tone not present in the quote.

Fan Quotes:
{formatted_quotes}

2. Game Context:
Use ONLY the context below for describing the game score, stats, and key events. Do not fabricate player performances or game flow that is not included here.

Game Context:
{st.session_state.game_context}

3. Optional Images:
The user may upload Reddit memes or screenshots. You may use them to understand tone, emotion, or narrative framing — but NOT for factual content or quotes.

4. Article Structure:
Write a 400–500 word article titled:
**From the Stands: [TEAM] Fans React to [EVENT]**

Structure:
- Short intro summarizing fan energy
- Sections on player performance, fan mood, key moments
- Finish with forward-looking fan sentiment

Tone:
- Lively, readable, and grounded in fan voice
- Use quotes naturally, e.g. 'One fan wrote…'
- Keep the structure tight and journalistic
- Do not speculate, exaggerate, or invent
- This article should be publishable

When you are finished, return the article as plain text suitable for download as a .txt file."""

        st.subheader("Generated Article Prompt")
        st.text_area("Copy this prompt into ChatGPT:", value=article_prompt, height=800)

    # --- Fact-Checking Prompt ---
    if st.button("Generate Fact-Checking Prompt"):
        fact_check_prompt = f"""Hi ChatGPT — you are acting as a newsroom fact-checker for an AI-generated sports article. You will verify that the article only uses the data provided below and contains no fabricated content.

You have the following materials:

1. Fan Quotes:
{formatted_quotes}

2. Game Context:
{st.session_state.game_context}

Fact-checking Instructions:

- Quotes: Are all quotes in the article taken directly from the quotes above? Do not allow any quote that does not appear verbatim or clearly paraphrased.
- Stats and game details: Are all stats and descriptions found in the game context? If not, flag them.
- Tone: Does the article reflect the sentiment of the fan quotes? Avoid exaggerated optimism or drama not supported by the material.
- Structure: Is the article structured logically (lead, body, conclusion)?
- Fabrication: Flag any information not supported by the provided context or quotes.

Be specific. Flag errors, give suggested edits, and finish with a verdict:
Pass / Needs Edits / Fail.

Reminder: This is a real editorial check. No hallucination is acceptable."""

        st.subheader("Generated Fact-Checking Prompt")
        st.text_area("Copy this fact-check prompt into ChatGPT:", value=fact_check_prompt, height=800)
