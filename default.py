import json
import os
import queue
import re
import shutil
import subprocess
import sys
import threading
import time
import traceback
import urllib.parse

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "resources", "lib")
)

import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin
import xbmcvfs

import kanyt

ADDON = xbmcaddon.Addon()
ADDON_PATH = xbmcvfs.translatePath(ADDON.getAddonInfo("path"))
PROFILE = xbmcvfs.translatePath(ADDON.getAddonInfo("profile"))
CACHE_DIR = os.path.join(PROFILE, "cache")
CONF_FILE = os.path.join(PROFILE, "channels.conf")
ERROR_LOG = os.path.join(PROFILE, "error.log")
DOWNLOAD_DIR = os.path.join(PROFILE, "downloads")
PLAYLISTS_FILE = os.path.join(PROFILE, "playlists.json")
HISTORY_FILE = os.path.join(PROFILE, "history.json")
DEFAULT_CONF = os.path.join(ADDON_PATH, "resources", "channels.conf")

REFRESH_INTERVAL = 86400  # 24 hours in seconds

os.makedirs(PROFILE, exist_ok=True)
if not os.path.exists(CONF_FILE):
    shutil.copyfile(DEFAULT_CONF, CONF_FILE)

PAGE_SIZE = 30
HANDLE = int(sys.argv[1])
BASE_URL = sys.argv[0]


def build_url(params):
    return BASE_URL + "?" + urllib.parse.urlencode(params)


def add_dir(listitem, url, isfolder=True):
    xbmcplugin.addDirectoryItem(HANDLE, url, listitem, isfolder)


def video_item(v):
    # Check history for resume indicator
    hist = load_history()
    entry = hist.get(v["id"])
    label = v["title"]
    if entry:
        pos = entry.get("position", 0)
        if pos > 30:  # only show if meaningful progress
            label += " [resume {}]".format(fmt_time(pos))
    li = xbmcgui.ListItem(label=label)
    li.setInfo(
        "video",
        {
            "title": v["title"],
            "plot": v["title"],
            "studio": v.get("channel", "Youtube On Kodi"),
        },
    )
    li.setArt({"thumb": v["thumb"], "icon": v["thumb"]})
    li.setProperty("IsPlayable", "true")
    return li


def dir_item(title, thumb=""):
    li = xbmcgui.ListItem(label=title)
    li.setInfo("video", {"title": title, "plot": title})
    li.setArt({"thumb": thumb, "icon": thumb})
    return li


def load_playlists():
    if not os.path.exists(PLAYLISTS_FILE):
        return []
    try:
        with open(PLAYLISTS_FILE) as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
    except (OSError, ValueError):
        pass
    return []


def save_playlists(plists):
    with open(PLAYLISTS_FILE, "w") as f:
        json.dump(plists, f)


def load_history():
    if not os.path.exists(HISTORY_FILE):
        return {}
    try:
        with open(HISTORY_FILE) as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
    except (OSError, ValueError):
        pass
    return {}


def save_history(hist):
    with open(HISTORY_FILE, "w") as f:
        json.dump(hist, f)


def fmt_time(sec):
    sec = int(sec or 0)
    m, s = divmod(sec, 60)
    h, m = divmod(m, 60)
    if h:
        return "{}:{:02d}:{:02d}".format(h, m, s)
    return "{}:{:02d}".format(m, s)


def write_conf(channels):
    with open(CONF_FILE, "w") as f:
        f.write("# One channel per line. Values: handle (@name), URL, ID, or plain name.\n")
        f.write("# Optional display name after '|'.\n")
        for c in channels:
            line = c["query"]
            if c.get("name"):
                line += " | " + c["name"]
            f.write(line + "\n")


def get_channel(query):
    name = None
    for c in kanyt.read_channels_conf(CONF_FILE):
        if c["query"] == query:
            name = c["name"]
            break
    ch = kanyt.resolve_cached(query, CACHE_DIR)
    if not ch:
        return None
    if name:
        ch["name"] = name
    return ch


# --- Refresh functions ---

def refresh_all_caches():
    if not xbmcgui.Dialog().yesno("Refresh", "Refresh all channel and search caches?"):
        return
    xbmc.executebuiltin("ActivateWindow(busydialog)")
    try:
        for f in os.listdir(CACHE_DIR):
            if f.endswith(".json"):
                os.remove(os.path.join(CACHE_DIR, f))
        xbmcgui.Dialog().notification("Youtube On Kodi", "All caches cleared.")
    except Exception as e:
        xbmcgui.Dialog().notification("Youtube On Kodi", "Error: " + str(e), xbmcgui.NOTIFICATION_ERROR)
    finally:
        xbmc.executebuiltin("Dialog.Close(busydialog)")
    xbmc.executebuiltin("Container.Refresh")


