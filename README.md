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

## Captions, music, and uploads

Enter an **On-screen caption** for each range. The text appears throughout that clip. Caption export requires FFmpeg with the drawtext filter. Choose an audio file under **Background music** and set its volume. Music starts at the beginning of each clip, loops if needed, and mixes with the source audio.

After exporting, choose a clip, write the post caption, and choose a platform. YouTube also needs a title and visibility. Instagram publishes the Reel publicly after processing. Choose 1080p for Instagram if a higher-resolution export is rejected.

To enable direct uploads, supply credentials as environment variables before starting the app. Keep them out of the repository.

| Platform | Environment variables |
| --- | --- |
| YouTube | `CLIPPING_YOUTUBE_TOKEN` with the `youtube.upload` scope |
| Instagram | `CLIPPING_INSTAGRAM_TOKEN`, `CLIPPING_INSTAGRAM_ID` and `CLIPPING_META_VERSION` for a professional Instagram account linked to Facebook, using a Meta app with Facebook Login for Business and Instagram content publishing access |

Use current tokens with permission to publish to the intended accounts. Restart Clipping after updating an expired token. You can also download the MP4 and use the YouTube Studio or Meta Business Suite links in the app.

[YouTube upload setup](https://developers.google.com/youtube/data/guides/uploading_a_video) · [Instagram content publishing](https://developers.facebook.com/docs/instagram-platform/instagram-api-with-facebook-login/content-publishing/)

## Browser edition

Use [Clipping on GitHub Pages](https://akshatjaiswal070.github.io/clipping/) to trim a local video and export a 720 × 1280 clip in a supported browser. Choose Cold Edit for a dark, high-contrast look, YT Shorts Edit for a center crop, or Insta Edit to keep the full source frame over a dimmed background. The browser records the clip in real time and downloads MP4 or WebM based on its recording support. The video stays on your device.
