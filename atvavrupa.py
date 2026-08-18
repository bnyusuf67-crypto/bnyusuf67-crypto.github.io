import os
import glob
import subprocess
import requests
from concurrent.futures import ThreadPoolExecutor

STREAM_DIR = "streams"
M3U8_FILENAME = os.path.join(STREAM_DIR, "atvavrupa.m3u8")
MAX_SEGMENTS = 60

def download_segment(args):
    """Tek bir segmenti indiren fonksiyon (thread içinde çalışır)."""
    fname, url = args
    fpath = os.path.join(STREAM_DIR, fname)
    if os.path.exists(fpath): return  # Zaten varsa indirme
    try:
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            with open(fpath, 'wb') as f: f.write(res.content)
    except: pass

def main():
    os.makedirs(STREAM_DIR, exist_ok=True)
    
    # 1. Streamlink ile URL al
    try:
        cmd = ["streamlink", "--stream-url", "https://www.atvavrupa.tv/canli-yayin", "best"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        stream_url = result.stdout.strip()
        if not stream_url: return
    except: return

    # 2. M3U8 listesini çek
    r = requests.get(stream_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
    lines = [l for l in r.text.splitlines() if l and not l.startswith("#")]
    base_url = stream_url.rsplit('/', 1)[0] + '/'
    
    target_urls = [l if l.startswith("http") else base_url + l for l in lines[-MAX_SEGMENTS:]]
    target_files = {f"seg_{abs(hash(url))}.ts": url for url in target_urls}
    
    # 3. MULTI-THREAD İNDİRME (Hızın sırrı burası)
    with ThreadPoolExecutor(max_workers=10) as executor:
        executor.map(download_segment, target_files.items())

    # 4. Temizlik
    existing_files = set(os.path.basename(f) for f in glob.glob(os.path.join(STREAM_DIR, "*.ts")))
    for fname in (existing_files - set(target_files.keys())):
        os.remove(os.path.join(STREAM_DIR, fname))

    # 5. Liste yaz
    with open(M3U8_FILENAME, "w") as f:
        f.write("#EXTM3U\n#EXT-X-VERSION:3\n#EXT-X-TARGETDURATION:10\n#EXT-X-PLAYLIST-TYPE:EVENT\n")
        for fname in sorted(target_files.keys()):
            f.write(f"#EXTINF:10.0,\n{fname}\n")

if __name__ == "__main__":
    main()
