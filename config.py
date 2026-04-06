"""
Configuration & Constants for Vedantu Multi-Agent Marketing System

API keys are read via:
  1. Streamlit Cloud Secrets  (st.secrets)  — production
  2. Environment variables     (os.getenv)   — local dev (.env file)
Neither source is committed to version control.
"""
import os
from dotenv import load_dotenv

load_dotenv()


# ── Helper: read a secret from Streamlit Cloud first, then env var ────────────
def _get_secret(key: str, default: str = "") -> str:
    """Return a secret, checking Streamlit Cloud secrets first, then env."""
    try:
        import streamlit as st
        val = st.secrets.get(key, None)
        if val:
            return str(val)
    except Exception:
        pass
    return os.getenv(key, default)


# ── API Keys ──────────────────────────────────────────────────────────────────
# Video generation
PIAPI_API_KEY = _get_secret("PIAPI_API_KEY")

# Script generation
GEMINI_API_KEY = _get_secret("GEMINI_API_KEY")

# Platform scraping (official APIs)
YOUTUBE_API_KEY = _get_secret("YOUTUBE_API_KEY")
REDDIT_CLIENT_ID = _get_secret("REDDIT_CLIENT_ID")
REDDIT_CLIENT_SECRET = _get_secret("REDDIT_CLIENT_SECRET")
INSTAGRAM_ACCESS_TOKEN = _get_secret("INSTAGRAM_ACCESS_TOKEN")
X_API_BEARER_TOKEN = _get_secret("X_API_BEARER_TOKEN")

# ── PiAPI / Seedance 2.0 ─────────────────────────────────────────────────────
PIAPI_BASE_URL = "https://api.piapi.ai/api/v1"
PIAPI_TASK_ENDPOINT = f"{PIAPI_BASE_URL}/task"
SEEDANCE_MODEL = "seedance-2-fast-preview"

VIDEO_DURATION_DEFAULT = 5
VIDEO_DURATION_OPTIONS = [5, 10, 15]
VIDEO_ASPECT_RATIO_DEFAULT = "9:16"
VIDEO_ASPECT_RATIO_OPTIONS = ["9:16", "16:9", "1:1", "4:3", "3:4"]
VIDEO_QUALITY_DEFAULT = "fast"
VIDEO_QUALITY_OPTIONS = ["fast", "standard"]
POLL_INTERVAL = 10        # seconds between status checks
MAX_POLL_ATTEMPTS = 60    # ~10 min max wait

# ── Vedantu Brand ─────────────────────────────────────────────────────────────
VEDANTU_BRAND = {
    "name": "Vedantu",
    "tagline": "India's Leading LIVE Online Tutoring Company",
    "colors": {
        "primary": "#4CAF50",       # Green
        "secondary": "#FF9800",     # Orange
        "accent": "#2196F3",        # Blue
        "dark": "#1a1a2e",          # Dark background
        "dark_card": "#16213e",     # Card background
        "dark_surface": "#0f3460",  # Surface
        "text": "#e8e8e8",          # Light text
        "text_muted": "#a0a0b0",    # Muted text
    },
    "usps": [
        "WAVE 2.0 Interactive Classroom — 3D models, hotspots, drag-and-drop learning",
        "Ved AI Personal Mentor — Tailored guidance, doubt-solving, learning roadmaps",
        "Live 1-on-1 Personalized Tutoring with India's top teachers",
        "JEE & NEET Exam Preparation with proven results",
        "Real-time engagement tracking with AI-powered attention analytics",
        "Works on 40% less bandwidth — accessible anywhere in India",
        "Post-class reports & analytics for parents and students",
        "Gamified learning with quizzes, leaderboards, and AR filters",
    ],
    "ctas": [
        "Download Vedantu now and start learning LIVE!",
        "Book your FREE demo class today on Vedantu!",
        "Join 10M+ students on Vedantu — Start for FREE!",
        "Try Vedantu's WAVE classroom — experience the future of learning!",
    ],
}

