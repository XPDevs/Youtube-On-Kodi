import json
import os
import queue
import re
import shutil
import subprocess
import sys
import threading
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
DEFAULT_CONF = os.path.join(ADDON_PATH, "resources", "channels.conf")

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
    li = xbmcgui.ListItem(label=v["title"])
    li.setInfo(
        "video",
        {
            "title": v["title"],
            "plot": v["title"],
            "studio": v.get("channel", "My YouTubers"),
        },
    )
    li.setArt({"thumb": v["thumb"], "icon": v["thumb"]})
    li.setProperty("IsPlayable", "true")
    return li


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
    li = xbmcgui.ListItem(label="[B]Downloads[/B]")
    add_dir(li, build_url({"mode": "downloads"}))
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
            "My YouTubers",
            "Could not resolve: " + query,
            xbmcgui.NOTIFICATION_ERROR,
        )
        return
    channels = kanyt.read_channels_conf(CONF_FILE)
    if any(c["query"] == query for c in channels):
        xbmcgui.Dialog().notification(
            "My YouTubers", "Already added: " + (name or ch["name"])
        )
        return
    channels.append({"query": query, "name": name or ch["name"]})
    write_conf(channels)
    xbmcgui.Dialog().notification(
        "My YouTubers", "Added: " + (name or ch["name"])
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
            "My YouTubers",
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
    for v in videos[offset:end]:
        add_dir(
            video_item(v),
            build_url({"mode": "video", "id": v["id"]}),
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
            "My YouTubers", "No results", xbmcgui.NOTIFICATION_WARNING
        )
    for v in videos:
        add_dir(
            video_item(v),
            build_url({"mode": "video", "id": v["id"]}),
            isfolder=False,
        )
    xbmcplugin.endOfDirectory(HANDLE)


def do_youtube_search():
    kb = xbmc.Keyboard("", "Search YouTube")
    kb.doModal()
    if not kb.isConfirmed():
        xbmc.executebuiltin("Container.Refresh")
        return
    text = kb.getText().strip()
    if not text:
        xbmc.executebuiltin("Container.Refresh")
        return
    xbmcplugin.setContent(HANDLE, "videos")
    videos = kanyt.search_youtube(text)
    if not videos:
        xbmcgui.Dialog().notification(
            "My YouTubers", "No results", xbmcgui.NOTIFICATION_WARNING
        )
    for v in videos:
        add_dir(
            video_item(v),
            build_url({"mode": "video", "id": v["id"]}),
            isfolder=False,
        )
    xbmcplugin.endOfDirectory(HANDLE)


def play_video(video_id):
    xbmc.executebuiltin("ActivateWindow(busydialog)")
    try:
        stream_url = kanyt.get_stream_url(video_id)
    finally:
        xbmc.executebuiltin("Dialog.Close(busydialog)")
    if not stream_url:
        xbmcgui.Dialog().notification(
            "My YouTubers", "Could not resolve stream", xbmcgui.NOTIFICATION_ERROR
        )
        return
    li = xbmcgui.ListItem(path=stream_url)
    li.setProperty("IsPlayable", "true")
    xbmc.Player().play(stream_url, li)


def video_menu(video_id):
    choice = xbmcgui.Dialog().select("Video", ["Play", "Download", "Cancel"])
    if choice == 0:
        play_video(video_id)
    elif choice == 1:
        download_video(video_id)


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
    dp.create("My YouTubers", "Downloading...")
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
        xbmcgui.Dialog().notification("My YouTubers", "Download cancelled")
    elif proc.returncode == 0:
        xbmcgui.Dialog().notification("My YouTubers", "Saved to downloads")
    else:
        xbmcgui.Dialog().notification(
            "My YouTubers", "Download failed", xbmcgui.NOTIFICATION_ERROR
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
            "My YouTubers", "File not found", xbmcgui.NOTIFICATION_ERROR
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
            xbmcgui.Dialog().notification("My YouTubers", "Deleted")
            xbmc.executebuiltin("Container.Refresh")


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
        do_youtube_search()
    elif mode == "video":
        video_menu(params.get("id", ""))
    elif mode == "play":
        play_video(params.get("id", ""))
    elif mode == "downloads":
        list_downloads()
    elif mode == "dlfile":
        dl_file(params.get("file", ""))
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
            "My YouTubers", "Error: " + str(e), xbmcgui.NOTIFICATION_ERROR
        )
    except Exception:
        pass


if __name__ == "__main__":
    try:
        router(sys.argv[2])
    except Exception as e:
        log_error(e)
