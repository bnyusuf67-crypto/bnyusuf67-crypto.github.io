import os
import glob
import requests
import time

STREAM_DIR = "streams"
M3U8_FILENAME = os.path.join(STREAM_DIR, "atvavrupa.m3u8")
LINK_FILE = "ffmpeglink.txt"
MAX_TS = 30 

def get_segments_from_file():
    """ffmpeglink.txt içindeki işlenmiş akış kaynağını okur ve segmentleri listeler."""
    try:
        with open(LINK_FILE, "r") as f:
            stream_url = f.read().strip()
            
        if not stream_url:
            print("HATA: ffmpeglink.txt boş!")
            return None
        
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        r = requests.get(stream_url, headers=headers, timeout=10)
        
        if r.status_code != 200:
            print(f"HATA: Kaynağa erişilemedi (Kod: {r.status_code})")
            return None
            
        lines = r.text.splitlines()
        base_url = stream_url.rsplit('/', 1)[0] + '/'
        
        segments = [line if line.startswith("http") else base_url + line 
                    for line in lines if line and not line.startswith("#")]
        return segments[-MAX_TS:]
    except Exception as e:
        print(f"Okuma/Bağlantı hatası: {e}")
        return None

def main():
    os.makedirs(STREAM_DIR, exist_ok=True)
    segments = get_segments_from_file()
    
    # 403 veya hata durumunda arşivi koru, hiçbir şeyi silme
    if segments is not None:
        for url in segments:
            fname = f"seg_{abs(hash(url))}.ts"
            fpath = os.path.join(STREAM_DIR, fname)
            if not os.path.exists(fpath):
                try:
                    r = requests.get(url, timeout=10)
                    if r.status_code == 200:
                        with open(fpath, 'wb') as f: f.write(r.content)
                except: continue
        
        # Sadece başarılı işlemde eski segmentleri temizle
        all_files = sorted(glob.glob(os.path.join(STREAM_DIR, "*.ts")), key=os.path.getmtime)
        if len(all_files) > MAX_TS:
            for f in all_files[:-MAX_TS]: os.remove(f)
    else:
        print("Erişim hatası alındı. Mevcut 30 segmentlik arşiv korunuyor.")

    # M3U8 dosyasını her durumda taze tut
    final_files = sorted(glob.glob(os.path.join(STREAM_DIR, "*.ts")), key=os.path.getmtime)
    if final_files:
        with open(M3U8_FILENAME, "w") as f:
            f.write("#EXTM3U\n#EXT-X-VERSION:3\n#EXT-X-TARGETDURATION:10\n#EXT-X-PLAYLIST-TYPE:EVENT\n")
            f.write(f"#EXT-X-PROGRAM-DATE-TIME:{time.strftime('%Y-%m-%dT%H:%M:%SZ')}\n")
            for ts_file in final_files:
                f.write(f"#EXTINF:10.0,\n{os.path.basename(ts_file)}\n")
        print(f"M3U8 güncellendi. Aktif segment: {len(final_files)}")
    else:
        print("Uyarı: Arşivde hiç segment bulunamadı!")

if __name__ == "__main__":
    main()
