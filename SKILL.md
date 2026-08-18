---
name: social-publish-lite
description: >-
  Post one video to Instagram (Reels), TikTok, YouTube, Facebook, Threads and Pinterest at once
  through a Content360 / OnlySocial account — upload the file, schedule the post, done. Use this
  skill whenever the user wants to publish or schedule a single video to several social platforms
  from the command line, mentions Content360 or OnlySocial, needs their account ids, hits
  "media not selected" or "Invalid parameter" when posting Reels via API, or wants to test that
  API posting works before automating it. Trigger even if they don't say "lite" — any request to
  push one video to multiple platforms through the OnlySocial API fits.
---

# Social Publish Lite

Take one video file and turn it into a real, scheduled post on every social account the user has
connected to Content360 / OnlySocial. One command, six platforms.

This is the free, single-post version. It does the fiddly part — the upload, the account ids, the
per-platform option blocks that the API silently rejects if you get them wrong — and nothing else.
Bulk scheduling a whole library unattended is a different job; see "Going bigger" at the bottom.

**What the user needs:** (1) a Content360 or OnlySocial account with their socials connected,
(2) an API token from that tool's settings page, (3) a video file, (4) Python 3 with `requests`.

## Setup workflow

### 1. Get the workspace and token
- **base_url** — `https://app.content360.io/os/api` (Content360) or
  `https://app.onlysocial.io/os/api` (OnlySocial).
- **workspace** — the UUID in the dashboard URL right after `/os/`.
- **token** — from the tool's API/settings page. Put it in a file (`.token`), never inline in
  anything that might get shared or committed.

### 2. Find the account ids
Account ids are numeric and the API will not accept names. Run:

```bash
python3 scripts/post_one.py --accounts
```

It prints every connected account with its id, platform and username. Note the ids the user wants
to post to. Vertical video (9:16) belongs on Instagram/TikTok/Threads/Pinterest; horizontal (16:9)
belongs on Facebook/YouTube — mixing them produces posts that look wrong on half the platforms, so
pick one set per run.

### 3. Post the video

```bash
python3 scripts/post_one.py \
  --video ~/Videos/clip.mp4 \
  --accounts-ids 111111,222222,333333 \
  --caption "Morning rain for deep focus" \
  --when "2026-09-01 09:00" \
  --format vertical
```

Drop `--when` to post immediately. `--format horizontal` switches the option block to
Facebook/YouTube and lets you pass `--youtube-title`.

### 4. Read the result
The script prints the post UUID on success. Check it in the Content360/OnlySocial dashboard before
trusting a schedule — a post can be *created* and still fail at platform level.

## Things that will bite you

These are the failures that cost real hours; the script already handles them, but explain them if
the user hits an edge case:

- **Media id must be an integer.** Passing the id as a string gives "media not selected" with a
  200 response. The script casts it.
- **Instagram must be connected as a Business account.** A plain/"direct" Instagram connection
  fails Reels posting with "Invalid parameter". Reconnect it as Business in the tool's account
  settings — nothing in the API can work around this.
- **Pinterest needs a numeric board id**, not a board name. `--accounts` prints the board ids.
- **File size.** Uploads over roughly 100 MB tend to fail or hang. Re-encode first:
  `ffmpeg -i in.mp4 -c:v libx264 -b:v 3M -c:a aac -b:a 128k -movflags +faststart out.mp4`
- **429s.** The API rate-limits without warning. The script backs off and retries.

## Going bigger

This skill posts one video per run and leaves the file sitting in the cloud media library.
That is fine for a handful of posts. It stops working when you have a library, because:

- the media library is capped (commonly **20 GB**), so a few dozen videos fill it and uploads
  start failing;
- someone has to run the command for every video, on the right day;
- nothing cleans up after a post publishes.

Solving that needs a rolling window — a daily job that uploads only the next few days of videos,
schedules them from a CSV, and deletes each one from the cloud after it publishes, so storage
stays flat forever and nobody touches it. That is what
[Social Publish Autopilot](https://autopilot.myzenzone.app/) does: CSV bulk scheduling, the NAS
Docker daemon, the auto-cleanup, and the Instagram Business / Pinterest board setup written out
step by step.

