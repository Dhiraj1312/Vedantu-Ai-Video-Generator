"""
Agent 1: Scraper/Scout — Identifies trending educational topics from YouTube, Reddit, Instagram.
Outputs a Trend Report JSON artifact.
"""
import json
import time
import re
import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from config import SCRAPING_CONFIG, ARTIFACTS_DIR, FALLBACK_TRENDS


class TrendScraperAgent:
    """Scrapes trending educational topics from multiple platforms."""

    def __init__(self, status_callback=None):
        self.status_callback = status_callback or (lambda msg: None)
        self.trends = []

    def _update_status(self, message):
        self.status_callback(message)

    # ── Reddit Scraping ───────────────────────────────────────────────────────
    def scrape_reddit(self):
        """Scrape hot posts from educational subreddits using Reddit's JSON API."""
        reddit_config = SCRAPING_CONFIG["reddit"]
        reddit_trends = []

        for subreddit in reddit_config["subreddits"]:
            self._update_status(f"🔍 Browsing Reddit r/{subreddit}...")
            try:
                url = reddit_config["base_url"].format(subreddit=subreddit)
                params = {"limit": reddit_config["limit"], "raw_json": 1}
                response = requests.get(
                    url,
                    headers=reddit_config["headers"],
                    params=params,
                    timeout=15,
                )
                response.raise_for_status()
                data = response.json()

                posts = data.get("data", {}).get("children", [])
                for post in posts:
                    post_data = post.get("data", {})
                    title = post_data.get("title", "")
                    ups = post_data.get("ups", 0)
                    permalink = post_data.get("permalink", "")

                    # Filter for education-related content
                    edu_keywords = [
                        "study", "learn", "exam", "test", "school", "college",
                        "tutor", "homework", "grade", "class", "student",
                        "math", "science", "physics", "chemistry", "biology",
                        "jee", "neet", "preparation", "tips", "hack", "focus",
                        "anxiety", "motivation", "online", "education",
                    ]
                    title_lower = title.lower()
                    if any(kw in title_lower for kw in edu_keywords) and ups > 20:
                        reddit_trends.append({
                            "topic": title,
                            "source": f"Reddit r/{subreddit}",
                            "engagement": f"{ups:,} upvotes",
                            "engagement_score": ups,
                            "url": f"https://reddit.com{permalink}",
                            "pain_point": self._extract_pain_point(title),
                        })

                time.sleep(1)  # rate limit
            except Exception as e:
                self._update_status(f"⚠️ Reddit r/{subreddit} scrape error: {str(e)[:80]}")
                continue

        return reddit_trends

    # ── YouTube Scraping ──────────────────────────────────────────────────────
    def scrape_youtube(self):
        """Scrape YouTube search results for educational content."""
        youtube_config = SCRAPING_CONFIG["youtube"]
        youtube_trends = []

        for query in youtube_config["search_queries"][:3]:  # limit queries for speed
            self._update_status(f"🎥 Searching YouTube for '{query}'...")
            try:
                search_url = f"https://www.youtube.com/results?search_query={requests.utils.quote(query)}"
                headers = {
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Accept-Language": "en-US,en;q=0.9",
                }
                response = requests.get(search_url, headers=headers, timeout=15)
                response.raise_for_status()

                # Extract initial data JSON from YouTube page
                matches = re.findall(
                    r"var ytInitialData = ({.*?});</script>", response.text
                )
                if matches:
                    yt_data = json.loads(matches[0])
                    contents = (
                        yt_data.get("contents", {})
                        .get("twoColumnSearchResultsRenderer", {})
                        .get("primaryContents", {})
                        .get("sectionListRenderer", {})
                        .get("contents", [{}])[0]
                        .get("itemSectionRenderer", {})
                        .get("contents", [])
                    )

                    for item in contents[:5]:
                        video = item.get("videoRenderer", {})
                        if video:
                            title = video.get("title", {}).get("runs", [{}])[0].get("text", "")
                            view_text = video.get("viewCountText", {}).get("simpleText", "0 views")
                            video_id = video.get("videoId", "")

                            # Parse view count
                            view_num = self._parse_view_count(view_text)

                            youtube_trends.append({
                                "topic": title,
                                "source": "YouTube Education",
                                "engagement": view_text,
                                "engagement_score": view_num,
                                "url": f"https://youtube.com/watch?v={video_id}",
                                "pain_point": self._extract_pain_point(title),
                            })

                time.sleep(1.5)
            except Exception as e:
                self._update_status(f"⚠️ YouTube scrape error for '{query}': {str(e)[:80]}")
                continue

        return youtube_trends

    # ── Instagram Scraping ────────────────────────────────────────────────────
    def scrape_instagram(self):
        """Attempt to scrape Instagram hashtag pages (best-effort, often blocked)."""
        ig_config = SCRAPING_CONFIG["instagram"]
        ig_trends = []

        for hashtag in ig_config["hashtags"][:2]:  # limit for MVP
            self._update_status(f"📸 Checking Instagram #{hashtag}...")
            try:
                url = ig_config["base_url"].format(hashtag=hashtag)
                headers = {
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                }
                response = requests.get(url, headers=headers, timeout=15)

                # Instagram heavily blocks non-authenticated scraping
                # Best-effort: try to find any embedded JSON data
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, "html.parser")
                    meta_desc = soup.find("meta", {"name": "description"})
                    if meta_desc:
                        content = meta_desc.get("content", "")
                        ig_trends.append({
                            "topic": f"Trending #{hashtag} — {content[:100]}",
                            "source": f"Instagram #{hashtag}",
                            "engagement": "Trending hashtag",
                            "engagement_score": 500,
                            "url": url,
                            "pain_point": f"Students engaging with #{hashtag} content for study motivation",
                        })
                else:
                    self._update_status(f"⚠️ Instagram #{hashtag}: blocked (status {response.status_code})")

                time.sleep(2)
            except Exception as e:
                self._update_status(f"⚠️ Instagram #{hashtag} error: {str(e)[:80]}")
                continue

        return ig_trends

    # ── Helpers ───────────────────────────────────────────────────────────────
    def _parse_view_count(self, text):
        """Parse YouTube view count text to integer."""
        text = text.replace(",", "").replace(" views", "").strip()
        multipliers = {"K": 1_000, "M": 1_000_000, "B": 1_000_000_000}
        for suffix, mult in multipliers.items():
            if text.upper().endswith(suffix):
                try:
                    return int(float(text[:-1]) * mult)
                except ValueError:
                    return 0
        try:
            return int(text)
        except ValueError:
            return 0

    def _extract_pain_point(self, title):
        """Derive a student pain point from a topic title."""
        pain_map = {
            "anxiety": "Students struggle with exam stress and anxiety",
            "focus": "Maintaining concentration during study sessions is hard",
            "motivation": "Students lack motivation to study consistently",
            "math": "Math concepts are difficult without visual/interactive tools",
            "jee": "JEE aspirants need structured preparation strategy",
            "neet": "NEET aspirants need efficient biology/chemistry revision",
            "study tips": "Students want proven, effective study techniques",
            "online": "Quality online learning is hard to find and expensive",
            "tutor": "Personalized tutoring is expensive and inaccessible",
            "hack": "Students want shortcuts to study more efficiently",
        }
        title_lower = title.lower()
        for keyword, pain in pain_map.items():
            if keyword in title_lower:
                return pain
        return "Students need better, more accessible educational resources"

    # ── Main Run ──────────────────────────────────────────────────────────────
    def run(self):
        """Execute full scraping pipeline and return trend report."""
        self._update_status("🚀 Agent 1 (Scraper/Scout) starting trend analysis...")

        # Scrape all sources
        all_trends = []

        reddit_trends = self.scrape_reddit()
        all_trends.extend(reddit_trends)
        self._update_status(f"✅ Reddit: Found {len(reddit_trends)} relevant trends")

        youtube_trends = self.scrape_youtube()
        all_trends.extend(youtube_trends)
        self._update_status(f"✅ YouTube: Found {len(youtube_trends)} relevant trends")

        ig_trends = self.scrape_instagram()
        all_trends.extend(ig_trends)
        self._update_status(f"✅ Instagram: Found {len(ig_trends)} relevant trends")

        # Use fallback if insufficient results
        if len(all_trends) < 3:
            self._update_status("⚡ Using enriched fallback data (scraping returned limited results)")
            all_trends = FALLBACK_TRENDS
        else:
            # Sort by engagement and take top 10
            all_trends.sort(key=lambda x: x.get("engagement_score", 0), reverse=True)
            all_trends = all_trends[:10]

        # Add rankings
        for i, trend in enumerate(all_trends):
            trend["rank"] = i + 1

        # Build the report
        report = {
            "report_id": f"trend_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "generated_at": datetime.now().isoformat(),
            "sources_scraped": ["Reddit", "YouTube", "Instagram"],
            "total_trends": len(all_trends),
            "trends": all_trends,
        }

        # Save artifact
        report_path = os.path.join(ARTIFACTS_DIR, "trend_report.json")
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)

        self._update_status(f"✅ Agent 1 complete! Generated report with {len(all_trends)} trends.")
        return report
