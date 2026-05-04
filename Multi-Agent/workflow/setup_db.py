#!/usr/bin/env python3
"""Create and seed the SQLite database for the insurance claim workflow demo."""

import json
import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(__file__), "claims_review.db")
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


def create_tables(conn):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS claims (
            claim_id TEXT PRIMARY KEY,
            policy_id TEXT NOT NULL,
            claimant_name TEXT NOT NULL,
            loss_date TEXT NOT NULL,
            filed_date TEXT NOT NULL,
            claim_amount REAL NOT NULL,
            property_address TEXT,
            property_type TEXT,
            cause_of_loss TEXT,
            description TEXT,
            state TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS policies (
            policy_id TEXT PRIMARY KEY,
            policyholder_name TEXT NOT NULL,
            effective_date TEXT NOT NULL,
            expiration_date TEXT NOT NULL,
            coverage_limit REAL NOT NULL,
            deductible REAL NOT NULL,
            coinsurance_pct REAL NOT NULL,
            covered_perils TEXT NOT NULL,
            exclusions TEXT,
            property_value REAL NOT NULL,
            depreciation_rate REAL NOT NULL,
            property_age_years INTEGER NOT NULL,
            state TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS claim_history (
            history_id INTEGER PRIMARY KEY AUTOINCREMENT,
            policy_id TEXT NOT NULL,
            claimant_name TEXT NOT NULL,
            claim_date TEXT NOT NULL,
            claim_amount REAL NOT NULL,
            cause_of_loss TEXT,
            status TEXT
        );

        CREATE TABLE IF NOT EXISTS search_evidence (
            evidence_id INTEGER PRIMARY KEY AUTOINCREMENT,
            claim_id TEXT NOT NULL,
            search_query TEXT NOT NULL,
            result_summary TEXT NOT NULL,
            source_url TEXT,
            searched_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS verdicts (
            verdict_id INTEGER PRIMARY KEY AUTOINCREMENT,
            claim_id TEXT NOT NULL,
            verdict TEXT NOT NULL,
            approved_amount REAL,
            coverage_result TEXT,
            regulation_result TEXT,
            fraud_result TEXT,
            payout_calculation TEXT,
            reasoning TEXT NOT NULL,
            reviewed_at TEXT NOT NULL
        );
    """)


def seed_policy(conn):
    conn.execute("""
        INSERT OR REPLACE INTO policies VALUES (
            'POL-CA-20221015',
            'Margaret Chen',
            '2022-10-15',
            '2025-10-15',
            500000.00,
            10000.00,
            0.80,
            'fire,wind,water_damage,theft,vandalism',
            'flood,earthquake,mold,acts_of_war',
            750000.00,
            0.03,
            12,
            'CA'
        )
    """)


def seed_claim_history(conn):
    history_path = os.path.join(DATA_DIR, "seed_claim_history.json")
    with open(history_path) as f:
        records = json.load(f)

    for r in records:
        conn.execute(
            "INSERT INTO claim_history (policy_id, claimant_name, claim_date, claim_amount, cause_of_loss, status) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (r["policy_id"], r["claimant_name"], r["claim_date"],
             r["claim_amount"], r["cause_of_loss"], r["status"]),
        )


def main():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print(f"Removed existing database: {DB_PATH}")

    with sqlite3.connect(DB_PATH) as conn:
        create_tables(conn)
        seed_policy(conn)
        seed_claim_history(conn)
        conn.commit()

    with sqlite3.connect(DB_PATH) as conn:
        policy_count = conn.execute("SELECT COUNT(*) FROM policies").fetchone()[0]
        history_count = conn.execute("SELECT COUNT(*) FROM claim_history").fetchone()[0]
        print(f"Database created: {DB_PATH}")
        print(f"  policies:      {policy_count} row(s)")
        print(f"  claim_history: {history_count} row(s)")
        print(f"  claims:        0 rows (populated at runtime by Agent 1)")
        print(f"  verdicts:      0 rows (populated at runtime by Agent 6)")


if __name__ == "__main__":
    main()
