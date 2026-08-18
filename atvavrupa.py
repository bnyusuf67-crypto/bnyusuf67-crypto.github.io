import os
import glob
import requests
import time

STREAM_DIR = "streams"
M3U8_FILENAME = os.path.join(STREAM_DIR, "atvavrupa.m3u8")
LINK_FILE = "ffmpeglink.txt"
MAX_TS = 100 

def main():
    os.makedirs(STREAM_DIR, exist_ok=True)
    
    # 1. Link dosyasını oku
    try:
        with open(LINK_FILE, "r") as f:
            stream_url = f.read().strip()
    except Exception:
        stream_url = ""

    if stream_url:
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Cache-Control': 'no-cache'
            }
            r = requests.get(stream_url, headers=headers, timeout=10)
            if r.status_code == 200:
                lines = r.text.splitlines()
                base_url = stream_url.rsplit('/', 1)[0] + '/'
                
                segments = [line if line.startswith("http") else base_url + line 
                            for line in lines if line and not line.startswith("#")]
                
                # Yeni segmentleri indir
                for url in segments[-MAX_TS:]:
                    # Çakışmayı önlemek ve her seferinde taze indirmek için benzersiz isim
                    clean_name = url.split('/')[-1].split('?')[0]
                    if not clean_name.endswith('.ts'):
                        clean_name = f"seg_{abs(hash(url))}.ts"
                        
                    fpath = os.path.join(STREAM_DIR, clean_name)
                    if not os.path.exists(fpath):
                        try:
                            res = requests.get(url, timeout=5)
                            if res.status_code == 200:
                                with open(fpath, 'wb') as f: f.write(res.content)
                        except: continue
        except Exception as e:
            print(f"Bağlantı hatası: {e}")

    # 2. Temizlik: MAX_TS (100) adet segmentten fazlasını sil
    all_files = sorted(glob.glob(os.path.join(STREAM_DIR, "*.ts")), key=os.path.getmtime)
    if len(all_files) > MAX_TS:
        for f in all_files[:-MAX_TS]: 
            try: os.remove(f)
            except: pass

    # 3. M3U8 Dosyasını Kesin Olarak Yeniden Oluştur (Önbellek Kırıcı ile)
    final_files = sorted(glob.glob(os.path.join(STREAM_DIR, "*.ts")), key=os.path.getmtime)
    if final_files:
        with open(M3U8_FILENAME, "w") as f:
            f.write("#EXTM3U\n#EXT-X-VERSION:3\n#EXT-X-TARGETDURATION:10\n#EXT-X-PLAYLIST-TYPE:EVENT\n")
            # Her güncellemede oynatıcının tetiklenmesi için zaman damgası:
            f.write(f"#EXT-X-PROGRAM-DATE-TIME:{time.strftime('%Y-%m-%dT%H:%M:%SZ')}\n")
            for ts_file in final_files:
                f.write(f"#EXTINF:10.0,\n{os.path.basename(ts_file)}\n")
        print(f"İşlem başarılı. Toplam segment: {len(final_files)}")
    else:
        print("Uyarı: Klasörde hiç .ts dosyası yok!")

if __name__ == "__main__":
    main()
