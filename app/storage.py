import json
import sqlite3
from pathlib import Path

from app.models import Outcome, ScreeningConfig, StockSnapshot


class Store:
    def __init__(self, path: str):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self.init()

    def connect(self):
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def init(self):
        with self.connect() as db:
            db.executescript("""
            CREATE TABLE IF NOT EXISTS settings (id INTEGER PRIMARY KEY CHECK(id=1), payload TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS recommendations (
              id INTEGER PRIMARY KEY AUTOINCREMENT, ticker TEXT NOT NULL, entry_price REAL NOT NULL,
              snapshot TEXT NOT NULL, scores TEXT NOT NULL, created_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS outcomes (
              id INTEGER PRIMARY KEY AUTOINCREMENT, recommendation_id INTEGER NOT NULL,
              horizon_days INTEGER NOT NULL CHECK(horizon_days IN (5,10)), exit_price REAL NOT NULL,
              return_pct REAL NOT NULL, mfe_pct REAL, mae_pct REAL,
              UNIQUE(recommendation_id,horizon_days), FOREIGN KEY(recommendation_id) REFERENCES recommendations(id));
            CREATE TABLE IF NOT EXISTS learning_proposals (
              id INTEGER PRIMARY KEY AUTOINCREMENT, payload TEXT NOT NULL,
              status TEXT NOT NULL DEFAULT 'pending', created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
            """)
            db.execute("INSERT OR IGNORE INTO settings(id,payload) VALUES(1,?)", (ScreeningConfig().model_dump_json(),))

    def get_config(self) -> ScreeningConfig:
        with self.connect() as db:
            return ScreeningConfig.model_validate_json(db.execute("SELECT payload FROM settings WHERE id=1").fetchone()[0])

    def save_config(self, config: ScreeningConfig):
        with self.connect() as db:
            db.execute("UPDATE settings SET payload=? WHERE id=1", (config.model_dump_json(),))

    def add_recommendation(self, snapshot: StockSnapshot, scores) -> int:
        with self.connect() as db:
            cur = db.execute("INSERT INTO recommendations(ticker,entry_price,snapshot,scores,created_at) VALUES(?,?,?,?,?)",
                (snapshot.ticker.upper(), snapshot.price, snapshot.model_dump_json(), scores.model_dump_json(), snapshot.data_as_of.isoformat()))
            return cur.lastrowid

    def add_outcome(self, outcome: Outcome):
        with self.connect() as db:
            row = db.execute("SELECT entry_price FROM recommendations WHERE id=?", (outcome.recommendation_id,)).fetchone()
            if not row: raise ValueError("recommendation not found")
            ret = (outcome.exit_price / row[0] - 1) * 100
            db.execute("INSERT OR REPLACE INTO outcomes(recommendation_id,horizon_days,exit_price,return_pct,mfe_pct,mae_pct) VALUES(?,?,?,?,?,?)",
                (outcome.recommendation_id, outcome.horizon_days, outcome.exit_price, ret, outcome.mfe_pct, outcome.mae_pct))

    def outcome_rows(self):
        with self.connect() as db:
            return [dict(r) for r in db.execute("SELECT r.scores,o.return_pct FROM outcomes o JOIN recommendations r ON r.id=o.recommendation_id")]

    def recent(self, limit=50):
        with self.connect() as db:
            return [dict(r) for r in db.execute("SELECT id,ticker,entry_price,scores,created_at FROM recommendations ORDER BY id DESC LIMIT ?", (limit,))]


