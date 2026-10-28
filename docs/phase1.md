# Phase 1 学习与验收

本阶段建立可以重复执行的开发环境，不实现战斗逻辑或后续数据库表。

- `.venv`：隔离项目依赖，复用已安装的 Python，不安装另一套 Python。
- `pyproject.toml`：声明包结构、Python 要求、运行与测试依赖。
- `pip install -e`：以可编辑方式安装源码，修改 `src/` 后无需重复安装。
- `python-dotenv`：从本地 `.env` 加载配置；已有环境变量优先。
- `psycopg`：Python 的 PostgreSQL 驱动。当前只使用直接连接和只读 SQL；SQLAlchemy 尚未引入。
- `pytest`：独立验证版本、配置优先级、敏感字段隐藏及参数边界。离线测试通过不代表数据库连接成功。
- Git：记录可追踪文件；`.gitignore` 阻止本地凭据、虚拟环境和临时产物被常规添加。

环境检查使用 `SELECT` 查询。查询数据库存在性时使用 `%s` 参数绑定，避免把输入直接拼接到 SQL。项目不会自动创建或清空数据库。

数据库配置完成后，从项目根目录运行：

```powershell
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m tft_simulator.environment
```

验收要求最后一个命令显示连接到目标库，并返回 0。如果缺少密码，请在 VS Code 中本地编辑 `.env`，无需将密码发送给任何人。

建议提交信息：`chore: initialize project environment and read-only database checks`

Phase 2 需用户确认后开始：调研真实来源、固定 Set/Patch、整理字段与可信度。当前无战斗引擎、英雄数据或分析结果。
