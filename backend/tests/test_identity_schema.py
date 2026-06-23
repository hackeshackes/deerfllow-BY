import os
from pathlib import Path

def test_schema_files_exist():
    migrations_dir = Path(__file__).parent.parent / "app" / "gateway" / "identity" / "migrations"
    files = sorted(migrations_dir.glob("*.sql"))
    assert len(files) >= 4, f"expected ≥4 migration files, found {len(files)}"

def test_001_init_has_required_tables():
    sql = (Path(__file__).parent.parent / "app" / "gateway" / "identity" / "migrations" / "001_init.sql").read_text()
    assert "CREATE TABLE IF NOT EXISTS oidc_providers" in sql
    assert "CREATE TABLE IF NOT EXISTS roles" in sql
    assert "CREATE TABLE IF NOT EXISTS audit_events" in sql