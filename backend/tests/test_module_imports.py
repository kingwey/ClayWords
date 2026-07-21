"""模块导入冒烟测试

背景: hunyuan3d/worker.py 曾误写 `from app.core.db import async_session_maker`
(该模块不存在), 导致 worker 进程启动即 ModuleNotFoundError。该文件 0% 测试覆盖,
bug 潜伏至 2026-06-24 才被发现。

本测试遍历 app 包下所有模块并逐个 import, 任一模块导入失败即 fail,
作为防止同类"潜伏导入错误"的最低保障网。
"""

import importlib
import pkgutil

import pytest

import app


@pytest.mark.unit
def test_all_app_modules_import_cleanly():
    """app 包下每个模块都应能被成功导入。"""
    failed: list[str] = []
    for mod in pkgutil.walk_packages(app.__path__, "app."):
        name = mod.name
        if "tests" in name:
            continue
        try:
            importlib.import_module(name)
        except Exception as exc:  # noqa: BLE001 - 汇总所有失败一次性报告
            failed.append(f"{name}: {type(exc).__name__}: {exc}")

    assert not failed, "以下模块导入失败:\n" + "\n".join(failed)


@pytest.mark.unit
def test_hunyuan3d_worker_imports():
    """回归: worker 模块及其会话依赖应可导入(曾因错误导入路径崩溃)。"""
    from app.services.hunyuan3d import worker

    assert hasattr(worker, "poll_hunyuan3d_tasks")
    assert hasattr(worker, "async_session_maker")