# ── Scraping Targets ──────────────────────────────────────────────────────────
SCRAPING_CONFIG = {
    "reddit": {
        "subreddits": ["studytips", "learning", "GetStudying", "Indian_Academia"],
        # Public JSON fallback URL (used when Reddit OAuth creds are absent)
        "public_base_url": "https://www.reddit.com/r/{subreddit}/hot.json",
        # Official OAuth endpoint (used when REDDIT_CLIENT_ID is available)
        "oauth_base_url": "https://oauth.reddit.com/r/{subreddit}/hot",
        "token_url": "https://www.reddit.com/api/v1/access_token",
        "limit": 15,
        "headers": {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) VedantuTrendBot/1.0"
        },
    },
    "youtube": {
        "search_queries": [
            "study tips 2026",
            "how to study effectively",
            "JEE preparation tips",
            "NEET strategy 2026",
            "online learning hacks",
            "exam anxiety help students",
        ],
        # Official YouTube Data API v3
        "api_search_url": "https://www.googleapis.com/youtube/v3/search",
        "api_videos_url": "https://www.googleapis.com/youtube/v3/videos",
        # Public fallback (scraping, no API key needed)
        "trending_url": "https://www.youtube.com/feed/trending?bp=4gIKEgJJQhIFCAEYAQ%3D%3D",
    },
    "instagram": {
        "hashtags": ["edtech", "studyhacks", "onlinelearning", "studymotivation", "jee2026", "neet2026"],
        # Instagram Graph API
        "graph_api_url": "https://graph.facebook.com/v19.0",
        # Public fallback
        "public_base_url": "https://www.instagram.com/explore/tags/{hashtag}/",
    },
    "x": {
        "search_queries": [
            "edtech India",
            "online tutoring",
            "JEE NEET preparation",
            "study motivation",
        ],
        "api_search_url": "https://api.x.com/2/tweets/search/recent",
    },
}

# ── Artifacts Directory ───────────────────────────────────────────────────────
ARTIFACTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "artifacts")
os.makedirs(ARTIFACTS_DIR, exist_ok=True)

# ── Fallback Seed Data ────────────────────────────────────────────────────────
FALLBACK_TRENDS = [
    {
        "rank": 1,
        "topic": "AI-Powered Study Tools Are Replacing Traditional Tutoring",
        "source": "Reddit r/studytips",
        "engagement": "2.4K upvotes",
        "pain_point": "Students struggle to find affordable personalized tutoring",
        "url": "https://reddit.com/r/studytips",
    },
    {
        "rank": 2,
        "topic": "How to Beat Exam Anxiety — The Pomodoro + Active Recall Method",
        "source": "YouTube Trending",
        "engagement": "1.2M views",
        "pain_point": "Exam anxiety and ineffective study methods",
        "url": "https://youtube.com",
    },
    {
        "rank": 3,
        "topic": "JEE 2026 Preparation Strategy — Top Ranker's Routine",
        "source": "YouTube Education",
        "engagement": "850K views",
        "pain_point": "Students need proven JEE/NEET strategy from toppers",
        "url": "https://youtube.com",
    },
    {
        "rank": 4,
        "topic": "Why Students Are Moving from Offline to Online Classes",
        "source": "Instagram #edtech",
        "engagement": "45K likes",
        "pain_point": "Accessibility and quality gap between urban/rural education",
        "url": "https://instagram.com",
    },
    {
        "rank": 5,
        "topic": "5 Study Hacks That Actually Work (Backed by Science)",
        "source": "Reddit r/GetStudying",
        "engagement": "3.1K upvotes",
        "pain_point": "Students want evidence-based study techniques",
        "url": "https://reddit.com/r/GetStudying",
    },
    {
        "rank": 6,
        "topic": "Interactive Learning > Passive Video Lectures",
        "source": "Reddit r/learning",
        "engagement": "1.8K upvotes",
        "pain_point": "Passive video-watching doesn't lead to retention",
        "url": "https://reddit.com/r/learning",
    },
    {
        "rank": 7,
        "topic": "How to Learn Math Faster with Visual Tools",
        "source": "YouTube Education",
        "engagement": "620K views",
        "pain_point": "Math is the most feared subject — visual tools help",
        "url": "https://youtube.com",
    },
    {
        "rank": 8,
        "topic": "NEET Bio Mnemonics Challenge — Going Viral",
        "source": "Instagram #neet2026",
        "engagement": "78K likes",
        "pain_point": "Biology memorization is overwhelming for NEET aspirants",
        "url": "https://instagram.com",
    },
    {
        "rank": 9,
        "topic": "Parents Are Tracking Kids' Study Progress Online Now",
        "source": "Reddit r/Indian_Academia",
        "engagement": "950 upvotes",
        "pain_point": "Parents need visibility into children's learning progress",
        "url": "https://reddit.com/r/Indian_Academia",
    },
    {
        "rank": 10,
        "topic": "Gamification in Education — Duolingo Effect for All Subjects",
        "source": "YouTube Trending",
        "engagement": "2.1M views",
        "pain_point": "Students lose motivation without gamified engagement",
        "url": "https://youtube.com",
    },
]
