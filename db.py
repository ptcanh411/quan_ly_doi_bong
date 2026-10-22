import sqlite3
import json
import os
from datetime import datetime, timedelta

DB_FILE = os.path.join(os.path.dirname(__file__), "fc_club.db")

def get_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db():
    conn = get_connection()
    cur = conn.cursor()

    # Players table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS players (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        nickname TEXT,
        phoneNumber TEXT,
        initialDeposit REAL DEFAULT 0,
        isActive INTEGER DEFAULT 1,
        displayOrder INTEGER DEFAULT 0,
        createdAt TEXT,
        updatedAt TEXT
    )
    """)

    # Matches table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS matches (
        id TEXT PRIMARY KEY,
        matchDate TEXT NOT NULL,
        title TEXT,
        timeSlot TEXT DEFAULT '06:00 - 07:30',
        stadiumName TEXT DEFAULT 'Sân bóng 6h50',
        pitchFee REAL DEFAULT 0,
        drinksFee REAL DEFAULT 0,
        defaultDrinkPerPerson REAL DEFAULT 10000,
        totalCost REAL DEFAULT 0,
        status TEXT DEFAULT 'SCHEDULED',
        isHidden INTEGER DEFAULT 0,
        notes TEXT,
        createdAt TEXT,
        updatedAt TEXT
    )
    """)

    # Match player records
    cur.execute("""
    CREATE TABLE IF NOT EXISTS match_player_records (
        id TEXT PRIMARY KEY,
        matchId TEXT NOT NULL,
        playerId TEXT NOT NULL,
        isPresent INTEGER DEFAULT 0,
        hasDrinks INTEGER DEFAULT 0,
        drinkAmount REAL DEFAULT 0,
        pitchShare REAL DEFAULT 0,
        feeCharged REAL DEFAULT 0,
        addedDeposit REAL DEFAULT 0,
        note TEXT,
        createdAt TEXT,
        updatedAt TEXT,
        UNIQUE(matchId, playerId),
        FOREIGN KEY(matchId) REFERENCES matches(id) ON DELETE CASCADE,
        FOREIGN KEY(playerId) REFERENCES players(id) ON DELETE CASCADE
    )
    """)

    # Direct deposit transactions table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS deposit_transactions (
        id TEXT PRIMARY KEY,
        playerId TEXT NOT NULL,
        amount REAL NOT NULL,
        depositDate TEXT NOT NULL,
        note TEXT,
        createdAt TEXT,
        FOREIGN KEY(playerId) REFERENCES players(id) ON DELETE CASCADE
    )
    """)

    # Pending deposit requests submitted by players (Multi-device approval queue)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS deposit_requests (
        id TEXT PRIMARY KEY,
        playerId TEXT NOT NULL,
        amount REAL NOT NULL,
        depositDate TEXT NOT NULL,
        note TEXT,
        status TEXT DEFAULT 'PENDING',
        createdAt TEXT,
        reviewedAt TEXT,
        FOREIGN KEY(playerId) REFERENCES players(id) ON DELETE CASCADE
    )
    """)

    # Admin active session tokens
    cur.execute("""
    CREATE TABLE IF NOT EXISTS admin_tokens (
        token TEXT PRIMARY KEY,
        createdAt TEXT,
        expiresAt TEXT
    )
    """)

    # Club config table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS club_config (
        id TEXT PRIMARY KEY,
        clubName TEXT DEFAULT 'FC 6H SÁNG CHỦ NHẬT',
        bankCode TEXT DEFAULT 'MB',
        bankAccount TEXT DEFAULT '0987654321',
        accountHolder TEXT DEFAULT 'NGUYEN VAN THU QUY',
        defaultTimeSlot TEXT DEFAULT '06:00 - 07:30'
    )
    """)

    # Default config
    cur.execute("""
    INSERT OR IGNORE INTO club_config (id, clubName, bankCode, bankAccount, accountHolder, defaultTimeSlot)
    VALUES ('default', 'FC 6H SÁNG CHỦ NHẬT', 'MB', '0987654321', 'NGUYEN VAN THU QUY', '06:00 - 07:30')
    """)

    conn.commit()

    # Check if players exist, if not seed from seed_data.json
    cur.execute("SELECT COUNT(*) as cnt FROM players")
    count = cur.fetchone()["cnt"]
    if count == 0:
        seed_db(conn)

    conn.close()

def seed_db(conn=None):
    close_after = False
    if conn is None:
        conn = get_connection()
        close_after = True

    cur = conn.cursor()
    cur.execute("DELETE FROM match_player_records")
    cur.execute("DELETE FROM matches")
    cur.execute("DELETE FROM players")

    seed_file = os.path.join(os.path.dirname(__file__), "seed_data.json")
    if not os.path.exists(seed_file):
        print("seed_data.json not found!")
        return

    with open(seed_file, "r", encoding="utf-8") as f:
        players_data = json.load(f)

    # Historical matches
    match_configs = [
        {"id": "m-19-9", "date": "2024-09-19T06:00:00", "title": "Trận CN 19/9", "pitchFee": 308000, "key": "19/9"},
        {"id": "m-27-9", "date": "2024-09-27T06:00:00", "title": "Trận CN 27/9", "pitchFee": 170000, "key": "27/9"},
        {"id": "m-04-10", "date": "2024-10-04T06:00:00", "title": "Trận CN 4/10", "pitchFee": 254000, "key": "4/10"},
        {"id": "m-11-10", "date": "2024-10-11T06:00:00", "title": "Trận CN 11/10", "pitchFee": 330000, "key": "11/10"},
        {"id": "m-18-10", "date": "2024-10-18T06:00:00", "title": "Trận CN 18/10", "pitchFee": 260000, "key": "18/10"},
    ]

    now = datetime.now().isoformat()
    for m in match_configs:
        cur.execute("""
        INSERT INTO matches (id, matchDate, title, timeSlot, stadiumName, pitchFee, drinksFee, defaultDrinkPerPerson, totalCost, status, notes, createdAt, updatedAt)
        VALUES (?, ?, ?, '06:00 - 07:30', 'Sân bóng 6h50', ?, 0, 10000, ?, 'COMPLETED', 'Trận đấu lịch sử', ?, ?)
        """, (m["id"], m["date"], m["title"], m["pitchFee"], m["pitchFee"], now, now))

    # Add next Sunday upcoming match
    today = datetime.now()
    days_ahead = 6 - today.weekday() # 6 is Sunday
    if days_ahead <= 0:
        days_ahead += 7
    next_sunday = today + timedelta(days=days_ahead)
    next_sunday_str = next_sunday.strftime("%Y-%m-%d") + "T06:00:00"
    next_sunday_title = f"Trận CN {next_sunday.day}/{next_sunday.month}"
    upcoming_id = "m-upcoming"

    cur.execute("""
    INSERT INTO matches (id, matchDate, title, timeSlot, stadiumName, pitchFee, drinksFee, defaultDrinkPerPerson, totalCost, status, notes, createdAt, updatedAt)
    VALUES (?, ?, ?, '06:00 - 07:30', 'Sân bóng 6h50', 300000, 0, 10000, 300000, 'SCHEDULED', 'Trận Chủ Nhật tuần này', ?, ?)
    """, (upcoming_id, next_sunday_str, next_sunday_title, now, now))

    # Insert players
    order = 0
    for p in players_data:
        order += 1
        player_id = f"p-{order}"
        nickname = p["name"].split(" ")[1] if " " in p["name"] else None
        cur.execute("""
        INSERT INTO players (id, name, nickname, phoneNumber, initialDeposit, isActive, displayOrder, createdAt, updatedAt)
        VALUES (?, ?, ?, '', ?, 1, ?, ?, ?)
        """, (player_id, p["name"], nickname, p["deposit"], order, now, now))

        # Records for historical matches
        for m in match_configs:
            fee = p["matches"].get(m["key"], 0)
            is_present = 1 if fee > 0 else 0
            cur.execute("""
            INSERT INTO match_player_records (id, matchId, playerId, isPresent, hasDrinks, drinkAmount, pitchShare, feeCharged, addedDeposit, note, createdAt, updatedAt)
            VALUES (?, ?, ?, ?, 0, 0, ?, ?, 0, '', ?, ?)
            """, (f"rec-{m['id']}-{player_id}", m["id"], player_id, is_present, fee, fee, now, now))

        # Empty record for upcoming match
        cur.execute("""
        INSERT INTO match_player_records (id, matchId, playerId, isPresent, hasDrinks, drinkAmount, pitchShare, feeCharged, addedDeposit, note, createdAt, updatedAt)
        VALUES (?, ?, ?, 0, 0, 0, 0, 0, 0, '', ?, ?)
        """, (f"rec-{upcoming_id}-{player_id}", upcoming_id, player_id, now, now))

    conn.commit()
    print("Database seeded with 25 players and 5 matches successfully!")
    if close_after:
        conn.close()

if __name__ == "__main__":
    init_db()
