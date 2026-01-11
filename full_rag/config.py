from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RagConfig:
    data_dir: Path
    results_dir: Path
    logs_dir: Path
    index_path: Path
    metadata_path: Path
    chunk_size: int = 400
    chunk_overlap: int = 60
    embed_model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    top_k: int = 3


def default_config() -> RagConfig:
    base = Path(__file__).parent
    return RagConfig(
        data_dir=base / "sample_data",
        results_dir=base / "results",
        logs_dir=base / "logs",
        index_path=base / "index.faiss",
        metadata_path=base / "metadata.json",
    )
