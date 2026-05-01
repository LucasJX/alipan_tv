# 阿里云盘 TV Token 获取工具

通过模拟 TV 客户端 OAuth 授权流程，获取阿里云盘 TV 端的 `access_token` 和 `refresh_token`。

基于 [i-tools](https://github.com/iLay1678/i-tools) 项目中的阿里云盘 TV Token 功能独立剥离重写。

## 功能

- 一键扫码获取阿里云盘 TV 端授权令牌
- 提供 OAuth 刷新接口，供 alist、播放器等第三方程序调用
- 纯本地运行，数据不经第三方服务器

## 快速部署（Docker，推荐）

无需安装 Python，一行命令启动：

```bash
docker compose up -d
```

启动后浏览器打开 http://localhost:5800

### 自定义端口

修改 `docker-compose.yml` 中的端口映射：

```yaml
ports:
  - "8080:5800"   # 改成你想要的端口
```

### 停止 / 更新

```bash
docker compose down      # 停止
docker compose pull && docker compose up -d   # 更新到最新版
```

## 源码部署

### 环境要求

- Python 3.10+
- [uv](https://docs.astral.sh/uv/)（推荐）或 pip

### 方式一：uv（推荐）

```bash
git clone git@github.com:LucasJX/alipan_tv.git
cd alipan_tv
uv sync
uv run app.py
```

### 方式二：pip

```bash
git clone git@github.com:LucasJX/alipan_tv.git
cd alipan_tv
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
.venv/bin/python app.py
```

启动后浏览器打开 http://localhost:5800

可通过环境变量 `PORT` 自定义端口：

```bash
PORT=8080 uv run app.py
```

## 第三方程序接入

其他程序（alist、影视仓等）可通过以下接口刷新 Token：

### GET 请求

```
GET http://<你的IP>:5800/api/oauth/alipan/token?refresh_ui=<refresh_token>
```

### POST 请求

```
POST http://<你的IP>:5800/api/oauth/alipan/token
Content-Type: application/json

{"refresh_token": "<refresh_token>"}
```

### 返回格式

```json
{
  "token_type": "Bearer",
  "access_token": "...",
  "refresh_token": "...",
  "expires_in": 7200
}
```

## 技术栈

- [Flask](https://flask.palletsprojects.com/) — Web 框架
- [PyCryptodome](https://pycryptodome.readthedocs.io/) — AES 解密
- [qrcode](https://pypi.org/project/qrcode/) — 二维码生成

## 项目结构

```
alipan-tv-token/
├── app.py              # Flask 后端（API 路由 + AES 解密）
├── index.html          # 前端页面
├── Dockerfile          # Docker 镜像定义
├── docker-compose.yml  # Docker Compose 编排
├── requirements.txt    # Python 依赖
├── pyproject.toml      # 项目配置
└── README.md
```

## 致谢

- [i-tools](https://github.com/iLay1678/i-tools) — 原始项目
