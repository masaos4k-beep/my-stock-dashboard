#!/usr/bin/env python3
"""Scan article HTML files and generate articles.json for the homepage."""
from pathlib import Path
from html.parser import HTMLParser
import json
import re

ROOT = Path(__file__).resolve().parents[1]
ARTICLES_DIR = ROOT / "articles"
OUTPUT = ROOT / "articles.json"

class MetadataParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.title_parts = []
        self.in_title = False
        self.meta = {}
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag.lower() == "title":
            self.in_title = True
        if tag.lower() == "meta":
            name = (attrs.get("name") or "").lower()
            if name in {"article-date", "article-category", "description"}:
                self.meta[name] = attrs.get("content", "").strip()
    def handle_endtag(self, tag):
        if tag.lower() == "title":
            self.in_title = False
    def handle_data(self, data):
        if self.in_title:
            self.title_parts.append(data.strip())

def main():
    records = []
    for path in sorted(ARTICLES_DIR.glob("*.html")):
        text = path.read_text(encoding="utf-8")
        parser = MetadataParser()
        parser.feed(text)
        title = " ".join(x for x in parser.title_parts if x).strip()
        title = re.sub(r"\s*[｜|]\s*Beyond the Headlines\s*$", "", title, flags=re.I).strip()
        date = parser.meta.get("article-date", "")
        category = parser.meta.get("article-category", "記事")
        description = parser.meta.get("description", "")
        if not title:
            print(f"SKIP: {path.name} has no <title>")
            continue
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
            print(f"SKIP: {path.name} needs <meta name=\"article-date\" content=\"YYYY-MM-DD\">")
            continue
        records.append({
            "title": title,
            "date": date,
            "category": category,
            "description": description,
            "url": f"articles/{path.name}"
        })
    records.sort(key=lambda x: x["date"], reverse=True)
    OUTPUT.write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Generated {OUTPUT.relative_to(ROOT)}: {len(records)} article(s)")

if __name__ == "__main__":
    main()
