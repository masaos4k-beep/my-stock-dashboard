#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成済み market_post.txt をBufferのXチャンネルの予約投稿キューへ追加する。"""

import json
import os
import re
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
POST_FILE = ROOT / "market_post.txt"

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
      post {
        id
        text
        dueAt
      }
    }
    ... on MutationError {
      message
    }
  }
}
"""


def main() -> None:
    token = os.environ.get("BUFFER_ACCESS_TOKEN", "").strip()
    if not token:
        raise RuntimeError("環境変数 BUFFER_ACCESS_TOKEN が設定されていません。")

    if not POST_FILE.exists():
        raise FileNotFoundError(f"投稿文ファイルがありません: {POST_FILE}")

    text = POST_FILE.read_text(encoding="utf-8").strip()
    if not text:
        raise ValueError("market_post.txt が空です。")

    # Xの加重文字数を保守的に概算し、上限280より余裕を持って送信を止める。
    url_pattern = re.compile(r"https?://\S+")
    weighted = 0
    last = 0
    for match in url_pattern.finditer(text):
        weighted += sum(2 if ord(ch) > 0x10FF else 1 for ch in text[last:match.start()])
        weighted += 23
        last = match.end()
    weighted += sum(2 if ord(ch) > 0x10FF else 1 for ch in text[last:])
    if weighted > 270:
        raise ValueError(
            f"X加重文字数の概算が270を超えています（{weighted}）。Bufferへ送信しません。"
        )

    payload = {
        "query": MUTATION,
        "variables": {
            "text": text,
        },
    }

    response = requests.post(
        BUFFER_API_URL,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=30,
    )

    if response.status_code != 200:
        raise RuntimeError(
            f"Buffer API HTTPエラー: {response.status_code} / {response.text[:500]}"
        )

    try:
        result = response.json()
    except json.JSONDecodeError as exc:
        raise RuntimeError("Buffer APIからJSON以外の応答が返りました。") from exc

    if result.get("errors"):
        messages = [
            error.get("message", "GraphQL error")
            for error in result["errors"]
        ]
        raise RuntimeError("Buffer API GraphQLエラー: " + " | ".join(messages))

    action = (result.get("data") or {}).get("createPost") or {}
    if action.get("message"):
        raise RuntimeError("Buffer投稿エラー: " + str(action["message"]))

    post = action.get("post")
    if not post:
        raise RuntimeError(
            "Buffer APIの応答に投稿情報がありません: "
            + json.dumps(result, ensure_ascii=False)[:1000]
        )

    print("Bufferへのキュー追加に成功しました。")
    print(f'Post ID: {post.get("id", "(不明)")}')
    print(f'Due At (UTC): {post.get("dueAt", "(未設定)")}')
    print("投稿文:")
    print(post.get("text", text))
    print(
        "注意: Bufferチャンネルのキューが稼働中の場合、"
        "設定された次の公開時刻にXへ自動公開されます。"
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
