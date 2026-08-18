import os
import time
import requests
import re
import urllib3

urllib3.disable_warnings()

TARGET_URL = "https://www.atvavrupa.tv/canli-yayin"
BACKUP_URL = "https://uzunmuhalefet.unaux.com/trkvz.php?kanal=atvavrupa&.m3u8"
STREAM_DIR = "streams"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": TARGET_URL
}

def get_latest_segment_from_quality(m3u8_url, target_quality="_576p"):
    try:
        res = requests.get(m3u8_url, headers=headers, verify=False, timeout=10)
        if res.status_code != 200:
            return None
        text = res.text
        if "#EXTM3U" not in text:
            return None
        base_url = m3u8_url.rsplit('/', 1)[0] + '/'
        lines = [line.strip() for line in text.splitlines() if line.strip()]

        selected_sub_playlist = None
        for i, line in enumerate(lines):
            if target_quality in line:
                if not line.startswith("#"):
                    selected_sub_playlist = line
                elif i + 1 < len(lines) and not lines[i + 1].startswith("#"):
                    selected_sub_playlist = lines[i + 1]
                break

        if not selected_sub_playlist:
            for line in lines:
                if line.endswith(".m3u8") and not line.startswith("#"):
                    selected_sub_playlist = line
                    break

        if not selected_sub_playlist:
            return None

        if not selected_sub_playlist.startswith("http"):
            selected_sub_playlist = base_url + selected_sub_playlist

        sub_res = requests.get(selected_sub_playlist, headers=headers, verify=False, timeout=10)
        if sub_res.status_code != 200:
            return None

        sub_text = sub_res.text
        sub_base_url = selected_sub_playlist.rsplit('/', 1)[0] + '/'
        segment_lines = [line.strip() for line in sub_text.splitlines() if line.strip() and not line.strip().startswith("#")]

        if not segment_lines:
            return None

        last_segment = segment_lines[-1]
        if not last_segment.startswith("http"):
            last_segment = sub_base_url + last_segment

        return last_segment
    except Exception:
        return None

def resolve_m3u8():
    # 1. Yedek adresi dene
    try:
        res = requests.get(BACKUP_URL, headers=headers, verify=False, timeout=10)
        if res.status_code == 200:
            text = res.text
            if "#EXTM3U" in text and "<html" not in text.lower():
                seg = get_latest_segment_from_quality(BACKUP_URL, target_quality="_576p")
                if seg: return seg
            matches = re.findall(r'https?://[^\s"\'<>]+(?:trkvz\.php\?[^\s"\'<>]*)', text)
            for target_url in matches:
                if target_url != BACKUP_URL:
                    seg = get_latest_segment_from_quality(target_url, target_quality="_576p")
                    if seg: return seg
    except Exception:
        pass

    # 2. Ana site API ve Token yapısını dene
    try:
        response = requests.get(TARGET_URL, headers=headers, verify=False, timeout=10)
        if response.status_code == 200:
            site_content = response.text
            v_match = re.search(r'data-videoid=["\']([^"\']+)["\']', site_content)
            w_match = re.search(r'data-websiteid=["\']([^"\']+)["\']', site_content)
            if v_match and w_match:
                video_id = v_match.group(1)
                website_id = w_match.group(1)
                getvideo_url = f"https://videojs.tmgrup.com.tr/getvideo/{website_id}/{video_id}"
                video_res = requests.get(getvideo_url, headers=headers, verify=False, timeout=10)
                if video_res.status_code == 200 and video_res.json().get("success"):
                    raw_hls_url = video_res.json()["video"]["VideoSmilUrl"]
                    secure_api = "https://securevideotoken.tmgrup.com.tr/webtv/secure"
                    token_res = requests.get(secure_api, params={"url": raw_hls_url}, headers=headers, verify=False, timeout=10)
                    if token_res.status_code == 200 and token_res.json().get("Success"):
                        secure_hls_url = token_res.json().get("Url")
                        seg = get_latest_segment_from_quality(secure_hls_url, target_quality="_576p")
                        if seg: return seg
    except Exception:
        pass
    return None

def main():
    os.makedirs(STREAM_DIR, exist_ok=True)
    
    ts_url = resolve_m3u8()
    if not ts_url:
        print("TS segment adresi çözülemedi.")
        return

    print(f"Çözülen TS URL: {ts_url}")

    try:
        ts_res = requests.get(ts_url, headers=headers, verify=False, timeout=15)
        if ts_res.status_code != 200:
            print("TS segment içeriği indirilemedi.")
            return
    except Exception as e:
        print(f"İndirme hatası: {e}")
        return

    # Benzersiz isimle ts dosyasını kaydet
    timestamp_str = str(int(time.time()))
    filename = f"seg_{timestamp_str}.ts"
    filepath = os.path.join(STREAM_DIR, filename)

    with open(filepath, "wb") as f:
        f.write(ts_res.content)
    print(f"Kaydedildi: {filepath}")

    # Eski segmentleri temizle (Sadece son 4 tanesini tut)
    existing_ts = sorted([f for f in os.listdir(STREAM_DIR) if f.endswith(".ts")])
    max_segments = 4
    if len(existing_ts) > max_segments:
        for old_file in existing_ts[:-max_segments]:
            try:
                os.remove(os.path.join(STREAM_DIR, old_file))
            except:
                pass
        existing_ts = existing_ts[-max_segments:]

    # streams/atvavrupa.m3u8 dosyasını oluştur/güncelle
    m3u8_path = os.path.join(STREAM_DIR, "atvavrupa.m3u8")
    m3u8_content = "#EXTM3U\n"
    m3u8_content += "#EXT-X-VERSION:3\n"
    m3u8_content += "#EXT-X-TARGETDURATION:10\n"
    m3u8_content += "#EXT-X-MEDIA-SEQUENCE:1\n"
    
    for ts_file in existing_ts:
        m3u8_content += "#EXTINF:6.000,\n"
        m3u8_content += f"https://bnyusuf67-crypto.github.io/{ts_file}\n"

    with open(m3u8_path, "w", encoding="utf-8") as f:
        f.write(m3u8_content)
    print(f"M3U8 Güncellendi: {m3u8_path}")

if __name__ == "__main__":
    main()
