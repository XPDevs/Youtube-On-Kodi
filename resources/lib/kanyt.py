import html as _html
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

FEED_TMPL = "https://www.youtube.com/feeds/videos.xml?channel_id={}"
WATCH_URL = "https://www.youtube.com/watch?v={}"
CHANNEL_VIDEOS_URL = "https://www.youtube.com/channel/{}/videos"
RESULTS_URL = "https://www.youtube.com/results?search_query={}"
THUMB = "https://i.ytimg.com/vi/{}/hqdefault.jpg"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"

FFMPEG_DIRS = [
    "/storage/.kodi/addons/tools.ffmpeg-tools/bin",
    os.environ.get("MYYT_FFMPEG_DIR", ""),
]


def find_ffmpeg_dir():
    exe = shutil.which("ffmpeg")
    if exe:
        return os.path.dirname(exe)
    for d in FFMPEG_DIRS:
        if d and os.path.exists(os.path.join(d, "ffmpeg")):
            return d
    return None


def find_ytdlp():
    here = os.path.dirname(os.path.abspath(__file__))
    for cand in (os.path.join(here, "..", "bin", "yt-dlp"), os.path.join(here, "yt-dlp")):
        if os.path.exists(cand):
            return cand
    return "yt-dlp"


def find_python():
    if getattr(sys, "executable", None) and os.path.exists(sys.executable):
        return sys.executable
    for name in ("python3", "python"):
        found = shutil.which(name)
        if found:
            return found
    return "python3"


def _js_runtimes():
    return [n for n in ("deno", "node", "nodejs") if shutil.which(n)]


def _failed(msg):
    return type("R", (), {"returncode": -1, "stdout": "", "stderr": msg})()


_STUB_DIR = None


def _stub_dir():
    global _STUB_DIR
    if _STUB_DIR is None:
        _STUB_DIR = tempfile.mkdtemp(prefix="myyt_stubs_")
        for mod in ("secretstorage", "cryptography", "_cffi_backend"):
            with open(os.path.join(_STUB_DIR, mod + ".py"), "w") as f:
                f.write("raise ImportError('blocked by myyoutubers')\n")
    return _STUB_DIR


def build_ytdlp_cmd(args):
    cmd = [find_python(), find_ytdlp(), "--no-update"]
    rt = _js_runtimes()
    if rt:
        cmd += ["--js-runtimes", ",".join(rt)]
    ffdir = find_ffmpeg_dir()
    if ffdir:
        cmd += ["--ffmpeg-location", ffdir]
    cmd += args
    env = dict(os.environ)
    stub = _stub_dir()
    env["PYTHONPATH"] = (
        stub
        + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    )
    if ffdir:
        env["PATH"] = ffdir + os.pathsep + env.get("PATH", "")
    return cmd, env


def _run_ytdlp(args, timeout=180, live=False):
    cmd, env = build_ytdlp_cmd(args)
    try:
        if live:
            return subprocess.run(cmd, timeout=timeout, env=env)
        return subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout, env=env
        )
    except subprocess.TimeoutExpired:
        return _failed("timed out")
    except OSError as e:
        return _failed(str(e))


def _get_page(url, timeout=25):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", "ignore")


def _channel_url(query):
    if re.match(r"^https?://", query, re.IGNORECASE):
        return query
    if re.fullmatch(r"UC[\w-]{22}", query):
        return "https://www.youtube.com/channel/" + query
    if query.startswith("@"):
        return "https://www.youtube.com/" + query
    handle = "@" + re.sub(r"[^A-Za-z0-9_.-]", "", query.replace(" ", ""))
    return "https://www.youtube.com/" + handle


def _scrape_channel(query):
    url = _channel_url(query)
    try:
        page = _get_page(url)
    except Exception:
        return None
    m = re.search(r'canonical" href="https://www\.youtube\.com/channel/(UC[\w-]{22})', page)
    if not m:
        m = re.search(r'"channelId"\s*:\s*"(UC[\w-]{22})"', page)
    if not m:
        return None
    cid = m.group(1)
    name = None
    nm = re.search(
        r'"channelMetadataRenderer":\{[^{}]*?"title":"((?:[^"\\]|\\.)*)"', page
    )
    if nm:
        try:
            name = _html.unescape(json.loads('"' + nm.group(1) + '"'))
        except Exception:
            name = None
    return {"id": cid, "name": name or query}


