import os
import glob
import subprocess
import requests

STREAM_DIR = "streams"
M3U8_FILENAME = os.path.join(STREAM_DIR, "atvavrupa.m3u8")
MAX_SEGMENTS = 15  # 10 dakikalık cron döngüsü için fazlasıyla yeterli segment sayısı

def main():
    os.makedirs(STREAM_DIR, exist_ok=True)
    
    # 1. Streamlink ile doğrudan taze m3u8 adresini al
    try:
        cmd = ["streamlink", "--stream-url", "https://www.atvavrupa.tv/canli-yayin", "best"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        stream_url = result.stdout.strip()
        if not stream_url or not stream_url.startswith("http"):
            return
    except Exception:
        return

    try:
        # 2. Ekstra istek atma adımı kaldırıldı, direkt stream_url içeriğini çekiyoruz
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(stream_url, headers=headers, timeout=8)
        if r.status_code != 200:
            return
        
        lines = r.text.splitlines()
        base_url = stream_url.rsplit('/', 1)[0] + '/'
        
        # Segmentleri topla
        active_segments = []
        for line in lines:
            if line and not line.startswith("#"):
                full_url = line if line.startswith("http") else base_url + line
                active_segments.append(full_url)
        
        # Cron sıklığına ve süreye göre sadece son segmentleri al (kesintisiz akış için)
        target_segments = active_segments[-MAX_SEGMENTS:]
        current_filenames = set()
        
        # 3. Segmentleri indir
        for url in target_segments:
            fname = f"seg_{abs(hash(url))}.ts"
            current_filenames.add(fname)
            fpath = os.path.join(STREAM_DIR, fname)
            
            if not os.path.exists(fpath):
                try:
                    res = requests.get(url, timeout=4)
                    if res.status_code == 200:
                        with open(fpath, 'wb') as f:
                            f.write(res.content)
                except:
                    continue

        # 4. Eski segmentleri temizle (disk şişmesini önle)
        for fpath in glob.glob(os.path.join(STREAM_DIR, "*.ts")):
            if os.path.basename(fpath) not in current_filenames:
                try: os.remove(fpath)
                except: pass

        # 5. Yerel m3u8 oynatma listesini güncelle
        final_files = sorted(glob.glob(os.path.join(STREAM_DIR, "*.ts")), key=os.path.getmtime)
        with open(M3U8_FILENAME, "w") as f:
            f.write("#EXTM3U\n#EXT-X-VERSION:3\n#EXT-X-TARGETDURATION:10\n#EXT-X-PLAYLIST-TYPE:EVENT\n")
            for ts_file in final_files:
                f.write(f"#EXTINF:10.0,\n{os.path.basename(ts_file)}\n")

    except Exception:
        pass

if __name__ == "__main__":
    main()
