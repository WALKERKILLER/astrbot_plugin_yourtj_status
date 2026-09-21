# YourTJ Status AstrBot Plugin

发送 `/监控`，实时获取 YourTJ 社区状态并生成状态海报。

## 功能

- 请求 `https://status.yourtj.de/api/status` 获取实时状态。
- 通过 AstrBot HTML + Jinja2 文转图能力生成 JPEG 海报。
- 沿用 `astrbot_plugin_picstatus` 的 loliapi 背景图方式。
- loliapi 失败时按配置回退到内置背景图。
- 海报保留 YourTJ Status 原页面的结构、样式、文案和 logo 资源。

## 安装

将整个 `astrbot_plugin_yourtj_status` 目录放入 AstrBot 的 `data/plugins`，然后在 AstrBot 插件管理中加载或重载插件。

依赖写在 `requirements.txt`。插件使用 AstrBot 已提供的 HTML 文转图服务，不需要额外安装 Node.js 或浏览器。

## 配置

配置文件由 AstrBot 根据 `_conf_schema.json` 生成，支持：

- `api_url`：状态 API 地址。
- `request_timeout`：状态 API 请求超时秒数。
- `background.bg_provider`：`loli`、`local` 或 `none`。
- `background.bg_fallback_chain`：背景失败后的回退顺序。
- `background.bg_local_path`：本地背景文件或目录。
- `background.bg_req_timeout`：背景请求超时秒数。
- `background.bg_proxy`：背景请求代理。

## 目录说明

```text
astrbot_plugin_yourtj_status/
├── main.py                 # /监控 指令与状态请求
├── background.py           # 背景图获取与回退
├── poster_renderer.py      # 原 status 页面模板与海报渲染
├── templates/poster.html.j2
├── status_source/apps/status/ # 从 YourTJ-Hub origin/dev 原样保留的 status 源码
├── default_bg.webp          # 内置背景图
├── metadata.yaml
├── _conf_schema.json
└── requirements.txt
```

## 开源说明

海报中的 status 页面源码、中文文案和 logo 资源来自 [YourTJ-Hub](https://github.com/YourTongji/YourTJ-Hub)，其版权和许可证以源仓库为准。