def refresh_channel_cache(query):
    ch = get_channel(query)
    if not ch:
        return
    cache_file = os.path.join(CACHE_DIR, ch["id"] + ".json")
    if os.path.exists(cache_file):
        os.remove(cache_file)
    plist_cache = os.path.join(CACHE_DIR, "plists_" + ch["id"] + ".json")
    if os.path.exists(plist_cache):
        os.remove(plist_cache)
    xbmcgui.Dialog().notification("Youtube On Kodi", "Cache refreshed for " + (ch.get("name") or query))
    xbmc.executebuiltin("Container.Refresh")


# --- Main menu ---

def list_channels():
    channels = kanyt.read_channels_conf(CONF_FILE)
    for c in channels:
        display = c["name"] or c["query"]
        li = xbmcgui.ListItem(label=display)
        li.setInfo("video", {"title": display, "plot": display})
        add_dir(
            li,
            build_url({"mode": "videos", "q": c["query"]}),
        )
    li = xbmcgui.ListItem(label="[B]+ Add YouTuber[/B]")
    add_dir(li, build_url({"mode": "add"}))
    if channels:
        li = xbmcgui.ListItem(label="[B]- Remove YouTuber[/B]")
        add_dir(li, build_url({"mode": "remove"}))
    li = xbmcgui.ListItem(label="[B]Search YouTube[/B]")
    add_dir(li, build_url({"mode": "ytsearch"}))
    li = xbmcgui.ListItem(label="[B]Popular[/B]")
    add_dir(li, build_url({"mode": "popular"}))
    li = xbmcgui.ListItem(label="[B]Playlists[/B]")
    add_dir(li, build_url({"mode": "playlists"}))
    li = xbmcgui.ListItem(label="[B]Downloads[/B]")
    add_dir(li, build_url({"mode": "downloads"}))
    li = xbmcgui.ListItem(label="[B]History[/B]")
    add_dir(li, build_url({"mode": "history"}))
    li = xbmcgui.ListItem(label="[B]Refresh all caches[/B]")
    add_dir(li, build_url({"mode": "refresh_all"}))
    xbmcplugin.endOfDirectory(HANDLE)


def add_channel():
    kb = xbmc.Keyboard("", "Enter channel handle (@name), URL or ID")
    kb.doModal()
    if not kb.isConfirmed():
        return
    query = kb.getText().strip()
    if not query:
        return
    kb2 = xbmc.Keyboard("", "Enter a display name")
    kb2.doModal()
    name = kb2.getText().strip() if kb2.isConfirmed() else ""
    xbmc.executebuiltin("ActivateWindow(busydialog)")
    try:
        ch = kanyt.resolve_cached(query, CACHE_DIR)
    finally:
        xbmc.executebuiltin("Dialog.Close(busydialog)")
    if not ch:
        xbmcgui.Dialog().notification(
            "Youtube On Kodi",
            "Could not resolve: " + query,
            xbmcgui.NOTIFICATION_ERROR,
        )
        return
    channels = kanyt.read_channels_conf(CONF_FILE)
    if any(c["query"] == query for c in channels):
        xbmcgui.Dialog().notification(
            "Youtube On Kodi", "Already added: " + (name or ch["name"])
        )
        return
    channels.append({"query": query, "name": name or ch["name"]})
    write_conf(channels)
    xbmcgui.Dialog().notification(
        "Youtube On Kodi", "Added: " + (name or ch["name"])
    )
    xbmc.executebuiltin("Container.Refresh")


def remove_channel():
    channels = kanyt.read_channels_conf(CONF_FILE)
    if not channels:
        return
    names = [c["name"] or c["query"] for c in channels]
    sel = xbmcgui.Dialog().select("Remove YouTuber", names)
    if sel < 0:
        return
    channels.pop(sel)
    write_conf(channels)
    xbmc.executebuiltin("Container.Refresh")


def list_videos(query, offset):
    ch = get_channel(query)
    if not ch:
        xbmcgui.Dialog().notification(
            "Youtube On Kodi",
            "Could not resolve channel: " + query,
            xbmcgui.NOTIFICATION_ERROR,
        )
        return
    end = offset + PAGE_SIZE
    videos = kanyt.get_channel_videos(ch["id"], CACHE_DIR, end=end)
    xbmcplugin.setContent(HANDLE, "videos")
    li = xbmcgui.ListItem(label="[B]Search in {}[/B]".format(ch["name"]))
    add_dir(
        li,
        build_url({"mode": "chansearch", "q": query}),
    )
    li = xbmcgui.ListItem(label="[B]Playlists: {}[/B]".format(ch["name"]))
    add_dir(
        li,
        build_url({"mode": "chplists", "q": query}),
    )
    li = xbmcgui.ListItem(label="[B]Refresh channel cache[/B]")
    add_dir(
        li,
        build_url({"mode": "refresh_channel", "q": query}),
    )
    for v in videos[offset:end]:
        add_dir(
            video_item(v),
            build_url({"mode": "video", "id": v["id"], "title": v["title"]}),
            isfolder=False,
        )
    if len(videos) >= end:
        li = xbmcgui.ListItem(label="[B]Load more...[/B]")
        add_dir(li, build_url({"mode": "videos", "q": query, "offset": str(end)}))
    xbmcplugin.endOfDirectory(HANDLE)


