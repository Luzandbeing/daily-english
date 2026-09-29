#!/usr/bin/env python3
"""扫描 study/*/study.json，生成站点首页 index.html，并修正各主题页的 <title>。

用法：
    python3 tools/build_index.py            # 生成首页 + 修正标题
    python3 tools/build_index.py --check    # 只报告，不写文件

设计约束：
  * 首页与主题页同为自包含单文件（无外部依赖），可直接静态托管。
  * 样式变量与主题页保持同一套设计语言（含深色模式）。
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from datetime import date, datetime
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent.parent
STUDY = ROOT / "study"
INDEX = ROOT / "index.html"

DATE_RE = re.compile(r"(\d{4})[.\-/]?(\d{2})[.\-/]?(\d{2})")

PAGE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>英语学习 · 目录</title>
<style>
  :root{{
    --bg:#f6f7f9; --card:#ffffff; --fg:#191b1f; --muted:#6b7280; --line:#e4e7ec;
    --accent:#4d6bfe; --accent-soft:#eef1ff;
    --serif:"Iowan Old Style",Georgia,"Times New Roman",serif;
    --sans:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue",
           "PingFang SC","Hiragino Sans GB","Microsoft YaHei",sans-serif;
    --radius:12px; --shadow:0 1px 2px rgba(16,24,40,.06),0 1px 3px rgba(16,24,40,.1);
  }}
  @media (prefers-color-scheme:dark){{
    :root{{
      --bg:#15171c; --card:#1d2027; --fg:#e8eaed; --muted:#9aa3af; --line:#2c313b;
      --accent:#8ba2ff; --accent-soft:#242a3f; --shadow:none;
    }}
  }}
  *{{box-sizing:border-box}}
  body{{margin:0;background:var(--bg);color:var(--fg);font-family:var(--sans);
       font-size:16px;line-height:1.65;-webkit-text-size-adjust:100%}}
  a{{color:var(--accent);text-decoration:none}}
  .wrap{{max-width:820px;margin:0 auto;padding:0 20px 64px}}
  header.top{{padding:34px 0 20px;border-bottom:1px solid var(--line);margin-bottom:22px}}
  h1{{margin:0 0 6px;font-size:25px;line-height:1.3}}
  .sub{{color:var(--muted);font-size:14px}}
  ul.list{{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:12px}}
  li.card{{background:var(--card);border:1px solid var(--line);border-radius:var(--radius);
          box-shadow:var(--shadow)}}
  li.card > a{{display:block;padding:16px 18px}}
  .t{{font-size:17px;font-weight:600;color:var(--fg);line-height:1.4}}
  .d{{color:var(--muted);font-size:13.5px;margin-top:5px}}
  .meta{{display:flex;flex-wrap:wrap;gap:8px;margin-top:11px}}
  .badge{{background:var(--accent-soft);color:var(--accent);border-radius:999px;
         padding:2px 10px;font-size:12.5px;white-space:nowrap}}
  footer{{margin-top:34px;padding-top:16px;border-top:1px solid var(--line);
         color:var(--muted);font-size:12.5px}}
</style>
</head>
<body>
<div class="wrap">
  <header class="top">
    <h1>英语学习 · 目录</h1>
    <div class="sub">共 {count} 个主题 · 点击进入逐句精读、词汇、语法与练习</div>
  </header>
  <ul class="list">
{cards}
  </ul>
  <footer>由 tools/build_index.py 生成 · 最后更新 {updated}</footer>
</div>
</body>
</html>
"""

CARD = """    <li class="card">
      <a href="{href}">
        <div class="t">{title}</div>
        <div class="d">{subtitle}</div>
        <div class="meta">{badges}</div>
      </a>
    </li>"""


def topic_date(folder: str) -> date:
    """从文件夹名里取日期；取不到则退回很早的时间，排到最后。"""
    m = DATE_RE.search(folder)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            pass
    return date(1970, 1, 1)


def load_topics() -> list[dict]:
    topics = []
    for d in sorted(STUDY.iterdir()):
        sj = d / "study.json"
        page = d / "index.html"
        if not (d.is_dir() and sj.is_file() and page.is_file()):
            continue
        try:
            data = json.loads(sj.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            print(f"  ! 跳过 {d.name}：无法读取 study.json（{exc}）", file=sys.stderr)
            continue

        meta = data.get("meta") or {}
        stats = data.get("_stats") or {}
        topics.append(
            {
                "dir": d,
                "name": d.name,
                "page": page,
                "title": meta.get("title") or d.name,
                "subtitle": meta.get("subtitle") or "",
                "level": meta.get("level") or "",
                "href": "study/" + quote(d.name) + "/",
                "counts": {
                    "vocab": len(data.get("vocab") or []),
                    "phrases": len(data.get("phrases") or []),
                    "grammar": len(data.get("grammar") or []),
                    "patterns": len(data.get("patterns") or []),
                },
                "date": topic_date(d.name),
            }
        )
    topics.sort(key=lambda t: (t["date"], t["name"]), reverse=True)
    return topics


def render(topics: list[dict]) -> str:
    cards = []
    for t in topics:
        badges = [f'<span class="badge">{html.escape(t["date"].isoformat())}</span>']
        if t["level"]:
            badges.append(f'<span class="badge">{html.escape(t["level"])}</span>')
        c = t["counts"]
        badges.append(
            f'<span class="badge">词汇 {c["vocab"]}</span>'
            f'<span class="badge">短语 {c["phrases"]}</span>'
            f'<span class="badge">语法 {c["grammar"]}</span>'
            f'<span class="badge">句型 {c["patterns"]}</span>'
        )
        cards.append(
            CARD.format(
                href=html.escape(t["href"], quote=True),
                title=html.escape(t["title"]),
                subtitle=html.escape(t["subtitle"]),
                badges="".join(badges),
            )
        )
    return PAGE.format(
        count=len(topics),
        cards="\n".join(cards),
        updated=datetime.now().strftime("%Y-%m-%d %H:%M"),
    )


def fix_page_title(page: Path, title: str, check: bool) -> bool:
    """把主题页静态 <title> 换成真实标题，方便手机书签/主屏幕显示。"""
    want = f"<title>{html.escape(title)} · 英语学习</title>"
    src = page.read_text(encoding="utf-8")
    new, n = re.subn(r"<title>.*?</title>", lambda _: want, src, count=1, flags=re.S)
    if n == 0 or new == src:
        return False
    print(f"  · 标题更新：{page.parent.name} → {title}")
    if not check:
        page.write_text(new, encoding="utf-8")
    return True


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="只报告差异，不写文件")
    args = ap.parse_args()

    if not STUDY.is_dir():
        print(f"找不到目录：{STUDY}", file=sys.stderr)
        return 1

    topics = load_topics()
    if not topics:
        print("没有找到任何主题（study/*/study.json + index.html）。", file=sys.stderr)
        return 1

    print(f"发现 {len(topics)} 个主题：")
    for t in topics:
        print(f"  · {t['date']} {t['title']}  →  {t['href']}")
        fix_page_title(t["page"], t["title"], args.check)

    out = render(topics)
    if args.check:
        old = INDEX.read_text(encoding="utf-8") if INDEX.is_file() else ""
        print("\n首页需要更新。" if old != out else "\n首页已是最新。")
        return 0

    INDEX.write_text(out, encoding="utf-8")
    print(f"\n已写入 {INDEX.relative_to(ROOT)}（{len(out)} 字节）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
