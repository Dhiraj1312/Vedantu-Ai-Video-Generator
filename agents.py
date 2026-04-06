"""
Agents Module — Creative Director (Agent 2) and Orchestrator for the multi-agent pipeline.
"""
import json
import os
from datetime import datetime

from config import GEMINI_API_KEY, VEDANTU_BRAND, ARTIFACTS_DIR
from scraper import TrendScraperAgent
from video_api import VideoProducerAgent

try:
    from google import genai
except ImportError:
    genai = None


# ══════════════════════════════════════════════════════════════════════════════
# Agent 2: Creative Director
# ══════════════════════════════════════════════════════════════════════════════
class CreativeDirectorAgent:
    """Generates 15-second promotional scripts based on trend report data."""

    def __init__(self, status_callback=None):
        self.status_callback = status_callback or (lambda msg: None)
        self.brand = VEDANTU_BRAND

    def _update_status(self, message):
        self.status_callback(message)

    def _build_system_prompt(self):
        usps = "\n".join(f"  - {u}" for u in self.brand["usps"])
        ctas = "\n".join(f"  - {c}" for c in self.brand["ctas"])

        return f"""You are a world-class creative director specializing in short-form promotional video scripts for edtech companies.

BRAND: {self.brand['name']}
TAGLINE: {self.brand['tagline']}

UNIQUE SELLING PROPOSITIONS:
{usps}

AVAILABLE CTAs:
{ctas}

RULES:
1. Each script must be exactly 15 seconds when read at a natural pace.
2. Structure: HOOK (0-3s) → SOLUTION (3-12s) → CTA (12-15s)
3. The HOOK must be an attention-grabbing question or shocking statement tied to the trending topic.
4. The SOLUTION must highlight a specific Vedantu feature/USP that directly addresses the pain point.
5. The CTA must be punchy and action-oriented.
6. Tone: energetic, inspiring, youthful — speaks directly to Indian students aged 14-18.
7. Use simple, conversational English (avoid jargon).
8. Make it suitable for Instagram Reels / YouTube Shorts (vertical video, fast-paced).

OUTPUT FORMAT (JSON):
{{
  "hook": "The hook text (0-3 seconds)",
  "body": "The solution/body text (3-12 seconds)",
  "cta": "The call-to-action text (12-15 seconds)",
  "full_script": "Complete script as one flowing paragraph",
  "visual_direction": "Brief description of suggested visuals for the video",
  "target_trend": "The specific trend this addresses"
}}"""

    def _build_user_prompt(self, trend_report):
        top_trends = trend_report.get("trends", [])[:7]
        trends_text = ""
        for t in top_trends:
            trends_text += f"\n  #{t.get('rank', '?')}: {t.get('topic', 'N/A')}"
            trends_text += f"\n     Source: {t.get('source', 'N/A')} | Engagement: {t.get('engagement', 'N/A')}"
            trends_text += f"\n     Pain Point: {t.get('pain_point', 'N/A')}\n"

        return f"""Based on the following trending educational topics, create 5 DIFFERENT promotional video scripts for Vedantu.

Each script should target a different trend from the list. Pick the 5 most compelling trends.

TRENDING TOPICS:
{trends_text}

Generate exactly 5 scripts. Return a JSON array of 5 script objects."""

    def run(self, trend_report):
        """Generate 5 script variants from the trend report."""
        self._update_status("🚀 Agent 2 (Creative Director) starting script generation...")

        # Try Google Gemini first
        if GEMINI_API_KEY and genai:
            return self._generate_with_gemini(trend_report)
        else:
            self._update_status("⚠️ Gemini not available — using built-in script templates")
            return self._generate_fallback_scripts(trend_report)

    def _generate_with_gemini(self, trend_report):
        """Generate scripts using Google Gemini."""
        self._update_status("🤖 Calling Google Gemini for script generation...")
        try:
            client = genai.Client(api_key=GEMINI_API_KEY)

            combined_prompt = (
                self._build_system_prompt()
                + "\n\n---\n\n"
                + self._build_user_prompt(trend_report)
                + "\n\nIMPORTANT: Return ONLY valid JSON. Wrap the 5 scripts in a JSON object like {\"scripts\": [...]}"
            )

            response = client.models.generate_content(
                model="gemini-2.5-flash-lite",
                contents=combined_prompt,
                config={
                    "response_mime_type": "application/json",
                    "temperature": 0.8,
                    "max_output_tokens": 3500,
                },
            )

            result_text = response.text
            result = json.loads(result_text)

            # Handle both {"scripts": [...]} and direct array
            if isinstance(result, dict):
                scripts = result.get("scripts", result.get("variants", [result]))
            elif isinstance(result, list):
                scripts = result
            else:
                scripts = [result]

            # Ensure we have at least 1, at most 5
            scripts = scripts[:5] if len(scripts) > 5 else scripts

            self._save_scripts(scripts)
            self._update_status(f"✅ Agent 2 complete! Generated {len(scripts)} script variants.")
            return scripts

        except Exception as e:
            self._update_status(f"⚠️ Gemini error: {str(e)[:100]} — falling back to templates")
            return self._generate_fallback_scripts(trend_report)

    def _generate_fallback_scripts(self, trend_report):
        """Generate scripts using built-in templates (no API needed)."""
        self._update_status("📝 Generating scripts from templates...")

        trends = trend_report.get("trends", [])
        scripts = []

        templates = [
            {
                "hook": "Still studying alone at midnight, staring at your phone? 😰",
                "body": "Vedantu's WAVE classroom brings India's top teachers LIVE to your screen — with 3D models, interactive quizzes, and real-time doubt solving. It's like having a personal tutor, but 10x smarter.",
                "cta": "Download Vedantu now — your first class is FREE! 🚀",
                "visual_direction": "Split screen: student struggling alone → vibrant WAVE classroom with 3D models popping out. Fast cuts, neon accents.",
                "full_script": "Still studying alone at midnight, staring at your phone? Vedantu's WAVE classroom brings India's top teachers LIVE to your screen — with 3D models, interactive quizzes, and real-time doubt solving. It's like having a personal tutor, but 10x smarter. Download Vedantu now — your first class is FREE!",
                "target_trend": trends[0]["topic"] if trends else "Online learning trends",
            },
            {
                "hook": "What if your study app actually understood YOUR weaknesses? 🧠",
                "body": "Meet Ved — Vedantu's AI mentor that analyzes your performance, builds a personalized study roadmap, and solves your doubts instantly. Smart learning isn't the future — it's happening NOW.",
                "cta": "Try Ved AI on Vedantu — start your personalized journey today!",
                "visual_direction": "Close-up of phone screen showing AI analysis → zoom out to confident student. Gradient purple/green tones.",
                "full_script": "What if your study app actually understood YOUR weaknesses? Meet Ved — Vedantu's AI mentor that analyzes your performance, builds a personalized study roadmap, and solves your doubts instantly. Smart learning isn't the future — it's happening NOW. Try Ved AI on Vedantu — start your personalized journey today!",
                "target_trend": trends[1]["topic"] if len(trends) > 1 else "AI in education",
            },
            {
                "hook": "JEE/NEET prep costs ₹2+ lakhs at coaching centers. But what if it didn't have to? 💡",
                "body": "Vedantu gives you LIVE classes from IIT/AIIMS alumni, unlimited doubt sessions, and AI-powered test analysis — all from your home. 10 million students already made the switch.",
                "cta": "Book your FREE demo class on Vedantu NOW! 📚",
                "visual_direction": "Price comparison animation → Vedantu app showcase with teacher avatars. Bold typography, orange and green theme.",
                "full_script": "JEE/NEET prep costs 2+ lakhs at coaching centers. But what if it didn't have to? Vedantu gives you LIVE classes from IIT/AIIMS alumni, unlimited doubt sessions, and AI-powered test analysis — all from your home. 10 million students already made the switch. Book your FREE demo class on Vedantu NOW!",
                "target_trend": trends[2]["topic"] if len(trends) > 2 else "Affordable education",
            },
            {
                "hook": "Your teacher just explained it 3 times… and you STILL don't get it? 😩",
                "body": "Vedantu's 1-on-1 LIVE tutoring connects you with India's best teachers who adapt to YOUR pace. Ask unlimited doubts, get instant answers, and finally understand — not just memorize.",
                "cta": "Get your first 1-on-1 session FREE on Vedantu! 🎯",
                "visual_direction": "Frustrated student in classroom → calm, focused student on Vedantu 1-on-1 call. Warm lighting, close-up reactions.",
                "full_script": "Your teacher just explained it 3 times and you still don't get it? Vedantu's 1-on-1 LIVE tutoring connects you with India's best teachers who adapt to YOUR pace. Ask unlimited doubts, get instant answers, and finally understand — not just memorize. Get your first 1-on-1 session FREE on Vedantu!",
                "target_trend": trends[3]["topic"] if len(trends) > 3 else "Personalized tutoring",
            },
            {
                "hook": "What if studying felt like playing a game? 🎮",
                "body": "Vedantu turns boring chapters into interactive challenges — earn coins, climb leaderboards, and compete with friends while mastering Physics, Chemistry, and Math. Learning has never been this addictive.",
                "cta": "Join 10M+ students on Vedantu — Start for FREE! 🏆",
                "visual_direction": "Game-style UI transitions: XP bars filling up, leaderboard animations, student celebrating. Bright neon colors, fast beats.",
                "full_script": "What if studying felt like playing a game? Vedantu turns boring chapters into interactive challenges — earn coins, climb leaderboards, and compete with friends while mastering Physics, Chemistry, and Math. Learning has never been this addictive. Join 10M+ students on Vedantu — Start for FREE!",
                "target_trend": trends[4]["topic"] if len(trends) > 4 else "Gamification in education",
            },
        ]

        scripts = templates[:5]
        self._save_scripts(scripts)
        self._update_status(f"✅ Agent 2 complete! Generated {len(scripts)} script variants.")
        return scripts

    def _save_scripts(self, scripts):
        """Save scripts to artifact file."""
        artifact = {
            "generated_at": datetime.now().isoformat(),
            "brand": self.brand["name"],
            "num_variants": len(scripts),
            "scripts": scripts,
        }
        path = os.path.join(ARTIFACTS_DIR, "scripts.json")
        with open(path, "w") as f:
            json.dump(artifact, f, indent=2)