def do_channel_search(query):
    kb = xbmc.Keyboard("", "Search in channel")
    kb.doModal()
    if not kb.isConfirmed():
        xbmc.executebuiltin("Container.Refresh")
        return
    text = kb.getText().strip()
    if not text:
        xbmc.executebuiltin("Container.Refresh")
        return
    ch = get_channel(query)
    if not ch:
        return
    xbmcplugin.setContent(HANDLE, "videos")
    videos = kanyt.search_channel(ch["id"], text)
    if not videos:
        xbmcgui.Dialog().notification(
            "Youtube On Kodi", "No results", xbmcgui.NOTIFICATION_WARNING
        )
    for v in videos:
        add_dir(
            video_item(v),
            build_url({"mode": "video", "id": v["id"], "title": v["title"]}),
            isfolder=False,
        )
    xbmcplugin.endOfDirectory(HANDLE)


def do_youtube_search(query, offset):
    if not query:
        kb = xbmc.Keyboard("", "Search YouTube")
        kb.doModal()
        if not kb.isConfirmed():
            xbmc.executebuiltin("Container.Refresh")
            return
        query = kb.getText().strip()
        if not query:
            xbmc.executebuiltin("Container.Refresh")
            return
    end = offset + PAGE_SIZE
    xbmc.executebuiltin("ActivateWindow(busydialog)")
    try:
        entries = kanyt.search_cached(query, CACHE_DIR, end=end)
    finally:
        xbmc.executebuiltin("Dialog.Close(busydialog)")
    xbmcplugin.setContent(HANDLE, "videos")
    shown = entries[offset:end]
    if not shown:
        xbmcgui.Dialog().notification(
            "Youtube On Kodi", "No results", xbmcgui.NOTIFICATION_WARNING
        )
    for e in shown:
        etype = e.get("type")
        if etype == "playlist":
            add_dir(
                dir_item(e["title"], e.get("thumb", "")),
                build_url({"mode": "plist", "url": e["url"]}),
            )
        elif etype == "channel":
            add_dir(
                dir_item(e["title"], e.get("thumb", "")),
                build_url({"mode": "videos", "q": e["id"]}),
            )
        else:
            add_dir(
                video_item(e),
                build_url({"mode": "video", "id": e["id"], "title": e["title"]}),
                isfolder=False,
            )
    if len(entries) >= end:
        li = xbmcgui.ListItem(label="[B]Load more...[/B]")
        add_dir(li, build_url({"mode": "ytsearch", "q": query, "offset": str(end)}))
    xbmcplugin.endOfDirectory(HANDLE)


def do_popular():
    channels = kanyt.read_channels_conf(CONF_FILE)
    resolved = []
    for c in channels:
        ch = get_channel(c["query"])
        if ch:
            resolved.append((ch["id"], ch["name"] or c["query"]))
    xbmc.executebuiltin("ActivateWindow(busydialog)")
    try:
        videos = kanyt.popular_videos(resolved, limit=30)
    finally:
        xbmc.executebuiltin("Dialog.Close(busydialog)")
    xbmcplugin.setContent(HANDLE, "videos")
    if not videos:
        xbmcgui.Dialog().notification(
            "Youtube On Kodi", "No results", xbmcgui.NOTIFICATION_WARNING
        )
    for v in videos:
        add_dir(
            video_item(v),
            build_url({"mode": "video", "id": v["id"], "title": v["title"]}),
            isfolder=False,
        )
    xbmcplugin.endOfDirectory(HANDLE)


# --- Playback and history tracking ---

def play_video(video_id, title="", auto_resume=False):
    hist = load_history()
    entry = hist.get(video_id)
    resume_at = 0
    if entry:
        pos = entry.get("position") or 0
        dur = entry.get("duration") or 0
        if pos > 30 and dur and pos < dur - 10:
            if auto_resume:
                resume_at = pos
            elif xbmcgui.Dialog().yesno(
                "Youtube On Kodi",
                "Resume from {}".format(fmt_time(pos)) + "?",
                "Select Yes to resume or No to start over.",
            ):
                resume_at = pos
    xbmc.executebuiltin("ActivateWindow(busydialog)")
    try:
        stream_url = kanyt.get_stream_url(video_id)
    finally:
        xbmc.executebuiltin("Dialog.Close(busydialog)")
    if not stream_url:
        xbmcgui.Dialog().notification(
            "Youtube On Kodi", "Could not resolve stream", xbmcgui.NOTIFICATION_ERROR
        )
        return
    li = xbmcgui.ListItem(path=stream_url)
    li.setProperty("IsPlayable", "true")
    player = xbmc.Player()
    player.play(stream_url, li)
    if resume_at:
        try:
            for _ in range(50):
                if player.isPlaying():
                    player.seekTime(resume_at)
                    break
                time.sleep(0.1)
        except Exception:
            pass
    threading.Thread(
        target=_track_playback, args=(video_id, title, resume_at), daemon=True
    ).start()


