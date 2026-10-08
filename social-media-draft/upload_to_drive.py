#!/usr/bin/env python3
"""Upload everything in social-media-draft/ into the Drive folder "Bloggerly Social Media Draft",
keeping the sub-folders. Standard library only.

Credentials (environment variables, set in the cloud environment's settings, never in chat):
  GOOGLE_OAUTH_CLIENT_ID, GOOGLE_OAUTH_CLIENT_SECRET, GOOGLE_OAUTH_REFRESH_TOKEN
    (OAuth refresh token for the Google account that owns the folder, scope drive.file or drive)

Usage: python3 upload_to_drive.py [FOLDER_ID]
"""
import json, mimetypes, os, re, sys, urllib.error, urllib.parse, urllib.request

ROOT_FOLDER = sys.argv[1] if len(sys.argv) > 1 else "18ZIgQCLbSlKLZef4JXJ8l6tUdwNcqzHY"
HERE = os.path.dirname(os.path.abspath(__file__))


def env(name):  # tolerate values pasted with quotes, commas or braces around them
    return os.environ[name].strip().strip('{}",\' ').strip()


def token():
    secret = re.search(r"GOCSPX-[A-Za-z0-9_-]+", os.environ["GOOGLE_OAUTH_CLIENT_SECRET"])
    data = urllib.parse.urlencode({
        "client_id": env("GOOGLE_OAUTH_CLIENT_ID"),
        "client_secret": secret.group(0) if secret else env("GOOGLE_OAUTH_CLIENT_SECRET"),
        "refresh_token": env("GOOGLE_OAUTH_REFRESH_TOKEN"),
        "grant_type": "refresh_token"}).encode()
    try:
        return json.load(urllib.request.urlopen("https://oauth2.googleapis.com/token", data))["access_token"]
    except urllib.error.HTTPError as e:
        sys.exit(f"Google sign-in failed: {json.load(e).get('error_description') or e.code}")


TOKEN = token()
H = {"Authorization": f"Bearer {TOKEN}"}


def api(url, body=None, headers=None, method=None):
    req = urllib.request.Request(url, data=body, headers={**H, **(headers or {})}, method=method)
    return urllib.request.urlopen(req)


def folder(name, parent):
    q = urllib.parse.quote(f"name='{name}' and '{parent}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false")
    found = json.load(api(f"https://www.googleapis.com/drive/v3/files?q={q}&supportsAllDrives=true&includeItemsFromAllDrives=true"))["files"]
    if found:
        return found[0]["id"]
    meta = json.dumps({"name": name, "parents": [parent], "mimeType": "application/vnd.google-apps.folder"}).encode()
    return json.load(api("https://www.googleapis.com/drive/v3/files?supportsAllDrives=true", meta, {"Content-Type": "application/json"}))["id"]


def upload(path, parent):
    mime = mimetypes.guess_type(path)[0] or "application/octet-stream"
    meta = json.dumps({"name": os.path.basename(path), "parents": [parent]}).encode()
    r = api("https://www.googleapis.com/upload/drive/v3/files?uploadType=resumable&supportsAllDrives=true", meta,
            {"Content-Type": "application/json; charset=UTF-8", "X-Upload-Content-Type": mime})
    with open(path, "rb") as f:
        api(r.headers["Location"], f.read(), {"Content-Type": mime}, "PUT")
    print("uploaded", os.path.relpath(path, HERE))


for dirpath, _, files in sorted(os.walk(HERE)):
    rel = os.path.relpath(dirpath, HERE)
    parent = ROOT_FOLDER
    if rel != ".":
        for part in rel.split(os.sep):
            parent = folder(part, parent)
    for f in sorted(files):
        if f.endswith((".mp4", ".png", ".jpg", ".md")):
            upload(os.path.join(dirpath, f), parent)
