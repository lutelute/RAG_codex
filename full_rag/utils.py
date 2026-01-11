import json
import re
from dataclasses import asdict
from pathlib import Path
from typing import Iterable, List, Union


def _iter_dirs(data_dirs: Union[Path, Iterable[Path]]):
    if isinstance(data_dirs, Path):
        return [data_dirs]
    return list(data_dirs)


def load_texts(data_dirs: Union[Path, Iterable[Path]]):
    docs = []
    for data_dir in _iter_dirs(data_dirs):
        if not data_dir.exists():
            continue
        for path in sorted(data_dir.glob("*.md")):
            docs.append((path.name, path.read_text(encoding="utf-8")))
        for path in sorted(data_dir.glob("*.txt")):
            docs.append((path.name, path.read_text(encoding="utf-8")))
    return docs


def chunk_text(text: str, chunk_size: int, overlap: int) -> List[str]:
    words = re.findall(r"\S+", text)
    chunks = []
    start = 0
    while start < len(words):
        end = min(len(words), start + chunk_size)
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        if end == len(words):
            break
        start = max(0, end - overlap)
    return chunks


def save_metadata(path: Path, metadata):
    path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")


def load_metadata(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def save_config(path: Path, config):
    path.write_text(json.dumps(asdict(config), indent=2), encoding="utf-8")
