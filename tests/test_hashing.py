from ai_mem.util.hashing import canonical_json_hash, short_id


def test_canonical_json_hash_is_key_order_invariant() -> None:
    a = {"x": 1, "y": [1, 2, {"b": 2, "a": 1}]}
    b = {"y": [1, 2, {"a": 1, "b": 2}], "x": 1}
    assert canonical_json_hash(a) == canonical_json_hash(b)


def test_canonical_json_hash_changes_on_value_change() -> None:
    assert canonical_json_hash({"x": 1}) != canonical_json_hash({"x": 2})


def test_short_id_length() -> None:
    assert len(short_id("a" * 64)) == 12
