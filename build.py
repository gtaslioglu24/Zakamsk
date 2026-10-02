#!/usr/bin/env python3
"""Builds the static multilingual site into dist/.

Usage:  python3 build.py
Output: dist/<lang>/index.html and dist/<lang>/legal/index.html for every
        language in config.json, dist/index.html (redirects by browser
        language), dist/assets/*, dist/sitemap.xml, dist/robots.txt.

Needs Python 3 (stdlib). If Pillow is installed, WebP copies, favicon and the
Open Graph image are generated too.
"""
import datetime
import html
import json
import re
import shutil
from pathlib import Path

try:
    from PIL import Image
except ImportError:  # WebP / favicon generation is optional
    Image = None

ROOT = Path(__file__).parent
SRC = ROOT / "src"
DIST = ROOT / "dist"
cfg = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
langs = cfg["languages"]
codes = [l["code"] for l in langs]
default = cfg["default_lang"]
site = cfg["site_url"].rstrip("/")
base = json.loads((ROOT / "i18n" / f"{default}.json").read_text(encoding="utf-8"))
BUILD_ID = datetime.datetime.now().strftime("%Y%m%d%H%M%S")

OG_LOCALE = {"en": "en_GB", "uk": "uk_UA", "ru": "ru_RU", "pl": "pl_PL", "de": "de_DE", "fr": "fr_FR", "tr": "tr_TR"}

# page key -> (template file, output sub-path, asset prefix, link back to the home page)
PAGES = {
    "index": ("index.html", "", "../", ""),
    "legal": ("legal.html", "legal/", "../../", "../"),
}

# Values that contain markup (everything else is HTML-escaped).
RAW_KEYS = {"hreflang_links", "lang_menu_items", "lang_links", "head_extra", "analytics", "robots_meta"}
NOINDEX = bool(cfg.get("noindex"))  # test/preview mode: keep search engines out


def load_partials():
    return {p.stem: p.read_text(encoding="utf-8") for p in (SRC / "partials").glob("*.html")}


def expand(tpl: str, partials: dict) -> str:
    return re.sub(r"\{\{>\s*(\w+)\s*\}\}", lambda m: partials[m.group(1)], tpl)


def analytics_snippet() -> str:
    domain = cfg.get("plausible_domain", "").strip()
    if not domain:
        return ""
    return f'  <script defer data-domain="{html.escape(domain)}" src="https://plausible.io/js/script.js"></script>'


def json_ld(strings: dict, lang: str) -> str:
    data = {
        "@context": "https://schema.org",
        "@type": "Organization",
        "name": "Zakamsk",
        "legalName": strings["legal_name"],
        "url": f"{site}/{lang}/",
        "logo": f"{site}/assets/img/logo.jpg",
        "email": cfg["contact_email"],
        "telephone": cfg["phone_primary"],
        "address": {"@type": "PostalAddress", "addressLocality": "Berlohy", "addressRegion": "Ivano-Frankivsk", "postalCode": "77600", "addressCountry": "UA"},
        "founder": {"@type": "Person", "name": "Marian Pasternak"},
        "foundingDate": "2014",
    }
    return '  <script type="application/ld+json">' + json.dumps(data, ensure_ascii=False) + "</script>"


def use_webp(markup: str, root: str) -> str:
    """Wrap photo <img> tags in <picture> with a WebP source when one was generated."""
    if Image is None:
        return markup

    def repl(m):
        tag, name = m.group(0), m.group(1)
        if name == "logo.jpg" or not (DIST / "assets" / "img" / (Path(name).stem + ".webp")).exists():
            return tag
        webp = f"{root}assets/img/{Path(name).stem}.webp"
        return f'<picture><source srcset="{webp}" type="image/webp">{tag}</picture>'

    return re.sub(r'<img [^>]*src="[^"]*assets/img/([\w.-]+\.(?:jpe?g|png))"[^>]*>', repl, markup)