# ══════════════════════════════════════════════════════════════════════════════
# Agent Manager / Orchestrator
# ══════════════════════════════════════════════════════════════════════════════
class AgentOrchestrator:
    """Manages communication between all 4 agents via JSON artifacts."""

    def __init__(self):
        self.agents = {
            "scraper": {"name": "Scraper/Scout", "status": "idle", "icon": "🔍"},
            "creative": {"name": "Creative Director", "status": "idle", "icon": "✍️"},
            "ui": {"name": "Dashboard (UI)", "status": "active", "icon": "🖥️"},
            "video": {"name": "Video Producer", "status": "idle", "icon": "🎬"},
        }
        self.log = []

    def get_agent_statuses(self):
        return self.agents

    def update_agent_status(self, agent_key, status, message=""):
        if agent_key in self.agents:
            self.agents[agent_key]["status"] = status
            self.agents[agent_key]["last_message"] = message
            self.log.append({
                "timestamp": datetime.now().isoformat(),
                "agent": agent_key,
                "status": status,
                "message": message,
            })

    def run_scraper(self, status_callback=None):
        """Run Agent 1: Scraper/Scout."""
        self.update_agent_status("scraper", "running", "Starting trend analysis...")

        def wrapped_callback(msg):
            self.update_agent_status("scraper", "running", msg)
            if status_callback:
                status_callback(msg)

        agent = TrendScraperAgent(status_callback=wrapped_callback)
        result = agent.run()
        self.update_agent_status("scraper", "completed", f"Found {result['total_trends']} trends")
        return result

    def run_creative(self, trend_report, status_callback=None):
        """Run Agent 2: Creative Director."""
        self.update_agent_status("creative", "running", "Generating scripts...")

        def wrapped_callback(msg):
            self.update_agent_status("creative", "running", msg)
            if status_callback:
                status_callback(msg)

        agent = CreativeDirectorAgent(status_callback=wrapped_callback)
        result = agent.run(trend_report)
        self.update_agent_status("creative", "completed", f"Generated {len(result)} scripts")
        return result

    def run_video_producer(self, prompt, image_path=None, video_settings=None, status_callback=None):
        """Run Agent 4: Video Producer."""
        self.update_agent_status("video", "running", "Starting video generation...")

        def wrapped_callback(msg):
            self.update_agent_status("video", "running", msg)
            if status_callback:
                status_callback(msg)

        agent = VideoProducerAgent(status_callback=wrapped_callback)
        result = agent.run(prompt, image_path, video_settings=video_settings)

        if result and result.get("status") == "completed":
            self.update_agent_status("video", "completed", "Video generated successfully!")
        else:
            self.update_agent_status("video", "error", "Video generation failed")

        return result
