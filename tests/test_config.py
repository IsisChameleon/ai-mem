from pathlib import Path

from ai_mem.config import load


def test_load_example_config(tmp_path: Path) -> None:
    cfg_src = Path(__file__).resolve().parents[1] / "config.example.yaml"
    cfg = load(cfg_src)
    assert cfg.paths.notes_subdir == "AI Chats"
    assert cfg.llm.model == "claude-haiku-4-5-20251001"
    assert cfg.gmail.scope.endswith("gmail.readonly")
    assert cfg.attachments.max_bytes == 50 * 1024 * 1024
