#!/usr/bin/env bash
set -euo pipefail

readonly PROG="${0##*/}"
readonly VERSION="0.1.0"
readonly NS_PER_SEC=1000000000

usage() {
  cat <<EOF
$PROG $VERSION - 渲染摸鱼时间平移工具

用法:
  $PROG [选项] 文件...

把一组文件的 atime/mtime 整体向后平移，保持文件之间的相对先后关系，
并让其中最新的文件落在当前时刻。

选项:
  -n, --dry-run   只显示将要执行的时间调整，不修改文件
  -v, --verbose   显示每个文件调整前后的时间
  -q, --quiet     不输出结果摘要
  -h, --help      显示帮助
  -V, --version   显示版本

示例:
  $PROG /path/to/render/*.exr
  $PROG -n /path/to/render/*.exr
  $PROG -v /path/to/render/*.exr
EOF
}

say() {
  (( QUIET )) || printf '%s\n' "$*"
}

stat_ns() {
  local fmt=$1 file=$2 raw sec frac
  raw=$(stat -c "$fmt" -- "$file") || return 1
  sec=${raw%%.*}
  if [[ $raw == *.* ]]; then
    frac=${raw#*.}
  else
    frac=0
  fi
  [[ $sec =~ ^[0-9]+$ ]] || return 1
  [[ $frac =~ ^[0-9]+$ ]] || frac=0
  printf '%s%09d\n' "$sec" "$((10#$frac))"
}

ns_to_ts() {
  local ns=$1
  printf '%d.%09d' "$((ns / NS_PER_SEC))" "$((ns % NS_PER_SEC))"
}

fmt_ns() {
  date -d "@$(ns_to_ts "$1")" '+%Y-%m-%d %H:%M:%S.%N %z'
}

DRY_RUN=0
VERBOSE=0
QUIET=0
FILES=()

while (($# > 0)); do
  case "$1" in
    -n|--dry-run) DRY_RUN=1 ;;
    -v|--verbose) VERBOSE=1 ;;
    -q|--quiet) QUIET=1 ;;
    -h|--help) usage; exit 0 ;;
    -V|--version) printf '%s %s\n' "$PROG" "$VERSION"; exit 0 ;;
    --) shift; FILES+=("$@"); break ;;
    -*) printf '%s: 未知选项: %s\n\n' "$PROG" "$1" >&2; usage >&2; exit 2 ;;
    *) FILES+=("$1") ;;
  esac
  shift
done

if ((${#FILES[@]} == 0)); then
  printf '%s: 缺少文件参数\n\n' "$PROG" >&2
  usage >&2
  exit 2
fi

INPUT_FILES=()
for f in "${FILES[@]}"; do
  if [[ -f "$f" ]]; then
    INPUT_FILES+=("$f")
  else
    printf '%s: 跳过（不是普通文件）: %s\n' "$PROG" "$f" >&2
  fi
done

if ((${#INPUT_FILES[@]} == 0)); then
  printf '%s: 没有可处理的普通文件\n' "$PROG" >&2
  exit 1
fi

MTIMES=()
ATIMES=()
MAX_MTIME=0

for i in "${!INPUT_FILES[@]}"; do
  f=${INPUT_FILES[$i]}
  if ! m=$(stat_ns '%.9Y' "$f"); then
    printf '%s: 无法读取修改时间: %s\n' "$PROG" "$f" >&2
    exit 1
  fi
  if ! a=$(stat_ns '%.9X' "$f"); then
    printf '%s: 无法读取访问时间: %s\n' "$PROG" "$f" >&2
    exit 1
  fi
  MTIMES[$i]=$m
  ATIMES[$i]=$a
  if ((10#$m > MAX_MTIME)); then
    MAX_MTIME=$((10#$m))
  fi
done

NOW_SEC=$(date +%s)
NOW_FRAC=$(date +%N)
[[ $NOW_FRAC =~ ^[0-9]+$ ]] || NOW_FRAC=0
NOW_NS=$((10#$NOW_SEC * NS_PER_SEC + 10#$NOW_FRAC))
DELTA=$((NOW_NS - MAX_MTIME))

if ((DELTA <= 0)); then
  printf '%s: 最新文件的时间不早于当前时间，无需调整\n' "$PROG" >&2
  exit 0
fi

DELTA_SEC=$((DELTA / NS_PER_SEC))
DELTA_FRAC=$((DELTA % NS_PER_SEC))

for i in "${!INPUT_FILES[@]}"; do
  f=${INPUT_FILES[$i]}
  old_m=${MTIMES[$i]}
  old_a=${ATIMES[$i]}
  new_m=$((old_m + DELTA))
  if ((old_a <= 0)); then
    new_a=$new_m
  else
    new_a=$((old_a + DELTA))
  fi
  new_m_ts=$(ns_to_ts "$new_m")
  new_a_ts=$(ns_to_ts "$new_a")

  if ((VERBOSE)); then
    printf '%s\n  修改时间: %s -> %s\n  访问时间: %s -> %s\n' \
      "$f" \
      "$(fmt_ns "$old_m")" "$(fmt_ns "$new_m")" \
      "$(fmt_ns "$old_a")" "$(fmt_ns "$new_a")"
  fi

  if ((DRY_RUN)); then
    continue
  fi

  touch -m -d "@$new_m_ts" -- "$f"
  touch -a -d "@$new_a_ts" -- "$f"
done

if ((DRY_RUN)); then
  say "$(printf '[dry-run] 将处理 %d 个文件，整体后移 %d.%09d 秒；最新文件将落在当前时刻' \
    "${#INPUT_FILES[@]}" "$DELTA_SEC" "$DELTA_FRAC")"
else
  say "$(printf '已处理 %d 个文件，整体后移 %d.%09d 秒；最新文件已落在当前时刻' \
    "${#INPUT_FILES[@]}" "$DELTA_SEC" "$DELTA_FRAC")"
fi