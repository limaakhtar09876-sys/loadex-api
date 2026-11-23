from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import yt_dlp

app = FastAPI()

class VideoRequest(BaseModel):
    url: str
    format_id: str = "best"

@app.post("/formats")
def get_formats(req: VideoRequest):
    ydl_opts = {'quiet': True, 'no_warnings': True}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(req.url, download=False)
            formats = []
            for f in info.get('formats', []):
                if f.get('vcodec') != 'none' or f.get('acodec') != 'none':
                    formats.append({
                        "format_id": f['format_id'],
                        "ext": f.get('ext', 'mp4'),
                        "resolution": f.get('resolution') or f.get('format_note') or "Audio",
                        "filesize": f.get('filesize') or f.get('filesize_approx') or 0,
                        "vcodec": f.get('vcodec'),
                        "acodec": f.get('acodec')
                    })
            return {"title": info.get('title'), "formats": formats}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/get_link")
def get_link(req: VideoRequest):
    # 1080p এর নিচে হলে এক ফাইলেই পাবেন, 1080p+ হলে আলাদা অডিও-ভিডিও আসবে
    ydl_opts = {'quiet': True, 'format': req.format_id}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(req.url, download=False)
            if 'requested_formats' in info:
                return {"type": "separate", "video_url": info['requested_formats'][0]['url'], "audio_url": info['requested_formats'][1]['url']}
            else:
                return {"type": "single", "url": info['url'], "ext": info.get('ext', 'mp4')}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
