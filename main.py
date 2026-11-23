import os
import re
import shutil

import yt_dlp
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

# Render-এ Secret File হিসেবে cookies.txt রাখলে এই পাথে পাওয়া যায়
SECRET_COOKIES = "/etc/secrets/cookies.txt"
TMP_COOKIES = "/tmp/cookies.txt"


class VideoRequest(BaseModel):
    url: str
    quality: str = "720p"  # অ্যাপ থেকে "720p", "1080p", "audio" আসবে


def clean_error(e: Exception) -> str:
    msg = re.sub(r"\x1b\[[0-9;]*m", "", str(e))  # রঙের কোড মুছে ফেলা
    return msg.strip()[:300]


def build_format(quality: str) -> str:
    q = quality.lower()
    if "audio" in q or "mp3" in q or "m4a" in q:
        return "bestaudio[ext=m4a]/bestaudio/best"

    m = re.search(r"\d+", q)
    h = int(m.group()) if m else 720

    if h <= 360:
        # ইউটিউবে ৩৬০p পর্যন্তই ভিডিও+অডিও একসাথে এক ফাইলে পাওয়া যায়
        return f"best[height<={h}][ext=mp4]/best[height<={h}]/best"

    # এর উপরে আলাদা ভিডিও ও অডিও (অ্যাপ ডাউনলোড শেষে মার্জ করবে)
    return (
        f"bestvideo[height<={h}][ext=mp4]+bestaudio[ext=m4a]/"
        f"bestvideo[height<={h}]+bestaudio/"
        f"best[height<={h}]/best"
    )


@app.get("/")
def health():
    return {"status": "ok"}


@app.post("/get_link")
def get_link(req: VideoRequest):
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "format": build_format(req.quality),
    }

    # কুকি থাকলে ব্যবহার করবে (বট-ব্লক এড়াতে সাহায্য করে)
    if os.path.exists(SECRET_COOKIES):
        shutil.copyfile(SECRET_COOKIES, TMP_COOKIES)
        ydl_opts["cookiefile"] = TMP_COOKIES

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(req.url, download=False)
    except Exception as e:
        raise HTTPException(status_code=400, detail=clean_error(e))

    title = info.get("title", "Video")

    # আলাদা ভিডিও ও অডিও স্ট্রিম
    if info.get("requested_formats"):
        v_url, a_url = "", ""
        for f in info["requested_formats"]:
            has_v = f.get("vcodec") not in (None, "none")
            has_a = f.get("acodec") not in (None, "none")
            if has_v:
                v_url = f.get("url", "")
            elif has_a:
                a_url = f.get("url", "")
        if v_url and a_url:
            return {"type": "separate", "video_url": v_url, "audio_url": a_url, "title": title}

    # একক ফাইল
    url = info.get("url")
    if not url:
        raise HTTPException(status_code=400, detail="ডাউনলোড লিংক পাওয়া যায়নি")
    return {"type": "single", "url": url, "ext": info.get("ext", "mp4"), "title": title}
