# Clipping

Clipping runs in your browser and uses FFmpeg on your computer. It needs Python 3.9 or newer and FFmpeg with the libx264 encoder. The launcher detects an FFmpeg installation on your PATH or the existing ShortFlow copy on this Mac. Set the FFMPEG environment variable to supply another executable.

From the clipping repository, run:

```sh
python3 app.py
```

1. Choose a local video. The app fills in an initial set of clip ranges.
2. Set a clip count and length, then select **Spread across video**. Change the start and end of each clip in seconds, or add a range from the preview's playhead.
3. Pick 1080p or 4K vertical output. **Center crop** fills the frame. **Fit with padding** keeps the full image.
4. Select **Export clips**, then download each MP4. Download your exports before closing the app. The server clears its temporary files when it shuts down normally.

The suggested ranges are evenly spaced. You choose which moments to keep. The browser may be unable to preview some formats that FFmpeg can export.

## Import a video link

Paste a public YouTube, Shorts, Instagram, TikTok, or other supported video URL and click **Import video**. Export works the same way as with local files. Availability depends on the platform and video. Use links for footage you have permission to download and edit.

Link import uses yt-dlp. Install it on your PATH or set the YTDLP environment variable to its executable path. The app also detects the copy in the earlier clipping workspace on this Mac. Install Node.js for YouTube extraction. Local files work without yt-dlp or Node.js.
