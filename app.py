"""Local browser interface for batch video clipping."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
from tempfile import TemporaryDirectory
from threading import Lock
from urllib.parse import urlsplit
from uuid import uuid4
import webbrowser

HERE = Path(__file__).resolve().parent
EXISTING_FFMPEG = Path.home() / "Documents/Codex/2026-11-08/ap/outputs/shortflow/bin/ffmpeg"
MAX_UPLOAD = 8 * 1024 ** 3


class Clipper:
    def __init__(self, ffmpeg, directory):
        self.ffmpeg = ffmpeg
        self.directory = directory
        self.sources = {}
        self.jobs = {}
        self.lock = Lock()
        self.worker = ThreadPoolExecutor(max_workers=1)

    def duration(self, source):
        result = subprocess.run(
            [self.ffmpeg, "-hide_banner", "-i", str(source)],
            capture_output=True, text=True, timeout=30,
        )
        match = re.search(r"Duration: (\d+):(\d+):([\d.]+)", result.stderr)
        if not match or not re.search(r"Stream #.*Video:", result.stderr):
            raise ValueError("Choose a video file with a readable duration.")
        hours, minutes, seconds = map(float, match.groups())
        return hours * 3600 + minutes * 60 + seconds

    def snapshot(self, job_id):
        with self.lock:
            job = self.jobs[job_id]
            return {**job, "files": list(job["files"])}

    def update(self, job_id, **values):
        with self.lock:
            self.jobs[job_id].update(values)

    def render(self, job_id, source, clips, resolution, framing):
        folder = self.directory / job_id
        files = []
        try:
            folder.mkdir()
            width, height = (2160, 3840) if resolution == "4k" else (1080, 1920)
            size = f"{width}:{height}"
            if framing == "crop":
                vf = f"scale={size}:force_original_aspect_ratio=increase:force_divisible_by=2,crop={size}"
            else:
                vf = f"scale={size}:force_original_aspect_ratio=decrease:force_divisible_by=2,pad={size}:(ow-iw)/2:(oh-ih)/2"
            for index, (start, end) in enumerate(clips, 1):
                name = f"clip-{index:02}.mp4"
                self.update(job_id, status="rendering", current=index)
                result = subprocess.run([
                    self.ffmpeg, "-nostdin", "-hide_banner", "-loglevel", "error",
                    "-ss", str(start), "-i", str(source), "-t", str(end - start),
                    "-map", "0:v:0", "-map", "0:a:0?", "-vf", vf + ",setsar=1",
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                    "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k",
                    "-movflags", "+faststart", str(folder / name),
                ], capture_output=True, text=True, timeout=900)
                if result.returncode:
                    (folder / name).unlink(missing_ok=True)
                    raise ValueError(result.stderr.strip()[-400:] or "FFmpeg could not export this clip.")
                files.append({"name": name, "url": f"/exports/{job_id}/{name}"})
                self.update(job_id, files=list(files))
            self.update(job_id, status="done")
        except (OSError, ValueError, subprocess.TimeoutExpired) as error:
            self.update(job_id, status="error", error=str(error))


class Handler(BaseHTTPRequestHandler):
    def __init__(self, *args, clipper, **kwargs):
        self.clipper = clipper
        super().__init__(*args, **kwargs)

    def reply(self, data, status=200):
        payload = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def file(self, path, content_type, download=False):
        if not path.is_file():
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(path.stat().st_size))
        if download:
            self.send_header("Content-Disposition", f'attachment; filename="{path.name}"')
        self.end_headers()
        with path.open("rb") as stream:
            shutil.copyfileobj(stream, self.wfile)

    def do_GET(self):
        path = urlsplit(self.path).path
        if path == "/":
            self.file(HERE / "index.html", "text/html; charset=utf-8")
        elif re.fullmatch(r"/api/jobs/[a-f0-9]{32}", path):
            try:
                self.reply(self.clipper.snapshot(path.rsplit("/", 1)[1]))
            except KeyError:
                self.send_error(404)
        elif re.fullmatch(r"/exports/[a-f0-9]{32}/clip-\d{2}\.mp4", path):
            _, _, job_id, name = path.split("/")
            try:
                ready = any(f["name"] == name for f in self.clipper.snapshot(job_id)["files"])
            except KeyError:
                ready = False
            if ready:
                self.file(self.clipper.directory / job_id / name, "video/mp4", download=True)
            else:
                self.send_error(404)
        else:
            self.send_error(404)

    def do_POST(self):
        if self.headers.get("Host") != f"127.0.0.1:{self.server.server_port}" or self.headers.get("Origin") not in (
            None, f"http://127.0.0.1:{self.server.server_port}",
        ):
            self.send_error(403)
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if self.path == "/api/source":
                self.upload(size)
            elif self.path == "/api/export" and 0 < size <= 65536:
                self.export(json.loads(self.rfile.read(size)))
            else:
                self.send_error(404)
        except (KeyError, ValueError, TypeError, OSError, subprocess.TimeoutExpired) as error:
            self.reply({"error": str(error)}, 400)

    def upload(self, size):
        if not 0 < size <= MAX_UPLOAD:
            raise ValueError("Choose a video smaller than 8 GB.")
        source_id = uuid4().hex
        path = self.clipper.directory / source_id
        try:
            with path.open("wb") as stream:
                while size:
                    chunk = self.rfile.read(min(size, 1024 * 1024))
                    if not chunk:
                        raise ValueError("The upload ended early. Try again.")
                    stream.write(chunk)
                    size -= len(chunk)
            duration = self.clipper.duration(path)
            if duration < 0.1:
                raise ValueError("The source video is too short.")
        except (ValueError, OSError, subprocess.TimeoutExpired):
            path.unlink(missing_ok=True)
            raise
        self.clipper.sources[source_id] = (path, duration)
        self.reply({"id": source_id, "duration": duration})

    def export(self, data):
        source, duration = self.clipper.sources[data["source"]]
        resolution, framing = data["resolution"], data["framing"]
        if resolution not in ("1080", "4k") or framing not in ("crop", "fit"):
            raise ValueError("Choose a supported resolution and framing mode.")
        if not 1 <= len(data["clips"]) <= 20:
            raise ValueError("Choose between 1 and 20 clips.")
        clips = []
        for clip in data["clips"]:
            start, end = map(float, clip)
            if not (math.isfinite(start) and math.isfinite(end) and 0 <= start < end <= duration and end - start >= 0.099):
                raise ValueError("Each clip must be at least 0.1 seconds and fit inside the source video.")
            clips.append((start, end))
        job_id = uuid4().hex
        with self.clipper.lock:
            self.clipper.jobs[job_id] = dict(status="queued", current=0, total=len(clips), files=[])
        self.clipper.worker.submit(self.clipper.render, job_id, source, clips, resolution, framing)
        self.reply({"id": job_id}, 202)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()
    ffmpeg = os.environ.get("FFMPEG") or shutil.which("ffmpeg")
    if not ffmpeg and EXISTING_FFMPEG.is_file():
        ffmpeg = str(EXISTING_FFMPEG)
    if not ffmpeg:
        parser.error("Install FFmpeg or set FFMPEG to its executable path.")
    with TemporaryDirectory(prefix="clipping-") as directory:
        clipper = Clipper(ffmpeg, Path(directory))
        handler = partial(Handler, clipper=clipper)
        with ThreadingHTTPServer(("127.0.0.1", args.port), handler) as server:
            url = f"http://127.0.0.1:{server.server_port}"
            print(f"Clipping is running at {url}", flush=True)
            if not args.no_browser:
                webbrowser.open(url)
            try:
                server.serve_forever()
            except KeyboardInterrupt:
                pass
            finally:
                clipper.worker.shutdown(cancel_futures=True)


if __name__ == "__main__":
    main()