def _scrape_videos(url, limit=30):
    try:
        page = _get_page(url)
    except Exception:
        return []
    videos = []
    marker = '"videoRenderer":{"videoId":"'
    idx = 0
    while len(videos) < limit:
        i = page.find(marker, idx)
        if i < 0:
            break
        i += len(marker)
        vid = page[i:i + 11]
        if not re.fullmatch(r"[\w-]{11}", vid):
            idx = i + 11
            continue
        seg = page[i + 11:i + 11 + 4000]
        title = vid
        tm = re.search(r'"title":\{"runs":\[\{"text":"((?:[^"\\]|\\.)*)"', seg)
        if tm:
            try:
                title = _html.unescape(json.loads('"' + tm.group(1) + '"'))
            except Exception:
                title = vid
        channel_id = None
        cm = re.search(r'"browseId":"(UC[\w-]{22})"', seg)
        if cm:
            channel_id = cm.group(1)
        view_count = None
        vm = re.search(
            r'"(?:shortViewCountText|viewCountText)":\{"simpleText":"((?:[^"\\]|\\.)*)"',
            seg,
        )
        if vm:
            try:
                txt = json.loads('"' + vm.group(1) + '"')
            except Exception:
                txt = vm.group(1)
            mc = re.search(r"([\d,.]+) views?", txt)
            if mc:
                view_count = int(mc.group(1).replace(",", ""))
        videos.append(
            {
                "id": vid,
                "title": title,
                "url": WATCH_URL.format(vid),
                "thumb": THUMB.format(vid),
                "channel": None,
                "channel_id": channel_id,
                "view_count": view_count,
            }
        )
        idx = i + 11
    return videos


def _entry_to_result(e):
    if not e or not e.get("id"):
        return None
    if e.get("ie_key") == "YoutubeTab":
        pid = e["id"]
        if pid.startswith("UC"):
            return {
                "type": "channel",
                "id": pid,
                "title": (e.get("title") or "").strip(),
                "url": "https://www.youtube.com/channel/" + pid,
                "thumb": e.get("thumbnail") or "",
            }
        return {
            "type": "playlist",
            "id": pid,
            "title": (e.get("title") or "").strip(),
            "url": "https://www.youtube.com/playlist?list=" + pid,
            "thumb": e.get("thumbnail") or "",
        }
    v = _entry_to_video(e)
    if v:
        v["type"] = "video"
    return v


def _entry_to_video(e):
    if not e or not e.get("id"):
        return None
    return {
        "type": "video",
        "id": e["id"],
        "title": (e.get("title") or "").strip(),
        "url": WATCH_URL.format(e["id"]),
        "thumb": THUMB.format(e["id"]),
        "channel": e.get("channel"),
        "channel_id": e.get("channel_id"),
    }


def read_channels_conf(path):
    channels = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "|" in line:
                query, name = [p.strip() for p in line.split("|", 1)]
            else:
                query, name = line, None
            channels.append({"query": query, "name": name})
    return channels


def resolve_channel(query):
    query = query.strip()
    if not query:
        return None
    ch = _scrape_channel(query)
    if ch:
        return ch
    if _js_runtimes():
        url = _channel_url(query)
        p = _run_ytdlp(
            [
                "--skip-download",
                "--no-warnings",
                "--print",
                "%(channel_id)s",
                "--print",
                "%(channel)s",
                url,
            ],
            timeout=30,
        )
        lines = [l for l in p.stdout.strip().splitlines() if l.strip()]
        if p.returncode == 0 and len(lines) >= 2:
            return {"id": lines[0], "name": lines[1]}
    return None


def resolve_cached(query, cache_dir):
    cache_file = os.path.join(cache_dir, "channels.json")
    data = {}
    if os.path.exists(cache_file):
        try:
            with open(cache_file) as f:
                data = json.load(f)
        except (OSError, ValueError):
            data = {}
    if query not in data:
        ch = resolve_channel(query)
        if ch:
            data[query] = ch
            os.makedirs(cache_dir, exist_ok=True)
            with open(cache_file, "w") as f:
                json.dump(data, f, indent=2)
        else:
            return None
    return data[query]


def get_channel_videos(channel_id, cache_dir, end=60, timeout=180):
    cache_file = os.path.join(cache_dir, channel_id + ".json")
    videos = []
    cached_end = 0
    if os.path.exists(cache_file):
        try:
            with open(cache_file) as f:
                data = json.load(f)
            videos = data.get("videos", [])
            cached_end = data.get("end", len(videos))
        except (OSError, ValueError):
            videos, cached_end = [], 0
    if cached_end < end:
        p = _run_ytdlp(
            [
                "--flat-playlist",
                "-J",
                "--playlist-items",
                "1-{}".format(end),
                "--no-warnings",
                CHANNEL_VIDEOS_URL.format(channel_id),
            ],
            timeout=timeout,
        )
        if p.returncode == 0:
            try:
                data = json.loads(p.stdout)
                videos = [_entry_to_video(e) for e in data.get("entries", [])]
                videos = [v for v in videos if v]
                cached_end = end
            except ValueError:
                pass
        if not videos:
            try:
                videos = get_latest_videos(channel_id, limit=15)
                cached_end = len(videos)
            except Exception:
                videos, cached_end = [], 0
        if videos:
            os.makedirs(cache_dir, exist_ok=True)
            with open(cache_file, "w") as f:
                json.dump({"end": cached_end, "videos": videos}, f)
    return videos[:end]


