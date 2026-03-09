#!/usr/bin/env python3
"""
飞书消息发送脚本
通过飞书开放平台 API 向个人用户发送消息。

凭证管理：通过环境变量或 .env 文件读取，不在命令行中传递敏感信息。

环境变量：
    FEISHU_APP_ID          飞书应用 App ID（必填）
    FEISHU_APP_SECRET      飞书应用 App Secret（必填）
    FEISHU_RECEIVE_ID_TYPE 默认接收者类型：open_id / user_id / email
    FEISHU_RECEIVE_ID      默认接收者 ID
    FEISHU_USE_LARK        设为 true 使用海外版 Lark API

用法：
    # 检查环境配置
    python3 send_message.py --check-env

    # 发送消息（凭证从环境变量读取）
    python3 send_message.py --msg-type text --content '{"text": "你好！"}'

    # 指定 .env 文件
    python3 send_message.py --env-file ~/.feishu.env --msg-type text --content '{"text": "你好！"}'

    # 覆盖默认接收者
    python3 send_message.py --receive-id-type open_id --receive-id ou_xxx --msg-type text --content '{"text": "你好！"}'
"""

import argparse
import json
import os
import sys
import urllib.request
import urllib.error

# ─── 飞书 API 地址 ───────────────────────────────────────────────────────────
FEISHU_BASE_URL = "https://open.feishu.cn/open-apis"
LARK_BASE_URL = "https://open.larksuite.com/open-apis"

# ─── 需要的环境变量 ──────────────────────────────────────────────────────────
REQUIRED_ENV = ["FEISHU_APP_ID", "FEISHU_APP_SECRET"]
OPTIONAL_ENV = ["FEISHU_RECEIVE_ID_TYPE", "FEISHU_RECEIVE_ID", "FEISHU_USE_LARK"]


# ─── .env 文件加载 ──────────────────────────────────────────────────────────
def load_env_file(env_file: str | None = None) -> dict[str, str]:
    """
    从 .env 文件加载环境变量。
    查找优先级：--env-file 参数 > 当前目录 .env > ~/.feishu.env
    只设置尚未存在的环境变量（已有的不会被覆盖）。
    """
    candidates = []
    if env_file:
        candidates.append(env_file)
    candidates.append(os.path.join(os.getcwd(), ".env"))
    # 脚本所在目录的父目录（即 feishu-messenger/），兼容沙盒环境
    script_dir = os.path.dirname(os.path.abspath(__file__))
    skill_root = os.path.dirname(script_dir)
    candidates.append(os.path.join(skill_root, ".feishu.env"))
    candidates.append(os.path.join(script_dir, ".feishu.env"))
    candidates.append(os.path.expanduser("~/.feishu.env"))

    loaded = {}
    for path in candidates:
        if os.path.isfile(path):
            print(f"[INFO] 读取配置文件: {path}")
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" not in line:
                        continue
                    key, _, value = line.partition("=")
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    if key and key not in os.environ:
                        os.environ[key] = value
                        loaded[key] = value
            break  # 只加载第一个找到的文件

    return loaded


# ─── 环境检查 ───────────────────────────────────────────────────────────────
def check_env() -> bool:
    """检查必要的环境变量是否已配置，并打印状态摘要。"""
    print("=" * 50)
    print("飞书消息 Skill — 环境配置检查")
    print("=" * 50)

    all_ok = True
    for var in REQUIRED_ENV:
        val = os.environ.get(var)
        if val:
            # 敏感值只显示前4位和后4位
            masked = val[:4] + "****" + val[-4:] if len(val) > 8 else "****"
            print(f"  ✅  {var} = {masked}")
        else:
            print(f"  ❌  {var} — 未设置（必填）")
            all_ok = False

    for var in OPTIONAL_ENV:
        val = os.environ.get(var)
        if val:
            print(f"  ✅  {var} = {val}")
        else:
            print(f"  ⬜  {var} — 未设置（可选）")

    print("=" * 50)
    if all_ok:
        print("✅ 核心配置就绪，可以发送消息。")
    else:
        print("❌ 缺少必填配置项，请创建 ~/.feishu.env 文件：")
        print()
        print("  cat > ~/.feishu.env << 'EOF'")
        print("  FEISHU_APP_ID=你的AppID")
        print("  FEISHU_APP_SECRET=你的AppSecret")
        print("  FEISHU_RECEIVE_ID_TYPE=open_id")
        print("  FEISHU_RECEIVE_ID=接收者的open_id")
        print("  EOF")
        print("  chmod 600 ~/.feishu.env")
    print()
    return all_ok


# ─── API 调用 ───────────────────────────────────────────────────────────────
def get_tenant_access_token(app_id: str, app_secret: str, base_url: str) -> str:
    """获取 tenant_access_token"""
    url = f"{base_url}/auth/v3/tenant_access_token/internal"
    payload = json.dumps({
        "app_id": app_id,
        "app_secret": app_secret,
    }).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"[ERROR] 获取 token 失败: HTTP {e.code} - {body}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"[ERROR] 网络连接失败: {e.reason}", file=sys.stderr)
        sys.exit(1)

    if data.get("code") != 0:
        print(f"[ERROR] 获取 token 失败: code={data.get('code')}, msg={data.get('msg')}", file=sys.stderr)
        sys.exit(1)

    token = data.get("tenant_access_token")
    print(f"[OK] 成功获取 tenant_access_token (有效期: {data.get('expire', '?')}s)")
    return token


