import streamlit as st
import praw
import pandas as pd
import requests
from bs4 import BeautifulSoup, Comment
import io

# --- Streamlit UI ---
st.set_page_config(page_title="Reddit Comment + Box Score Scraper", layout="centered")
st.title("Reddit Comment + Box Score Scraper")
st.write("Paste in Reddit thread URLs and optionally a Basketball-Reference box score URL. Extract comments, team scores, player stats, and generate a structured AI prompt.")

# --- Session State Init ---
if 'df' not in st.session_state:
    st.session_state.df = pd.DataFrame()
if 'score_df' not in st.session_state:
    st.session_state.score_df = pd.DataFrame()
if 'players_df' not in st.session_state:
    st.session_state.players_df = pd.DataFrame()

# --- Reddit API Credentials ---
client_id = st.secrets["client_id"]
client_secret = st.secrets["client_secret"]
user_agent = "fan-scraper by u/yourusername"

# --- Input ---
urls_input = st.text_area("Reddit thread URLs (one per line)")
limit = st.slider("Number of top-level comments to extract per thread", 5, 100, 25)
box_url = st.text_input("Basketball-Reference box score URL (optional)")

# --- Scraper Functions ---
def extract_comments_from_urls(urls, limit):
    reddit = praw.Reddit(client_id=client_id, client_secret=client_secret, user_agent=user_agent)
    all_comments = []
    for url in urls:
        try:
            submission = reddit.submission(url=url.strip())
            submission.comments.replace_more(limit=0)
            for comment in submission.comments[:limit]:
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

def scrape_bref_box_score(url):
    try:
        res = requests.get(url)
        soup = BeautifulSoup(res.text, "html.parser")
        comments = soup.find_all(string=lambda text: isinstance(text, Comment))

        # Team box
        score_df = pd.DataFrame()
        for comment in comments:
            comment_soup = BeautifulSoup(comment, "html.parser")
            table = comment_soup.find("table", id="line_score")
            if table:
                rows = table.find_all("tr")
                structured_data = []
                for row in rows[1:]:
                    cells = row.find_all("td")
                    if len(cells) >= 5:
                        team = row.find("a").text if row.find("a") else "Unknown"
                        q_scores = [cell.text for cell in cells[:4]]
                        total = cells[4].text
                        structured_data.append({"team": team, "Q1": q_scores[0], "Q2": q_scores[1], "Q3": q_scores[2], "Q4": q_scores[3], "Total": total})
                score_df = pd.DataFrame(structured_data)

        # Player stats
        player_stats = []
        for comment in comments:
            comment_soup = BeautifulSoup(comment, "html.parser")
            for table in comment_soup.find_all("table"):
                if table.get("id") and "box" in table.get("id") and "basic" in table.get("id"):
                    team = table.get("id").split("-")[1].upper()
                    rows = table.find_all("tr", class_=lambda x: x != 'thead')
                    headers = [th.text for th in table.find_all("thead")[0].find_all("th")][1:]
                    for row in rows:
                        cells = row.find_all("td")
                        if not cells:
                            continue
                        player = row.find("th").text.strip()
                        stats = [cell.text.strip() for cell in cells]
                        player_stats.append(dict(zip(["team", "player"] + headers, [team, player] + stats)))
        players_df = pd.DataFrame(player_stats)
        return score_df, players_df
    except Exception as e:
        st.error(f"Basketball-Reference scrape failed: {e}")
        return pd.DataFrame(), pd.DataFrame()

# --- Scrape Buttons ---
if urls_input and st.button("Scrape Reddit Comments"):
    urls = urls_input.strip().splitlines()
    st.session_state.df = extract_comments_from_urls(urls, limit)

if box_url and st.button("Scrape Box Score"):
    st.session_state.score_df, st.session_state.players_df = scrape_bref_box_score(box_url)

# --- Display Tables ---
if not st.session_state.df.empty:
    st.subheader("Fan Comments")
    st.dataframe(st.session_state.df)
    csv = st.session_state.df.to_csv(index=False).encode("utf-8")
    st.download_button("Download Comments CSV", csv, "comments.csv", "text/csv")

if not st.session_state.score_df.empty:
    st.subheader("Team Score Summary")
    st.dataframe(st.session_state.score_df)
    score_csv = st.session_state.score_df.to_csv(index=False).encode("utf-8")
    st.download_button("Download Team Box CSV", score_csv, "box_score.csv", "text/csv")

if not st.session_state.players_df.empty:
    st.subheader("Player Stats")
    st.dataframe(st.session_state.players_df)
    players_csv = st.session_state.players_df.to_csv(index=False).encode("utf-8")
    st.download_button("Download Player Stats CSV", players_csv, "player_stats.csv", "text/csv")

# --- Generate AI Prompt ---
if st.button("Generate Prefilled AI Prompt"):
    game_context = "[Paste game summary here]"

    if not st.session_state.df.empty and all(col in st.session_state.df.columns for col in ['username', 'comment_text']):
        comments_buffer = io.StringIO()
        st.session_state.df[['username', 'comment_text']].head(5).to_csv(comments_buffer, index=False)
        comments_preview = comments_buffer.getvalue()
    else:
        comments_preview = "(No comments scraped or columns missing)"

    box_buffer = io.StringIO()
    st.session_state.score_df.to_csv(box_buffer, index=False)
    box_preview = box_buffer.getvalue() if not st.session_state.score_df.empty else "(No team scores scraped yet)"

    if not st.session_state.players_df.empty and all(col in st.session_state.players_df.columns for col in ['team', 'player', 'PTS', 'REB', 'AST']):
        players_buffer = io.StringIO()
        st.session_state.players_df[['team', 'player', 'PTS', 'REB', 'AST']].head(5).to_csv(players_buffer, index=False)
        player_preview = players_buffer.getvalue()
    else:
        player_preview = "(No player stats scraped or missing columns)"

    prompt = f"""Hi ChatGPT — you are helping a sports journalist write a fan reaction story powered by real Reddit comments and box score data. You will generate a 400–500 word article that captures the community’s sentiment, key game takeaways, and standout performances.

Here’s what you’re working with:

1. Game Context:
{game_context}

2. Fan Quotes Preview:
{comments_preview}

3. Team Box Score Preview:
{box_preview}

4. Player Stats Preview:
{player_preview}

Write an article titled:
From the Stands: [TEAM] Fans React to [EVENT or OPPONENT]

Follow this format:
- Intro paragraph: Set the emotional tone from fans. What was the vibe after the game?
- Sentiment section(s): What themes emerged? Praise, criticism, tension? Use direct fan quotes.
- Player highlights: Pull 1–2 standout stat lines from the player stats CSV and connect to what fans said.
- Game rhythm: Use the team box score to describe the momentum and any big shifts.
- Conclusion: Reflect how the fanbase feels heading into the next game or moment.

Use a casual yet editorial tone. Quote fans naturally (“One fan wrote…”). Do not fabricate anything — use only the content provided."""

    st.subheader("Generated AI Prompt")
    st.text_area("Copy this prompt into ChatGPT:", value=prompt, height=700)
