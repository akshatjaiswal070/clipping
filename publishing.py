"""Upload a rendered clip using account credentials supplied to the local app."""
import json
import os
import re
import time
from urllib.error import HTTPError
from urllib.parse import urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def request(url, *, headers, data=None, method=None):
    try:
        with build_opener(NoRedirect()).open(Request(url, data, headers, method=method), timeout=120) as response:
            body = response.read()
            return json.loads(body) if body.strip() else {}, response.headers
    except HTTPError as error:
        raise ValueError(f"The platform returned HTTP {error.code}. Check the account permissions and video requirements.") from error


def upload_file(url, host, path, headers, method):
    target = urlsplit(url)
    if target.scheme != "https" or target.netloc != host:
        raise ValueError("The platform returned an unexpected upload address.")
    with path.open("rb") as stream:
        return request(url, headers={**headers, "Content-Length": str(path.stat().st_size)}, data=stream, method=method)[0]


def youtube(path, title, caption, privacy):
    token = os.environ.get("CLIPPING_YOUTUBE_TOKEN")
    if not token:
        raise ValueError("Set CLIPPING_YOUTUBE_TOKEN with YouTube upload permission and restart Clipping.")
    if not 1 <= len(title) <= 100 or len(caption.encode()) > 5000 or privacy not in ("private", "unlisted", "public"):
        raise ValueError("YouTube needs a title up to 100 characters, a description up to 5,000 bytes, and a visibility selection.")
    headers = {"Authorization": f"Bearer {token}"}
    metadata = {"snippet": {"title": title, "description": caption, "categoryId": "22"},
                "status": {"privacyStatus": privacy, "selfDeclaredMadeForKids": False}}
    _, response_headers = request(
        "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status",
        headers={**headers, "Content-Type": "application/json", "X-Upload-Content-Type": "video/mp4",
                 "X-Upload-Content-Length": str(path.stat().st_size)},
        data=json.dumps(metadata).encode(),
    )
    result = upload_file(response_headers["Location"], "www.googleapis.com", path,
                         {**headers, "Content-Type": "video/mp4"}, "PUT")
    return {"id": result["id"], "url": "https://youtu.be/" + result["id"],
            "visibility": result.get("status", {}).get("privacyStatus", privacy)}


def instagram(path, caption):
    token = os.environ.get("CLIPPING_INSTAGRAM_TOKEN")
    account = os.environ.get("CLIPPING_INSTAGRAM_ID", "")
    version = os.environ.get("CLIPPING_META_VERSION", "")
    if not token or not account.isdigit() or not re.fullmatch(r"v\d+\.\d+", version):
        raise ValueError("Configure a Meta publishing token, Instagram professional account ID, and Graph API version.")
    if len(caption) > 2200:
        raise ValueError("Instagram captions must be 2,200 characters or fewer.")
    base = f"https://graph.facebook.com/{version}"
    headers = {"Authorization": f"Bearer {token}"}
    container, _ = request(f"{base}/{account}/media", headers=headers, data=urlencode({
        "media_type": "REELS", "upload_type": "resumable", "caption": caption,
    }).encode())
    result = upload_file(container["uri"], "rupload.facebook.com", path, {
        "Authorization": f"OAuth {token}", "offset": "0",
        "file_size": str(path.stat().st_size), "Content-Type": "application/octet-stream",
    }, "POST")
    if result.get("success") is not True:
        raise ValueError("Instagram did not confirm receipt of the video.")
    container_id = container["id"]
    for _ in range(30):
        state, _ = request(f"{base}/{container_id}?fields=status_code", headers=headers)
        if state.get("status_code") == "FINISHED":
            break
        if state.get("status_code") in ("ERROR", "EXPIRED"):
            raise ValueError("Instagram could not process the Reel. Try a 1080p export.")
        time.sleep(5)
    else:
        raise ValueError("Instagram is still processing the Reel. It was not published.")
    result, _ = request(f"{base}/{account}/media_publish", headers=headers,
                        data=urlencode({"creation_id": container_id}).encode())
    return {"id": result["id"]}
