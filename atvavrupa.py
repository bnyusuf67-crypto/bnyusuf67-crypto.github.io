import os
import time
import glob
import requests

STREAM_DIR = "streams"
M3U8_FILENAME = os.path.join(STREAM_DIR, "atvavrupa.m3u8")

# İstediğiniz gibi ts değişkeni tanımlandı ve limit belirlendi
ts = 6  # İlk denemede indirilecek ve havuzda tutulacak maksimum segment sayısı

os.makedirs(STREAM_DIR, exist_ok=True)

def fetch_and_save_segment(index_id):
    """Canlı yayından tek bir segment çeken fonksiyon."""
    try:
        filename = f"seg_{index_id}.ts"
        filepath = os.path.join(STREAM_DIR, filename)
        
        # Gerçek indirme kodunuz buraya gelecek
        with open(filepath, 'wb') as f:
            f.write(b"") # Test aşaması için boş dosya
            
        print(f"Segment başarıyla indirildi: {filename}")
        return True
    except Exception as e:
        print(f"Segment indirilemedi: {e}")
        return False

def update_m3u8_playlist():
    """Klasördeki .ts dosyalarını tarayarak m3u8 oynatma listesini günceller."""
    ts_files = sorted([os.path.basename(f) for f in glob.glob(os.path.join(STREAM_DIR, "*.ts"))])
    
    m3u8_content = "#EXTM3U\n"
    m3u8_content += "#EXT-X-VERSION:3\n"
    m3u8_content += "#EXT-X-TARGETDURATION:10\n"
    m3u8_content += "#EXT-X-PLAYLIST-TYPE:EVENT\n"
    
    for t_file in ts_files:
        m3u8_content += "#EXTINF:10.0,\n"
        m3u8_content += f"https://bnyusuf67-crypto.github.io/{t_file}\n"
        
    with open(M3U8_FILENAME, "w", encoding="utf-8") as f:
        f.write(m3u8_content)
    print("M3U8 oynatma listesi güncellendi.")

def main():
    existing_ts = sorted(glob.glob(os.path.join(STREAM_DIR, "*.ts")))
    
    # İLK ÇALIŞTIRMA (Klasör boşsa anında ts kadar segment indirip havuzu doldurur)
    if len(existing_ts) == 0:
        print(f"İlk çalıştırılma: Havuz boş. Anında {ts} adet segment indiriliyor...")
        for i in range(ts):
            unique_id = int(time.time()) + i
            fetch_and_save_segment(unique_id)
            if i < ts - 1:
                time.sleep(1)
                
    # SONRAKİ ÇALIŞMALAR (Periyodik güncelleme)
    else:
        print("Periyodik güncelleme: Yeni segment ekleniyor...")
        unique_id = int(time.time())
        fetch_and_save_segment(unique_id)
        
        # Sınırı aştıysa en eskisini sil
        existing_ts = sorted(glob.glob(os.path.join(STREAM_DIR, "*.ts")))
        if len(existing_ts) > ts:
            for old_file in existing_ts[:-ts]:
                try:
                    os.remove(old_file)
                    print(f"Eski segment silindi: {os.path.basename(old_file)}")
                except Exception as e:
                    print(f"Dosya silinemedi: {e}")

    update_m3u8_playlist()

if __name__ == "__main__":
    main()
