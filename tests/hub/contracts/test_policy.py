"""Boundary cases for shared W1 policy, without claiming production security."""

import pytest

from semaphore_hub import policy


@pytest.mark.parametrize("value", ["a", " admin", "admin ", "éclair", "a-b", "a" * 33])
def test_login_rejects_ambiguous_or_unbounded_identifiers(value):
    with pytest.raises(ValueError):
        policy.normalize_login(value)


def test_identity_normalization_and_password_preservation():
    assert policy.normalize_login("Alice_42") == "alice_42"
    assert policy.normalize_display_name("  Ａlice\t Doe  ") == "Alice Doe"
    password = "  pass\tＷord !  "
    assert policy.validate_password(password) == password
    assert policy.validate_password("x", registering=False) == "x"


@pytest.mark.parametrize("value", ["", " ", "x" * 65, "Alice\x00", "Alice\u200b"])
def test_display_name_rejects_empty_long_and_control_content(value):
    with pytest.raises(ValueError):
        policy.normalize_display_name(value)


@pytest.mark.parametrize("value", ["x" * 11, "x" * 129, "passwordwith\ud800"])
def test_registration_password_bounds(value):
    with pytest.raises(ValueError):
        policy.validate_password(value)


@pytest.mark.parametrize(
    "origin",
    [
        "*",
        "null",
        "http://*.local",
        "http://user:secret@hub.local",
        "http://hub.local/",
        "http://hub.local/path",
        "http://hub.local?x=1",
        "http://hub.local#fragment",
        "http://HUB.local",
        "http://hub.local:bad",
        "ftp://hub.local",
        "http://hub.local\n",
        "http://hub.local:99999",
        "http://hub.local:0",
    ],
)
def test_transport_rejects_nonexact_configuration(origin):
    with pytest.raises(ValueError):
        policy.TransportPolicy(origin)


@pytest.mark.parametrize(
    "origin", ["http://hub.local:8000", "https://hub.local", "http://[::1]:8000"]
)
def test_exact_host_origin_and_cookie_transport(origin):
    config = policy.TransportPolicy(origin)
    assert config.accepts(host=config.host, origin=origin, mutation=True)
    assert config.accepts(host=config.host, origin=None, mutation=False)
    for supplied in [None, "null", "http://evil.local", origin + "/"]:
        assert not config.accepts(host=config.host, origin=supplied, mutation=True)
    assert not config.accepts(host="evil.local", origin=origin, mutation=False)
    assert not config.accepts(host=config.host, origin="null", mutation=False)
    assert config.secure_cookie == origin.startswith("https:")


def test_frozen_resource_and_retention_contract():
    assert policy.SESSION_ABSOLUTE_MS == 24 * 60 * 60 * 1000
    assert policy.SESSION_IDLE_MS == 8 * 60 * 60 * 1000
    assert policy.RAW_RETENTION_MS == policy.BACKUP_RETENTION_MS == 30 * policy.DAY_MS
    assert policy.RECEIPT_RETENTION_MS == 90 * policy.DAY_MS
    assert policy.MAX_OUTSTANDING_INFERENCES == 8
    assert policy.INFERENCE_DEADLINE_MS == 5000
    assert policy.MAX_COMMANDS_PER_GAME == 4096
    assert policy.MAX_GAME_DURATION_MS == 600000
    assert policy.INSTALL_MAX_CLUES == 5 * policy.INSTALL_MAX_ENTRIES