def render(page: str, lang: str, partials: dict) -> str:
    strings = json.loads((ROOT / "i18n" / f"{lang}.json").read_text(encoding="utf-8"))
    missing = sorted(set(base) - set(strings))
    if missing:
        raise SystemExit(f"[{lang}] missing keys: {', '.join(missing)}")
    extra = sorted(set(strings) - set(base))
    if extra:
        print(f"  warning [{lang}] unused keys: {', '.join(extra)}")

    tpl_file, sub, root, home = PAGES[page]
    tpl = expand((SRC / "pages" / tpl_file).read_text(encoding="utf-8"), partials)
    ctx = dict(strings)
    head_extra = [json_ld(strings, lang)]
    if page == "index":
        ext, mime = ("webp", "image/webp") if Image else ("jpg", "image/jpeg")
        head_extra.insert(0, f'  <link rel="preload" as="image" href="{root}assets/img/hero.{ext}" type="{mime}">')
    ctx.update(
        lang=lang,
        root=root,
        home=home,
        year=str(datetime.date.today().year),
        build_id=BUILD_ID,
        site_url=site,
        og_locale=OG_LOCALE.get(lang, lang),
        page_title=strings["meta_title"] if page == "index" else f'{strings["legal_title"]} | Zakamsk',
        canonical=f"{site}/{lang}/{sub}",
        legal_href=f"{root}{lang}/legal/",
        contact_email=cfg["contact_email"],
        phone_primary=cfg["phone_primary"],
        phone_primary_raw=re.sub(r"[^\d+]", "", cfg["phone_primary"]),
        form_endpoint=cfg.get("form_endpoint", ""),
        head_extra="\n".join(head_extra),
        analytics=analytics_snippet(),
        robots_meta='  <meta name="robots" content="noindex, nofollow">' if NOINDEX else "",
        hreflang_links="\n".join(
            [f'  <link rel="alternate" hreflang="{c}" href="{site}/{c}/{sub}">' for c in codes]
            + [f'  <link rel="alternate" hreflang="x-default" href="{site}/{default}/{sub}">']
        ),
        lang_current=next(l["name"] for l in langs if l["code"] == lang),
        lang_menu_items="\n".join(
            f'          <li><a href="{root}{l["code"]}/{sub}" hreflang="{l["code"]}" lang="{l["code"]}" data-code="{l["code"]}"'
            + (' aria-current="page"' if l["code"] == lang else "")
            + f'>{l["name"]}</a></li>'
            for l in langs
        ),
        lang_links="\n".join(
            f'      <a href="{root}{l["code"]}/{sub}" hreflang="{l["code"]}" lang="{l["code"]}"'
            + (' aria-current="page"' if l["code"] == lang else "")
            + f'>{l["name"]}</a>'
            for l in langs
        ),
    )

    def sub_key(m):
        key = m.group(1)
        if key not in ctx:
            raise SystemExit(f"[{lang}/{page}] template key not defined: {key}")
        val = ctx[key]
        return val if key in RAW_KEYS else html.escape(val, quote=True)

    out = re.sub(r"\{\{\s*([\w.]+)\s*\}\}", sub_key, tpl)
    out = use_webp(out, root)
    if "—" in out:
        print(f"  warning [{lang}/{page}] contains an em-dash")
    return out


def build_fonts(pages_markup: str):
    """Copy self-hosted fonts and keep only the icon rules the pages actually use."""
    fonts_out = DIST / "assets" / "fonts"
    fonts_out.mkdir(parents=True)
    for f in (SRC / "fonts").glob("*.woff2"):
        shutil.copy(f, fonts_out / f.name)
    used = sorted(set(re.findall(r"\bph-([a-z0-9-]+)", pages_markup)))
    icons = (SRC / "fonts" / "icons-all.css").read_text(encoding="utf-8")
    rules = []
    for name in used:
        m = re.search(r"\.ph\.ph-" + re.escape(name) + r":before \{\s*content: (\"[^\"]+\");\s*\}", icons)
        if m:
            rules.append(f".ph.ph-{name}:before {{ content: {m.group(1)}; }}")
        else:
            print(f"  warning: icon not found: ph-{name}")
    css = (SRC / "fonts" / "fonts-base.css").read_text(encoding="utf-8") + "\n" + "\n".join(rules) + "\n"
    (fonts_out / "fonts.css").write_text(css, encoding="utf-8")


