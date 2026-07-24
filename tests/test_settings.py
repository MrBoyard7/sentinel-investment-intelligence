from sentinel.settings import _env_bool, _env_int


def test_env_bool_default_when_unset(monkeypatch):
    monkeypatch.delenv("SENTINEL_TEST_FLAG", raising=False)
    assert _env_bool("SENTINEL_TEST_FLAG", True) is True
    assert _env_bool("SENTINEL_TEST_FLAG", False) is False


def test_env_bool_recognizes_truthy_strings(monkeypatch):
    for value in ["1", "true", "TRUE", "yes", "On"]:
        monkeypatch.setenv("SENTINEL_TEST_FLAG", value)
        assert _env_bool("SENTINEL_TEST_FLAG", False) is True


def test_env_bool_false_for_other_strings(monkeypatch):
    monkeypatch.setenv("SENTINEL_TEST_FLAG", "nope")
    assert _env_bool("SENTINEL_TEST_FLAG", True) is False


def test_env_int_default_when_unset(monkeypatch):
    monkeypatch.delenv("SENTINEL_TEST_NUM", raising=False)
    assert _env_int("SENTINEL_TEST_NUM", 42) == 42


def test_env_int_default_when_empty_string(monkeypatch):
    monkeypatch.setenv("SENTINEL_TEST_NUM", "")
    assert _env_int("SENTINEL_TEST_NUM", 42) == 42


def test_env_int_parses_valid_integer(monkeypatch):
    monkeypatch.setenv("SENTINEL_TEST_NUM", "99")
    assert _env_int("SENTINEL_TEST_NUM", 42) == 99


def test_env_int_falls_back_on_invalid_value(monkeypatch):
    monkeypatch.setenv("SENTINEL_TEST_NUM", "not-a-number")
    assert _env_int("SENTINEL_TEST_NUM", 42) == 42


def test_database_full_path_creates_parent_directory(tmp_path, monkeypatch):
    from sentinel.settings import Settings

    custom = Settings(database_path=str(tmp_path / "nested" / "sentinel.sqlite3"))
    resolved = custom.database_full_path

    assert resolved.parent.exists()
    assert resolved.name == "sentinel.sqlite3"
