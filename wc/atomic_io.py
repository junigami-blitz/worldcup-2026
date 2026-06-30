"""JSONのアトミック書き込みと安全な読み込み。"""
import json
import os
from pathlib import Path


def write_json_atomic(path, obj) -> None:
    """一時ファイルに書いてから os.replace で差し替える。

    途中でクラッシュしても元ファイルが壊れない。親ディレクトリは自動作成。
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)  # 同一ディレクトリ内のアトミックなrename


def read_json_or_none(path):
    """存在し正常なJSONなら読み込む。無い/壊れている場合は None。"""
    path = Path(path)
    if not path.exists():
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None
