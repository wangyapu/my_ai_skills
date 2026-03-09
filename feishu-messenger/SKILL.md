---
name: feishu-messenger
description: 通过飞书开放平台 API 发送消息给个人用户。当用户提到"发送飞书消息"时，必须使用此 skill。支持发送文本、富文本（post）和交互式卡片消息。即使用户只是说"帮我发个飞书消息"或"通知一下XX"，也应主动触发此 skill。
---

# 飞书消息发送 Skill

通过飞书开放平台 API 向个人用户发送消息，支持文本、富文本和卡片消息。

## 前置条件

用户需要在飞书开放平台（https://open.feishu.cn）创建一个应用，并获取以下信息：

1. **App ID** 和 **App Secret**（应用凭证页面获取）
2. **接收者标识**（以下任一）：
   - `open_id`：用户的 Open ID（推荐，应用范围内唯一）
   - `user_id`：用户的 User ID
   - `email`：用户的邮箱
3. 应用需要开通 **消息** 相关权限（`im:message:send_as_bot`）

## 凭证管理

敏感信息（App ID、App Secret、接收者 ID 等）通过 **环境变量** 管理，**绝不要在命令行参数或聊天中直接传递**。

### 方式一：`.env` 文件（推荐）

在用户的项目目录或 home 目录下创建 `.env` 文件：

```bash
# ~/.feishu.env
FEISHU_APP_ID=cli_xxxxxxxxxxxxxxxx
FEISHU_APP_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
FEISHU_RECEIVE_ID_TYPE=open_id
FEISHU_RECEIVE_ID=ou_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
FEISHU_USE_LARK=false
```

安全事项：
- 确保 `.env` 文件权限为 `600`（`chmod 600 ~/.feishu.env`），仅当前用户可读
- 如果在 Git 项目中使用，务必将 `.env` 加入 `.gitignore`
- 不要将 `.env` 文件提交到版本控制

脚本会按以下优先级查找 `.env` 文件：
1. `--env-file` 参数指定的路径
2. 当前目录下的 `.env`
3. skill 根目录下的 `.feishu.env`（即 `feishu-messenger/.feishu.env`，兼容沙盒环境）
4. 脚本目录下的 `.feishu.env`（即 `feishu-messenger/scripts/.feishu.env`）
5. `~/.feishu.env`

### 方式二：直接导出环境变量

```bash
export FEISHU_APP_ID="cli_xxxxxxxxxxxxxxxx"
export FEISHU_APP_SECRET="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
export FEISHU_RECEIVE_ID_TYPE="open_id"
export FEISHU_RECEIVE_ID="ou_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
```

### 使用 Skill 时的交互规范

当用户要求发送飞书消息时：

1. **先检查环境变量是否已配置**：运行 `scripts/send_message.py --check-env` 检测
2. **如果未配置**：引导用户创建 `.env` 文件，告诉用户需要填入哪些值，但不要让用户把密钥贴到聊天中
3. **如果已配置**：只需从用户处获取消息内容，然后执行发送

关键原则：**永远不要在聊天中向用户索要 App Secret 等敏感信息。** 引导用户将其写入 `.env` 文件。

## 使用方法

### 第 1 步：确认环境配置

```bash
python3 scripts/send_message.py --check-env
```

如果输出显示缺少配置项，引导用户创建 `.env` 文件。

### 第 2 步：执行发送脚本

凭证从环境变量读取，命令行只传消息内容：

```bash
# 发送文本消息（使用环境变量中的默认接收者）
python3 scripts/send_message.py \
  --msg-type "text" \
  --content '{"text": "你好，这是一条测试消息"}'

# 发送给指定接收者（覆盖环境变量中的默认值）
python3 scripts/send_message.py \
  --receive-id-type "open_id" \
  --receive-id "ou_xxxxx" \
  --msg-type "text" \
  --content '{"text": "你好！"}'

# 指定 .env 文件路径
python3 scripts/send_message.py \
  --env-file ~/projects/my-bot/.env \
  --msg-type "text" \
  --content '{"text": "你好！"}'
```

### 支持的消息类型

#### 1. 纯文本消息（text）

```bash
--msg-type "text" \
--content '{"text": "Hello, 这是一条纯文本消息！"}'
```

#### 2. 富文本消息（post）

```bash
--msg-type "post" \
--content '{
  "zh_cn": {
    "title": "项目更新通知",
    "content": [
      [
        {"tag": "text", "text": "项目进度："},
        {"tag": "a", "text": "查看详情", "href": "https://example.com"},
        {"tag": "text", "text": "\n已完成 80% 的开发任务。"}
      ]
    ]
  }
}'
```

#### 3. 交互式卡片消息（interactive）

```bash
--msg-type "interactive" \
--content '{
  "header": {
    "title": {"content": "任务提醒", "tag": "plain_text"}
  },
  "elements": [
    {"tag": "div", "text": {"content": "你有一个待处理的任务", "tag": "lark_md"}},
    {"tag": "action", "actions": [
      {"tag": "button", "text": {"content": "查看任务", "tag": "plain_text"}, "type": "primary", "url": "https://example.com"}
    ]}
  ]
}'
```

## 环境变量参考

| 变量名 | 必填 | 说明 |
|--------|------|------|
| `FEISHU_APP_ID` | 是 | 飞书应用 App ID |
| `FEISHU_APP_SECRET` | 是 | 飞书应用 App Secret |
| `FEISHU_RECEIVE_ID_TYPE` | 否 | 默认接收者类型（open_id / user_id / email） |
| `FEISHU_RECEIVE_ID` | 否 | 默认接收者 ID |
| `FEISHU_USE_LARK` | 否 | 设为 `true` 使用海外版 Lark API |

## 错误排查

| 错误码 | 含义 | 解决方法 |
|--------|------|----------|
| 99991663 | 找不到接收者 | 检查 receive_id 和 receive_id_type 是否正确 |
| 99991668 | 无权限发送 | 确认应用已开通 im:message:send_as_bot 权限 |
| 99991672 | 机器人未启用 | 在飞书开放平台启用机器人能力 |
| 10003 | App ID/Secret 错误 | 检查 .env 中的应用凭证是否正确 |
