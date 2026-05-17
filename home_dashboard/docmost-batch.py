#!/usr/bin/env python3
"""
DocMost Batch Page Manager

Usage:
  python3 docmost-batch.py list              - List all pages
  python3 docmost-batch.py list "keyword"    - List pages matching keyword
  python3 docmost-batch.py delete <id>       - Delete a single page
  python3 docmost-batch.py delete-all "key"  - Delete all pages matching keyword
  python3 docmost-batch.py delete-ids id1 id2 ...  - Delete specific pages by ID
  python3 docmost-batch.py nuke              - Delete ALL pages
"""

import sys
import json
import urllib.request

API = "http://192.168.110.223:3000"
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIwMTllMzIxNi1lNTlmLTcxYTYtYjkzMy1hMzgwOTA0MTVlNjkiLCJhcGlLZXlJZCI6IjAxOWUzMjUxLWVhZmItNzc5Ni1iODJhLWE3ODhjMjA0ZmQyZCIsIndvcmtzcGFjZUlkIjoiMDE5ZTMyMTYtZTVhYS03MjNkLWExZDAtMzJlOTI0NTgyODZlIiwidHlwZSI6ImFwaV9rZXkiLCJpYXQiOjE3Nzg5NjA2ODksImV4cCI6MTgxMDQ5NjY4OCwiaXNzIjoiRG9jbW9zdCJ9.EltL74Q71LBOr-Xe0_ulKStVRuELj54XV8tYteF2-NU"
SPACE_ID = "019e3216-e5c9-721d-b249-3e261907b2bb"


def api_post(endpoint, data):
    body = json.dumps(data).encode()
    req = urllib.request.Request(
        f"{API}{endpoint}",
        data=body,
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return json.loads(e.read())


def fetch_all_pages():
    all_pages = []
    cursor = None
    while True:
        payload = {"spaceId": SPACE_ID, "limit": 100}
        if cursor:
            payload["cursor"] = cursor
        result = api_post("/api/pages/recent", payload)
        data = result.get("data", {})
        items = data.get("items", [])
        all_pages.extend(items)
        meta = data.get("meta", {})
        if not meta.get("hasNextPage"):
            break
        cursor = meta.get("nextCursor")
    return all_pages


def delete_page(page_id):
    return api_post("/api/pages/delete", {"pageId": page_id})


def cmd_list(keyword=None):
    pages = fetch_all_pages()
    if keyword:
        pages = [p for p in pages if keyword.lower() in p["title"].lower()]
    for p in pages:
        print(f"  {p['id']}  {p['title']}")
    print(f"\n  {'Matched' if keyword else 'Total'}: {len(pages)} pages")


def cmd_delete(page_id):
    result = delete_page(page_id)
    if "error" in result:
        print(f"  Error: {result.get('message', result)}")
    else:
        print(f"  Deleted: {page_id}")


def cmd_delete_all(keyword):
    pages = fetch_all_pages()
    matched = [p for p in pages if keyword.lower() in p["title"].lower()]
    if not matched:
        print("  No pages found.")
        return
    print(f"  Found {len(matched)} pages matching '{keyword}':")
    for p in matched:
        print(f"    {p['title'][:70]}")
    confirm = input(f"\n  Delete all {len(matched)} pages? (yes/no): ")
    if confirm.strip().lower() != "yes":
        print("  Aborted.")
        return
    ok = 0
    for p in matched:
        result = delete_page(p["id"])
        if "error" not in result:
            ok += 1
            print(f"  Deleted: {p['title'][:60]}")
        else:
            print(f"  Failed: {p['title'][:60]} - {result.get('message')}")
    print(f"\n  Done. {ok}/{len(matched)} pages deleted.")


def cmd_delete_ids(ids):
    print(f"  Deleting {len(ids)} pages...")
    ok = 0
    for pid in ids:
        result = delete_page(pid)
        if "error" not in result:
            ok += 1
            print(f"  Deleted: {pid}")
        else:
            print(f"  Failed: {pid} - {result.get('message')}")
    print(f"\n  Done. {ok}/{len(ids)} deleted.")


def cmd_nuke():
    pages = fetch_all_pages()
    if not pages:
        print("  No pages to delete.")
        return
    print(f"  WARNING: This will delete ALL {len(pages)} pages!")
    confirm = input("  Type 'yes' to confirm: ")
    if confirm.strip() != "yes":
        print("  Aborted.")
        return
    ok = 0
    for p in pages:
        result = delete_page(p["id"])
        if "error" not in result:
            ok += 1
    print(f"  Done. {ok}/{len(pages)} pages deleted.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == "list":
        keyword = sys.argv[2] if len(sys.argv) > 2 else None
        cmd_list(keyword)
    elif cmd == "delete":
        if len(sys.argv) < 3:
            print("Usage: docmost-batch.py delete <page-id>")
            sys.exit(1)
        cmd_delete(sys.argv[2])
    elif cmd == "delete-all":
        if len(sys.argv) < 3:
            print("Usage: docmost-batch.py delete-all \"keyword\"")
            sys.exit(1)
        cmd_delete_all(sys.argv[2])
    elif cmd == "delete-ids":
        if len(sys.argv) < 3:
            print("Usage: docmost-batch.py delete-ids id1 id2 ...")
            sys.exit(1)
        cmd_delete_ids(sys.argv[2:])
    elif cmd == "nuke":
        cmd_nuke()
    else:
        print(__doc__)
