#!/usr/bin/env bash
set -euo pipefail

# Batch-download all lessons in a course: fetch lesson list -> fetch signed m3u8 per lesson -> remux to MP4.
# Requirements: bash, curl, python3, ffmpeg.
#
# Usage:
#   ACCESS_TOKEN="xxx" bash fetch_course_to_mp4.sh            # defaults to course 41, outputs to ./outputs
#   ACCESS_TOKEN="xxx" COURSE_ID=41 OUT_DIR=/tmp/mp4 bash fetch_course_to_mp4.sh
#   ACCESS_URL="https://.../api/lesson?...&token=VTJ..." bash fetch_course_to_mp4.sh
#   ACCESS_CURL='curl "https://.../api/lesson?...&token=VTJ..." ...' bash fetch_course_to_mp4.sh
#
# Inputs (env override):
COURSE_ID="${COURSE_ID:-41}"
ACCESS_TOKEN="${ACCESS_TOKEN:-${TOKEN:-}}"
ACCESS_URL="${ACCESS_URL:-}"
ACCESS_CURL="${ACCESS_CURL:-}"
API_HOST="${API_HOST:-api.ixunke.cn}"
APP_NAME="${APP_NAME:-appni3brwoydrxr}"
VIDEO_FORMAT="${VIDEO_FORMAT:-rtmp}"
OUT_DIR="${OUT_DIR:-./outputs}"
ONLY_LESSON_ID="${ONLY_LESSON_ID:-}"
CLIP_SECONDS="${CLIP_SECONDS:-}"

# 如果没有提供 ACCESS_TOKEN，尝试从缓存读取
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -z "$ACCESS_TOKEN" ] && [ -z "$ACCESS_URL" ] && [ -z "$ACCESS_CURL" ]; then
  CACHED_TOKEN=$(python3 "${SCRIPT_DIR}/token_manager.py" get 2>/dev/null || true)
  if [ -n "$CACHED_TOKEN" ]; then
    ACCESS_TOKEN="$CACHED_TOKEN"
    echo ">> 使用缓存的 token (${CACHED_TOKEN:0:20}...)"
  fi
fi

