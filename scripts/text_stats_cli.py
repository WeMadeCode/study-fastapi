import argparse
import json
import os


def main():
    parser = argparse.ArgumentParser(description="统计 Unicode 码点数量")
    parser.add_argument("text", help="待统计文本；用 -- 结束选项解析")
    args = parser.parse_args()
    # argparse 默认返回 Any；在入口确认形状后再使用。
    text = args.text
    if not isinstance(text, str):
        parser.error("text 必须是字符串")
    print(json.dumps({"characters": len(text), "pid": os.getpid()}, ensure_ascii=False))


if __name__ == "__main__":
    main()
