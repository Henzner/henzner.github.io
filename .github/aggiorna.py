"""Aggiorna le caselle del sito dai feed pubblici di YouTube.

Riscrive solo le parti tra i marcatori <!-- auto:nome --> e <!-- /auto:nome -->.
Se un feed non risponde esce senza toccare niente: il sito resta com'è.
"""
import html
import pathlib
import re
import sys
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
FILES_ID = "7na3KraAe6-3LGP6lkcR4A"
GAMES_ID = "JcDx-q7tjyligH3BPGXZ7Q"
MESI = "gen feb mar apr mag giu lug ago set ott nov dic".split()
MONTHS = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()
LETTERS = "abcdefghijklmnopqrstuvwxyz"
EXT = 'target="_blank" rel="noopener"'


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "henzner-site"})
    return urllib.request.urlopen(req, timeout=20).read().decode("utf-8")


def feed(cid, prefix, kind):
    xml = fetch(f"https://www.youtube.com/feeds/videos.xml?playlist_id={prefix}{cid}")
    items = []
    for e in xml.split("<entry>")[1:]:
        vid = re.search(r"<yt:videoId>(.*?)<", e).group(1)
        full = html.unescape(re.search(r"<title>(.*?)</title>", e).group(1))
        title = re.sub(r"\s*#\S+", "", full.split(" | ")[0])
        title = re.sub(r"[\U0001F000-\U0001FFFF☀-➿️]+\s*", "", title).strip()
        stamp = re.search(r"<published>(.*?)<", e).group(1)
        _, m, d = stamp[:10].split("-")
        items.append({
            "vid": vid, "title": title, "kind": kind, "day": stamp[:10],
            "date": f"{int(d)} {MESI[int(m) - 1]}", "date_en": f"{MONTHS[int(m) - 1]} {int(d)}",
        })
    return items


def load(cid):
    items = feed(cid, "UULF", "Video") + feed(cid, "UUSH", "Short")
    # dal più recente; nello stesso giorno prima il video, poi gli Short
    items.sort(key=lambda x: x["kind"] != "Video")
    items.sort(key=lambda x: x["day"], reverse=True)
    if not items:
        raise ValueError(f"feed vuoto per {cid}")
    return items


def exists(url):
    try:
        return urllib.request.urlopen(urllib.request.Request(url, method="HEAD"), timeout=10).status == 200
    except urllib.error.URLError:
        return False


def image(it):
    vid = it["vid"]
    name = "oar2" if it["kind"] == "Short" else "maxresdefault"
    url = f"https://i.ytimg.com/vi/{vid}/{name}.jpg"
    return url if exists(url) else f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg"


def card(el, grp, num, it):
    short = it["kind"] == "Short"
    vid = it["vid"]
    href = f"https://www.youtube.com/shorts/{vid}" if short else f"https://www.youtube.com/watch?v={vid}"
    cls = " tall" if short else ""
    title = html.escape(it["title"], quote=False)
    return f'''<a class="el {el} sub media{cls}" href="{href}" {EXT}>
    <div class="shot"><img src="{image(it)}" alt="" loading="lazy"></div>
    <div class="top"><span class="num">{num}</span><span class="grp">{grp}</span></div>
    <div class="name"><strong>{title}</strong><span data-en="{it["kind"]} · {it["date_en"]}">{it["kind"]} · {it["date"]}</span></div>
    <span class="tag">{it["kind"]}</span>
  </a>'''


def minis(items):
    return '<div class="minis">' + "".join(f'<img src="{image(i)}" alt="" loading="lazy">' for i in items) + "</div>"


def preview(items):
    """Ultimo video e ultimi due Short, come nelle anteprime della home."""
    videos = [i for i in items if i["kind"] == "Video"][:1]
    shorts = [i for i in items if i["kind"] == "Short"]
    return (videos + shorts)[:3]


def put(text, name, value):
    pattern = re.compile(rf"(<!-- auto:{name} -->\n).*?(\s*<!-- /auto:{name} -->)", re.S)
    text, n = pattern.subn(lambda m: m.group(1) + value + m.group(2), text)
    if n != 1:
        raise ValueError(f"marcatore {name}: trovati {n}")
    return text


def main():
    files = load(FILES_ID)
    games = load(GAMES_ID)

    # Henzner Files
    f_video = [card("files", "YouTube", f"02.{LETTERS[n]}", it) for n, it in enumerate(files) if it["kind"] == "Video"]
    f_short = [card("files", "YouTube", f"02.{LETTERS[n]}", it) for n, it in enumerate(files) if it["kind"] == "Short"]
    nxt = f"02.{LETTERS[len(files)]}"
    f_short.append(f'<div class="el empty tall" data-en="{nxt} — NEXT STORY">{nxt} — PROSSIMA STORIA</div>')

    p = ROOT / "files.html"
    t = p.read_text(encoding="utf-8")
    t = put(t, "conteggio", f'    <span class="count" data-en="{len(f_video)} videos · {len(f_short) - 1} Shorts">{len(f_video)} video · {len(f_short) - 1} Short</span>')
    t = put(t, "video", "  " + "\n  ".join(f_video))
    t = put(t, "short", "  " + "\n  ".join(f_short))
    p.write_text(t, encoding="utf-8")

    # Henzner Games: 03.a è l'evento, il feed parte da 03.b
    g_video = [card("games", "Games", f"03.{LETTERS[n + 1]}", it) for n, it in enumerate(games) if it["kind"] == "Video"]
    g_short = [card("games", "Games", f"03.{LETTERS[n + 1]}", it) for n, it in enumerate(games) if it["kind"] == "Short"]
    p = ROOT / "games.html"
    t = p.read_text(encoding="utf-8")
    t = put(t, "conteggio", f'    <span class="count" data-en="1 game · {len(g_video)} video{"s" if len(g_video) != 1 else ""} · {len(g_short)} Shorts">1 gioco · {len(g_video)} video · {len(g_short)} Short</span>')
    t = put(t, "video", "  " + "\n  ".join(g_video))
    t = put(t, "short", "  " + "\n  ".join(g_short))
    p.write_text(t, encoding="utf-8")

    # Home
    last = html.escape(files[0]["title"], quote=True)
    p = ROOT / "index.html"
    t = p.read_text(encoding="utf-8")
    t = put(t, "files-anteprime", "    " + minis(preview(files)))
    t = put(t, "files-nota", f'    <span class="note" data-en="Latest: {last}">Ultimo: {last}</span>')
    t = put(t, "games-anteprime", "    " + minis(preview(games)))
    p.write_text(t, encoding="utf-8")
    print("ok", len(files), "Files,", len(games), "Games")


if __name__ == "__main__":
    try:
        main()
    except (urllib.error.URLError, ValueError, AttributeError, TimeoutError) as e:
        print("niente aggiornamento:", e)
        sys.exit(0)
