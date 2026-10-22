#!/usr/bin/env bash
# 已知手滑词扫描:命中则打印行号并退出 1,通过则退出 0
TYPOS="contet|emial|DATATBASE|retrun|lenght|publich"

if [ $# -eq 0 ]; then
    echo "用法: check_typos.sh <文件...>"
    exit 2
fi

for path in "$@"; do
    if [ ! -f "$path" ] || [ ! -r "$path" ]; then
        echo "无法读取文件: $path" >&2
        exit 2
    fi
done

matches=$(grep -nE "$TYPOS" "$@")
status=$?
if [ "$status" -eq 2 ]; then
    echo "扫描失败" >&2
    exit 2
elif [ "$status" -eq 0 ]; then
    echo "$matches"
    echo "发现手滑词 ↑"
    exit 1
else
    echo "拼写扫描通过"
fi