def _track_playback(video_id, title, start_pos):
    player = xbmc.Player()
    deadline = time.time() + 6 * 60 * 60
    last_save = 0
    while time.time() < deadline:
        try:
            if not player.isPlaying():
                break
            duration = player.getTotalTime()
            position = player.getTime()
        except Exception:
            duration, position = 0, 0
        now = time.time()
        if position and duration and now - last_save >= 5:
            last_save = now
            hist = load_history()
            # Get additional metadata from player if available
            try:
                info_tag = player.getVideoInfoTag()
                channel = info_tag.getStudio() or ""
                thumb = info_tag.getArt("thumb") or kanyt.THUMB.format(video_id)
            except:
                channel = ""
                thumb = kanyt.THUMB.format(video_id)
            percentage = int((position / duration) * 100) if duration else 0
            hist[video_id] = {
                "title": title or video_id,
                "position": int(position),
                "duration": int(duration),
                "percentage": percentage,
                "channel": channel,
                "thumb": thumb,
                "date": time.strftime("%Y-%m-%d %H:%M"),
            }
            try:
                save_history(hist)
            except Exception:
                pass
        time.sleep(5)
    # Final save when stopped
    try:
        duration = player.getTotalTime()
        position = player.getTime()
    except Exception:
        duration, position = 0, 0
    if position and duration:
        hist = load_history()
        try:
            info_tag = player.getVideoInfoTag()
            channel = info_tag.getStudio() or ""
            thumb = info_tag.getArt("thumb") or kanyt.THUMB.format(video_id)
        except:
            channel = ""
            thumb = kanyt.THUMB.format(video_id)
        percentage = int((position / duration) * 100) if duration else 0
        hist[video_id] = {
            "title": title or video_id,
            "position": int(position),
            "duration": int(duration),
            "percentage": percentage,
            "channel": channel,
            "thumb": thumb,
            "date": time.strftime("%Y-%m-%d %H:%M"),
        }
        try:
            save_history(hist)
        except Exception:
            pass


def video_menu(video_id, title="", plist_idx=None, vpos=None):
    options = ["Play", "Download", "Add to playlist"]
    if plist_idx is not None:
        options.insert(2, "Remove from playlist")
    options.append("Cancel")
    choice = xbmcgui.Dialog().select("Video", options)
    if choice == 0:
        play_video(video_id, title)
    elif choice == 1:
        download_video(video_id)
    elif plist_idx is not None and choice == 2:
        remove_from_playlist(plist_idx, vpos)
    elif choice == 2 or (plist_idx is not None and choice == 3):
        add_to_playlist(video_id, title)


def add_to_playlist(video_id, title=""):
    plists = load_playlists()
    names = [p["name"] for p in plists]
    names.append("[B]+ New playlist...[/B]")
    sel = xbmcgui.Dialog().select("Add to playlist", names)
    if sel < 0:
        return
    if sel == len(plists):
        kb = xbmc.Keyboard("", "Playlist name")
        kb.doModal()
        name = kb.getText().strip() if kb.isConfirmed() else ""
        if not name:
            return
        plists.append({"name": name, "videos": []})
        sel = len(plists) - 1
    p = plists[sel]
    entry = {
        "id": video_id,
        "title": title or video_id,
        "thumb": kanyt.THUMB.format(video_id),
    }
    if any(v["id"] == video_id for v in p.get("videos", [])):
        xbmcgui.Dialog().notification("Youtube On Kodi", "Already in playlist")
        return
    p.setdefault("videos", []).append(entry)
    save_playlists(plists)
    xbmcgui.Dialog().notification("Youtube On Kodi", "Added to " + p["name"])


def remove_from_playlist(plist_idx, vpos):
    plists = load_playlists()
    if plist_idx < 0 or plist_idx >= len(plists):
        return
    p = plists[plist_idx]
    if vpos is None or vpos < 0 or vpos >= len(p.get("videos", [])):
        return
    if xbmcgui.Dialog().yesno("Remove", "Remove from {}?".format(p["name"])):
        p["videos"].pop(vpos)
        save_playlists(plists)
        xbmcgui.Dialog().notification("Youtube On Kodi", "Removed")
        xbmc.executebuiltin("Container.Refresh")


