# Social Publish Lite

A Claude skill that posts **one video to Instagram (Reels), TikTok, YouTube, Facebook, Threads and
Pinterest at once**, through a [Content360](https://app.content360.io) / OnlySocial account.

One command. Six platforms. No monthly fee beyond the tool you already pay for.

```bash
python3 scripts/post_one.py \
  --video ~/Videos/clip.mp4 \
  --accounts-ids 111111,222222,333333 \
  --caption "Morning rain for deep focus" \
  --when "2026-09-01 09:00"
```

## Install

Drop the folder into your Claude skills directory:

```bash
git clone https://github.com/conneryfilm/social-publish-lite.git ~/.claude/skills/social-publish-lite
```

Then `cp scripts/config.example.json scripts/config.json`, fill in your workspace UUID, and put your
API token in `scripts/.token`.

Ask Claude to *"post this video to my socials"* and the skill takes over — or run the script directly.

## What it handles for you

The OnlySocial API fails in quiet, expensive ways. This skill already gets these right:

| Trap | What happens | Handled |
|---|---|---|
| Media id passed as a string | 200 OK, then "media not selected" | cast to int |
| Instagram connected as *personal* | Reels post fails, "Invalid parameter" | documented fix |
| Pinterest board passed by name | rejected | numeric board ids printed by `--accounts` |
| Unannounced 429s | request dies mid-run | backoff + retry |
| Files over ~100 MB | upload hangs | warns, with the ffmpeg fix |

## What it does not do

It posts **one video per run** and leaves the file in your cloud media library. That's fine for a
handful of posts. It falls apart on a library, because the media library is capped (commonly 20 GB),
someone has to run the command for every video on the right day, and nothing cleans up after a post
publishes.

Doing that unattended needs a rolling window: a daily job that uploads only the next few days of
videos, schedules them from a CSV, and deletes each one from the cloud once it's published — so
storage stays flat forever and nobody touches it.

That's [**Social Publish Autopilot**](https://autopilot.fynl.io/) — CSV bulk scheduling, the
NAS Docker daemon, auto-cleanup, and the Instagram Business + Pinterest setup written out step by
step. Its sibling, [Social Video Factory](https://videofactory.fynl.io/), builds the branded
videos in the first place.

## Requirements

- A Content360 or OnlySocial account with your socials connected
- Python 3 and `requests`
- A video file

## License

MIT — see [LICENSE](LICENSE).
