from pathlib import Path

from ai_mem.enrich.topics import TopicVocabulary, load, normalize


def test_normalize_maps_aliases() -> None:
    vocab = TopicVocabulary(
        canonical={"ai-mem": ["ai memory", "obsidian sync"]},
    )
    out = normalize(["AI Memory", "unrelated"], vocab)
    assert out == ["ai-mem", "unrelated"]


def test_normalize_dedupes_preserve_order() -> None:
    vocab = TopicVocabulary(canonical={"x": ["x-alias"]})
    out = normalize(["x-alias", "x", "y", "y"], vocab)
    assert out == ["x", "y"]


def test_load_empty_file(tmp_path: Path) -> None:
    f = tmp_path / "topics.yaml"
    f.write_text("topics: {}\n")
    vocab = load(f)
    assert vocab.canonical == {}