def download_video(video_id):
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    url = kanyt.WATCH_URL.format(video_id)
    fmt = (
        "bv*[height<=?720][ext=mp4]+ba[ext=m4a]"
        "/b[height<=?720][ext=mp4]/b[height<=?720]/b"
    )
    outtmpl = os.path.join(DOWNLOAD_DIR, "%(title)s.%(ext)s")
    cmd, env = kanyt.build_ytdlp_cmd(
        ["-f", fmt, "-o", outtmpl, "--newline", "--progress", url]
    )
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env=env,
        bufsize=1,
    )
    q = queue.Queue()

    def reader():
        for line in proc.stdout:
            q.put(line)

    threading.Thread(target=reader, daemon=True).start()
    dp = xbmcgui.DialogProgress()
    dp.create("Youtube On Kodi", "Downloading...")
    pct = 0
    canceled = False
    while proc.poll() is None:
        if dp.iscanceled():
            canceled = True
            proc.terminate()
            break
        try:
            line = q.get(timeout=0.2)
        except queue.Empty:
            continue
        m = re.search(r"(\d+(?:\.\d+)?)%", line)
        if m:
            pct = int(float(m.group(1)))
        dp.update(pct, "Downloading... {}%".format(pct))
    proc.wait()
    dp.close()
    if canceled:
        xbmcgui.Dialog().notification("Youtube On Kodi", "Download cancelled")
    elif proc.returncode == 0:
        xbmcgui.Dialog().notification("Youtube On Kodi", "Saved to downloads")
    else:
        xbmcgui.Dialog().notification(
            "Youtube On Kodi", "Download failed", xbmcgui.NOTIFICATION_ERROR
        )


def list_downloads():
    if not os.path.isdir(DOWNLOAD_DIR):
        os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    videos = [
        f
        for f in os.listdir(DOWNLOAD_DIR)
        if f.lower().endswith((".mp4", ".mkv", ".m4a", ".webm"))
    ]
    videos.sort()
    if not videos:
        li = xbmcgui.ListItem(label="No downloads yet")
        add_dir(li, build_url({"mode": "main"}))
        xbmcplugin.endOfDirectory(HANDLE)
        return
    for name in videos:
        size = os.path.getsize(os.path.join(DOWNLOAD_DIR, name)) // (1024 * 1024)
        li = xbmcgui.ListItem(label="{} ({} MB)".format(name, size))
        add_dir(
            li,
            build_url({"mode": "dlfile", "file": name}),
            isfolder=False,
        )
    xbmcplugin.endOfDirectory(HANDLE)


def dl_file(name):
    path = os.path.join(DOWNLOAD_DIR, name)
    if not os.path.exists(path):
        xbmcgui.Dialog().notification(
            "Youtube On Kodi", "File not found", xbmcgui.NOTIFICATION_ERROR
        )
        return
    choice = xbmcgui.Dialog().select(name, ["Play", "Delete", "Cancel"])
    if choice == 0:
        li = xbmcgui.ListItem(path=path)
        li.setInfo("video", {"title": name})
        xbmc.Player().play(path, li)
    elif choice == 1:
        if xbmcgui.Dialog().yesno("Delete", "Delete {}?".format(name)):
            os.remove(path)
            xbmcgui.Dialog().notification("Youtube On Kodi", "Deleted")
            xbmc.executebuiltin("Container.Refresh")


def list_playlists():
    plists = load_playlists()
    li = xbmcgui.ListItem(label="[B]+ New playlist[/B]")
    add_dir(li, build_url({"mode": "newplist"}))
    for i, p in enumerate(plists):
        n = len(p.get("videos", []))
        label = p["name"]
        if p.get("url"):
            label += " (YouTube playlist)"
        elif n:
            label += " ({} videos)".format(n)
        add_dir(dir_item(label), build_url({"mode": "myplist", "idx": str(i)}))
    li = xbmcgui.ListItem(label="[B]YouTube playlists[/B]")
    add_dir(li, build_url({"mode": "ytplists"}))
    xbmcplugin.endOfDirectory(HANDLE)


def new_playlist():
    kb = xbmc.Keyboard("", "Playlist name")
    kb.doModal()
    name = kb.getText().strip() if kb.isConfirmed() else ""
    if not name:
        return
    plists = load_playlists()
    plists.append({"name": name, "videos": []})
    save_playlists(plists)
    xbmc.executebuiltin("Container.Refresh")


