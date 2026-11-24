#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Buffer送信 v5: 取引日単位の重複防止を追加。"""

import json
import os
import re
import sys
from datetime import date
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
POST_FILE = ROOT / "market_post.txt"
POSTED_DATE_FILE = ROOT / "data" / "last_posted_trading_day.txt"

BUFFER_API_URL = "https://api.buffer.com"
BUFFER_CHANNEL_ID = "6af4899362b70b94b0f6a450"

MUTATION = """
mutation CreateMarketPost($text: String!) {
  createPost(input: {
    text: $text,
    channelId: "6af4899362b70b94b0f6a450",
    schedulingType: automatic,
    mode: addToQueue
  }) {
    ... on PostActionSuccess {
      post { id text dueAt }
    }
    ... on MutationError {
      message
    }
  }
}
"""


def get_trading_date() -> date:
    raw = os.environ.get("LATEST_TRADING_DATE", "").strip()
    if not raw:
        raise RuntimeError(
            "LATEST_TRADING_DATE がありません。Workflowから最新取引日を渡してください。"
        )
    try:
        return date.fromisoformat(raw)
    except ValueError as exc:
        raise RuntimeError(f"LATEST_TRADING_DATEの形式が不正です: {raw}") from exc


def check_duplicate(trading_date: date) -> None:
    if not POSTED_DATE_FILE.exists():
        print("投稿済み取引日ファイルがありません。初回投稿として扱います。")
        return

    raw = POSTED_DATE_FILE.read_text(encoding="utf-8").strip()
    if not raw:
        raise RuntimeError("投稿済み取引日ファイルが空です。安全のため送信を停止します。")

    try:
        last_posted = date.fromisoformat(raw)
    except ValueError as exc:
        raise RuntimeError(f"投稿済み取引日の形式が不正です: {raw}") from exc

    print(f"今回の取引日: {trading_date}")
    print(f"前回投稿済み取引日: {last_posted}")
    if trading_date <= last_posted:
        print("同じ取引日以前の投稿は登録済みです。Buffer登録をスキップします。")
        raise SystemExit(0)


def validate_post_text(text: str) -> None:
    if not text:
        raise ValueError("market_post.txt が空です。")

    url_pattern = re.compile(r"https?://\S+")
    weighted = 0
    last = 0
    for match in url_pattern.finditer(text):
        weighted += sum(2 if ord(ch) > 0x10FF else 1 for ch in text[last:match.start()])
        weighted += 23
        last = match.end()
    weighted += sum(2 if ord(ch) > 0x10FF else 1 for ch in text[last:])
    if weighted > 270:
        raise ValueError(f"X加重文字数の概算が270を超えています（{weighted}）。Bufferへ送信しません。")


def main() -> None:
    token = os.environ.get("BUFFER_ACCESS_TOKEN", "").strip()
    if not token:
        raise RuntimeError("環境変数 BUFFER_ACCESS_TOKEN が設定されていません。")

    trading_date = get_trading_date()
    check_duplicate(trading_date)

    if not POST_FILE.exists():
        raise FileNotFoundError(f"投稿文ファイルがありません: {POST_FILE}")

    text = POST_FILE.read_text(encoding="utf-8").strip()
    validate_post_text(text)

    payload = {"query": MUTATION, "variables": {"text": text}}

    # 結果不明時は自動再送信しない。Buffer側のキュー確認が必要。
    try:
        response = requests.post(
            BUFFER_API_URL,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=30,
        )
    except requests.RequestException as exc:
        raise RuntimeError(
            "Bufferへの通信結果が不明です。自動再送信しません。Bufferのキューを確認してください。"
        ) from exc

    if response.status_code != 200:
        raise RuntimeError(
            f"Buffer API HTTPエラー: {response.status_code} / {response.text[:500]}。"
            "Buffer側で登録有無を確認してください。"
        )

    try:
        result = response.json()
    except json.JSONDecodeError as exc:
        raise RuntimeError("Buffer API応答がJSONではありません。Buffer側を確認してください。") from exc

    if result.get("errors"):
        messages = [e.get("message", "GraphQL error") for e in result["errors"]]
        raise RuntimeError("Buffer API GraphQLエラー: " + " | ".join(messages))

    action = (result.get("data") or {}).get("createPost") or {}
    if action.get("message"):
        raise RuntimeError("Buffer投稿エラー: " + str(action["message"]))

    post = action.get("post")
    if not post or not post.get("id"):
        raise RuntimeError(
            "Buffer APIの応答に投稿IDがありません。Buffer側で登録有無を確認してください: "
            + json.dumps(result, ensure_ascii=False)[:1000]
        )

    # Buffer成功応答を確認した後にだけローカル記録を更新。
    POSTED_DATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    POSTED_DATE_FILE.write_text(trading_date.isoformat() + "\n", encoding="utf-8")

    print("Bufferへのキュー追加に成功しました。")
    print(f"取引日: {trading_date.isoformat()}")
    print(f'Post ID: {post.get("id")}')
    print(f'Due At (UTC): {post.get("dueAt", "(未設定)")}')
    print("投稿文:")
    print(post.get("text", text))


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
