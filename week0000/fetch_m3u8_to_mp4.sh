#!/usr/bin/env bash
set -euo pipefail

# Fetch ixunke m3u8 URL via stream_info, then remux to MP4 with ffmpeg.
# Requirements: bash, curl, python3, ffmpeg.

# -------- configurable inputs (override via env) --------
ACCESS_TOKEN="${ACCESS_TOKEN:-${TOKEN:-}}"
ACCESS_URL="${ACCESS_URL:-}"
ACCESS_CURL="${ACCESS_CURL:-}"
ROOM_ID="${ROOM_ID:-59}"
LESSON_ID="${LESSON_ID:-1071}"
VIDEO_FORMAT="${VIDEO_FORMAT:-rtmp}"
API_HOST="${API_HOST:-api.ixunke.cn}"
APP_NAME="${APP_NAME:-appni3brwoydrxr}"
OUT_MP4="${OUT_MP4:-./output.mp4}"
CLIP_SECONDS="${CLIP_SECONDS:-}"

# 如果没有提供 ACCESS_TOKEN，尝试从缓存读取
if [ -z "$ACCESS_TOKEN" ] && [ -z "$ACCESS_URL" ] && [ -z "$ACCESS_CURL" ]; then
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  CACHED_TOKEN=$(python3 "${SCRIPT_DIR}/token_manager.py" get 2>/dev/null || true)
  if [ -n "$CACHED_TOKEN" ]; then
    ACCESS_TOKEN="$CACHED_TOKEN"
    echo ">> 使用缓存的 token (${CACHED_TOKEN:0:20}...)"
  fi
fi

if [ -z "${ACCESS_TOKEN}" ] && { [ -n "${ACCESS_URL}" ] || [ -n "${ACCESS_CURL}" ]; }; then
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
print(qs.get("token", [""])[0])
print(qs.get("lessonId", [""])[0])
print(qs.get("id", [""])[0])
print(qs.get("videoFormat", [""])[0])
')
  ACCESS_TOKEN=$(printf '%s\n' "$parsed" | sed -n '1p')
  parsed_lesson_id=$(printf '%s\n' "$parsed" | sed -n '2p')
  parsed_room_id=$(printf '%s\n' "$parsed" | sed -n '3p')
  parsed_video_format=$(printf '%s\n' "$parsed" | sed -n '4p')
  if [ -n "$parsed_lesson_id" ]; then
    LESSON_ID="$parsed_lesson_id"
  fi
  if [ -n "$parsed_room_id" ]; then
    ROOM_ID="$parsed_room_id"
  fi
  if [ -n "$parsed_video_format" ]; then
    VIDEO_FORMAT="$parsed_video_format"
  fi
fi

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

api_base="https://${API_HOST}/${APP_NAME}/api/v1"

if [ -z "${ACCESS_TOKEN}" ]; then
  echo "ACCESS_TOKEN is required."
  echo "Use the VTJ... token captured from /api/lesson or /api/v1/room/stream_info,"
  echo "not the minicheckaccount login token."
  exit 1
fi

echo ">> 1) fetch stream_info to get signed m3u8..."
stream_json=$(curl -s "${COMMON_HEADERS[@]}" --compressed \
  "${api_base}/room/stream_info?id=${ROOM_ID}&videoFormat=${VIDEO_FORMAT}&lessonId=${LESSON_ID}&app=true&token=${ACCESS_TOKEN}")

M3U8=$(python3 -c 'import json,sys
data=json.load(sys.stdin)
if data.get("errno") != 0:
    sys.stderr.write(f"stream_info error: {data}\n")
    sys.exit(1)
try:
    print(data["data"]["mediaUri"])
except Exception as e:
    sys.stderr.write(f"Failed to parse mediaUri: {e}\nFull response: {data}\n")
    sys.exit(1)
' <<<"$stream_json")
if [ -z "${M3U8}" ]; then
  echo "Empty m3u8, abort. Raw response:"
  echo "$stream_json"
  exit 1
fi
echo "   m3u8: ${M3U8}"

echo ">> 2) fetch playlist body..."
M3U8_BODY=$(curl -s -H "User-Agent: ${UA}" -H "Referer: ${REFERER}" "${M3U8}")
if [ -z "${M3U8_BODY}" ]; then
  echo "Empty playlist body, abort."
  exit 1
fi

echo ">> 3) remux to MP4 with ffmpeg..."
ffmpeg_args=(
  -y
  -loglevel warning
  -stats
  -headers "User-Agent: ${UA}\r\nReferer: ${REFERER}\r\n"
)
if [ -n "${CLIP_SECONDS}" ]; then
  ffmpeg_args+=(-t "${CLIP_SECONDS}")
fi
ffmpeg "${ffmpeg_args[@]}" -i "${M3U8}" -c copy -bsf:a aac_adtstoasc -movflags +faststart "${OUT_MP4}"
echo "Done. Saved to ${OUT_MP4}"
