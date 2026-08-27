from __future__ import annotations
import json
from pathlib import Path
from datetime import datetime, timezone
import pandas as pd

try:
    import duckdb
    HAS_DUCKDB = True
except Exception:
    HAS_DUCKDB = False

DB_PATH_ENV = "./data/btfi.duckdb"

class ExperimentStore:
    def __init__(self, db_path: str | Path | None = None):
        self.db_path = Path(db_path or DB_PATH_ENV)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._con = None
        if HAS_DUCKDB:
            try:
                self._con = duckdb.connect(str(self.db_path))
                self._con.execute("""
                    CREATE TABLE IF NOT EXISTS experiments (
                        id INTEGER PRIMARY KEY,
                        title VARCHAR,
                        config JSON,
                        results JSON,
                        verdict VARCHAR,
                        btfi_score DOUBLE,
                        created_at VARCHAR
                    )
                """)
            except Exception:
                self._con = None
        # fallback json file
        self.json_path = self.db_path.with_suffix(".json")
        if not self.json_path.exists():
            self.json_path.write_text("[]")

    def _load_json(self) -> list[dict]:
        try:
            return json.loads(self.json_path.read_text())
        except Exception:
            return []

    def _save_json(self, data: list[dict]):
        self.json_path.write_text(json.dumps(data, indent=2, default=str))

    def next_id(self) -> int:
        if self._con is not None:
            try:
                r = self._con.execute("SELECT COALESCE(MAX(id),0)+1 FROM experiments").fetchone()
                return int(r[0]) if r else 1
            except Exception:
                pass
        data = self._load_json()
        return max([d.get("id",0) for d in data], default=0) + 1

    def save(self, title: str, config: dict, results: dict, verdict: str, btfi_score: float) -> int:
        eid = self.next_id()
        created = datetime.now(timezone.utc).isoformat()
        if self._con is not None:
            try:
                self._con.execute("INSERT INTO experiments VALUES (?, ?, ?, ?, ?, ?, ?)",
                                  [eid, title, json.dumps(config, default=str), json.dumps(results, default=str), verdict, float(btfi_score), created])
            except Exception as e:
                print(f"duckdb save failed: {e}")
        # also json
        data = self._load_json()
        data.append({"id": eid, "title": title, "config": config, "results": results, "verdict": verdict, "btfi_score": btfi_score, "created_at": created})
        self._save_json(data)
        return eid

    def list(self, limit: int = 100) -> list[dict]:
        if self._con is not None:
            try:
                df = self._con.execute("SELECT id, title, verdict, btfi_score, created_at, config FROM experiments ORDER BY id DESC LIMIT ? ", [limit]).fetchdf()
                return df.to_dict(orient="records")
            except Exception:
                pass
        data = self._load_json()
        return sorted(data, key=lambda x: x["id"], reverse=True)[:limit]

    def get(self, eid: int) -> dict | None:
        if self._con is not None:
            try:
                df = self._con.execute("SELECT * FROM experiments WHERE id=?", [eid]).fetchdf()
                if not df.empty:
                    row = df.iloc[0].to_dict()
                    # parse json
                    import json as _j
                    row["config"] = _j.loads(row["config"]) if isinstance(row["config"], str) else row["config"]
                    row["results"] = _j.loads(row["results"]) if isinstance(row["results"], str) else row["results"]
                    return row
            except Exception:
                pass
        data = self._load_json()
        for d in data:
            if d["id"] == eid:
                return d
        return None

    def delete(self, eid: int):
        if self._con is not None:
            try:
                self._con.execute("DELETE FROM experiments WHERE id=?", [eid])
            except Exception:
                pass
        data = self._load_json()
        data = [d for d in data if d["id"] != eid]
        self._save_json(data)

    def clear(self):
        if self._con is not None:
            try:
                self._con.execute("DELETE FROM experiments")
            except Exception:
                pass
        self._save_json([])
