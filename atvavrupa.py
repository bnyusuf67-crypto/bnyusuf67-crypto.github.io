import os
import glob
import requests
import subprocess
import time

STREAM_DIR = "streams"
M3U8_FILENAME = os.path.join(STREAM_DIR, "atvavrupa.m3u8")
MAX_TS = 30 

def get_live_segments():
    try:
        # Streamlink ile canlı yayını yakala
        cmd = ["streamlink", "--stream-url", "https://www.atvavrupa.tv/canli-yayin", "best"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        master_url = result.stdout.strip()
        
        if not master_url or "http" not in master_url:
            return []

        # m3u8 içeriğini çek ve işle
        r = requests.get(master_url, timeout=10)
        lines = r.text.splitlines()
        base_url = master_url.rsplit('/', 1)[0] + '/'
        
        segments = [line if line.startswith("http") else base_url + line 
                    for line in lines if line and not line.startswith("#")]
        return segments[-MAX_TS:]
    except Exception as e:
        print(f"Hata: {e}")
        return []

def main():
    os.makedirs(STREAM_DIR, exist_ok=True)
    segments = get_live_segments()
    
    # 1. Yeni segmentleri indir
    if segments:
        for url in segments:
            # Segmentin değişmez ismini URL'den türet
            fname = f"seg_{abs(hash(url))}.ts"
            fpath = os.path.join(STREAM_DIR, fname)
            if not os.path.exists(fpath):
                try:
                    r = requests.get(url, timeout=10)
                    if r.status_code == 200:
                        with open(fpath, 'wb') as f: f.write(r.content)
                        print(f"Eklendi: {fname}")
                except: continue

    # 2. Temizlik: En eski dosyaları sil
    all_files = sorted(glob.glob(os.path.join(STREAM_DIR, "*.ts")), key=os.path.getmtime)
    if len(all_files) > MAX_TS:
        for f in all_files[:-MAX_TS]:
            os.remove(f)

    # 3. M3U8 Dosyasını Güncelle (Canlılık için Zaman Damgalı)
    final_files = sorted(glob.glob(os.path.join(STREAM_DIR, "*.ts")), key=os.path.getmtime)
    with open(M3U8_FILENAME, "w") as f:
        f.write("#EXTM3U\n#EXT-X-VERSION:3\n#EXT-X-TARGETDURATION:10\n#EXT-X-PLAYLIST-TYPE:EVENT\n")
        # Oynatıcının önbelleğini kıran etiket:
        f.write(f"#EXT-X-PROGRAM-DATE-TIME:{time.strftime('%Y-%m-%dT%H:%M:%SZ')}\n")
        for ts_file in final_files:
            f.write(f"#EXTINF:10.0,\n{os.path.basename(ts_file)}\n")
    print(f"M3U8 güncellendi. Segment sayısı: {len(final_files)}")

if __name__ == "__main__":
    main()
