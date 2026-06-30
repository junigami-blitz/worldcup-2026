"""curl サブプロセスでURL本文を取得する（macOSのSSL証明書エラー回避のため）。"""
import subprocess


class FetchError(Exception):
    """取得失敗（非ゼロ終了・空応答・タイムアウト）。"""


def fetch_text(url, timeout=30):
    """curl -sL でURL本文を返す。失敗時は FetchError。"""
    try:
        proc = subprocess.run(
            ["curl", "-sL", "--fail", "--max-time", str(timeout), url],
            capture_output=True, text=True, timeout=timeout + 5,
        )
    except subprocess.TimeoutExpired as e:
        raise FetchError(f"timeout: {url}") from e
    if proc.returncode != 0:
        raise FetchError(f"curl exit {proc.returncode}: {url} {proc.stderr.strip()}")
    if not proc.stdout or not proc.stdout.strip():
        raise FetchError(f"empty response: {url}")
    return proc.stdout
