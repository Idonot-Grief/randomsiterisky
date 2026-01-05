import random
import time
from urllib.parse import urlparse

from flask import Flask, redirect, render_template_string, session
import aiohttp
import asyncio
import nest_asyncio

# ---------------- CONFIG ----------------
DOMAIN_FILE = "./servers.csv"
NSFW_WORDLIST_URL = (
    "https://raw.githubusercontent.com/LDNOOBW/"
    "List-of-Dirty-Naughty-Obscene-and-Otherwise-Bad-Words/master/en"
)

RESET_INTERVAL = 600  # 10 minutes
MAX_RETRIES = 50
REDIRECT_DELAY = 5  # seconds before redirect

# --------------------------------------

nest_asyncio.apply()
app = Flask(__name__)
app.secret_key = "random-website-secret-key-change-me"

nsfw_words = set()


# ---------- Helpers ----------

async def load_nsfw_words():
    global nsfw_words
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(NSFW_WORDLIST_URL, timeout=10) as r:
                text = await r.text()
        nsfw_words = {w.strip().lower() for w in text.splitlines() if w.strip()}
        print(f"[✓] Loaded {len(nsfw_words)} NSFW words")
    except Exception as e:
        print("[!] NSFW list failed:", e)
        nsfw_words = set()


def is_nsfw(domain):
    d = domain.lower()
    return any(bad in d for bad in nsfw_words)


def pick_random_domain():
    for _ in range(MAX_RETRIES):
        with open(DOMAIN_FILE, "r", encoding="utf-8", errors="ignore") as f:
            line = random.choice(f.readlines()).strip()
        if "," in line:
            line = line.split(",", 1)[1]
        if line and not is_nsfw(line):
            return line
    return None


def get_session_domain(reset=False):
    now = time.time()
    if (
        reset
        or "domain" not in session
        or now - session.get("timestamp", 0) > RESET_INTERVAL
    ):
        domain = pick_random_domain()
        session["domain"] = domain
        session["timestamp"] = now
    return session["domain"]


# ---------- Routes ----------

@app.route("/")
def index():
    # Remove preview; button just goes to /go
    return render_template_string("""
<!doctype html>
<html>
<head>
<title>Random Website Portal</title>
<style>
body {
    margin:0;
    height:100vh;
    background: radial-gradient(circle,#1a2a6c,#b21f1f,#fdbb2d);
    display:flex;
    justify-content:center;
    align-items:center;
    font-family:sans-serif;
    animation: glow 15s infinite alternate;
}
@keyframes glow {
    from { filter:hue-rotate(0deg); }
    to { filter:hue-rotate(360deg); }
}
button {
    padding:32px 64px;
    font-size:24px;
    border:none;
    border-radius:30px;
    cursor:pointer;
    background: linear-gradient(45deg,#00f2fe,#4facfe);
    color:white;
    transition: transform .2s;
}
button:hover { transform: scale(1.15); }
</style>
</head>
<body>
<form action="/go">
<button>Go to a random website 🌐</button>
</form>
</body>
</html>
""")


@app.route("/go")
def go():
    domain = get_session_domain(reset=True)
    if not domain:
        return "No valid domain found", 500

    if not urlparse(domain).scheme:
        domain_url = "http://" + domain
    else:
        domain_url = domain

    # Show redirect page with countdown
    return render_template_string("""
<!doctype html>
<html>
<head>
<title>Redirecting...</title>
<meta http-equiv="refresh" content="{{delay}};url={{url}}">
<style>
body {
    margin:0;
    height:100vh;
    background: linear-gradient(45deg,#ff6ec4,#7873f5,#42e695,#3bb2b8);
    display:flex;
    justify-content:center;
    align-items:center;
    font-family:sans-serif;
    color:white;
    text-align:center;
}
h1 { font-size:32px; margin-bottom:16px; }
p { font-size:20px; }
</style>
</head>
<body>
<h1>Redirecting...</h1>
<p>You will be sent to <strong>{{url_display}}</strong> in {{delay}} seconds.</p>
</body>
</html>
""", url=domain_url, url_display=domain, delay=REDIRECT_DELAY)


# ---------- Start ----------

if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(load_nsfw_words())
    app.run(host="0.0.0.0", port=5000, threaded=True)
