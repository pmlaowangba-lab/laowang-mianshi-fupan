#!/usr/bin/env python3
"""Initialize fupan-deck + Feishu wiki doc for laowang-mianshi-fupan."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

import yaml

API_BASE = "https://open.feishu.cn/open-apis"
SKILL_DIR = Path(__file__).resolve().parent.parent
DEFAULT_OBSIDIAN_WX = (
    SKILL_DIR.parents[3] / ".obsidian" / "plugins" / "obsidian-wx" / "data.json"
)


def resolve_app_secret(workspace: Path | None, obsidian_secret: str) -> str:
    if obsidian_secret and obsidian_secret != "obsidian-wx:secret-storage:v1":
        return obsidian_secret
    env_secret = os.environ.get("FEISHU_APP_SECRET", "").strip()
    if env_secret:
        return env_secret
    if workspace:
        for name in ("feishu-app.secret", ".feishu-app-secret"):
            path = workspace / name
            if path.is_file():
                text = path.read_text(encoding="utf-8").strip()
                if text:
                    return text
    return ""


def load_obsidian_feishu(obsidian_path: Path, workspace: Path | None = None) -> dict:
    raw = json.loads(obsidian_path.read_text(encoding="utf-8")) if obsidian_path.is_file() else {}
    kbs = raw.get("feishuKnowledgeBases") or []
    kb = kbs[0] if kbs else {}
    return {
        "app_id": os.environ.get("FEISHU_APP_ID", str(raw.get("feishuAppId", ""))).strip(),
        "app_secret": resolve_app_secret(workspace, str(raw.get("feishuAppSecret", "")).strip()),
        "space_id": os.environ.get("FEISHU_SPACE_ID", str(kb.get("spaceId", ""))).strip(),
        "parent_node_token": os.environ.get("FEISHU_PARENT_NODE_TOKEN", str(kb.get("parentNodeToken", ""))).strip(),
        "kb_name": str(kb.get("name", "")),
    }


def tenant_token(app_id: str, app_secret: str) -> str:
    body = json.dumps({"app_id": app_id, "app_secret": app_secret}).encode()
    req = urllib.request.Request(
        f"{API_BASE}/auth/v3/tenant_access_token/internal",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = json.loads(resp.read().decode())
    if raw.get("code") != 0:
        raise RuntimeError(raw.get("msg"))
    return raw["tenant_access_token"]


def feishu_json(
    token: str, method: str, path: str, payload: dict | None = None
) -> dict:
    url = f"{API_BASE}{path}"
    data = None
    headers = {"Authorization": f"Bearer {token}"}
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode()
        headers["Content-Type"] = "application/json; charset=utf-8"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=60) as resp:
        raw = json.loads(resp.read().decode())
    if raw.get("code") != 0:
        raise RuntimeError(f"{path}: {raw.get('msg')} ({raw})")
    return raw.get("data") or {}


def create_wiki_doc(
    token: str, space_id: str, parent_node_token: str, title: str
) -> tuple[str, str]:
    body: dict = {"obj_type": "docx", "node_type": "origin", "title": title}
    if parent_node_token:
        body["parent_node_token"] = parent_node_token
    data = feishu_json(
        token,
        "POST",
        f"/wiki/v2/spaces/{space_id}/nodes",
        body,
    )
    node = data.get("node") or {}
    document_id = node.get("obj_token")
    node_token = node.get("node_token")
    if not document_id or not node_token:
        raise RuntimeError("创建飞书文档失败：缺少 obj_token / node_token")
    return document_id, node_token


def strip_html_comments(markdown: str) -> str:
    return re.sub(r"<!--.*?-->", "", markdown, flags=re.S)


def build_feishu_summary(season: str) -> str:
    return build_seed_deck(season)


def insert_markdown(token: str, document_id: str, markdown: str, index: int = 0) -> None:
    markdown = strip_html_comments(markdown)
    converted = feishu_json(
        token,
        "POST",
        "/docx/v1/documents/blocks/convert",
        {"content_type": "markdown", "content": markdown},
    )
    children = converted.get("first_level_block_ids") or []
    blocks = converted.get("blocks") or []
    if not children or not blocks:
        return
    feishu_json(
        token,
        "POST",
        f"/docx/v1/documents/{document_id}/blocks/{document_id}/descendant?document_revision_id=-1",
        {
            "index": index,
            "children_id": children,
            "descendants": blocks,
        },
    )


def list_child_block_ids(token: str, document_id: str) -> list[str]:
    data = feishu_json(
        token,
        "GET",
        f"/docx/v1/documents/{document_id}/blocks/{document_id}/children?page_size=500",
    )
    return [item["block_id"] for item in (data.get("items") or []) if item.get("block_id")]


def clear_document_body(token: str, document_id: str) -> None:
    """Delete all top-level blocks (Feishu uses index range DELETE, not block_ids)."""
    while True:
        count = len(list_child_block_ids(token, document_id))
        if count == 0:
            return
        feishu_json(
            token,
            "DELETE",
            f"/docx/v1/documents/{document_id}/blocks/{document_id}/children/batch_delete"
            "?document_revision_id=-1",
            {"start_index": 0, "end_index": count},
        )


def markdown_tables_to_lists(text: str) -> str:
    lines = text.splitlines()
    out: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if (
            stripped.startswith("|")
            and i + 1 < len(lines)
            and re.match(r"^\|\s*[-: ]+\|", lines[i + 1].strip())
        ):
            header = [c.strip() for c in stripped.strip("|").split("|")]
            i += 2
            while i < len(lines) and lines[i].strip().startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if len(cells) == len(header):
                    parts = [
                        f"{header[j]}：{cells[j]}"
                        for j in range(len(header))
                        if cells[j] and header[j] not in ("---", "")
                    ]
                    if parts:
                        out.append("- " + " · ".join(parts))
                i += 1
            continue
        out.append(line)
        i += 1
    return "\n".join(out)


def deck_to_feishu_markdown(deck_path: Path, season: str) -> str:
    if not deck_path.is_file():
        return build_feishu_summary(season)
    body = strip_html_comments(deck_path.read_text(encoding="utf-8"))
    body = markdown_tables_to_lists(body)
    banner = f"\n\n> 飞书镜像 · 同步于 {date.today()} · 源文件 fupan-deck.md\n"
    if "飞书镜像" not in body:
        body = body.replace("\n\n## 避坑错题库", banner + "\n## 避坑错题库", 1)
    return body


def set_link_share_edit(
    token: str, document_id: str, node_token: str = ""
) -> dict[str, str]:
    """Set tenant link share to editable on docx token and wiki node (best-effort)."""
    public_body = {"link_share_entity": "tenant_editable"}
    status: dict[str, str] = {}
    for kind, file_token in (("docx", document_id), ("wiki", node_token)):
        if not file_token:
            continue
        try:
            feishu_json(
                token,
                "PATCH",
                f"/drive/v1/permissions/{file_token}/public?type={kind}",
                public_body,
            )
            status[kind] = "ok"
        except (RuntimeError, urllib.error.HTTPError) as exc:
            status[kind] = str(exc)
    return status


def build_seed_deck(season: str) -> str:
    template = SKILL_DIR / "assets" / "fupan-deck-template.md"
    return template.read_text(encoding="utf-8").replace("2027-fall", season)


def cmd_sync_feishu(args: argparse.Namespace) -> int:
    workspace = (args.workspace or SKILL_DIR / "workspace" / args.season).resolve()
    config_path = workspace / "feishu-fupan-config.yaml"
    if not config_path.is_file():
        print("ERROR: 先执行 fupan-init", file=sys.stderr)
        return 1
    config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    document_id = config.get("document_id")
    if not document_id:
        print("ERROR: feishu-fupan-config 缺少 document_id", file=sys.stderr)
        return 1

    obsidian_path = args.obsidian_wx.expanduser().resolve()
    fx = load_obsidian_feishu(obsidian_path, workspace)
    if not fx["app_secret"]:
        print(
            "ERROR: 需要 FEISHU_APP_SECRET 或 workspace/feishu-app.secret（一行密钥，勿提交 Git）",
            file=sys.stderr,
        )
        return 1

    token = tenant_token(fx["app_id"], fx["app_secret"])
    deck_path = workspace / config.get("local_deck", "fupan-deck.md")
    body = deck_to_feishu_markdown(deck_path, args.season)
    clear_document_body(token, document_id)
    insert_markdown(token, document_id, body, index=0)
    perm = set_link_share_edit(token, document_id, str(config.get("node_token", "")))
    child_count = len(list_child_block_ids(token, document_id))

    config["last_synced_at"] = str(date.today())
    config_path.write_text(yaml.dump(config, allow_unicode=True, sort_keys=False), encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "wiki_url": config.get("wiki_url"),
                "document_id": document_id,
                "top_level_blocks": child_count,
                "permissions": perm,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def add_workspace_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--season", default="2027-fall")
    parser.add_argument("--workspace", type=Path, default=None)
    parser.add_argument("--obsidian-wx", type=Path, default=DEFAULT_OBSIDIAN_WX)
    parser.add_argument("--title", default="")
    parser.add_argument("--local-only", action="store_true", help="Initialize local deck without Feishu")


def main() -> int:
    parser = argparse.ArgumentParser()
    add_workspace_args(parser)
    sub = parser.add_subparsers(dest="command")

    add_workspace_args(sub.add_parser("init", help="Create local deck + new Feishu wiki doc"))
    p_sync = sub.add_parser("sync-feishu", help="Rewrite Feishu doc from current fupan state")
    add_workspace_args(p_sync)
    p_sync.set_defaults(func=cmd_sync_feishu)

    args = parser.parse_args()
    if args.command == "sync-feishu":
        return cmd_sync_feishu(args)
    if args.command not in (None, "init"):
        print(f"Unknown command: {args.command}", file=sys.stderr)
        return 1

    workspace = (args.workspace or SKILL_DIR / "workspace" / args.season).resolve()
    workspace.mkdir(parents=True, exist_ok=True)

    obsidian_path = args.obsidian_wx.expanduser().resolve()
    if args.local_only:
        deck_path = workspace / "fupan-deck.md"
        if not deck_path.exists():
            deck_path.write_text(build_seed_deck(args.season), encoding="utf-8")
        print(json.dumps({"ok": True, "local_only": True, "deck": str(deck_path)}, ensure_ascii=False))
        return 0

    fx = load_obsidian_feishu(obsidian_path, workspace)
    if not fx["app_id"] or not fx["app_secret"]:
        print("ERROR: 缺少 feishuAppId 或 FEISHU_APP_SECRET", file=sys.stderr)
        return 1
    if not fx["space_id"]:
        print("ERROR: obsidian-wx 未配置 feishuKnowledgeBases", file=sys.stderr)
        return 1

    title = args.title or f"秋招面试复盘总册-{args.season}"
    deck_md = build_seed_deck(args.season)
    (workspace / "fupan-deck.md").write_text(deck_md, encoding="utf-8")

    token = tenant_token(fx["app_id"], fx["app_secret"])
    document_id, node_token = create_wiki_doc(
        token, fx["space_id"], fx["parent_node_token"], title
    )
    feishu_body = build_feishu_summary(args.season)
    try:
        insert_markdown(token, document_id, feishu_body)
    except (RuntimeError, urllib.error.HTTPError) as exc:
        print(f"WARN: 飞书正文灌入失败（已创建空文档）: {exc}", file=sys.stderr)
    set_link_share_edit(token, document_id, node_token)

    wiki_url = f"https://feishu.cn/wiki/{node_token}"
    config = {
        "season": args.season,
        "title": title,
        "document_id": document_id,
        "node_token": node_token,
        "wiki_url": wiki_url,
        "space_id": fx["space_id"],
        "parent_node_token": fx["parent_node_token"],
        "obsidian_wx_data_path": os.path.relpath(obsidian_path, workspace),
        "local_deck": "fupan-deck.md",
        "initialized_at": str(date.today()),
    }
    (workspace / "feishu-fupan-config.yaml").write_text(
        yaml.dump(config, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )

    print(
        json.dumps(
            {
                "ok": True,
                "local_deck": str(workspace / "fupan-deck.md"),
                "wiki_url": wiki_url,
                "document_id": document_id,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
