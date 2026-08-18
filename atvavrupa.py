import os
import glob
import subprocess
import requests

STREAM_DIR = "streams"
M3U8_FILENAME = os.path.join(STREAM_DIR, "atvavrupa.m3u8")

def get_live_url():
    """Streamlink ile canlı yayın m3u8 adresini çözer."""
    try:
        cmd = ["streamlink", "--stream-url", "https://www.atvavrupa.tv/canli-yayin", "best"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return result.stdout.strip()
    except Exception as e:
        print(f"Streamlink hatası: {e}")
        return None

def main():
    os.makedirs(STREAM_DIR, exist_ok=True)
    
    stream_url = get_live_url()
    if not stream_url:
        print("Canlı yayın URL'si alınamadı.")
        return

    try:
        # Aktif m3u8 dosyasını indir
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(stream_url, headers=headers, timeout=10)
        if r.status_code != 200:
            print(f"M3U8 dosyası indirilemedi, HTTP Kod: {r.status_code}")
            return
        
        lines = r.text.splitlines()
        base_url = stream_url.rsplit('/', 1)[0] + '/'
        
        # M3U8 içerisindeki aktif segment URL'lerini topla
        active_segments = []
        for line in lines:
            if line and not line.startswith("#"):
                full_url = line if line.startswith("http") else base_url + line
                active_segments.append(full_url)
        
        current_filenames = set()
        
        # Yeni segmentleri indir ve kaydet
        for url in active_segments:
            fname = f"seg_{abs(hash(url))}.ts"
            current_filenames.add(fname)
            fpath = os.path.join(STREAM_DIR, fname)
            
            if not os.path.exists(fpath):
                try:
                    res = requests.get(url, timeout=5)
                    if res.status_code == 200:
                        with open(fpath, 'wb') as f:
                            f.write(res.content)
                except:
                    continue

        # TEMİZLİK: Artık aktif m3u8 listesinde olmayan ESKİ segmentleri sil
        existing_files = glob.glob(os.path.join(STREAM_DIR, "*.ts"))
        for fpath in existing_files:
            fname = os.path.basename(fpath)
            if fname not in current_filenames:
                try:
                    os.remove(fpath)
                    print(f"Eski segment silindi: {fname}")
                except:
                    pass

        # Yerel m3u8 oynatma listesini güncelle
        final_files = sorted(glob.glob(os.path.join(STREAM_DIR, "*.ts")), key=os.path.getmtime)
        with open(M3U8_FILENAME, "w") as f:
            f.write("#EXTM3U\n#EXT-X-VERSION:3\n#EXT-X-TARGETDURATION:10\n#EXT-X-PLAYLIST-TYPE:EVENT\n")
            for ts_file in final_files:
                f.write(f"#EXTINF:10.0,\n{os.path.basename(ts_file)}\n")
                
        print(f"Senkronizasyon başarılı. Aktif segment sayısı: {len(final_files)}")

    except Exception as e:
        print(f"Hata oluştu: {e}")

if __name__ == "__main__":
    main()