def send_message(
    token: str,
    receive_id_type: str,
    receive_id: str,
    msg_type: str,
    content: str,
    base_url: str,
) -> dict:
    """发送消息给指定用户"""
    url = f"{base_url}/im/v1/messages?receive_id_type={receive_id_type}"

    # 规范化 content 为 JSON 字符串
    try:
        content_obj = json.loads(content)
        content_str = json.dumps(content_obj, ensure_ascii=False)
    except json.JSONDecodeError:
        if msg_type == "text":
            content_str = json.dumps({"text": content}, ensure_ascii=False)
        else:
            print(f"[ERROR] {msg_type} 类型的 content 必须是合法 JSON", file=sys.stderr)
            sys.exit(1)

    payload = json.dumps({
        "receive_id": receive_id,
        "msg_type": msg_type,
        "content": content_str,
    }).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "Authorization": f"Bearer {token}",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"[ERROR] 发送消息失败: HTTP {e.code} - {body}", file=sys.stderr)
        return {"code": e.code, "msg": body}
    except urllib.error.URLError as e:
        print(f"[ERROR] 网络连接失败: {e.reason}", file=sys.stderr)
        return {"code": -1, "msg": str(e.reason)}

    return data


# ─── 主函数 ─────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="飞书消息发送工具（凭证通过环境变量管理）")

    # 环境管理
    parser.add_argument("--env-file", help="指定 .env 文件路径")
    parser.add_argument("--check-env", action="store_true", help="检查环境配置是否完整")

    # 接收者（可选，覆盖环境变量中的默认值）
    parser.add_argument(
        "--receive-id-type",
        choices=["open_id", "user_id", "email"],
        help="接收者 ID 类型（默认读取 FEISHU_RECEIVE_ID_TYPE）",
    )
    parser.add_argument("--receive-id", help="单个接收者 ID（默认读取 FEISHU_RECEIVE_ID）")
    parser.add_argument("--receive-ids", help="多个接收者 ID，用逗号分隔（批量发送）")

    # 消息
    parser.add_argument(
        "--msg-type",
        default="text",
        choices=["text", "post", "interactive"],
        help="消息类型（默认: text）",
    )
    parser.add_argument("--content", help="消息内容（JSON 字符串）")

    args = parser.parse_args()

    # 加载 .env 文件
    load_env_file(args.env_file)

    # 仅检查环境
    if args.check_env:
        ok = check_env()
        sys.exit(0 if ok else 1)

    # 从环境变量读取凭证
    app_id = os.environ.get("FEISHU_APP_ID")
    app_secret = os.environ.get("FEISHU_APP_SECRET")

    if not app_id or not app_secret:
        print("[ERROR] 缺少必要的环境变量 FEISHU_APP_ID 和 FEISHU_APP_SECRET", file=sys.stderr)
        print("[HINT] 请创建 ~/.feishu.env 文件或运行 --check-env 查看详情", file=sys.stderr)
        sys.exit(1)

    # 确定接收者
    receive_id_type = args.receive_id_type or os.environ.get("FEISHU_RECEIVE_ID_TYPE")
    if not receive_id_type:
        print("[ERROR] 未指定接收者类型，请通过 --receive-id-type 或 FEISHU_RECEIVE_ID_TYPE 设置", file=sys.stderr)
        sys.exit(1)

    if args.receive_ids:
        receive_ids = [rid.strip() for rid in args.receive_ids.split(",") if rid.strip()]
    elif args.receive_id:
        receive_ids = [args.receive_id]
    elif os.environ.get("FEISHU_RECEIVE_ID"):
        receive_ids = [os.environ["FEISHU_RECEIVE_ID"]]
    else:
        print("[ERROR] 未指定接收者，请通过 --receive-id 或 FEISHU_RECEIVE_ID 设置", file=sys.stderr)
        sys.exit(1)

    if not args.content:
        print("[ERROR] 请通过 --content 指定消息内容", file=sys.stderr)
        sys.exit(1)

    # 确定 API 地址
    use_lark = os.environ.get("FEISHU_USE_LARK", "false").lower() == "true"
    base_url = LARK_BASE_URL if use_lark else FEISHU_BASE_URL

    # 获取 token
    print("[INFO] 正在获取 tenant_access_token...")
    token = get_tenant_access_token(app_id, app_secret, base_url)

    # 发送消息
    success_count = 0
    fail_count = 0

    for rid in receive_ids:
        print(f"\n[INFO] 正在向 {receive_id_type}={rid} 发送 {args.msg_type} 消息...")
        result = send_message(
            token=token,
            receive_id_type=receive_id_type,
            receive_id=rid,
            msg_type=args.msg_type,
            content=args.content,
            base_url=base_url,
        )

        code = result.get("code", -1)
        if code == 0:
            msg_id = result.get("data", {}).get("message_id", "unknown")
            print(f"[OK] 消息发送成功！message_id: {msg_id}")
            success_count += 1
        else:
            print(f"[FAIL] 发送失败: code={code}, msg={result.get('msg', 'unknown')}")
            fail_count += 1

    # 汇总
    print(f"\n{'=' * 40}")
    print(f"发送完成: 成功 {success_count}, 失败 {fail_count}, 共 {len(receive_ids)} 条")

    if fail_count > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
