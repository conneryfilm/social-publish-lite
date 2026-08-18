#!/usr/bin/env python3
"""
Post one video to several social platforms through the Content360 / OnlySocial API.

  python3 post_one.py --accounts
  python3 post_one.py --video clip.mp4 --accounts-ids 1,2,3 --caption "hi" --when "2026-09-01 09:00"

Config comes from config.json next to this script (copy config.example.json), or from
--base-url / --workspace / --token-file.
"""
import argparse, json, os, sys, time

try:
    import requests
except ImportError:
    sys.exit("requests is not installed.  pip3 install requests")

HERE = os.path.dirname(os.path.abspath(__file__))


def load_config(args):
    cfg = {}
    path = os.path.join(HERE, "config.json")
    if os.path.exists(path):
        cfg = json.load(open(path))
    if args.base_url:
        cfg["base_url"] = args.base_url
    if args.workspace:
        cfg["workspace"] = args.workspace
    if args.token_file:
        cfg["token_file"] = args.token_file
    for key in ("base_url", "workspace", "token_file"):
        if not cfg.get(key):
            sys.exit(f"Missing '{key}'. Copy config.example.json to config.json and fill it in.")
    tok_path = os.path.expanduser(cfg["token_file"])
    if not os.path.exists(tok_path):
        sys.exit(f"Token file not found: {tok_path}")
    cfg["token"] = open(tok_path).read().strip()
    if not cfg["token"]:
        sys.exit(f"Token file is empty: {tok_path}")
    return cfg


class Api:
    def __init__(self, cfg):
        self.base = f"{cfg['base_url'].rstrip('/')}/{cfg['workspace']}"
        self.s = requests.Session()
        self.s.headers.update({
            "Authorization": f"Bearer {cfg['token']}",
            "Accept": "application/json",
            "User-Agent": "social-publish-lite",
        })

    def __call__(self, method, path, **kw):
        """Rate-limit-aware request. The API 429s without warning, so back off and retry."""
        url = path if path.startswith("http") else f"{self.base}/{path}"
        delay = 2
        for _ in range(8):
            try:
                r = self.s.request(method, url, timeout=600, **kw)
            except requests.RequestException:
                time.sleep(2)
                continue
            if r.status_code == 429:
                time.sleep(delay)
                delay = min(delay * 1.6, 30)
                continue
            try:
                return r.json()
            except ValueError:
                return {"_status": r.status_code, "_text": r.text[:300]}
        return None


def list_accounts(api):
    j = api("GET", "accounts")
    rows = (j or {}).get("data", j if isinstance(j, list) else [])
    if not rows:
        sys.exit(f"Could not read accounts: {str(j)[:300]}")
    print(f"{'id':>10}  {'platform':<12}  name")
    print("-" * 52)
    for a in rows:
        print(f"{str(a.get('id','?')):>10}  {str(a.get('provider', a.get('platform','?'))):<12}  "
              f"{a.get('name') or a.get('username') or ''}")
        # Pinterest boards are numeric ids; posting with a board *name* is rejected.
        for b in (a.get("boards") or []):
            print(f"{'':>10}    board {b.get('id')}  {b.get('name','')}")
    return rows


def upload_media(api, path):
    size_mb = os.path.getsize(path) / (1024 * 1024)
    if size_mb > 100:
        print(f"warning: {size_mb:.0f} MB — uploads over ~100 MB often fail. Re-encode first.")
    with open(path, "rb") as f:
        j = api("POST", "media", files={"file": (os.path.basename(path), f, "video/mp4")})
    if isinstance(j, dict) and (j.get("data") or j.get("id")):
        return (j.get("data", j)).get("id")
    sys.exit(f"Upload failed: {str(j)[:300]}")


def build_body(args, account_ids, media_id):
    # The media id MUST be an integer. As a string the API returns 200 and then
    # silently fails the post with "media not selected".
    media_id = int(media_id)
    body = {"accounts": account_ids, "tags": []}
    if args.when:
        date, _, tm = args.when.partition(" ")
        if not tm:
            sys.exit('--when must look like "2026-09-01 09:00"')
        body.update(date=date, time=tm[:5], schedule=True)
    else:
        body["schedule"] = False

    if args.format == "vertical":
        options = {"instagram": {"type": "reel", "collaborators": [], "share_to_story": False}}
        if args.tiktok_account:
            t = args.tiktok_account
            options["tiktok"] = {
                "privacy_level": {"account-0": "PUBLIC_TO_EVERYONE", f"account-{t}": "PUBLIC_TO_EVERYONE"},
                "allow_comments": {"account-0": True, f"account-{t}": True},
                "allow_duet": {"account-0": True, f"account-{t}": True},
                "allow_stitch": {"account-0": True, f"account-{t}": True},
            }
        if args.pinterest_account and args.pinterest_board:
            p = args.pinterest_account
            options["pinterest"] = {
                "title": args.caption[:100],
                "link": "",
                "boards": {"account-0": args.pinterest_board, f"account-{p}": args.pinterest_board},
            }
    else:
        options = {
            "facebook_page": {"type": "post", "share_to_story": False,
                              "loop_count": 0, "livestream_title": ""},
            "youtube": {"type": "video", "title": args.youtube_title or args.caption[:100],
                        "status": "public", "made_for_kids": False, "loop_count": 0, "tags": []},
        }

    body["versions"] = [{
        "account_id": 0,
        "is_original": True,
        "content": [{"body": args.caption, "media": [media_id], "url": ""}],
        "options": options,
    }]
    return body


def main():
    p = argparse.ArgumentParser(description="Post one video to multiple social platforms.")
    p.add_argument("--accounts", action="store_true", help="list connected accounts and exit")
    p.add_argument("--video")
    p.add_argument("--accounts-ids", help="comma-separated numeric account ids")
    p.add_argument("--caption", default="")
    p.add_argument("--when", help='"YYYY-MM-DD HH:MM" — omit to post now')
    p.add_argument("--format", choices=["vertical", "horizontal"], default="vertical")
    p.add_argument("--youtube-title")
    p.add_argument("--tiktok-account", type=int)
    p.add_argument("--pinterest-account", type=int)
    p.add_argument("--pinterest-board", help="numeric board id (names are rejected)")
    p.add_argument("--base-url")
    p.add_argument("--workspace")
    p.add_argument("--token-file")
    args = p.parse_args()

    api = Api(load_config(args))

    if args.accounts:
        list_accounts(api)
        return

    if not args.video or not args.accounts_ids:
        p.error("--video and --accounts-ids are required (or use --accounts to look them up)")
    video = os.path.expanduser(args.video)
    if not os.path.exists(video):
        sys.exit(f"No such file: {video}")
    try:
        account_ids = [int(x) for x in args.accounts_ids.split(",") if x.strip()]
    except ValueError:
        sys.exit("--accounts-ids must be numeric ids, comma-separated. Run --accounts to list them.")

    print(f"uploading {os.path.basename(video)} ...")
    media_id = upload_media(api, video)
    print(f"  media id {media_id}")

    j = api("POST", "posts", json=build_body(args, account_ids, media_id))
    uuid = (j or {}).get("data", j if isinstance(j, dict) else {}).get("uuid")
    if not uuid:
        sys.exit(f"Post creation failed: {str(j)[:300]}")
    print(f"posted — {uuid}")
    print("Check it in the dashboard: a post can be created and still fail at platform level.")


if __name__ == "__main__":
    main()

