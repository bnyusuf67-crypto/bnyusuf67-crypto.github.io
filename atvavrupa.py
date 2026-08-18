import os
import glob
import subprocess
import requests
import time

STREAM_DIR = "streams"
M3U8_FILENAME = os.path.join(STREAM_DIR, "atvavrupa.m3u8")
MAX_TS = 30 # İdeal canlı akış boyutu

def get_live_url():
    """Streamlink ile her seferinde taze token'lı URL'yi alır."""
    try:
        # Streamlink ile en iyi kalite URL'yi yakala
        cmd = ["streamlink", "--stream-url", "https://www.atvavrupa.tv/canli-yayin", "best"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=40)
        return result.stdout.strip()
    except Exception as e:
        print(f"Streamlink hatası: {e}")
        return None

def main():
    os.makedirs(STREAM_DIR, exist_ok=True)
    
    stream_url = get_live_url()
    
    # HATA DURUMUNDA KORUMA: Eğer Streamlink URL vermezse, mevcut segmentleri silme!
    if stream_url and stream_url.startswith("http"):
        try:
            r = requests.get(stream_url, timeout=10)
            if r.status_code == 200:
                lines = r.text.splitlines()
                base_url = stream_url.rsplit('/', 1)[0] + '/'
                segments = [line if line.startswith("http") else base_url + line 
                            for line in lines if line and not line.startswith("#")]
                
                # Yeni segmentleri indir
                for i, url in enumerate(segments[-MAX_TS:]):
                    fpath = os.path.join(STREAM_DIR, f"seg_{i:03d}.ts")
                    try:
                        res = requests.get(url, timeout=5)
                        if res.status_code == 200:
                            with open(fpath, 'wb') as f: f.write(res.content)
                    except: continue
        except: pass

    # M3U8 Güncelleme (Her durumda çalışır, oynatıcıyı yeniler)
    final_files = sorted(glob.glob(os.path.join(STREAM_DIR, "*.ts")))
    if final_files:
        with open(M3U8_FILENAME, "w") as f:
            f.write("#EXTM3U\n#EXT-X-VERSION:3\n#EXT-X-TARGETDURATION:10\n#EXT-X-PLAYLIST-TYPE:EVENT\n")
            f.write(f"#EXT-X-PROGRAM-DATE-TIME:{time.strftime('%Y-%m-%dT%H:%M:%SZ')}\n")
            for ts_file in final_files:
                f.write(f"#EXTINF:10.0,\n{os.path.basename(ts_file)}\n")
    print(f"İşlem tamamlandı. Segment: {len(final_files)}")

if __name__ == "__main__":
    main()