def build_images():
    img_out = DIST / "assets" / "img"
    for name, src in cfg["images"].items():
        shutil.copy(ROOT / src, img_out / name)
    if Image is None:
        print("  note: Pillow not installed, skipping WebP/favicon generation")
        return
    for f in list(img_out.glob("*.jp*g")):
        if f.name == "logo.jpg":
            continue
        with Image.open(f) as im:
            im = im.convert("RGB")
            if im.width > 1600:
                im = im.resize((1600, round(im.height * 1600 / im.width)), Image.LANCZOS)
            webp = img_out / (f.stem + ".webp")
            im.save(webp, "WEBP", quality=74, method=6)
            if webp.stat().st_size >= f.stat().st_size * 0.9:  # keep WebP only when it clearly saves bytes
                webp.unlink()
    with Image.open(img_out / "logo.jpg") as logo:
        logo = logo.convert("RGB")
        for size, name in ((64, "favicon-64.png"), (180, "apple-touch-icon.png")):
            canvas = Image.new("RGB", (size, size), (255, 255, 255))
            lg = logo.copy()
            lg.thumbnail((int(size * .9), int(size * .9)), Image.LANCZOS)
            canvas.paste(lg, ((size - lg.width) // 2, (size - lg.height) // 2))
            canvas.save(img_out / name)
    with Image.open(img_out / "hero.jpg") as hero:  # 1200x630 social preview
        hero = hero.convert("RGB")
        h = round(hero.width * 630 / 1200)
        top = max(0, min(hero.height - h, round(hero.height * .62 - h / 2)))
        hero.crop((0, top, hero.width, top + h)).resize((1200, 630), Image.LANCZOS).save(img_out / "og.jpg", quality=85)


def main():
    if DIST.exists():
        shutil.rmtree(DIST)
    (DIST / "assets" / "img").mkdir(parents=True)
    shutil.copy(SRC / "styles.css", DIST / "assets" / "styles.css")
    shutil.copy(SRC / "main.js", DIST / "assets" / "main.js")
    build_images()

    partials = load_partials()
    all_markup = "".join(expand((SRC / "pages" / p[0]).read_text(encoding="utf-8"), partials) for p in PAGES.values())
    build_fonts(all_markup + (SRC / "main.js").read_text(encoding="utf-8"))

    for code in codes:
        for page, (_, sub, _, _) in PAGES.items():
            out = DIST / code / sub
            out.mkdir(parents=True, exist_ok=True)
            (out / "index.html").write_text(render(page, code, partials), encoding="utf-8")
        print(f"  built /{code}/")

    # Root: pick language from saved choice or browser, fallback to default.
    links = "".join(f'<li><a href="{l["code"]}/">{l["name"]}</a></li>' for l in langs)
    (DIST / "index.html").write_text(
        f"""<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Zakamsk</title>
<script>(function(){{var s={json.dumps(codes)},l;try{{l=localStorage.getItem("lang")}}catch(e){{}}
if(!l||s.indexOf(l)<0){{var n=(navigator.languages||[navigator.language||""]);for(var i=0;i<n.length;i++){{var c=(n[i]||"").slice(0,2).toLowerCase();if(c==="ua")c="uk";if(s.indexOf(c)>=0){{l=c;break}}}}}}
location.replace((l||"{default}")+"/");}})();</script></head>
<body><ul>{links}</ul></body></html>""",
        encoding="utf-8",
    )

    urls = "".join(f"<url><loc>{site}/{c}/{sub}</loc></url>" for c in codes for (_, sub, _, _) in PAGES.values())
    (DIST / "sitemap.xml").write_text(
        f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>',
        encoding="utf-8",
    )
    if NOINDEX:
        (DIST / "robots.txt").write_text("User-agent: *\nDisallow: /\n", encoding="utf-8")
    else:
        (DIST / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {site}/sitemap.xml\n", encoding="utf-8")

    print("done ->", DIST)


if __name__ == "__main__":
    main()