def get_channel_playlists(channel_id, cache_dir, timeout=90):
    cache_file = os.path.join(cache_dir, "plists_" + channel_id + ".json")
    playlists = []
    if os.path.exists(cache_file):
        try:
            with open(cache_file) as f:
                playlists = json.load(f)
            if playlists:
                return playlists
        except (OSError, ValueError):
            playlists = []
    url = "https://www.youtube.com/channel/{}/playlists".format(channel_id)
    p = _run_ytdlp(
        ["--flat-playlist", "-J", "--no-warnings", url],
        timeout=timeout,
    )
    if p.returncode == 0:
        try:
            data = json.loads(p.stdout)
            for e in data.get("entries", []):
                if not e or not e.get("id"):
                    continue
                playlists.append(
                    {
                        "id": e["id"],
                        "title": (e.get("title") or "").strip(),
                        "url": "https://www.youtube.com/playlist?list=" + e["id"],
                    }
                )
        except ValueError:
            playlists = []
    if playlists:
        os.makedirs(cache_dir, exist_ok=True)
        with open(cache_file, "w") as f:
            json.dump(playlists, f)
    return playlists


def get_playlist_videos(playlist_url, cache_dir, end=30, timeout=90):
    cache_file = os.path.join(
        cache_dir,
        "plist_" + hashlib.sha1(playlist_url.encode("utf-8", "ignore")).hexdigest() + ".json",
    )
    videos, cached_end = [], 0
    if os.path.exists(cache_file):
        try:
            with open(cache_file) as f:
                data = json.load(f)
            videos = data.get("videos", [])
            cached_end = data.get("end", len(videos))
        except (OSError, ValueError):
            videos, cached_end = [], 0
    if cached_end < end:
        p = _run_ytdlp(
            [
                "--flat-playlist",
                "-J",
                "--no-warnings",
                "--playlist-items",
                "1-{}".format(end),
                playlist_url,
            ],
            timeout=timeout,
        )
        if p.returncode == 0:
            try:
                data = json.loads(p.stdout)
                videos = [_entry_to_video(e) for e in data.get("entries", [])]
                videos = [v for v in videos if v]
                cached_end = end
            except ValueError:
                pass
        if videos:
            os.makedirs(cache_dir, exist_ok=True)
            with open(cache_file, "w") as f:
                json.dump({"end": cached_end, "videos": videos}, f)
    return videos[:end]


def get_latest_videos(channel_id, limit=15):
    url = FEED_TMPL.format(channel_id)
    with urllib.request.urlopen(url, timeout=20) as resp:
        root = ET.fromstring(resp.read())
    ns = {
        "a": "http://www.w3.org/2005/Atom",
        "yt": "http://www.youtube.com/xml/schemas/2015",
    }
    out = []
    for entry in root.findall("a:entry", ns)[:limit]:
        vid = entry.find("yt:videoId", ns).text.strip()
        title = entry.find("a:title", ns).text.strip()
        published = entry.find("a:published", ns).text.strip()
        out.append(
            {
                "id": vid,
                "title": title,
                "published": published,
                "url": WATCH_URL.format(vid),
                "thumb": THUMB.format(vid),
            }
        )
    return out


def search_youtube(query, count=20):
    p = _run_ytdlp(
        [
            "--flat-playlist",
            "-J",
            "--no-warnings",
            "ytsearch{}:{}".format(count, query),
        ],
        timeout=90,
    )
    if p.returncode == 0:
        try:
            data = json.loads(p.stdout)
            videos = [_entry_to_video(e) for e in data.get("entries", [])]
            videos = [v for v in videos if v]
            if videos:
                return videos
        except ValueError:
            pass
    return _scrape_videos(RESULTS_URL.format(urllib.parse.quote(query)), limit=count)


