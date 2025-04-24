import streamlit as st
import praw
import pandas as pd
import requests
from bs4 import BeautifulSoup, Comment

# --- Streamlit UI ---
st.set_page_config(page_title="Reddit Comment + Box Score Scraper", layout="centered")
st.title("Reddit Comment + Box Score Scraper")
st.write("Paste in Reddit thread URLs and optionally a Basketball-Reference box score URL. Extract comments, team scores, player stats, and generate a structured AI prompt.")

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

        # Extract team score summary
        comments = soup.find_all(string=lambda text: isinstance(text, Comment))
        score_df = pd.DataFrame()
        for comment in comments:
            comment_soup = BeautifulSoup(comment, "html.parser")
            linescore_table = comment_soup.find("table", id="line_score")
            if linescore_table:
                rows = linescore_table.find_all("tr")
                structured_data = []
                for row in rows[1:]:
                    cells = row.find_all("td")
                    if len(cells) >= 5:
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
                score_df = pd.DataFrame(structured_data)

        # Extract player stats from box-* tables
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
    score_df, players_df = scrape_bref_box_score(box_url)
    if not score_df.empty:
        st.success("Box score extracted successfully!")
        st.subheader("Team Score Summary")
        st.dataframe(score_df)
        score_csv = score_df.to_csv(index=False).encode('utf-8')
        st.download_button("Download Team Box CSV", score_csv, "box_score.csv", "text/csv")

    if not players_df.empty:
        st.subheader("Player Stats")
        st.dataframe(players_df)
        players_csv = players_df.to_csv(index=False).encode('utf-8')
        st.download_button("Download Player Stats CSV", players_csv, "player_stats.csv", "text/csv")

    if score_df.empty and players_df.empty:
        st.warning("No box score data found or failed to parse.")

# --- Prefilled AI Prompt Template ---
st.subheader("AI Prompt Template: Generate Fan Reaction Article")
st.text_area("Copy and paste this into ChatGPT or another LLM tool:", value="""Hi ChatGPT — you are helping a sports journalist write a fan reaction story powered by real Reddit comments and box score data. You will generate a 400–500 word article that captures the community’s sentiment, key game takeaways, and standout performances.

Here’s what you’re working with:

1. Game Context:
[Paste in a short game summary or key facts — score, playoff implications, etc.]

2. Fan Quotes (CSV):
This CSV contains real top-level Reddit comments. The columns are:
- username
- comment_text
- upvotes
- thread_url
Use this to understand the fanbase’s vibe, key discussion points, emotional tone, and highlight quotes. Quote or paraphrase accurately.

3. Team Box Score (CSV):
This CSV contains quarter-by-quarter scores and final totals. The columns are:
- team, Q1, Q2, Q3, Q4, Total
Use this to support comments about momentum, scoring gaps, or how a team held or lost a lead.

4. Player Stats (CSV):
This CSV includes individual player lines from both teams. The columns include:
- team, player, and typical stat fields like PTS, REB, AST, MIN, +/-, etc.
Use this to highlight standout player performances, support fan praise or critiques, and identify statistical leaders.

Your Task:
Write an article titled:
From the Stands: [TEAM] Fans React to [EVENT or OPPONENT]

Follow this format:
- Intro paragraph: Set the emotional tone from fans. What was the vibe after the game?
- Sentiment section(s): What themes emerged? Praise, criticism, tension? Use direct fan quotes.
- Player highlights: Pull 1–2 standout stat lines from the player stats CSV and connect to what fans said.
- Game rhythm: Use the team box score to describe the momentum and any big shifts.
- Conclusion: Reflect how the fanbase feels heading into the next game or moment.

Use a casual yet editorial tone. Quote fans naturally (“One fan wrote…”). Do not fabricate anything — use only the content provided.""", height=600)
