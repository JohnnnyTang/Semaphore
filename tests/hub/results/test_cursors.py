import pytest

from semaphore_hub.results.service import cursor_decode, cursor_encode


def test_cursor_preserves_full_key_and_rejects_wrong_scope():
    key = [100, 12345678, "game-with-tie"]
    cursor = cursor_encode("exact-cohort-one", key)
    assert len(cursor) <= 200
    assert cursor_decode("exact-cohort-one", cursor) == key
    with pytest.raises(ValueError):
        cursor_decode("exact-cohort-two", cursor)


@pytest.mark.parametrize("value", ["", "!", "a" * 201, "e30"])
def test_invalid_cursor(value):
    with pytest.raises(ValueError):
        cursor_decode("history:owner", value)