def list_my_playlist(idx, offset):
    plists = load_playlists()
    if idx < 0 or idx >= len(plists):
        return
    p = plists[idx]
    xbmcplugin.setContent(HANDLE, "videos")
    if p.get("url"):
        li = xbmcgui.ListItem(label="[B]Rename[/B]")
        add_dir(li, build_url({"mode": "plist_rename", "idx": str(idx)}))
        li = xbmcgui.ListItem(label="[B]Delete playlist[/B]")
        add_dir(li, build_url({"mode": "plist_del", "idx": str(idx)}))
        end = offset + PAGE_SIZE
        xbmc.executebuiltin("ActivateWindow(busydialog)")
        try:
            videos = kanyt.get_playlist_videos(p["url"], CACHE_DIR, end=end)
        finally:
            xbmc.executebuiltin("Dialog.Close(busydialog)")
        for v in videos[offset:end]:
            add_dir(
                video_item(v),
                build_url({"mode": "video", "id": v["id"], "title": v["title"]}),
                isfolder=False,
            )
        if len(videos) >= end:
            li = xbmcgui.ListItem(label="[B]Load more...[/B]")
            add_dir(
                li, build_url({"mode": "myplist", "idx": str(idx), "offset": str(end)})
            )
        xbmcplugin.endOfDirectory(HANDLE)
        return
    li = xbmcgui.ListItem(label="[B]+ Add video[/B]")
    add_dir(li, build_url({"mode": "plist_add", "idx": str(idx)}))
    li = xbmcgui.ListItem(label="[B]Rename[/B]")
    add_dir(li, build_url({"mode": "plist_rename", "idx": str(idx)}))
    li = xbmcgui.ListItem(label="[B]Delete playlist[/B]")
    add_dir(li, build_url({"mode": "plist_del", "idx": str(idx)}))
    for i, v in enumerate(p.get("videos", [])):
        add_dir(
            video_item(v),
            build_url(
                {
                    "mode": "video",
                    "id": v["id"],
                    "title": v["title"],
                    "idx": str(idx),
                    "vpos": str(i),
                }
            ),
            isfolder=False,
        )
    if not p.get("videos"):
        li = xbmcgui.ListItem(label="Playlist is empty")
        add_dir(li, build_url({"mode": "playlists"}))
    xbmcplugin.endOfDirectory(HANDLE)


def plist_add_video(idx):
    kb = xbmc.Keyboard("", "Paste a YouTube video URL or ID")
    kb.doModal()
    text = kb.getText().strip() if kb.isConfirmed() else ""
    if not text:
        return
    m = re.search(r"(?:v=|v/|youtu\.be/|shorts/|^)([\w-]{11})(?:[?&]|$)", text)
    video_id = m.group(1) if m else None
    if not video_id:
        xbmcgui.Dialog().notification(
            "Youtube On Kodi", "Could not find video ID", xbmcgui.NOTIFICATION_ERROR
        )
        return
    xbmc.executebuiltin("ActivateWindow(busydialog)")
    try:
        info = kanyt.get_video_info(video_id)
    finally:
        xbmc.executebuiltin("Dialog.Close(busydialog)")
    plists = load_playlists()
    if idx < 0 or idx >= len(plists):
        return
    p = plists[idx]
    if any(v["id"] == video_id for v in p.get("videos", [])):
        xbmcgui.Dialog().notification("Youtube On Kodi", "Already in playlist")
        return
    entry = {
        "id": video_id,
        "title": (info or {}).get("title") or video_id,
        "thumb": (info or {}).get("thumb") or kanyt.THUMB.format(video_id),
    }
    p.setdefault("videos", []).append(entry)
    save_playlists(plists)
    xbmcgui.Dialog().notification("Youtube On Kodi", "Added")
    xbmc.executebuiltin("Container.Refresh")


def plist_rename(idx):
    plists = load_playlists()
    if idx < 0 or idx >= len(plists):
        return
    kb = xbmc.Keyboard(plists[idx]["name"], "Playlist name")
    kb.doModal()
    name = kb.getText().strip() if kb.isConfirmed() else ""
    if not name:
        return
    plists[idx]["name"] = name
    save_playlists(plists)
    xbmc.executebuiltin("Container.Refresh")


def plist_delete(idx):
    plists = load_playlists()
    if idx < 0 or idx >= len(plists):
        return
    if xbmcgui.Dialog().yesno("Delete", "Delete {}?".format(plists[idx]["name"])):
        plists.pop(idx)
        save_playlists(plists)
        xbmc.executebuiltin("Container.Refresh")


def list_yt_playlists():
    channels = kanyt.read_channels_conf(CONF_FILE)
    li = xbmcgui.ListItem(label="[B]Search playlists[/B]")
    add_dir(li, build_url({"mode": "ytplistsrch"}))
    li = xbmcgui.ListItem(label="[B]Open playlist by URL[/B]")
    add_dir(li, build_url({"mode": "plist_url"}))
    for c in channels:
        label = "[B]Playlists: {}[/B]".format(c["name"] or c["query"])
        add_dir(dir_item(label), build_url({"mode": "chplists", "q": c["query"]}))
    xbmcplugin.endOfDirectory(HANDLE)


def do_playlist_search(query, offset):
    if not query:
        kb = xbmc.Keyboard("", "Search playlists")
        kb.doModal()
        if not kb.isConfirmed():
            xbmc.executebuiltin("Container.Refresh")
            return
        query = kb.getText().strip()
        if not query:
            xbmc.executebuiltin("Container.Refresh")
            return
    end = offset + PAGE_SIZE
    xbmc.executebuiltin("ActivateWindow(busydialog)")
    try:
        playlists = kanyt.search_playlists_cached(query, CACHE_DIR, end=end)
    finally:
        xbmc.executebuiltin("Dialog.Close(busydialog)")
    if not playlists:
        xbmcgui.Dialog().notification(
            "Youtube On Kodi", "No results", xbmcgui.NOTIFICATION_WARNING
        )
    for p in playlists:
        add_dir(
            dir_item(p["title"], p.get("thumb", "")),
            build_url({"mode": "plist", "url": p["url"]}),
        )
    if len(playlists) >= end:
        li = xbmcgui.ListItem(label="[B]Load more...[/B]")
        add_dir(li, build_url({"mode": "ytplistresults", "q": query, "offset": str(end)}))
    xbmcplugin.endOfDirectory(HANDLE)


