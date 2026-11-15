"""带磁盘缓存、重试与限速的 HTTP 客户端（标准库实现）。"""

from __future__ import annotations

import gzip
import hashlib
import json
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import zlib
from pathlib import Path

from . import config


class FetchError(Exception):
    """网络抓取失败。status 为 HTTP 状态码（若有）。"""

    def __init__(self, message: str, status: int | None = None):
        super().__init__(message)
        self.status = status


class HttpClient:
    def __init__(
        self,
        cache_dir: Path | None = None,
        timeout: int = config.REQUEST_TIMEOUT,
        ttl: int = config.CACHE_TTL,
        min_interval: float = config.MIN_REQUEST_INTERVAL,
    ) -> None:
        self.cache_dir = Path(cache_dir or config.CACHE_DIR)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.timeout = timeout
        self.ttl = ttl
        self.min_interval = min_interval
        self._lock = threading.Lock()
        self._last_request = 0.0

    # ------------------------------------------------------------------ 缓存
    def _cache_path(self, key: str) -> Path:
        digest = hashlib.sha1(key.encode("utf-8")).hexdigest()
        return self.cache_dir / f"{digest}.json"

    def _read_cache(self, key: str, ttl: int) -> str | None:
        path = self._cache_path(key)
        if not path.exists():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        if ttl >= 0 and time.time() - float(payload.get("ts", 0)) > ttl:
            return None
        return payload.get("text")

    def _write_cache(self, key: str, text: str) -> None:
        payload = {"key": key, "ts": time.time(), "text": text}
        tmp = self._cache_path(key).with_suffix(".tmp")
        try:
            tmp.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            tmp.replace(self._cache_path(key))
        except OSError:
            pass

    def peek_cache(self, key: str, ttl: int | None = None) -> str | None:
        """只读缓存，不发起网络请求；供离线短路时优先取已缓存内容。"""
        return self._read_cache(key, self.ttl if ttl is None else ttl)

    # ------------------------------------------------------------------ 限速
    def _throttle(self) -> None:
        with self._lock:
            wait = self.min_interval - (time.time() - self._last_request)
            if wait > 0:
                time.sleep(wait)
            self._last_request = time.time()

    # ------------------------------------------------------------------ 请求
    def get_text(
        self,
        url: str,
        *,
        force: bool = False,
        use_cache: bool = True,
        ttl: int | None = None,
        timeout: float | None = None,
    ) -> tuple[str, bool]:
        """返回 (文本, 是否命中缓存)。"""
        ttl = self.ttl if ttl is None else ttl
        if use_cache and not force:
            cached = self._read_cache(url, ttl)
            if cached is not None:
                return cached, True

        text = self._download(url, timeout)
        if use_cache:
            self._write_cache(url, text)
        return text, False

    def _download(self, url: str, timeout: float | None = None) -> str:
        timeout = self.timeout if timeout is None else timeout
        url = urllib.parse.quote(url, safe=":/?&=#%+~")
        headers = {
            "User-Agent": config.USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.6",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "close",
        }
        last_error = "未知错误"
        for attempt in range(max(1, config.HTTP_RETRIES)):
            self._throttle()
            request = urllib.request.Request(url, headers=headers)
            try:
                with urllib.request.urlopen(request, timeout=timeout) as response:
                    raw = response.read()
                    encoding = (response.headers.get("Content-Encoding") or "").lower()
                    if "gzip" in encoding:
                        raw = gzip.decompress(raw)
                    elif "deflate" in encoding:
                        try:
                            raw = zlib.decompress(raw)
                        except zlib.error:
                            raw = zlib.decompress(raw, -zlib.MAX_WBITS)
                    charset = response.headers.get_content_charset() or "utf-8"
                    if charset.lower() in ("gb2312", "gbk", "gb-2312"):
                        charset = "gb18030"
                    return raw.decode(charset, errors="replace")
            except urllib.error.HTTPError as exc:
                if exc.code == 404:
                    raise FetchError("页面不存在（HTTP 404）", status=404) from exc
                if exc.code in (403, 410, 451):
                    raise FetchError(f"站点拒绝访问（HTTP {exc.code}）", status=exc.code) from exc
                last_error = f"HTTP {exc.code}"
            except urllib.error.URLError as exc:
                last_error = f"网络不可达：{exc.reason}"
                reason = str(exc.reason).lower()
                if "timed out" in reason or "timeout" in reason:
                    break  # 连接阶段就超时，重试没有意义
            except TimeoutError:
                last_error = "请求超时"
                break
            except OSError as exc:
                last_error = f"网络错误：{exc}"
                if getattr(exc, "errno", None) in (10060, 110):
                    break
            if attempt < 2:
                time.sleep(1.2 * (attempt + 1))
        raise FetchError(last_error)
