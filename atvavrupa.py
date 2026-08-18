import os
import time
import glob
import requests

STREAM_DIR = "streams"
M3U8_FILENAME = os.path.join(STREAM_DIR, "atvavrupa.m3u8")
MAX_SEGMENTS = 6

os.makedirs(STREAM_DIR, exist_ok=True)

def fetch_and_save_segment(index_id):
    """
    Canlı yayından tek bir segment (veya o anlık .ts parçası) çeken fonksiyon.
    Token veya stream linki çözme mantığınız buraya entegre edilir.
    """
    try:
        # Örnek token / stream alma endpoint mantığı (kendi yapınıza göre düzenleyebilirsiniz)
        # Örn: yt-dlp veya securevideotoken isteği ile .ts bağlantısını bulma
        # Burada simülasyon veya gerçek indirme komutunuz yer alır.
        
        # Güvenli token URL örneği veya streamlink entegrasyonu:
        # stream_url = get_secure_stream_url()
        
        # Örnek olarak benzersiz isimli bir .ts dosyası oluşturuyoruz:
        filename = f"seg_{index_id}.ts"
        filepath = os.path.join(STREAM_DIR, filename)
        
        # Gerçek indirme işlemi (Örnek boş veya stream kaydı):
        # r = requests.get(stream_url, stream=True, timeout=15)
        # if r.status_code == 200:
        #     with open(filepath, 'wb') as f:
        #         for chunk in r.iter_content(chunk_size=1024):
        #             if chunk:
        #                 f.write(chunk)
        
        print(f"Segment indirildi: {filename}")
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
    
    for ts in ts_files:
        m3u8_content += "#EXTINF:10.0,\n"
        m3u8_content += f"{ts}\n"
        
    with open(M3U8_FILENAME, "w", encoding="utf-8") as f:
        f.write(m3u8_content)
    print("M3U8 oynatma listesi güncellendi.")

def main():
    existing_ts = sorted(glob.glob(os.path.join(STREAM_DIR, "*.ts")))
    
    # İLK ÇALIŞTIRMA (Klasör boşsa anında 6 segment indirip havuzu doldurur)
    if len(existing_ts) == 0:
        print(f"İlk çalıştırılma tespit edildi. Havuz {MAX_SEGMENTS} segment ile dolduruluyor...")
        for i in range(MAX_SEGMENTS):
            unique_id = int(time.time()) + i
            fetch_and_save_segment(unique_id)
            if i < MAX_SEGMENTS - 1:
                time.sleep(2) # Segmentler arası minik gecikme
    
    # SONRAKİ ÇALIŞMALAR (Her 1 dakikada bir 1 yeni segment ekler)
    else:
        print("Periyodik güncelleme: Yeni segment ekleniyor...")
        unique_id = int(time.time())
        fetch_and_save_segment(unique_id)
        
        # Eski segmentleri temizle (En fazla MAX_SEGMENTS kalacak şekilde)
        existing_ts = sorted(glob.glob(os.path.join(STREAM_DIR, "*.ts")))
        if len(existing_ts) > MAX_SEGMENTS:
            for old_file in existing_ts[:-MAX_SEGMENTS]:
                try:
                    os.remove(old_file)
                    print(f"Eski segment silindi: {os.path.basename(old_file)}")
                except Exception as e:
                    print(f"Dosya silinemedi: {e}")

    # Oynatma listesini yenile
    update_m3u8_playlist()

if __name__ == "__main__":
    main()
