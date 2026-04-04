"""
Agent 4: Video Producer — Seedance 2.0 API wrapper for text-to-video and image-to-video generation.
"""
import os
import time
import base64
import requests
from config import (
    MUAPI_API_KEY,
    SEEDANCE_T2V_ENDPOINT,
    SEEDANCE_I2V_ENDPOINT,
    SEEDANCE_RESULT_ENDPOINT,
    VIDEO_DURATION_DEFAULT,
    VIDEO_ASPECT_RATIO_DEFAULT,
    VIDEO_QUALITY_DEFAULT,
    POLL_INTERVAL,
    MAX_POLL_ATTEMPTS,
    ARTIFACTS_DIR,
)


class VideoProducerAgent:
    """Generates promotional videos using Seedance 2.0 API."""

    def __init__(self, status_callback=None):
        self.status_callback = status_callback or (lambda msg: None)
        self.headers = {
            "x-api-key": MUAPI_API_KEY,
            "Content-Type": "application/json",
        }
        # Defaults — overridden by video_settings in run()
        self.duration = VIDEO_DURATION_DEFAULT
        self.aspect_ratio = VIDEO_ASPECT_RATIO_DEFAULT
        self.quality = VIDEO_QUALITY_DEFAULT

    def _update_status(self, message):
        self.status_callback(message)

    def _image_to_data_url(self, image_path):
        """Convert a local image file to a base64 data URL."""
        with open(image_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode("utf-8")
        # Detect format
        ext = os.path.splitext(image_path)[1].lower()
        mime_map = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}
        mime = mime_map.get(ext, "image/png")
        return f"data:{mime};base64,{image_data}"

    def _upload_image_and_get_url(self, image_path):
        """
        For MVP, we'll convert the image to base64 and pass it directly.
        In production, you'd upload to a CDN and get a public URL.
        """
        return self._image_to_data_url(image_path)

    # ── Text-to-Video ─────────────────────────────────────────────────────────
    def generate_t2v(self, prompt):
        """Generate a video from text prompt using Seedance 2.0 T2V."""
        self._update_status("🎬 Agent 4: Submitting text-to-video request...")

        if not MUAPI_API_KEY:
            self._update_status("❌ Error: MUAPI_API_KEY not set in environment")
            return None

        payload = {
            "prompt": prompt,
            "duration": self.duration,
            "aspect_ratio": self.aspect_ratio,
        }

        try:
            response = requests.post(
                SEEDANCE_T2V_ENDPOINT,
                json=payload,
                headers=self.headers,
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()
            request_id = data.get("request_id")

            if not request_id:
                self._update_status(f"❌ No request_id in response: {data}")
                return None

            self._update_status(f"📡 Task submitted (ID: {request_id}). Polling for results...")
            return self._poll_for_result(request_id)

        except requests.exceptions.RequestException as e:
            self._update_status(f"❌ API request failed: {str(e)[:100]}")
            return None

    # ── Image-to-Video ────────────────────────────────────────────────────────
    def generate_i2v(self, prompt, image_path):
        """Generate a video from text prompt + reference image using Seedance 2.0 I2V."""
        self._update_status("🖼️ Agent 4: Submitting image-to-video request...")

        if not MUAPI_API_KEY:
            self._update_status("❌ Error: MUAPI_API_KEY not set in environment")
            return None

        # Convert image to base64 data URL
        try:
            image_data_url = self._image_to_data_url(image_path)
        except Exception as e:
            self._update_status(f"❌ Failed to process image: {str(e)[:100]}")
            return None

        payload = {
            "prompt": prompt,
            "image_url": image_data_url,
            "duration": self.duration,
            "aspect_ratio": self.aspect_ratio,
        }

        try:
            response = requests.post(
                SEEDANCE_I2V_ENDPOINT,
                json=payload,
                headers=self.headers,
                timeout=60,
            )
            response.raise_for_status()
            data = response.json()
            request_id = data.get("request_id")

            if not request_id:
                self._update_status(f"❌ No request_id in response: {data}")
                return None

            self._update_status(f"📡 I2V task submitted (ID: {request_id}). Polling...")
            return self._poll_for_result(request_id)

        except requests.exceptions.RequestException as e:
            self._update_status(f"❌ I2V API request failed: {str(e)[:100]}")
            return None

    # ── Polling ───────────────────────────────────────────────────────────────
    def _poll_for_result(self, request_id):
        """Poll the Seedance API for video generation result."""
        result_url = f"{SEEDANCE_RESULT_ENDPOINT}/{request_id}/result"

        for attempt in range(1, MAX_POLL_ATTEMPTS + 1):
            try:
                res = requests.get(result_url, headers=self.headers, timeout=15)
                result_data = res.json()

                status = result_data.get("data", {}).get("status", "unknown")
                self._update_status(f"⏳ Polling ({attempt}/{MAX_POLL_ATTEMPTS}): Status = {status}")

                if status == "completed":
                    output = result_data.get("data", {}).get("output", [])
                    if output:
                        video_url = output[0]
                        self._update_status(f"✅ Video generated successfully!")

                        # Download video
                        local_path = self._download_video(video_url)
                        return {
                            "status": "completed",
                            "video_url": video_url,
                            "local_path": local_path,
                            "request_id": request_id,
                        }
                    else:
                        self._update_status("❌ Completed but no output URL found")
                        return None

                elif status == "failed":
                    error = result_data.get("data", {}).get("error", "Unknown error")
                    self._update_status(f"❌ Video generation failed: {error}")
                    return None

            except Exception as e:
                self._update_status(f"⚠️ Poll error: {str(e)[:80]}")

            time.sleep(POLL_INTERVAL)

        self._update_status("❌ Timed out waiting for video generation")
        return None

    # ── Download ──────────────────────────────────────────────────────────────
    def _download_video(self, video_url):
        """Download the generated video to local artifacts directory."""
        self._update_status("📥 Downloading generated video...")
        try:
            response = requests.get(video_url, stream=True, timeout=120)
            response.raise_for_status()

            local_path = os.path.join(ARTIFACTS_DIR, "output_video.mp4")
            with open(local_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            self._update_status(f"✅ Video saved to {local_path}")
            return local_path
        except Exception as e:
            self._update_status(f"⚠️ Download failed: {str(e)[:100]}")
            return None

    # ── Main Run ──────────────────────────────────────────────────────────────
    def run(self, prompt, image_path=None, video_settings=None):
        """
        Generate a promotional video.
        Uses I2V if image_path is provided, otherwise T2V.
        video_settings: dict with optional keys 'duration', 'aspect_ratio', 'quality'
        """
        self._update_status("🚀 Agent 4 (Video Producer) starting...")

        # Apply custom settings
        if video_settings:
            self.duration = video_settings.get("duration", self.duration)
            self.aspect_ratio = video_settings.get("aspect_ratio", self.aspect_ratio)
            self.quality = video_settings.get("quality", self.quality)

        self._update_status(
            f"⚙️ Settings: duration={self.duration}s, aspect_ratio={self.aspect_ratio}, quality={self.quality}"
        )

        if image_path and os.path.exists(image_path):
            self._update_status("🖼️ Reference image detected — using Image-to-Video mode")
            return self.generate_i2v(prompt, image_path)
        else:
            self._update_status("📝 No reference image — using Text-to-Video mode")
            return self.generate_t2v(prompt)
