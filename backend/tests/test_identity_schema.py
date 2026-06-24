from pathlib import Path


def test_001_init_has_required_tables():
    sql = (Path(__file__).parent.parent / "app" / "gateway" / "identity" / "migrations" / "001_init.sql").read_text()
    assert "CREATE TABLE IF NOT EXISTS oidc_providers" in sql
    assert "CREATE TABLE IF NOT EXISTS roles" in sql
    assert "CREATE TABLE IF NOT EXISTS audit_events" in sql
