# Zakamsk yatırım sitesi (taslak)

Statik, 7 dilli site. Sadece Python 3 gerekir; Pillow kuruluysa WebP, favicon ve paylaşım görseli de üretilir.

```
site/
  config.json          site adresi, e-posta, telefon, diller, görseller, form_endpoint, plausible_domain
  src/partials/        head, header, footer (tüm sayfalarda ortak)
  src/pages/           index.html (ana sayfa), legal.html (künye + gizlilik)
  src/styles.css       tüm stiller (açık/koyu mod otomatik)
  src/main.js          animasyon, mobil menü, dil menüsü, harita onayı, form
  src/fonts/           kendi sunucumuzdan sunulan Onest fontu + Phosphor ikonları
  i18n/<dil>.json      en, uk, ru, pl, de, fr, tr metinleri (anahtarlar en.json ile aynı olmalı)
  build.py             dist/ klasörünü üretir
```

## Derleme ve önizleme

```bash
python3 build.py
python3 -m http.server 4321 --directory dist
```

http://localhost:4321 açılır, tarayıcı diline göre `/en/`, `/uk/`... sayfasına yönlendirir. Künye/gizlilik sayfası: `/<dil>/legal/`.

Metin değiştirmek için ilgili `i18n/*.json` dosyasını düzenleyip `build.py`'yi yeniden çalıştırın. Bir dilde eksik anahtar varsa build hata verir.

## GitHub + Vercel ile yayın

Bu klasör (`site/`) tek başına bir git deposudur; kullanılan görseller `src/img/` içindedir. Vercel her `git push` sonrası `vercel.json`'daki komutla (`pip3 install -r requirements.txt && python3 build.py`) siteyi derler ve `dist/` klasörünü yayınlar. `dist/` repoya eklenmez.

- **Test modu:** `config.json` → `"noindex": true` iken site arama motorlarına kapalıdır. Ayrıca `vercel.json`'daki `X-Robots-Tag` başlığı da aynı işi yapar. Gerçek yayında ikisi de kaldırılmalı.
- Vercel'de proje ayarı: Framework Preset **Other**, Root Directory boş (repo kökü). Build/Output ayarları `vercel.json`'dan gelir.

## Neler hazır

- 7 dil, her dil ayrı adreste (SEO: hreflang, canonical, sitemap.xml, robots.txt, JSON-LD)
- Fontlar ve ikonlar kendi sunucumuzdan (Google/CDN isteği yok; GDPR açısından temiz)
- Harita yalnızca ziyaretçi "Haritayı göster"e tıklayınca yüklenir
- Mobil menü, klavye erişimi, açık/koyu mod
- Künye + gizlilik politikası sayfası (7 dil)
- Form: spam tuzağı (honeypot), gönderim/başarı/hata durumları
- WebP görseller (yalnızca gerçekten küçükse), favicon, sosyal medya paylaşım görseli (og.jpg)
- Resmî kaynaklı piyasa verileri (Norveç Deniz Ürünleri Konseyi, Ukrayna Bakanlar Kurulu, UIFSA)

## Yayına almadan önce yapılacaklar

- [ ] **Form servisi:** formspree.io'da ücretsiz hesap açıp form oluşturun, verilen adresi `config.json` → `form_endpoint` alanına yazın (ör. `https://formspree.io/f/xxxxxx`). Boş kalırsa form ziyaretçinin e-posta uygulamasını açar.
- [ ] **Alan adı:** `config.json` → `site_url` gerçek adresle değişecek.
- [ ] **Ziyaretçi ölçümü (isteğe bağlı):** Plausible hesabı açılırsa alan adını `plausible_domain` alanına yazın.
- [ ] Yatırım tutarları ("To be confirmed" rozetleri) ve EDRPOU kodu (künye sayfası).
- [ ] Vektör logo, yüksek çözünürlüklü fotoğraflar.
- [ ] Mersin balığı fotoğrafı ve tatil merkezi renderı için teyit/izin.
- [ ] Çevirilerin anadili konuşanlarca kontrolü; gizlilik metninin bir hukukçu tarafından kontrolü.
