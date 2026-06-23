# 测试指南

## 快速开始

```bash
# 安装依赖（包含 pytest-cov）
pip install -r requirements.txt

# 运行所有单元测试（带覆盖率）
pytest tests/ -m "unit"

# 跳过覆盖率检查（开发调试时）
pytest tests/ -m "unit" --no-cov

# 运行特定测试文件
pytest tests/test_crypto.py -v
```

## 覆盖率要求

- **最低覆盖率**: 70%（由 `pytest.ini` 中的 `--cov-fail-under=70` 强制）
- **覆盖范围**: `app/` 目录（排除 `tests/`、`alembic/`、`__init__.py`）
- **报告格式**: 
  - 终端输出（`term-missing`）：显示未覆盖的行号
  - XML 报告（`coverage.xml`）：CI 上传到 Codecov

## 测试分类（Markers）

| Marker | 说明 | 运行命令 |
|--------|------|----------|
| `unit` | 单元测试（不依赖外部服务） | `pytest -m "unit"` |
| `integration` | 集成测试（需要真实 DB/Redis） | `pytest -m "integration"` |
| `smoke` | 烟雾测试（快速导入检查） | `pytest -m "smoke"` |
| `slow` | 慢速测试 | `pytest -m "not slow"` 跳过慢测试 |

## CI 行为

GitHub Actions 在每次 push/PR 时：
1. 运行所有标记为 `unit` 的测试
2. 收集覆盖率，生成 `coverage.xml`
3. 检查覆盖率是否 ≥ 70%，低于此阈值 CI 失败
4. 上传覆盖率报告到 Codecov（可选，失败不阻塞）

## 提升覆盖率建议

1. **优先覆盖核心逻辑**：
   - `app/services/` 业务逻辑
   - `app/api/` 端点参数验证与错误处理
   - `app/core/` 工具函数（crypto、time、config）

2. **可跳过的代码**（添加 `# pragma: no cover` 注释）：
   - `__repr__` / `__str__` 方法
   - 防御性代码（如 `if __name__ == "__main__"`）
   - 不应到达的分支（如 `raise NotImplementedError`）

3. **集成测试单独跑**（本地需配置 DB）：
   ```bash
   # 需先启动 Postgres + Redis
   pytest -m "integration"
   ```

## 查看详细覆盖率报告

```bash
# 生成 HTML 报告
pytest --cov-report=html
open htmlcov/index.html  # macOS/Linux
start htmlcov/index.html  # Windows

# 查看哪些行未覆盖
pytest --cov-report=term-missing
```

## 常见问题

**Q: 本地运行报 `ModuleNotFoundError: No module named 'asyncpg'`？**  
A: 安装完整依赖 `pip install -r requirements.txt`，或在无 DB 环境运行不依赖数据库的测试：
```bash
pytest tests/test_crypto.py tests/test_order_state_machine.py --no-cov
```

**Q: CI 通过但本地覆盖率不足？**  
A: CI 只跑 `-m "unit"` 的测试。本地运行 `pytest tests/ -m "unit"` 确保一致。

**Q: 如何临时禁用覆盖率检查？**  
A: 添加 `--no-cov` 或临时修改 `pytest.ini` 注释掉 `--cov` 相关行。

**Q: 覆盖率门槛能调吗？**  
A: 可以，修改 `pytest.ini` 中的 `--cov-fail-under=70` 值。建议逐步提升而非降低。
