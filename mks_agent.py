
"""
Meme‑Kernel Swarm – all‑in‑one agent v0.2  (Facebook + TikTok)
Run:
  python mks_agent.py  --gui     # Streamlit GUI
  python mks_agent.py  --cli     # Headless CLI loop
"""
import os, sys, json, uuid, datetime, asyncio, random, argparse, subprocess
from typing import List

import openai, asyncpraw, requests, hashlib
from supabase import create_client
from playwright.async_api import async_playwright

REQUIRED_ENV = ["OPENAI_KEY", "SUPABASE_URL", "SUPABASE_KEY", "CT_API_KEY"]
TABLES_SQL = {
    "raw_trends": "CREATE TABLE IF NOT EXISTS raw_trends(id SERIAL PRIMARY KEY, platform TEXT, source_id TEXT, text TEXT, meta JSONB, collected_at TIMESTAMP);",
    "kernels": "CREATE TABLE IF NOT EXISTS kernels(id UUID PRIMARY KEY, text TEXT, generation INT, created_at TIMESTAMP DEFAULT now());",
}
CT_ENDPOINT = "https://api.crowdtangle.com/posts/search"

def env_check():
    missing = [e for e in REQUIRED_ENV if not os.getenv(e)]
    if missing:
        raise EnvironmentError(f"Missing ENV vars: {', '.join(missing)}")


def init_db():
    sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
    for sql in TABLES_SQL.values():
        sb.postgrest.rpc("execute_sql", {"sql": sql}).execute()
    return sb


async def fetch_facebook(query="meme", n=20):
    params = {"token": os.getenv("CT_API_KEY"), "searchTerm": query, "sortBy": "overperforming", "count": n}
    r = requests.get(CT_ENDPOINT, params=params, timeout=30).json()
    rows = []
    for p in r.get("result", {}).get("posts", []):
        rows.append({
            "platform": "facebook",
            "source_id": p["id"],
            "text": p.get("message", "")[:500],
            "meta": {"actual": p.get("statistics", {}).get("actual", {})},
        })
    return rows


async def fetch_reddit(reddit, sub="memes", n=20):
    sr = await reddit.subreddit(sub)
    out = []
    async for p in sr.hot(limit=n):
        out.append({"platform": "reddit", "source_id": p.id, "text": p.title + "\n" + (p.selftext or ""), "meta": {"score": p.score}})
    return out


async def fetch_tiktok(tag="viral", n=10):
    ua_list = ["Mozilla/5.0 (Windows NT 10.0; Win64; x64)", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"]
    rows = []
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(user_agent=random.choice(ua_list))
        await pg.goto(f"https://www.tiktok.com/tag/{tag}")
        await pg.wait_for_selector("div[data-e2e=top-video]", timeout=20000)
        # Scroll to load more
        for _ in range(3):
            await pg.mouse.wheel(0, 2000)
            await asyncio.sleep(1)
        vids = await pg.query_selector_all("div[data-e2e=top-video]")
        for v in vids[:n]:
            cap = await v.query_selector_eval("a div", "el=>el.innerText")
            vid_id = await v.get_attribute("data-id") or hashlib.md5(cap.encode()).hexdigest()
            rows.append({"platform": "tiktok", "source_id": vid_id, "text": cap, "meta": {}})
        await b.close()
    return rows


async def ingest_all(sb, fb_query, reddit_sub, tiktok_tag):
    reddit = asyncpraw.Reddit(client_id=os.getenv("REDDIT_ID"), client_secret=os.getenv("REDDIT_SECRET"), user_agent="mks_agent")
    fb, rd, tt = await asyncio.gather(fetch_facebook(fb_query), fetch_reddit(reddit, reddit_sub), fetch_tiktok(tiktok_tag))
    rows = []
    now = datetime.datetime.utcnow().isoformat()
    for src in [fb, rd, tt]:
        for r in src:
            r["collected_at"] = now
            rows.append(r)
    if rows:
        sb.table("raw_trends").insert(rows).execute()
    return len(rows)


async def generate_kernels(sb, k=20):
    openai.api_key = os.getenv("OPENAI_KEY")
    rec = sb.table("raw_trends").select("text").order("collected_at", desc=True).limit(50).execute().data
    texts = [r["text"] for r in rec]
    kernels = []
    for p in random.sample(texts, min(len(texts), k)):
        res = openai.ChatCompletion.create(model="gpt-4o-mini", messages=[{"role": "system", "content": "You are a meme copywriter."}, {"role": "user", "content": f"Write a 120‑char meme caption inspired by:\n{p}"}], max_tokens=40)
        kernels.append({"id": str(uuid.uuid4()), "text": res.choices[0].message.content.strip(), "generation": 0})
    if kernels:
        sb.table("kernels").insert(kernels).execute()
    return len(kernels)


async def run_loop(args):
    env_check()
    sb = init_db()
    print("MKS Agent running... Ctrl+C to exit.")
    while True:
        ing = await ingest_all(sb, args.fb_query, args.reddit_sub, args.tiktok_tag)
        gen = await generate_kernels(sb, args.kernel_batch)
        print(f"Cycle complete → Ingested {ing}, Generated {gen}. Sleeping {args.loop_minutes} min.")
        await asyncio.sleep(args.loop_minutes * 60)


def run_gui():
    try:
        import streamlit as st
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "streamlit"])
        import streamlit as st

    st.title("🌀 Meme‑Kernel Swarm Agent")
    fb_q = st.text_input("Facebook search term", "meme")
    reddit_sub = st.text_input("Reddit subreddit", "memes")
    tiktok_tag = st.text_input("TikTok tag", "viral")
    batch = st.slider("Kernels per cycle", 5, 50, 20)
    loop_min = st.slider("Loop interval (min)", 1, 60, 10)
    if st.button("🚀 Launch Loop"):
        st.success("Agent running in background – see terminal logs.")
        asyncio.run(run_loop(argparse.Namespace(fb_query=fb_q, reddit_sub=reddit_sub, tiktok_tag=tiktok_tag, kernel_batch=batch, loop_minutes=loop_min)))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--gui", action="store_true")
    parser.add_argument("--fb_query", default="meme")
    parser.add_argument("--reddit_sub", default="memes")
    parser.add_argument("--tiktok_tag", default="viral")
    parser.add_argument("--kernel_batch", type=int, default=20)
    parser.add_argument("--loop_minutes", type=int, default=10)
    args = parser.parse_args()
    if args.gui:
        run_gui()
    else:
        asyncio.run(run_loop(args))


if __name__ == "__main__":
    main()
