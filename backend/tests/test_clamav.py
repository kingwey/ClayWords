"""ClamAV 客户端单元测试

不连真实 ClamAV daemon，用 monkeypatch 替换 asyncio.open_connection
返回的 (reader, writer)，分别注入 OK / FOUND / ERROR / 异常 响应，
验证 INSTREAM 协议与响应解析。
"""

from __future__ import annotations

import asyncio
import struct
from typing import List

import pytest

from app.core.clamav import (
    CHUNK_SIZE,
    ClamAVClient,
    ClamAVError,
    ScanResult,
)


class _FakeWriter:
    """记录所有 write 调用 + 模拟 close/drain。"""

    def __init__(self) -> None:
        self.buffer: bytearray = bytearray()
        self.closed = False

    def write(self, data: bytes) -> None:
        self.buffer.extend(data)

    async def drain(self) -> None:
        await asyncio.sleep(0)

    def close(self) -> None:
        self.closed = True

    async def wait_closed(self) -> None:
        await asyncio.sleep(0)


class _FakeReader:
    """单次 readuntil(\\0) 返回预设响应。"""

    def __init__(self, response: bytes) -> None:
        self._response = response

    async def readuntil(self, separator: bytes) -> bytes:
        await asyncio.sleep(0)
        return self._response


def _patch_open_connection(monkeypatch, response: bytes) -> _FakeWriter:
    """让 asyncio.open_connection 返回我们的 fake，并暴露 writer 给断言用。"""
    writer = _FakeWriter()
    reader = _FakeReader(response)

    async def _fake(*args, **kwargs):
        return reader, writer

    monkeypatch.setattr(
        "app.core.clamav.asyncio.open_connection", _fake
    )
    return writer


# ---- 协议解析 ---------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_scan_clean_file(monkeypatch):
    """ClamAV 返回 'stream: OK\\0' → ScanResult.clean=True。"""
    writer = _patch_open_connection(monkeypatch, b"stream: OK\0")
    client = ClamAVClient(host="ignored", port=0, timeout=5)

    result = await client.scan_bytes(b"hello world")

    assert isinstance(result, ScanResult)
    assert result.clean is True
    assert result.virus_name is None
    assert result.is_infected is False

    # 协议验证：必须以 zINSTREAM\0 开头，结尾以 4 字节 0 收尾
    assert writer.buffer.startswith(b"zINSTREAM\0")
    assert writer.buffer.endswith(struct.pack("!I", 0))
    assert writer.closed


@pytest.mark.unit
@pytest.mark.asyncio
async def test_scan_infected_file(monkeypatch):
    """命中 EICAR 测试病毒：clean=False + virus_name 解析正确。"""
    _patch_open_connection(
        monkeypatch, b"stream: Eicar-Test-Signature FOUND\0"
    )
    client = ClamAVClient(host="ignored", port=0, timeout=5)

    result = await client.scan_bytes(b"X5O!P%@AP[4...")

    assert result.clean is False
    assert result.virus_name == "Eicar-Test-Signature"
    assert result.is_infected is True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_scan_scanner_error(monkeypatch):
    """ClamAV 报错（如 SizeLimitExceeded ERROR）应翻成 ClamAVError，不能误判为干净。"""
    _patch_open_connection(monkeypatch, b"stream: SizeLimitExceeded ERROR\0")
    client = ClamAVClient(host="ignored", port=0, timeout=5)

    with pytest.raises(ClamAVError, match="SizeLimitExceeded"):
        await client.scan_bytes(b"oversized")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_scan_unexpected_response(monkeypatch):
    """格式无法识别的响应必须报错而非默认放过。"""
    _patch_open_connection(monkeypatch, b"garbage\0")
    client = ClamAVClient(host="ignored", port=0, timeout=5)

    with pytest.raises(ClamAVError, match="Unexpected"):
        await client.scan_bytes(b"data")


# ---- 网络/连接错误 ---------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_scan_connection_refused(monkeypatch):
    """连不上 daemon：socket 异常翻成 ClamAVError 让上层走「保持 pending 待重试」分支。"""

    async def _refuse(*args, **kwargs):
        raise ConnectionRefusedError("nothing listening on :3310")

    monkeypatch.setattr("app.core.clamav.asyncio.open_connection", _refuse)
    client = ClamAVClient(host="ignored", port=0, timeout=5)

    with pytest.raises(ClamAVError, match="connection failed"):
        await client.scan_bytes(b"data")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_scan_timeout(monkeypatch):
    """超时也要变 ClamAVError，不能让请求悬挂。"""

    async def _hang(*args, **kwargs):
        await asyncio.sleep(10)
        raise AssertionError("should have timed out before reaching here")

    monkeypatch.setattr("app.core.clamav.asyncio.open_connection", _hang)
    client = ClamAVClient(host="ignored", port=0, timeout=0.05)

    with pytest.raises(ClamAVError, match="timed out"):
        await client.scan_bytes(b"data")


# ---- 分块逻辑 --------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_scan_chunks_large_payload(monkeypatch):
    """超过 CHUNK_SIZE 的数据应被分成多块发送（每块前缀 4 字节大端长度）。"""
    writer = _patch_open_connection(monkeypatch, b"stream: OK\0")
    client = ClamAVClient(host="ignored", port=0, timeout=5)

    # 2.5 个块大小的 payload
    payload_size = CHUNK_SIZE * 2 + CHUNK_SIZE // 2
    await client.scan_bytes(b"x" * payload_size)

    # 解析 writer.buffer：去掉 zINSTREAM\0 前缀，剩下应是 N 段 (len + data) + 4 字节 0
    body = bytes(writer.buffer)[len(b"zINSTREAM\0"):]
    chunks: List[int] = []
    pos = 0
    while pos < len(body):
        size = struct.unpack("!I", body[pos : pos + 4])[0]
        pos += 4
        if size == 0:
            break
        chunks.append(size)
        pos += size

    # 第三个块是半块，前两个是满块；总和等于原 payload
    assert len(chunks) == 3
    assert chunks[0] == CHUNK_SIZE
    assert chunks[1] == CHUNK_SIZE
    assert chunks[2] == CHUNK_SIZE // 2
    assert sum(chunks) == payload_size


@pytest.mark.unit
def test_scan_result_flags():
    """ScanResult.is_infected 派生属性的真值表。"""
    assert ScanResult(clean=True).is_infected is False
    assert ScanResult(clean=False, virus_name=None).is_infected is False  # 错误状态≠染毒
    assert ScanResult(clean=False, virus_name="X").is_infected is True
