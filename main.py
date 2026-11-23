from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import yt_dlp
import re

app = FastAPI()

class VideoRequest(BaseModel):
    url: str
    quality: str = "720" # আপনার অ্যাপ থেকে "720p", "1080p", "Audio" আসবে

@app.post("/get_link")
def get_link(req: VideoRequest):
    q = req.quality.lower()
    
    # ১. কোয়ালিটি বুঝে ফরম্যাট সিলেক্ট করা
    if "audio" in q or "mp3" in q or "m4a" in q:
        fmt = "bestaudio/best"
    else:
        # "720p" থেকে শুধু "720" নাম্বারটি বের করা
        height_match = re.search(r'\d+', q)
        height = int(height_match.group()) if height_match else 720
        
        if height <= 720:
            # ৭২০p বা তার নিচে সাধারণত এক ফাইলেই (MP4) পাওয়া যায়
            fmt = f"best[height<={height}][ext=mp4]/best[height<={height}]/best"
        else:
            # ১০৮০p, ৪K এর জন্য আলাদা ভিডিও এবং অডিও
            fmt = f"bestvideo[height<={height}]+bestaudio/best"

    ydl_opts = {'quiet': True, 'format': fmt}
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(req.url, download=False)
            
            # যদি আলাদা ভিডিও এবং অডিও স্ট্রিম থাকে
            if 'requested_formats' in info:
                v_url = ""
                a_url = ""
                for f in info['requested_formats']:
                    if f.get('vcodec') != 'none': v_url = f['url']
                    if f.get('acodec') != 'none': a_url = f['url']
                return {"type": "separate", "video_url": v_url, "audio_url": a_url, "title": info.get('title', 'Video')}
            
            # যদি একক ফাইল হয়
            else:
                return {"type": "single", "url": info['url'], "ext": info.get('ext', 'mp4'), "title": info.get('title', 'Video')}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
