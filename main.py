import os
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel
import yt_dlp

app = FastAPI()

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

class DownloadRequest(BaseModel):
    url: str
    format_type: str = "video"

def cleanup_file(filepath: str):
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
    except Exception as e:
        print(f"Cleanup error: {e}")

HTML_CONTENT = """<!DOCTYPE html>
<html lang="bn">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>মিডিয়া ডাউনলোডার</title>
<style>
body { font-family: sans-serif; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; background: #0f172a; color: white; }
.card { background: #1e293b; padding: 25px; border-radius: 12px; max-width: 420px; width: 90%; box-shadow: 0 4px 20px rgba(0,0,0,0.5); text-align: center; }
input, select, button { width: 100%; padding: 12px; margin: 10px 0; border-radius: 8px; border: none; box-sizing: border-box; font-size: 15px; }
input { background: #334155; color: white; }
select { background: #334155; color: white; }
button { background: #3b82f6; color: white; font-weight: bold; cursor: pointer; }
button:disabled { background: #64748b; }
#msg { margin-top: 15px; font-size: 14px; }
</style>
</head>
<body>
<div class="card">
<h2>মিডিয়া ডাউনলোডার</h2>
<p style="color: #94a3b8; font-size: 13px;">ইউটিউব, ফেসবুক ও অন্যান্য সাইটের লিংক দিন</p>
<input type="url" id="mediaUrl" placeholder="ভিডিও বা অডিও লিংক পেস্ট করুন..." required>
<select id="formatType">
<option value="video">ভিডিও (MP4)</option>
<option value="audio">অডিও (MP3)</option>
</select>
<button id="dlBtn" onclick="startDownload()">ডাউনলোড শুরু করুন</button>
<div id="msg"></div>
</div>
<script>
async function startDownload() {
const url = document.getElementById('mediaUrl').value.trim();
const format = document.getElementById('formatType').value;
const msg = document.getElementById('msg');
const btn = document.getElementById('dlBtn');
if(!url) { msg.innerHTML = '<span style="color: #f87171;">দয়া করে লিংক দিন!</span>'; return; }
btn.disabled = true;
btn.innerText = 'প্রসেসিং হচ্ছে, অপেক্ষা করুন...';
msg.innerHTML = '<span style="color: #60a5fa;">ফাইল তৈরি হচ্ছে...</span>';
try {
const res = await fetch('/api/download', {
method: 'POST',
headers: {'Content-Type': 'application/json'},
body: JSON.stringify({ url: url, format_type: format })
});
if(!res.ok) {
const err = await res.json();
throw new Error(err.detail || 'ডাউনলোড ব্যর্থ হয়েছে');
}
const blob = await res.blob();
const dlUrl = window.URL.createObjectURL(blob);
const a = document.createElement('a');
a.href = dlUrl;
a.download = format === 'audio' ? 'media.mp3' : 'media.mp4';
document.body.appendChild(a);
a.click();
a.remove();
msg.innerHTML = '<span style="color: #4ade80;">ডাউনলোড সফল হয়েছে!</span>';
} catch(e) {
msg.innerHTML = '<span style="color: #f87171;">' + e.message + '</span>';
} finally {
btn.disabled = false;
btn.innerText = 'ডাউনলোড শুরু করুন';
}
}
</script>
</body>
</html>"""

@app.get("/")
def home():
    return Response(content=HTML_CONTENT, media_type="text/html")

@app.post("/api/download")
def download_media(request: DownloadRequest, background_tasks: BackgroundTasks):
    url_str = str(request.url)
    if request.format_type == "audio":
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': f'{DOWNLOAD_DIR}/%(id)s.%(ext)s',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'quiet': True,
        }
        target_ext = "mp3"
    else:
        ydl_opts = {
            'format': 'best[ext=mp4]/best',
            'outtmpl': f'{DOWNLOAD_DIR}/%(id)s.%(ext)s',
            'quiet': True,
        }
        target_ext = "mp4"

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url_str, download=True)
            video_id = info_dict.get("id", "media")
            video_title = info_dict.get("title", "download")

            downloaded_file = os.path.join(DOWNLOAD_DIR, f"{video_id}.{target_ext}")
            if not os.path.exists(downloaded_file):
                for f in os.listdir(DOWNLOAD_DIR):
                    if f.startswith(video_id):
                        downloaded_file = os.path.join(DOWNLOAD_DIR, f)
                        break

            if not os.path.exists(downloaded_file):
                raise HTTPException(status_code=500, detail="ফাইল তৈরি করা সম্ভব হয়নি।")

            background_tasks.add_task(cleanup_file, downloaded_file)
            clean_filename = f"{video_title[:30]}.{target_ext}".replace("/", "_")
            return FileResponse(
                path=downloaded_file,
                filename=clean_filename,
                media_type='application/octet-stream'
            )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"ত্রুটি: {str(e)}")