def open_playlist_by_url():
    kb = xbmc.Keyboard("", "Paste a YouTube playlist URL")
    kb.doModal()
    url = kb.getText().strip() if kb.isConfirmed() else ""
    if not url:
        return
    if "list=" not in url:
        xbmcgui.Dialog().notification(
            "Youtube On Kodi", "Not a playlist URL", xbmcgui.NOTIFICATION_ERROR
        )
        return
    xbmc.executebuiltin("Container.Open(" + build_url({"mode": "plist", "url": url}) + ")")
    xbmc.executebuiltin("ActivateWindow(Videos)")


def list_channel_playlists(query):
    ch = get_channel(query)
    if not ch:
        xbmcgui.Dialog().notification(
            "Youtube On Kodi", "Could not resolve channel: " + query, xbmcgui.NOTIFICATION_ERROR
        )
        return
    xbmc.executebuiltin("ActivateWindow(busydialog)")
    try:
        playlists = kanyt.get_channel_playlists(ch["id"], CACHE_DIR)
    finally:
        xbmc.executebuiltin("Dialog.Close(busydialog)")
    if not playlists:
        xbmcgui.Dialog().notification(
            "Youtube On Kodi", "No playlists found", xbmcgui.NOTIFICATION_WARNING
        )
        return
    for p in playlists:
        li = xbmcgui.ListItem(label=p["title"])
        add_dir(
            li,
            build_url({"mode": "chplistitem", "url": p["url"], "title": p["title"]}),
        )
    xbmcplugin.endOfDirectory(HANDLE)


def channel_playlist_menu(url, title):
    choice = xbmcgui.Dialog().select(
        title, ["Open", "Save to My Playlists", "Cancel"]
    )
    if choice == 0:
        xbmc.executebuiltin(
            "Container.Open(" + build_url({"mode": "plist", "url": url}) + ")"
        )
        xbmc.executebuiltin("ActivateWindow(Videos)")
    elif choice == 1:
        plists = load_playlists()
        plists.append({"name": title, "url": url, "videos": []})
        save_playlists(plists)
        xbmcgui.Dialog().notification("Youtube On Kodi", "Saved to My Playlists")


def list_playlist_videos(url, offset, saved=False):
    end = offset + PAGE_SIZE
    xbmc.executebuiltin("ActivateWindow(busydialog)")
    try:
        videos = kanyt.get_playlist_videos(url, CACHE_DIR, end=end)
    finally:
        xbmc.executebuiltin("Dialog.Close(busydialog)")
    xbmcplugin.setContent(HANDLE, "videos")
    if saved:
        plists = load_playlists()
        exists = any(
            p.get("url") == url for p in plists
        )
        if not exists:
            li = xbmcgui.ListItem(label="[B]+ Save to My Playlists[/B]")
            add_dir(li, build_url({"mode": "plistsave", "url": url}))
    for v in videos[offset:end]:
        add_dir(
            video_item(v),
            build_url({"mode": "video", "id": v["id"], "title": v["title"]}),
            isfolder=False,
        )
    if not videos:
        xbmcgui.Dialog().notification(
            "Youtube On Kodi", "No videos", xbmcgui.NOTIFICATION_WARNING
        )
    if len(videos) >= end:
        li = xbmcgui.ListItem(label="[B]Load more...[/B]")
        add_dir(li, build_url({"mode": "plist", "url": url, "offset": str(end)}))
    xbmcplugin.endOfDirectory(HANDLE)


def save_playlist_by_url(url):
    plists = load_playlists()
    if any(p.get("url") == url for p in plists):
        xbmcgui.Dialog().notification("Youtube On Kodi", "Already saved")
        return
    kb = xbmc.Keyboard("", "Playlist name")
    kb.doModal()
    name = kb.getText().strip() if kb.isConfirmed() else ""
    if not name:
        return
    plists.append({"name": name, "url": url, "videos": []})
    save_playlists(plists)
    xbmcgui.Dialog().notification("Youtube On Kodi", "Saved to My Playlists")


# --- History list (enhanced) ---

