"""Tests for the maintenance CLI used by the systemd backup timer."""

import os

import pytest

from app import cli
from app.db.connection import get_backup_dir, set_db_path
from app.db.migrations import init_db


def test_backup_creates_one_snapshot_per_day(
    tmp_path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    set_db_path(tmp_path / "pacioli.db")
    try:
        init_db()
        assert cli.main(["backup"]) == 0
        first = capsys.readouterr().out.strip()
        assert os.path.exists(first)

        assert cli.main(["backup"]) == 0  # same day: nothing new
        assert "No backup needed" in capsys.readouterr().out
        assert len(os.listdir(get_backup_dir())) == 1
    finally:
        set_db_path(None)


def test_backup_rejects_unknown_command() -> None:
    with pytest.raises(SystemExit):
        cli.main(["restore"])
