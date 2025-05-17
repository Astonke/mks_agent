# Meme‑Kernel Swarm – Simple User Guide

## What the Tool Does
* **Listens**: Pulls trending posts from Facebook public pages, TikTok hashtags, and Reddit subreddits every few minutes.
* **Thinks**: Uses OpenAI GPT‑4o‑mini to turn those trends into punchy 120‑character meme kernels.
* **Learns** (coming next): Measures engagement, mutates the winners, and repeats.
* **Posts** (next milestone): Automatically publishes the kernels back to your Facebook Page and TikTok account, then pings your CRM webhook for fresh leads.

## Quick Setup (5 Steps)
1. **Create/collect API keys**
   * OpenAI **`OPENAI_KEY`**
   * CrowdTangle (Facebook) **`CT_API_KEY`**
   * Supabase **`SUPABASE_URL`** & **`SUPABASE_KEY`**
   * Reddit **`REDDIT_ID`** & **`REDDIT_SECRET`** (free script app)
2. **Copy keys into `program.config`** (see next file).
3. `pip install -r requirements.txt` (Python 3.9+).
4. Run **GUI mode**: `python mks_agent.py --gui`  → browser dashboard opens.
5. Press **🚀 Launch Loop** – the terminal shows ingestion / generation cycles.

## Streamlit Controls
| Control | What it Tweaks |
|---------|----------------|
| Facebook search term | Keywords CrowdTangle scans for viral posts |
| Reddit subreddit | Sub where memes are sourced |
| TikTok tag | Hashtag page to scrape |
| Kernels per cycle | How many meme captions GPT generates each loop |
| Loop interval (min) | Wait time between each full cycle |

## CLI Mode (power users)
```
python mks_agent.py --cli \
  --fb_query="funny" \
  --reddit_sub="dankmemes" \
  --tiktok_tag="trending" \
  --kernel_batch=30 \
  --loop_minutes=5
```

## What’s Next
* **Automatic posting** – fill in your `FB_PAGE_ID` & `PAGE_ACCESS_TOKEN`, plus TikTok upload creds.
* **Lead capture** – point `LEAD_WEBHOOK_URL` in `program.config` to your CRM endpoint.
