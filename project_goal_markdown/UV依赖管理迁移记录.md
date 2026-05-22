# UV 依赖管理迁移记录

完成时间：2026-05-21

## 迁移目标

将后端依赖管理从 `pip install -r requirements.txt` 迁移到 `uv sync`，提升依赖安装速度、锁定解析结果，并让后续新增依赖统一使用 `uv add`。

## 完成内容

1. 新增 `pyproject.toml`
   - 作为新的 Python 依赖源文件。
   - 依赖版本从原 `requirements.txt` 迁移。
   - 设置 `requires-python = ">=3.11,<3.12"`。
   - 设置 `[tool.uv] package = false`，匹配当前 Django 应用型项目。

2. 新增 `uv.lock`
   - 固定当前依赖解析结果。
   - 后续新增依赖后应执行 `uv lock` 或直接使用 `uv add` 自动更新。

3. 更新 Docker 构建
   - `Dockerfile` 使用官方 Astral uv 镜像复制 `uv/uvx`。
   - 镜像构建阶段执行 `uv sync --frozen --no-dev`。
   - 容器虚拟环境固定为 `/opt/venv`，避免 `docker-compose` 挂载源码时覆盖容器环境。

4. 更新 docker-compose
   - `web` 启动命令改为 `uv run python manage.py migrate` 和 `uv run python manage.py runserver`。
   - `celery-worker` 启动命令改为 `uv run celery -A ai_evaluation worker -l info`。
   - 增加 `UV_PROJECT_ENVIRONMENT=/opt/venv`。
   - 增加 `UV_CACHE_DIR=/tmp/uv-cache`。

5. 更新 README
   - 本地依赖安装改为 `uv sync`。
   - 本地 Django 命令改为 `uv run python manage.py ...`。
   - 记录 `uv add`、`uv remove`、`uv lock`、`uv export` 的使用方式。

6. 保留 `requirements.txt`
   - 当前作为兼容清单保留。
   - 后续如需同步旧脚本，可执行：

```bash
uv export --format requirements-txt --no-hashes -o requirements.txt
```

## 涉及文件

- `pyproject.toml`
- `uv.lock`
- `Dockerfile`
- `docker-compose.yml`
- `.dockerignore`
- `README.md`
- `docs/superpowers/plans/2026-05-21-uv-migration.md`
- `project_goal_markdown/UV依赖管理迁移记录.md`

## 验证结果

- `uv --version` 通过：`uv 0.9.26`
- `uv lock` 通过，解析出 117 个包。
- `uv sync --frozen` 通过。
- `uv lock --check` 通过。
- `uv run python manage.py check` 在 sqlite 内存配置下通过。
- `uv run python -m compileall ...` 通过。
- `uv run python manage.py test rag_security trace_analysis redteam_engine mitigation model_evaluation --noinput` 通过，当前这些模块没有发现测试用例。
- `docker compose config` 通过。

## 注意事项

- Windows 默认 uv cache 目录曾出现访问拒绝，因此本地可设置：

```powershell
$env:UV_CACHE_DIR = ".uv-cache"
```

- `docker compose config` 仍提示 `C:\Users\Administrator\.docker\config.json` 访问拒绝，这是 Docker 客户端本地配置权限问题，不是 compose 文件语法问题。
- `uv run python manage.py test --noinput` 当前失败 2 个既有 OneAPI 实时连通性测试，原因是本地 `127.0.0.1:3000` OneAPI 服务不可连接；这不是 uv 迁移引入的问题。
- 后续新增 Python 依赖优先使用 `uv add 包名`，不要直接手改 `requirements.txt`。

## 依赖追加：ChromaDB Python SDK

完成时间：2026-05-21

- 使用 `uv add chromadb==0.5.23` 添加 ChromaDB Python SDK。
- 选择 `0.5.23` 是为了和 `docker-compose.yml` 中的 `chromadb/chroma:0.5.23` 服务端版本保持一致。
- `uv.lock` 已更新，依赖解析规模从 117 个包增加到 177 个包。
- `requirements.txt` 已通过 `uv export --format requirements-txt --no-hashes -o requirements.txt` 同步为兼容清单。

验证结果：

- `uv run python -c "import chromadb; print(chromadb.__version__)"` 输出 `0.5.23`。
- `uv lock --check` 通过。
- `uv run python manage.py check` 在 sqlite 内存配置下通过。
