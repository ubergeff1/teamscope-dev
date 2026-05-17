#!/bin/bash
# DocMost Batch Page Manager
# Usage:
#   ./docmost-batch.sh list              - List all pages
#   ./docmost-batch.sh list "keyword"    - List pages matching keyword
#   ./docmost-batch.sh delete <id>       - Delete a single page
#   ./docmost-batch.sh delete-all "keyword" - Delete all pages matching keyword
#   ./docmost-batch.sh delete-ids id1 id2 id3 ... - Delete specific pages by ID
#   ./docmost-batch.sh nuke              - Delete ALL pages (danger!)

API="http://192.168.110.223:3000"
TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIwMTllMzIxNi1lNTlmLTcxYTYtYjkzMy1hMzgwOTA0MTVlNjkiLCJhcGlLZXlJZCI6IjAxOWUzMjUxLWVhZmItNzc5Ni1iODJhLWE3ODhjMjA0ZmQyZCIsIndvcmtzcGFjZUlkIjoiMDE5ZTMyMTYtZTVhYS03MjNkLWExZDAtMzJlOTI0NTgyODZlIiwidHlwZSI6ImFwaV9rZXkiLCJpYXQiOjE3Nzg5NjA2ODksImV4cCI6MTgxMDQ5NjY4OCwiaXNzIjoiRG9jbW9zdCJ9.EltL74Q71LBOr-Xe0_ulKStVRuELj54XV8tYteF2-NU"
SPACE_ID="019e3216-e5c9-721d-b249-3e261907b2bb"

fetch_pages() {
  curl -s -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
    -d "{\"spaceId\":\"$SPACE_ID\",\"limit\":200}" \
    "$API/api/pages/recent"
}

delete_page() {
  local page_id="$1"
  curl -s -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
    -d "{\"pageId\":\"$page_id\"}" \
    "$API/api/pages/delete"
}

case "$1" in
  list)
    FILTER="${2:-}"
    fetch_pages | python3 -c "
import sys, json
data = json.load(sys.stdin)
pages = data['data']['items']
filt = '$FILTER'.lower()
for p in pages:
    if filt and filt not in p['title'].lower():
        continue
    print(f'{p[\"id\"]}  {p[\"title\"]}')
if not filt:
    print(f'\nTotal: {len(pages)} pages')
else:
    matched = [p for p in pages if filt in p['title'].lower()]
    print(f'\nMatched: {len(matched)} pages')
"
    ;;

  delete)
    if [ -z "$2" ]; then echo "Usage: $0 delete <page-id>"; exit 1; fi
    echo "Deleting page $2..."
    delete_page "$2"
    echo
    ;;

  delete-all)
    if [ -z "$2" ]; then echo "Usage: $0 delete-all \"keyword\""; exit 1; fi
    FILTER="$2"
    echo "Finding pages matching '$FILTER'..."
    PAGES=$(fetch_pages | python3 -c "
import sys, json
data = json.load(sys.stdin)
pages = data['data']['items']
filt = '$FILTER'.lower()
matched = [p for p in pages if filt in p['title'].lower()]
for p in matched:
    print(p['id'])
")
    COUNT=$(echo "$PAGES" | grep -c .)
    if [ "$COUNT" -eq 0 ]; then echo "No pages found."; exit 0; fi
    echo "Found $COUNT pages. Deleting..."
    echo "$PAGES" | while read -r pid; do
      RESULT=$(delete_page "$pid")
      TITLE=$(echo "$RESULT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('data',{}).get('title','done'))" 2>/dev/null || echo "done")
      echo "  Deleted: $pid"
    done
    echo "Done. $COUNT pages deleted."
    ;;

  delete-ids)
    shift
    if [ $# -eq 0 ]; then echo "Usage: $0 delete-ids id1 id2 id3 ..."; exit 1; fi
    echo "Deleting $# pages..."
    for pid in "$@"; do
      delete_page "$pid" > /dev/null
      echo "  Deleted: $pid"
    done
    echo "Done."
    ;;

  nuke)
    echo "⚠️  This will delete ALL pages in the space!"
    read -p "Type 'yes' to confirm: " CONFIRM
    if [ "$CONFIRM" != "yes" ]; then echo "Aborted."; exit 0; fi
    PAGES=$(fetch_pages | python3 -c "
import sys, json
data = json.load(sys.stdin)
for p in data['data']['items']:
    print(p['id'])
")
    COUNT=$(echo "$PAGES" | grep -c .)
    echo "Deleting $COUNT pages..."
    echo "$PAGES" | while read -r pid; do
      delete_page "$pid" > /dev/null
      echo "  Deleted: $pid"
    done
    echo "Done. $COUNT pages deleted."
    ;;

  *)
    echo "DocMost Batch Page Manager"
    echo ""
    echo "Commands:"
    echo "  list              - List all pages"
    echo "  list \"keyword\"    - List pages matching keyword"
    echo "  delete <id>       - Delete a single page by ID"
    echo "  delete-all \"key\"  - Delete all pages matching keyword"
    echo "  delete-ids id1 id2 ... - Delete specific pages by ID"
    echo "  nuke              - Delete ALL pages"
    ;;
esac
