import os
import glob
import subprocess
import requests

STREAM_DIR = "streams"
M3U8_FILENAME = os.path.join(STREAM_DIR, "atvavrupa.m3u8")
MAX_SEGMENTS = 60 

def main():
    os.makedirs(STREAM_DIR, exist_ok=True)
    
    # 1. Hızlı Streamlink (Time-out ile)
    try:
        cmd = ["streamlink", "--stream-url", "https://www.atvavrupa.tv/canli-yayin", "best"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
        stream_url = result.stdout.strip()
        if not stream_url: return
    except: return

    try:
        # 2. M3U8 içeriğini al
        r = requests.get(stream_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
        if r.status_code != 200: return
        
        lines = [l for l in r.text.splitlines() if l and not l.startswith("#")]
        base_url = stream_url.rsplit('/', 1)[0] + '/'
        
        # Güncel 60 segmentin isimlerini hash ile hazırla
        target_urls = [l if l.startswith("http") else base_url + l for l in lines[-MAX_SEGMENTS:]]
        # İsimleri hash ile eşleştir
        target_files = {f"seg_{abs(hash(url))}.ts": url for url in target_urls}
        
        # 3. İNDİRME OPTİMİZASYONU: Sadece mevcut olmayanları indir
        for fname, url in target_files.items():
            fpath = os.path.join(STREAM_DIR, fname)
            if not os.path.exists(fpath):
                try:
                    res = requests.get(url, timeout=3) # Daha kısa timeout
                    if res.status_code == 200:
                        with open(fpath, 'wb') as f: f.write(res.content)
                except: continue

        # 4. TEMİZLİK: Sadece hedefte olmayanları sil (set farkı ile çok hızlı)
        existing_files = set(os.path.basename(f) for f in glob.glob(os.path.join(STREAM_DIR, "*.ts")))
        to_delete = existing_files - set(target_files.keys())
        for fname in to_delete:
            os.remove(os.path.join(STREAM_DIR, fname))

        # 5. M3U8 yazma
        with open(M3U8_FILENAME, "w") as f:
            f.write("#EXTM3U\n#EXT-X-VERSION:3\n#EXT-X-TARGETDURATION:10\n#EXT-X-PLAYLIST-TYPE:EVENT\n")
            for fname in sorted(target_files.keys()):
                f.write(f"#EXTINF:10.0,\n{fname}\n")

    except: pass

if __name__ == "__main__":
    main()
