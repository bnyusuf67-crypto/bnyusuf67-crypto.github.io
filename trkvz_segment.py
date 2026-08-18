from playwright.sync_api import sync_playwright
import requests
from urllib.parse import urlparse, urlunparse

CHANNELS = [
    {"name": "ATV", "slug": "atv"},
    {"name": "A Haber", "slug": "ahaber"},
    {"name": "A News", "slug": "anews"},
    {"name": "A Para", "slug": "apara"},
    {"name": "A Spor", "slug": "aspor"},
    {"name": "A2 TV", "slug": "a2tv"},
    {"name": "Minika Çocuk", "slug": "minikacocuk"},
    {"name": "Minika GO", "slug": "minikago"},
    {"name": "Vav TV", "slug": "vavtv"},
    {"name": "ATV Avrupa", "slug": "atvavrupa"}
]

UNAUX_RESOLVER = "https://uzunmuhalefet.unaux.com/trkvz.php?kanal={slug}&.m3u8"

def clean_ts_url(ts_url):
    """TS parçacık URL'sindeki st ve e parametrelerini temizler."""
    parsed = urlparse(ts_url)
    query_params = parsed.query.split("&")
    filtered_params = [p for p in query_params if not p.startswith("st=") and not p.startswith("e=")]
    new_query = "&".join(filtered_params)
    new_parsed = parsed._replace(query=new_query if new_query else "")
    return urlunparse(new_parsed)

def get_stream_via_unaux(slug, page):
    """Playwright ile unaux üzerinden ana m3u8 bağlantısını yakalar."""
    found_urls = []

    def handle_response(response):
        if "ercdn.net" in response.url and "st=" in response.url:
            found_urls.append(response.url)

    page.on("response", handle_response)
    
    try:
        page.goto(UNAUX_RESOLVER.format(slug=slug), timeout=15000)
        page.wait_for_timeout(3000)
    except:
        pass
    
    page.remove_listener("response", handle_response)
    
    for q in ["1080p", "720p", "576p", "360p"]:
        for u in found_urls:
            if f"_{q}" in u:
                return u
    return found_urls[-1] if found_urls else None

def process_ts_playlist(master_url):
    """Ana m3u8 dosyasını indirip TS parçalarını optimize edilmiş zaman aşımıyla test eder ve parametrelerini temizler."""
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(master_url, headers=headers, timeout=10)
        if res.status_code != 200:
            return None

        lines = res.text.splitlines()
        base_url_prefix = master_url.rsplit('/', 1)[0] + '/'
        new_m3u8_lines = []

        for line in lines:
            line_str = line.strip()
            if line_str and not line_str.startswith("#"):
                ts_full_url = line_str if line_str.startswith("http") else base_url_prefix + line_str
                try:
                    test_res = requests.head(ts_full_url, headers=headers, timeout=3)
                    if test_res.status_code == 200:
                        cleaned_url = clean_ts_url(ts_full_url)
                        new_m3u8_lines.append(cleaned_url)
                    else:
                        new_m3u8_lines.append(line_str)
                except:
                    new_m3u8_lines.append(line_str)
            else:
                new_m3u8_lines.append(line)

        return "\n".join(new_m3u8_lines) + "\n"
    except:
        return None

def generate_all_channels():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        print("Tüm Kanallar İçin TS İşleme ve M3U8 Oluşturma Başlatıldı...\n")

        for ch in CHANNELS:
            print(f"[İŞLENİYOR] {ch['name']}...")
            master_url = get_stream_via_unaux(ch["slug"], page)
            
            if master_url:
                processed_content = process_ts_playlist(master_url)
                if processed_content:
                    filename = f"{ch['slug']}.m3u8"
                    with open(filename, "w", encoding="utf-8") as f:
                        f.write(processed_content)
                    print(f"  -> Başarılı! Kaydedildi: {filename}")
                else:
                    print(f"  -> Uyarı: TS içerikleri işlenemedi.")
            else:
                print(f"  -> Hata: Ana m3u8 linki bulunamadı.")

        browser.close()
    print("\nTüm işlemler tamamlandı.")

if __name__ == "__main__":
    generate_all_channels()