if [ -z "$ACCESS_TOKEN" ] && { [ -n "$ACCESS_URL" ] || [ -n "$ACCESS_CURL" ]; }; then
  parsed=$(python3 -c 'import os, shlex, urllib.parse
raw = os.environ.get("ACCESS_URL") or os.environ.get("ACCESS_CURL") or ""
if raw.startswith("curl "):
    try:
        parts = shlex.split(raw)
    except Exception:
        parts = raw.split()
    matches = [p for p in parts if p.startswith("http://") or p.startswith("https://")]
    raw = matches[0] if matches else raw
raw = raw.rstrip("。")
qs = urllib.parse.parse_qs(urllib.parse.urlparse(raw).query)
token = qs.get("token", [""])[0]
course_id = qs.get("courseId", [""])[0]
print(token)
print(course_id)
' )
  ACCESS_TOKEN=$(printf '%s\n' "$parsed" | sed -n '1p')
  parsed_course_id=$(printf '%s\n' "$parsed" | sed -n '2p')
  if [ -n "$parsed_course_id" ]; then
    COURSE_ID="$parsed_course_id"
  fi
fi

if [ -z "$ACCESS_TOKEN" ]; then
  echo "ACCESS_TOKEN is required."
  echo "Use the VTJ... token captured from /api/lesson or /api/v1/room/stream_info,"
  echo "not the minicheckaccount login token."
  exit 1
fi

mkdir -p "$OUT_DIR"

UA="Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 MicroMessenger/8.0.69(0x18004533) NetType/WIFI Language/zh_CN"
REFERER="https://servicewechat.com/wx613cd6930dab2d0a/2/page-frame.html"
COMMON_HEADERS=(
  -H "Host: ${API_HOST}"
  -H "x-platform: mp"
  -H "content-type: application/json"
  -H "x-systemType: ios"
  -H "User-Agent: ${UA}"
  -H "Referer: ${REFERER}"
)

api_base="https://${API_HOST}/${APP_NAME}/api"

echo ">> Fetch lesson list for course ${COURSE_ID}..."
lesson_json=$(curl -s "${COMMON_HEADERS[@]}" --compressed \
  "${api_base}/lesson?courseId=${COURSE_ID}&list=true&rewardedAd=1&app=true&token=${ACCESS_TOKEN}")

lessons=$(python3 -c 'import json,sys,re
data=json.load(sys.stdin)
if data.get("errno")!=0:
    sys.stderr.write(f"Lesson list error: {data}\n"); sys.exit(1)
rows=[]
for item in data.get("data",[]):
    lid=item["id"]
    room=item.get("relateRoomId") or item.get("roomId") or item.get("streamName") or ""
    title=item.get("title","lesson")
    safe=re.sub(r"[^\w\d.-]+","_",title).strip("_")
    rows.append((lid,room,safe))
for lid,room,safe in rows:
    print(f"{lid}\t{room}\t{safe}")
' <<<"$lesson_json")

if [ -z "$lessons" ]; then
  echo "No lessons parsed. Raw response:"
  echo "$lesson_json"
  exit 1
fi

echo "Found lessons:"
echo "$lessons"

while IFS=$'\t' read -r LESSON_ID ROOM_ID SAFE_TITLE; do
  [ -z "$LESSON_ID" ] && continue
  if [ -n "$ONLY_LESSON_ID" ] && [ "$LESSON_ID" != "$ONLY_LESSON_ID" ]; then
    continue
  fi
  echo ">> Lesson ${LESSON_ID} (room ${ROOM_ID}) -> ${SAFE_TITLE}.mp4"
  out_path="${OUT_DIR}/${SAFE_TITLE:-lesson_${LESSON_ID}}.mp4"
  tmp_out="${out_path}.part"
  download_ok=0

  if [ -f "$out_path" ] && ffprobe -v error -show_entries format=duration "$out_path" >/dev/null 2>&1; then
    echo "   existing valid file found, skip."
    continue
  fi

  for attempt in 1 2 3; do
    echo "   prepare attempt ${attempt}/3 ..."
    stream_json=$(curl -s "${COMMON_HEADERS[@]}" --compressed \
      "${api_base}/v1/room/stream_info?id=${ROOM_ID}&videoFormat=${VIDEO_FORMAT}&lessonId=${LESSON_ID}&app=true&token=${ACCESS_TOKEN}")
    M3U8=$(python3 -c 'import json,sys
data=json.load(sys.stdin)
if data.get("errno") != 0:
    sys.stderr.write(f"stream_info error: {data}\n"); sys.exit(1)
try:
    print(data["data"]["mediaUri"])
except Exception as e:
    sys.stderr.write(f"Parse mediaUri failed: {e}\nFull response: {data}\n"); sys.exit(1)
' <<<"$stream_json")

    if [ -z "$M3U8" ]; then
      echo "   empty mediaUri, retry..."
      sleep 1
      continue
    fi

    # GET the playlist body; HEAD on this CDN is unreliable.
    M3U8_BODY=$(curl -s -H "User-Agent: ${UA}" -H "Referer: ${REFERER}" "$M3U8")
    ts_sample=$(python3 -c 'import sys
count = 0
for line in sys.stdin.read().splitlines():
    if (line.startswith("http://") or line.startswith("https://")) and ".ts" in line:
        print(line)
        count += 1
        if count == 3:
            break
' <<<"$M3U8_BODY")
    sample_ok=1
    if [ -z "$ts_sample" ]; then
      sample_ok=0
    else
      while read -r tsurl; do
        [ -z "$tsurl" ] && continue
        st=$(curl -s -r 0-1023 -o /dev/null -w "%{http_code}" -H "User-Agent: ${UA}" -H "Referer: ${REFERER}" "$tsurl")
        if [ "$st" != "200" ] && [ "$st" != "206" ]; then
          sample_ok=0
          break
        fi
      done <<< "$ts_sample"
    fi

    if [ $sample_ok -ne 1 ]; then
      echo "   playlist/TS sample check failed, refetch..."
      sleep 1
      continue
    fi

    echo "   ffmpeg attempt ${attempt}/3 ..."
    rm -f "$tmp_out"
    ffmpeg_args=(
      -y
      -loglevel warning
      -stats
      -headers "User-Agent: ${UA}\r\nReferer: ${REFERER}\r\n"
    )
    if [ -n "$CLIP_SECONDS" ]; then
      ffmpeg_args+=(-t "$CLIP_SECONDS")
    fi
    if ffmpeg "${ffmpeg_args[@]}" \
      -i "$M3U8" -c copy -bsf:a aac_adtstoasc -movflags +faststart "$tmp_out"; then
        mv "$tmp_out" "$out_path"
        download_ok=1
        echo "   saved: $out_path"
        break
    fi
    echo "   ffmpeg failed, refetch validated m3u8 and retry..."
    sleep 1
  done

  if [ $download_ok -ne 1 ]; then
    echo "  !! give up ${SAFE_TITLE} after retries."
  fi
  rm -f "$tmp_out"
done <<< "$lessons"

echo "All done."
