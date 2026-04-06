"""
Agent 1: Scraper/Scout — Identifies trending educational topics from YouTube, Reddit, Instagram, and X.
Uses official platform APIs when keys are available, falls back to public scraping otherwise.
Outputs a Trend Report JSON artifact.
"""
import json
import time
import re
import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from config import (
    SCRAPING_CONFIG, ARTIFACTS_DIR, FALLBACK_TRENDS,
    YOUTUBE_API_KEY, REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET,
    INSTAGRAM_ACCESS_TOKEN, X_API_BEARER_TOKEN,
)


class TrendScraperAgent:
    """Scrapes trending educational topics from multiple platforms."""

    def __init__(self, status_callback=None):
        self.status_callback = status_callback or (lambda msg: None)
        self.trends = []

    def _update_status(self, message):
        self.status_callback(message)

    # ══════════════════════════════════════════════════════════════════════════
    # Reddit
    # ══════════════════════════════════════════════════════════════════════════
    def scrape_reddit(self):
        """Scrape hot posts from educational subreddits.
        Uses OAuth API if credentials are available, else public JSON endpoint.
        """
        if REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET:
            return self._scrape_reddit_oauth()
        return self._scrape_reddit_public()

    def _get_reddit_oauth_token(self):
        """Obtain a Reddit OAuth2 application-only token."""
        reddit_config = SCRAPING_CONFIG["reddit"]
        auth = (REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET)
        data = {"grant_type": "client_credentials"}
        headers = {"User-Agent": reddit_config["headers"]["User-Agent"]}
        try:
            resp = requests.post(
                reddit_config["token_url"],
                auth=auth, data=data, headers=headers, timeout=15,
            )
            resp.raise_for_status()
            return resp.json().get("access_token")
        except Exception as e:
            self._update_status(f"⚠️ Reddit OAuth failed: {str(e)[:80]}. Falling back to public API.")
            return None

    def _scrape_reddit_oauth(self):
        """Scrape Reddit using the official OAuth API."""
        self._update_status("🔑 Using Reddit OAuth API...")
        token = self._get_reddit_oauth_token()
        if not token:
            return self._scrape_reddit_public()

        reddit_config = SCRAPING_CONFIG["reddit"]
        headers = {
            "Authorization": f"Bearer {token}",
            "User-Agent": reddit_config["headers"]["User-Agent"],
        }
        reddit_trends = []

        for subreddit in reddit_config["subreddits"]:
            self._update_status(f"🔍 Reddit OAuth: r/{subreddit}...")
            try:
                url = reddit_config["oauth_base_url"].format(subreddit=subreddit)
                params = {"limit": reddit_config["limit"], "raw_json": 1}
                response = requests.get(url, headers=headers, params=params, timeout=15)
                response.raise_for_status()
                data = response.json()
                reddit_trends.extend(self._parse_reddit_posts(data, subreddit))
                time.sleep(0.5)
            except Exception as e:
                self._update_status(f"⚠️ Reddit OAuth r/{subreddit} error: {str(e)[:80]}")
                continue

        return reddit_trends

    def _scrape_reddit_public(self):
        """Scrape Reddit using the public JSON API (no auth required)."""
        reddit_config = SCRAPING_CONFIG["reddit"]
        reddit_trends = []

        for subreddit in reddit_config["subreddits"]:
            self._update_status(f"🔍 Browsing Reddit r/{subreddit} (public)...")
            try:
                url = reddit_config["public_base_url"].format(subreddit=subreddit)
                params = {"limit": reddit_config["limit"], "raw_json": 1}
                response = requests.get(
                    url, headers=reddit_config["headers"], params=params, timeout=15,
                )
                response.raise_for_status()
                data = response.json()
                reddit_trends.extend(self._parse_reddit_posts(data, subreddit))
                time.sleep(1)
            except Exception as e:
                self._update_status(f"⚠️ Reddit r/{subreddit} scrape error: {str(e)[:80]}")
                continue

        return reddit_trends

    def _parse_reddit_posts(self, data, subreddit):
        """Parse Reddit API JSON response into trend entries."""
        trends = []
        posts = data.get("data", {}).get("children", [])
        edu_keywords = [
            "study", "learn", "exam", "test", "school", "college",
            "tutor", "homework", "grade", "class", "student",
            "math", "science", "physics", "chemistry", "biology",
            "jee", "neet", "preparation", "tips", "hack", "focus",
            "anxiety", "motivation", "online", "education",
        ]
        for post in posts:
            post_data = post.get("data", {})
            title = post_data.get("title", "")
            ups = post_data.get("ups", 0)
            permalink = post_data.get("permalink", "")
            title_lower = title.lower()
            if any(kw in title_lower for kw in edu_keywords) and ups > 20:
                trends.append({
                    "topic": title,
                    "source": f"Reddit r/{subreddit}",
                    "engagement": f"{ups:,} upvotes",
                    "engagement_score": ups,
                    "url": f"https://reddit.com{permalink}",
                    "pain_point": self._extract_pain_point(title),
                })
        return trends

    # ══════════════════════════════════════════════════════════════════════════
    # YouTube
    # ══════════════════════════════════════════════════════════════════════════
    def scrape_youtube(self):
        """Scrape YouTube for educational content.
        Uses Data API v3 if key is available, else falls back to HTML scraping.
        """
        if YOUTUBE_API_KEY:
            return self._scrape_youtube_api()
        return self._scrape_youtube_public()

    def _scrape_youtube_api(self):
        """Scrape YouTube using the official Data API v3."""
        self._update_status("🔑 Using YouTube Data API v3...")
        youtube_config = SCRAPING_CONFIG["youtube"]
        youtube_trends = []

        for query in youtube_config["search_queries"][:4]:
            self._update_status(f"🎥 YouTube API: searching '{query}'...")
            try:
                # Step 1: Search for videos
                search_params = {
                    "part": "snippet",
                    "q": query,
                    "type": "video",
                    "order": "viewCount",
                    "maxResults": 5,
                    "relevanceLanguage": "en",
                    "key": YOUTUBE_API_KEY,
                }
                search_resp = requests.get(
                    youtube_config["api_search_url"],
                    params=search_params, timeout=15,
                )
                search_resp.raise_for_status()
                search_data = search_resp.json()

                video_ids = [
                    item["id"]["videoId"]
                    for item in search_data.get("items", [])
                    if item.get("id", {}).get("videoId")
                ]

                if not video_ids:
                    continue

                # Step 2: Get video statistics
                stats_params = {
                    "part": "statistics,snippet",
                    "id": ",".join(video_ids),
                    "key": YOUTUBE_API_KEY,
                }
                stats_resp = requests.get(
                    youtube_config["api_videos_url"],
                    params=stats_params, timeout=15,
                )
                stats_resp.raise_for_status()
                stats_data = stats_resp.json()

                for item in stats_data.get("items", []):
                    title = item.get("snippet", {}).get("title", "")
                    video_id = item.get("id", "")
                    stats = item.get("statistics", {})
                    view_count = int(stats.get("viewCount", 0))

                    youtube_trends.append({
                        "topic": title,
                        "source": "YouTube Education",
                        "engagement": self._format_view_count(view_count),
                        "engagement_score": view_count,
                        "url": f"https://youtube.com/watch?v={video_id}",
                        "pain_point": self._extract_pain_point(title),
                    })

                time.sleep(0.2)
            except Exception as e:
                self._update_status(f"⚠️ YouTube API error for '{query}': {str(e)[:80]}")
                continue

        return youtube_trends

    def _scrape_youtube_public(self):
        """Scrape YouTube search results without API key (HTML parsing)."""
        youtube_config = SCRAPING_CONFIG["youtube"]
        youtube_trends = []

        for query in youtube_config["search_queries"][:3]:
            self._update_status(f"🎥 Searching YouTube for '{query}' (public)...")
            try:
                search_url = f"https://www.youtube.com/results?search_query={requests.utils.quote(query)}"
                headers = {
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Accept-Language": "en-US,en;q=0.9",
                }
                response = requests.get(search_url, headers=headers, timeout=15)
                response.raise_for_status()

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

    def _format_view_count(self, count):
        """Format a numeric view count into a readable string."""
        if count >= 1_000_000:
            return f"{count / 1_000_000:.1f}M views"
        elif count >= 1_000:
            return f"{count / 1_000:.1f}K views"
        return f"{count} views"

    # ══════════════════════════════════════════════════════════════════════════
    # Instagram
    # ══════════════════════════════════════════════════════════════════════════
    def scrape_instagram(self):
        """Scrape Instagram for educational hashtags.
        Uses Graph API if token is available, else falls back to public scraping.
        """
        if INSTAGRAM_ACCESS_TOKEN:
            return self._scrape_instagram_api()
        return self._scrape_instagram_public()

    def _scrape_instagram_api(self):
        """Scrape Instagram using the Graph API."""
        self._update_status("🔑 Using Instagram Graph API...")
        ig_config = SCRAPING_CONFIG["instagram"]
        ig_trends = []

        for hashtag in ig_config["hashtags"][:3]:
            self._update_status(f"📸 Instagram API: #{hashtag}...")
            try:
                # Step 1: Search for hashtag ID
                search_url = f"{ig_config['graph_api_url']}/ig_hashtag_search"
                search_params = {
                    "q": hashtag,
                    "access_token": INSTAGRAM_ACCESS_TOKEN,
                }
                search_resp = requests.get(search_url, params=search_params, timeout=15)
                search_resp.raise_for_status()
                hashtag_data = search_resp.json().get("data", [])

                if not hashtag_data:
                    continue

                hashtag_id = hashtag_data[0].get("id")

                # Step 2: Get top media for the hashtag
                media_url = f"{ig_config['graph_api_url']}/{hashtag_id}/top_media"
                media_params = {
                    "fields": "id,caption,like_count,comments_count,permalink",
                    "access_token": INSTAGRAM_ACCESS_TOKEN,
                }
                media_resp = requests.get(media_url, params=media_params, timeout=15)
                media_resp.raise_for_status()
                media_items = media_resp.json().get("data", [])

                for post in media_items[:3]:
                    caption = post.get("caption", "")[:100]
                    likes = post.get("like_count", 0)
                    permalink = post.get("permalink", "")

                    ig_trends.append({
                        "topic": f"#{hashtag}: {caption}" if caption else f"Trending #{hashtag} post",
                        "source": f"Instagram #{hashtag}",
                        "engagement": f"{likes:,} likes",
                        "engagement_score": likes,
                        "url": permalink or f"https://instagram.com/explore/tags/{hashtag}/",
                        "pain_point": f"Students engaging with #{hashtag} content for study motivation",
                    })

                time.sleep(0.5)
            except Exception as e:
                self._update_status(f"⚠️ Instagram API #{hashtag} error: {str(e)[:80]}")
                continue

        return ig_trends

    def _scrape_instagram_public(self):
        """Attempt to scrape Instagram hashtag pages (best-effort, often blocked)."""
        ig_config = SCRAPING_CONFIG["instagram"]
        ig_trends = []

        for hashtag in ig_config["hashtags"][:2]:
            self._update_status(f"📸 Checking Instagram #{hashtag} (public)...")
            try:
                url = ig_config["public_base_url"].format(hashtag=hashtag)
                headers = {
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                }
                response = requests.get(url, headers=headers, timeout=15)

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

    # ══════════════════════════════════════════════════════════════════════════
    # X (Twitter)
    # ══════════════════════════════════════════════════════════════════════════
    def scrape_x(self):
        """Scrape X/Twitter for educational content using the official API v2."""
        if not X_API_BEARER_TOKEN:
            self._update_status("ℹ️ X/Twitter API: No bearer token set — skipping")
            return []

        self._update_status("🔑 Using X/Twitter API v2...")
        x_config = SCRAPING_CONFIG["x"]
        x_trends = []

        for query in x_config["search_queries"][:3]:
            self._update_status(f"🐦 X API: searching '{query}'...")
            try:
                headers = {
                    "Authorization": f"Bearer {X_API_BEARER_TOKEN}",
                }
                params = {
                    "query": f"{query} -is:retweet lang:en",
                    "max_results": 10,
                    "tweet.fields": "public_metrics,created_at",
                    "sort_order": "relevancy",
                }
                response = requests.get(
                    x_config["api_search_url"],
                    headers=headers, params=params, timeout=15,
                )
                response.raise_for_status()
                data = response.json()

                for tweet in data.get("data", []):
                    text = tweet.get("text", "")[:120]
                    metrics = tweet.get("public_metrics", {})
                    likes = metrics.get("like_count", 0)
                    retweets = metrics.get("retweet_count", 0)
                    tweet_id = tweet.get("id", "")
                    total_engagement = likes + retweets

                    if total_engagement > 5:
                        x_trends.append({
                            "topic": text,
                            "source": "X (Twitter)",
                            "engagement": f"{likes} likes, {retweets} RTs",
                            "engagement_score": total_engagement,
                            "url": f"https://x.com/i/status/{tweet_id}",
                            "pain_point": self._extract_pain_point(text),
                        })

                time.sleep(1)
            except Exception as e:
                self._update_status(f"⚠️ X API error for '{query}': {str(e)[:80]}")
                continue

        return x_trends

    # ══════════════════════════════════════════════════════════════════════════
    # Helpers
    # ══════════════════════════════════════════════════════════════════════════
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

    # ══════════════════════════════════════════════════════════════════════════
    # Main Run
    # ══════════════════════════════════════════════════════════════════════════
    def run(self):
        """Execute full scraping pipeline and return trend report."""
        self._update_status("🚀 Agent 1 (Scraper/Scout) starting trend analysis...")

        all_trends = []

        # Reddit
        reddit_trends = self.scrape_reddit()
        all_trends.extend(reddit_trends)
        self._update_status(f"✅ Reddit: Found {len(reddit_trends)} relevant trends")

        # YouTube
        youtube_trends = self.scrape_youtube()
        all_trends.extend(youtube_trends)
        self._update_status(f"✅ YouTube: Found {len(youtube_trends)} relevant trends")

        # Instagram
        ig_trends = self.scrape_instagram()
        all_trends.extend(ig_trends)
        self._update_status(f"✅ Instagram: Found {len(ig_trends)} relevant trends")

        # X (Twitter)
        x_trends = self.scrape_x()
        all_trends.extend(x_trends)
        self._update_status(f"✅ X/Twitter: Found {len(x_trends)} relevant trends")

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
        sources_scraped = ["Reddit", "YouTube", "Instagram"]
        if X_API_BEARER_TOKEN:
            sources_scraped.append("X (Twitter)")

        report = {
            "report_id": f"trend_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "generated_at": datetime.now().isoformat(),
            "sources_scraped": sources_scraped,
            "total_trends": len(all_trends),
            "trends": all_trends,
        }

        # Save artifact
        report_path = os.path.join(ARTIFACTS_DIR, "trend_report.json")
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)

        self._update_status(f"✅ Agent 1 complete! Generated report with {len(all_trends)} trends.")
        return report