def search_cached(query, cache_dir, end, timeout=90):
    cache_file = os.path.join(
        cache_dir, "search_" + hashlib.sha1(query.encode("utf-8", "ignore")).hexdigest() + ".json"
    )
    entries, cached_end = [], 0
    if os.path.exists(cache_file):
        try:
            with open(cache_file) as f:
                data = json.load(f)
            entries = data.get("entries") or data.get("videos", [])
            cached_end = data.get("end", len(entries))
        except (OSError, ValueError):
            entries, cached_end = [], 0
    if cached_end < end:
        url = RESULTS_URL.format(urllib.parse.quote(query))
        p = _run_ytdlp(
            [
                "--flat-playlist",
                "-J",
                "--no-warnings",
                "--playlist-items",
                "1-{}".format(end),
                url,
            ],
            timeout=timeout,
        )
        entries = []
        if p.returncode == 0:
            try:
                data = json.loads(p.stdout)
                entries = [_entry_to_result(e) for e in data.get("entries", [])]
                entries = [e for e in entries if e]
            except ValueError:
                entries = []
        if not entries:
            try:
                p2 = _run_ytdlp(
                    [
                        "--flat-playlist",
                        "-J",
                        "--no-warnings",
                        "ytsearch{}:{}".format(end, query),
                    ],
                    timeout=timeout,
                )
                if p2.returncode == 0:
                    data2 = json.loads(p2.stdout)
                    entries = [_entry_to_video(e) for e in data2.get("entries", [])]
                    entries = [e for e in entries if e]
            except Exception:
                entries = []
        if not entries:
            try:
                entries = _scrape_videos(url, limit=end)
            except Exception:
                entries = []
        cached_end = len(entries)
        if entries:
            os.makedirs(cache_dir, exist_ok=True)
            with open(cache_file, "w") as f:
                json.dump({"end": cached_end, "entries": entries}, f)
    return entries[:end]


def search_playlists_cached(query, cache_dir, end, timeout=90):
    cache_file = os.path.join(
        cache_dir,
        "psrch_" + hashlib.sha1(query.encode("utf-8", "ignore")).hexdigest() + ".json",
    )
    playlists, cached_end = [], 0
    if os.path.exists(cache_file):
        try:
            with open(cache_file) as f:
                data = json.load(f)
            playlists = data.get("playlists", [])
            cached_end = data.get("end", len(playlists))
        except (OSError, ValueError):
            playlists, cached_end = [], 0
    if cached_end < end:
        url = RESULTS_URL.format(urllib.parse.quote(query))
        p = _run_ytdlp(
            [
                "--flat-playlist",
                "-J",
                "--no-warnings",
                "--playlist-items",
                "1-{}".format(end),
                url,
            ],
            timeout=timeout,
        )
        if p.returncode == 0:
            try:
                data = json.loads(p.stdout)
                playlists = [
                    e
                    for e in data.get("entries", [])
                    if e
                    and e.get("ie_key") == "YoutubeTab"
                    and e.get("id", "").startswith(("PL", "PLAY"))
                ]
                playlists = [_entry_to_result(e) for e in playlists]
                playlists = [p for p in playlists if p]
            except ValueError:
                playlists = []
        cached_end = len(playlists)
        if playlists:
            os.makedirs(cache_dir, exist_ok=True)
            with open(cache_file, "w") as f:
                json.dump({"end": cached_end, "playlists": playlists}, f)
    return playlists[:end]


def popular_videos(channels, limit=30):
    out = {}
    for cid, name in channels:
        if not name:
            continue
        try:
            vids = _scrape_videos(
                RESULTS_URL.format(urllib.parse.quote(name)), limit=30
            )
        except Exception:
            continue
        for v in vids:
            if v.get("channel_id") == cid and v.get("view_count") is not None:
                out.setdefault(v["id"], v)
    popular = sorted(out.values(), key=lambda v: v.get("view_count") or 0, reverse=True)
    return popular[:limit]


def search_channel(channel_id, query, count=30):
    return [
        v
        for v in search_youtube(query, count)
        if v.get("type") != "playlist" and v.get("channel_id") == channel_id
    ]


def get_video_info(video_id):
    url = WATCH_URL.format(video_id)
    p = _run_ytdlp(["-J", "--no-warnings", url], timeout=60)
    if p.returncode == 0:
        try:
            d = json.loads(p.stdout)
        except ValueError:
            return None
        vid = d.get("id") or video_id
        return {
            "id": vid,
            "title": (d.get("title") or video_id).strip(),
            "thumb": THUMB.format(vid),
            "channel": d.get("channel"),
        }
    return None


def get_stream_url(video_id, max_height=720):
    url = WATCH_URL.format(video_id)
    p = _run_ytdlp(
        [
            "-f",
            "b[height<=?{}]/b".format(max_height),
            "--get-url",
            "--no-warnings",
            url,
        ]
    )
    lines = [l for l in p.stdout.strip().splitlines() if l.strip()]
    if p.returncode != 0 or not lines:
        return None
    return lines[0]


def download(video_id, outdir, max_height=720):
    url = WATCH_URL.format(video_id)
    os.makedirs(outdir, exist_ok=True)
    outtmpl = os.path.join(outdir, "%(title)s.%(ext)s")
    fmt = (
        "bv*[height<=?{h}][ext=mp4]+ba[ext=m4a]"
        "/b[height<=?{h}][ext=mp4]"
        "/b[height<=?{h}]/b".format(h=max_height)
    )
    p = _run_ytdlp(["-f", fmt, "-o", outtmpl, url], timeout=600, live=True)
    return p.returncode == 0