def list_history():
    hist = load_history()
    if not hist:
        li = xbmcgui.ListItem(label="No history yet")
        add_dir(li, build_url({"mode": "main"}))
        xbmcplugin.endOfDirectory(HANDLE)
        return
    items = sorted(hist.items(), key=lambda kv: kv[1].get("date", ""), reverse=True)
    li = xbmcgui.ListItem(label="[B]Clear history[/B]")
    add_dir(li, build_url({"mode": "hist_clear"}))
    for vid, h in items:
        pos = fmt_time(h.get("position", 0))
        dur = fmt_time(h.get("duration", 0))
        pct = h.get("percentage", 0)
        title = h.get("title", vid)
        channel = h.get("channel", "")
        thumb = h.get("thumb", kanyt.THUMB.format(vid))
        label = "{} - {}% ({}/{})".format(title, pct, pos, dur)
        if channel:
            label = "[{}] ".format(channel) + label
        li = xbmcgui.ListItem(label=label)
        li.setInfo("video", {"title": title, "plot": title, "studio": channel})
        li.setArt({"thumb": thumb, "icon": thumb})
        li.setProperty("IsPlayable", "true")  # so it can be played directly
        # Add a progress bar using Kodi's property
        li.setProperty("Progress", str(pct))
        # Instead of playing directly, we route to a menu
        add_dir(
            li,
            build_url({"mode": "hist_item", "id": vid, "title": title}),
            isfolder=False,
        )
    xbmcplugin.endOfDirectory(HANDLE)


def history_item_menu(video_id, title):
    options = ["Play (auto-resume)", "Remove from history", "Cancel"]
    choice = xbmcgui.Dialog().select("History item", options)
    if choice == 0:
        play_video(video_id, title, auto_resume=True)
    elif choice == 1:
        hist = load_history()
        if video_id in hist:
            del hist[video_id]
            save_history(hist)
            xbmcgui.Dialog().notification("Youtube On Kodi", "Removed from history")
            xbmc.executebuiltin("Container.Refresh")


def clear_history():
    if xbmcgui.Dialog().yesno("History", "Clear watch history?"):
        save_history({})
        xbmc.executebuiltin("Container.Refresh")


# --- Router ---

def router(paramstring):
    params = dict(urllib.parse.parse_qsl(paramstring[1:]))
    mode = params.get("mode", "main")
    if mode == "main":
        list_channels()
    elif mode == "add":
        add_channel()
    elif mode == "remove":
        remove_channel()
    elif mode == "videos":
        list_videos(params.get("q", ""), int(params.get("offset", "0")))
    elif mode == "chansearch":
        do_channel_search(params.get("q", ""))
    elif mode == "ytsearch":
        do_youtube_search(params.get("q", ""), int(params.get("offset", "0")))
    elif mode == "popular":
        do_popular()
    elif mode == "video":
        video_menu(
            params.get("id", ""),
            params.get("title", ""),
            int(params.get("idx", "-1")),
            int(params.get("vpos", "-1")),
        )
    elif mode == "play":
        play_video(
            params.get("id", ""),
            params.get("title", ""),
            auto_resume=params.get("resume") == "1",
        )
    elif mode == "downloads":
        list_downloads()
    elif mode == "dlfile":
        dl_file(params.get("file", ""))
    elif mode == "playlists":
        list_playlists()
    elif mode == "newplist":
        new_playlist()
    elif mode == "myplist":
        list_my_playlist(int(params.get("idx", "-1")), int(params.get("offset", "0")))
    elif mode == "plist_add":
        plist_add_video(int(params.get("idx", "-1")))
    elif mode == "plist_rename":
        plist_rename(int(params.get("idx", "-1")))
    elif mode == "plist_del":
        plist_delete(int(params.get("idx", "-1")))
    elif mode == "ytplists":
        list_yt_playlists()
    elif mode == "ytplistsrch":
        do_playlist_search("", 0)
    elif mode == "ytplistresults":
        do_playlist_search(params.get("q", ""), int(params.get("offset", "0")))
    elif mode == "plist_url":
        open_playlist_by_url()
    elif mode == "chplists":
        list_channel_playlists(params.get("q", ""))
    elif mode == "chplistitem":
        channel_playlist_menu(params.get("url", ""), params.get("title", "Playlist"))
    elif mode == "plist":
        list_playlist_videos(
            params.get("url", ""),
            int(params.get("offset", "0")),
            saved=True,
        )
    elif mode == "plistsave":
        save_playlist_by_url(params.get("url", ""))
    elif mode == "history":
        list_history()
    elif mode == "hist_clear":
        clear_history()
    elif mode == "hist_item":
        history_item_menu(params.get("id", ""), params.get("title", ""))
    elif mode == "refresh_all":
        refresh_all_caches()
    elif mode == "refresh_channel":
        refresh_channel_cache(params.get("q", ""))
    else:
        list_channels()


def log_error(e):
    try:
        with open(ERROR_LOG, "w") as f:
            f.write(traceback.format_exc())
    except Exception:
        pass
    try:
        xbmcgui.Dialog().notification(
            "Youtube On Kodi", "Error: " + str(e), xbmcgui.NOTIFICATION_ERROR
        )
    except Exception:
        pass


if __name__ == "__main__":
    try:
        router(sys.argv[2])
    except Exception as e:
        log_error(e)
