import os
import glob
import requests
import time

STREAM_DIR = "streams"
M3U8_FILENAME = os.path.join(STREAM_DIR, "atvavrupa.m3u8")
LINK_FILE = "ffmpeglink.txt"
MAX_TS = 100 

def get_segments_from_file():
    try:
        with open(LINK_FILE, "r") as f:
            stream_url = f.read().strip()
            
        # Cache'i kırmak için header ekliyoruz
        headers = {
            'User-Agent': 'Mozilla/5.0',
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache'
        }
        r = requests.get(stream_url, headers=headers, timeout=10)
        
        if r.status_code != 200: return None
            
        lines = r.text.splitlines()
        base_url = stream_url.rsplit('/', 1)[0] + '/'
        
        # Segmentleri URL'den ayıkla
        segments = [line if line.startswith("http") else base_url + line 
                    for line in lines if line and not line.startswith("#")]
        return segments[-MAX_TS:]
    except Exception:
        return None

def main():
    os.makedirs(STREAM_DIR, exist_ok=True)
    segments = get_segments_from_file()
    
    if segments:
        for url in segments:
            # URL'nin içindeki dosya adını (örneğin: segment_123.ts) doğrudan alalım
            # Bu, farklı isimlerin gelmesini sağlar
            filename = url.split('/')[-1].split('?')[0] 
            fpath = os.path.join(STREAM_DIR, filename)
            
            if not os.path.exists(fpath):
                try:
                    r = requests.get(url, timeout=10)
                    if r.status_code == 200:
                        with open(fpath, 'wb') as f: f.write(r.content)
                except: continue

        # Temizlik
        all_files = sorted(glob.glob(os.path.join(STREAM_DIR, "*.ts")), key=os.path.getmtime)
        if len(all_files) > MAX_TS:
            for f in all_files[:-MAX_TS]: os.remove(f)

    # M3U8 Güncelleme
    final_files = sorted(glob.glob(os.path.join(STREAM_DIR, "*.ts")), key=os.path.getmtime)
    with open(M3U8_FILENAME, "w") as f:
        f.write("#EXTM3U\n#EXT-X-VERSION:3\n#EXT-X-TARGETDURATION:10\n#EXT-X-PLAYLIST-TYPE:EVENT\n")
        f.write(f"#EXT-X-PROGRAM-DATE-TIME:{time.strftime('%Y-%m-%dT%H:%M:%SZ')}\n")
        for ts_file in final_files:
            f.write(f"#EXTINF:10.0,\n{os.path.basename(ts_file)}\n")

if __name__ == "__main__":
    main()
