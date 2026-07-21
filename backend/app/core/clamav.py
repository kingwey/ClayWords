"""ClamAV 病毒扫描客户端（INSTREAM 协议）

使用 ClamAV daemon 的原生 TCP 协议 INSTREAM（端口 3310），避免引入 pyclamd 等额外依赖。

协议规范（clamd.conf / clamd(8) 文档）:
  - 发送 b"zINSTREAM\\0"
  - 循环发送数据块：每块 4 字节大端长度 + 数据；以 4 字节 0 收尾
  - 服务器返回单行响应（z 命令以 \\0 分隔）:
      "stream: OK\\0"                 → 干净
      "stream: <Virus.Name> FOUND\\0" → 染毒
      其他                             → 视为扫描错误

设计要点:
  - asyncio.open_connection 避免阻塞事件循环
  - 块大小默认 64KB，匹配 ClamAV 默认 StreamMaxLength 配置下的常见块尺寸
  - 单次扫描超时统一从 settings.CLAMAV_TIMEOUT_SECONDS 读取
  - settings.CLAMAV_ENABLED=False 时由调用方走「跳过扫描」路径，本模块不做默认放行
"""

from __future__ import annotations

import asyncio
import struct
from dataclasses import dataclass
from typing import Optional

import structlog

from app.core.config import settings

logger = structlog.get_logger()

# 单次发送的最大块大小。INSTREAM 协议长度域是 4 字节大端无符号，
# 实际上 ClamAV 的 StreamMaxLength 默认 25M；这里选 64KB 是为了:
#   1) 流式发送大文件时减少单次 send 的内存压力
#   2) 控制单包大小，避免 TCP MSS 分片影响延迟
CHUNK_SIZE = 64 * 1024


@dataclass(frozen=True)
class ScanResult:
    """扫描结果。clean=True 代表 ClamAV 明确判断为 OK。"""

    clean: bool
    virus_name: Optional[str] = None  # 命中时填病毒名，干净时 None
    raw_response: str = ""

    @property
    def is_infected(self) -> bool:
        return not self.clean and self.virus_name is not None


class ClamAVError(Exception):
    """ClamAV 通信或扫描层面的错误（不同于「发现病毒」，这是中间状态）。"""


class ClamAVClient:
    """异步 ClamAV INSTREAM 客户端。

    每次扫描建立独立 TCP 连接，结束后关闭——ClamAV daemon 对短连接的支持比长连接更好，
    长连接需要走 IDSESSION/END 配对，没必要为我们的低 QPS 文件扫描引入复杂度。
    """

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        timeout: Optional[float] = None,
    ):
        self.host = host or settings.CLAMAV_HOST
        self.port = port or settings.CLAMAV_PORT
        self.timeout = timeout or settings.CLAMAV_TIMEOUT_SECONDS

    async def scan_bytes(self, data: bytes) -> ScanResult:
        """扫描字节流，返回 ScanResult。

        Raises:
            ClamAVError: 连接失败、超时或响应格式无法识别
        """
        try:
            return await asyncio.wait_for(
                self._scan(data), timeout=self.timeout
            )
        except asyncio.TimeoutError as exc:
            raise ClamAVError(
                f"ClamAV scan timed out after {self.timeout}s "
                f"(host={self.host}:{self.port}, size={len(data)})"
            ) from exc
        except (OSError, ConnectionError) as exc:
            raise ClamAVError(
                f"ClamAV connection failed: {exc} (host={self.host}:{self.port})"
            ) from exc

    async def _scan(self, data: bytes) -> ScanResult:
        """实际的 INSTREAM 实现。被 scan_bytes 包装超时/异常翻译。"""
        reader, writer = await asyncio.open_connection(self.host, self.port)
        try:
            writer.write(b"zINSTREAM\0")
            await writer.drain()

            # 分块发送
            for i in range(0, len(data), CHUNK_SIZE):
                chunk = data[i : i + CHUNK_SIZE]
                writer.write(struct.pack("!I", len(chunk)) + chunk)
                await writer.drain()

            # 0 长度块表示流结束
            writer.write(struct.pack("!I", 0))
            await writer.drain()

            # 读取单行响应（z 命令以 \0 结尾）
            response_bytes = await reader.readuntil(b"\0")
            response = response_bytes.rstrip(b"\0").decode("utf-8", errors="replace")
            return self._parse_response(response)
        finally:
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:  # noqa: BLE001 - 关闭阶段错误不影响扫描结果
                pass

    @staticmethod
    def _parse_response(response: str) -> ScanResult:
        """解析 ClamAV 响应。

        响应格式（注意 ClamAV 在 INSTREAM 下固定用 "stream:" 前缀）:
          "stream: OK"
          "stream: Eicar-Test-Signature FOUND"
          "stream: SizeLimitExceeded ERROR"  → 抛 ClamAVError
        """
        # 去掉 "stream: " 前缀（如果有）
        body = response.split(": ", 1)[1] if ": " in response else response

        if body.strip() == "OK":
            return ScanResult(clean=True, raw_response=response)

        if body.endswith(" FOUND"):
            virus_name = body[: -len(" FOUND")].strip()
            return ScanResult(clean=False, virus_name=virus_name, raw_response=response)

        if body.endswith(" ERROR"):
            raise ClamAVError(f"ClamAV reported error: {response}")

        raise ClamAVError(f"Unexpected ClamAV response: {response!r}")


# 模块级单例（与 minio_client / redis_client 风格一致）
clamav_client = ClamAVClient()


def get_clamav() -> ClamAVClient:
    return clamav_client
