import os
import glob
import requests
import subprocess

STREAM_DIR = "streams"
M3U8_FILENAME = os.path.join(STREAM_DIR, "atvavrupa.m3u8")
ts = 30  # Havuzda tutulacak maksimum segment sınırı

os.makedirs(STREAM_DIR, exist_ok=True)

def get_live_segment_urls():
    """Streamlink kullanarak ATV Avrupa canlı yayın akışının m3u8 adresini bulur."""
    try:
        # Streamlink ile canlı yayının stream URL'sini çekiyoruz
        # ATV Avrupa resmi canlı yayın web sitesi veya turkuvaz streamlink plugin yapısı
        cmd = ["streamlink", "--stream-url", "https://www.atvavrupa.tv/canli-yayin", "best"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=25)
        master_url = result.stdout.strip()
        
        if not master_url or "error" in master_url.lower():
            print(f"Streamlink URL çözemedi: {result.stderr.strip()}")
            return []
            
        print(f"Çözülen Master URL: {master_url}")
        
        # Alınan m3u8 / master listesini indirip içindeki segmentleri okuyoruz
        res = requests.get(master_url, timeout=10)
        lines = res.text.splitlines()
        
        segment_urls = []
        base_url_path = "/".join(master_url.split("/")[:-1]) + "/"
        
        for line in lines:
            line = line.strip()
            if line and not line.startswith("#"):
                # Göreceli linkleri (relative path) tam URL'ye çeviriyoruz
                if line.startswith("http"):
                    segment_urls.append(line)
                else:
                    segment_urls.append(base_url_path + line)
                
        return segment_urls
    except Exception as e:
        print(f"Streamlink ile canlı segmentler alınırken hata oluştu: {e}")
        return []

def download_segment(segment_url, filepath):
    """Belirli bir segment URL'sini indirip dosyaya kaydeder."""
    try:
        r = requests.get(segment_url, stream=True, timeout=15)
        if r.status_code == 200:
            with open(filepath, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            return True
    except Exception as e:
        print(f"Segment indirme hatası: {e}")
    return False

def main():
    print("Streamlink ile canlı yayın segmentleri taranıyor...")
    live_segments = get_live_segment_urls()
    
    if not live_segments:
        print("Canlı akıştan segment listesi alınamadı.")
        return

    # Sadece son 30 segmenti hedefle
    target_segments = live_segments[-ts:]
    
    existing_files = set(os.path.basename(f) for f in glob.glob(os.path.join(STREAM_DIR, "*.ts")))
    
    for seg_url in target_segments:
        # Segment dosya adını URL'den güvenli şekilde türet
        filename = seg_url.split("/")[-1].split("?")[0]
        if not filename.endswith(".ts"):
            filename = f"seg_{abs(hash(seg_url))}.ts"
            
        filepath = os.path.join(STREAM_DIR, filename)
        
        # Eğer bu segment henüz indirilmemişse indir ve havuza ekle
        if filename not in existing_files:
            if download_segment(seg_url, filepath):
                print(f"Yeni segment eklendi: {filename}")

    # Havuz boyutunu 'ts' (30) sınırında tutmak için eskileri temizle
    all_ts_files = sorted(glob.glob(os.path.join(STREAM_DIR, "*.ts")))
    if len(all_ts_files) > ts:
        for old_file in all_ts_files[:-ts]:
            try:
                os.remove(old_file)
                print(f"Eski segment temizlendi: {os.path.basename(old_file)}")
            except Exception as e:
                print(f"Dosya silinemedi: {e}")

    # Oynatma listesini güncel dosyalara göre yeniden oluştur
    final_ts_files = sorted([os.path.basename(f) for f in glob.glob(os.path.join(STREAM_DIR, "*.ts"))])
    
    m3u8_content = "#EXTM3U\n"
    m3u8_content += "#EXT-X-VERSION:3\n"
    m3u8_content += "#EXT-X-TARGETDURATION:10\n"
    m3u8_content += "#EXT-X-PLAYLIST-TYPE:EVENT\n"
    
    for ts_file in final_ts_files:
        m3u8_content += "#EXTINF:10.0,\n"
        m3u8_content += f"{ts_file}\n"
        
    with open(M3U8_FILENAME, "w", encoding="utf-8") as f:
        f.write(m3u8_content)
    print(f"M3U8 oynatma listesi güncellendi. Toplam aktif segment: {len(final_ts_files)}")

if __name__ == "__main__":
    main()
