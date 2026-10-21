import http.server
import socketserver
import json
import urllib.parse
import os
import uuid
import sys
import io
from datetime import datetime, timedelta
import sqlite3
from db import get_connection, init_db, seed_db

PORT = int(os.environ.get("PORT", 8000))
PUBLIC_DIR = os.path.join(os.path.dirname(__file__), "public")

class FCRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=PUBLIC_DIR, **kwargs)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_cors_headers()
        self.end_headers()

    def send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def send_json(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_cors_headers()
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

    def read_body(self):
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length == 0:
            return {}
        body = self.rfile.read(content_length).decode("utf-8")
        try:
            return json.loads(body)
        except Exception:
            return {}

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path.startswith("/api/"):
            return self.handle_api_get(path)

        # Fallback to serving static files from public/
        if path == "/":
            self.path = "/index.html"
        return super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path.startswith("/api/"):
            return self.handle_api_post(path)
        self.send_json({"error": "Not Found"}, 404)

    def do_PUT(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path.startswith("/api/"):
            return self.handle_api_put(path)
        self.send_json({"error": "Not Found"}, 404)

    def do_DELETE(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path.startswith("/api/"):
            return self.handle_api_delete(path)
        self.send_json({"error": "Not Found"}, 404)

    # ---------------- API HANDLERS ----------------

    def handle_api_get(self, path):
        conn = get_connection()
        cur = conn.cursor()

        try:
            if path == "/api/players":
                # Get all active players
                cur.execute("SELECT * FROM players WHERE isActive = 1 ORDER BY displayOrder ASC")
                players = [dict(row) for row in cur.fetchall()]

                # Get all match records for these players
                cur.execute("SELECT * FROM match_player_records")
                records = [dict(row) for row in cur.fetchall()]

                records_by_player = {}
                for r in records:
                    pid = r["playerId"]
                    if pid not in records_by_player:
                        records_by_player[pid] = {}
                    records_by_player[pid][r["matchId"]] = r

                # Get direct deposits outside matches
                cur.execute("SELECT playerId, SUM(amount) as totalDirect FROM deposit_transactions GROUP BY playerId")
                direct_map = {row["playerId"]: (row["totalDirect"] or 0) for row in cur.fetchall()}

                for p in players:
                    pid = p["id"]
                    p_recs = records_by_player.get(pid, {})
                    p["matchRecords"] = p_recs
                    p["totalAddedDeposit"] = sum(r.get("addedDeposit", 0) for r in p_recs.values())
                    p["totalDirectDeposit"] = direct_map.get(pid, 0)
                    p["totalPaid"] = (p.get("initialDeposit") or 0) + p["totalAddedDeposit"] + p["totalDirectDeposit"]
                    p["totalUsed"] = sum(r.get("feeCharged", 0) for r in p_recs.values())
                    p["balance"] = p["totalPaid"] - p["totalUsed"]

                return self.send_json(players)

            elif path == "/api/deposits":
                cur.execute("""
                SELECT d.*, p.name as playerName, p.nickname as playerNickname
                FROM deposit_transactions d
                JOIN players p ON d.playerId = p.id
                ORDER BY d.depositDate DESC, d.createdAt DESC
                """)
                return self.send_json([dict(row) for row in cur.fetchall()])

            elif path == "/api/matches":
                cur.execute("SELECT * FROM matches ORDER BY matchDate ASC")
                matches = [dict(row) for row in cur.fetchall()]

                # Enrich with attendee stats
                cur.execute("""
                SELECT matchId,
                       SUM(CASE WHEN isPresent = 1 THEN 1 ELSE 0 END) as attendingCount,
                       SUM(CASE WHEN hasDrinks = 1 THEN 1 ELSE 0 END) as drinksCount,
                       SUM(feeCharged) as totalFeeCharged,
                       SUM(addedDeposit) as totalAddedDeposit
                FROM match_player_records
                GROUP BY matchId
                """)
                stats_rows = cur.fetchall()
                stats_map = {row["matchId"]: dict(row) for row in stats_rows}

                for m in matches:
                    st = stats_map.get(m["id"], {})
                    m["attendingCount"] = st.get("attendingCount", 0) or 0
                    m["drinksCount"] = st.get("drinksCount", 0) or 0
                    m["totalFeeCharged"] = st.get("totalFeeCharged", 0) or 0
                    m["totalAddedDeposit"] = st.get("totalAddedDeposit", 0) or 0

                return self.send_json(matches)

            elif path.startswith("/api/matches/"):
                match_id = path.split("/api/matches/")[1]
                cur.execute("SELECT * FROM matches WHERE id = ?", (match_id,))
                match_row = cur.fetchone()
                if not match_row:
                    return self.send_json({"error": "Trận đấu không tồn tại"}, 404)
                
                match_data = dict(match_row)
                cur.execute("""
                SELECT r.*, p.name as playerName, p.nickname as playerNickname
                FROM match_player_records r
                JOIN players p ON r.playerId = p.id
                WHERE r.matchId = ? AND p.isActive = 1
                ORDER BY p.displayOrder ASC
                """, (match_id,))
                match_data["records"] = [dict(row) for row in cur.fetchall()]
                return self.send_json(match_data)

            elif path == "/api/config":
                cur.execute("SELECT * FROM club_config WHERE id = 'default'")
                cfg = cur.fetchone()
                return self.send_json(dict(cfg) if cfg else {})

            elif path == "/api/summary":
                # Compute total paid, used, balance
                cur.execute("SELECT SUM(initialDeposit) as totalInitial FROM players WHERE isActive = 1")
                initial = cur.fetchone()["totalInitial"] or 0

                cur.execute("SELECT SUM(addedDeposit) as totalAdded, SUM(feeCharged) as totalUsed FROM match_player_records")
                row = cur.fetchone()
                added = row["totalAdded"] or 0
                used = row["totalUsed"] or 0

                cur.execute("SELECT SUM(amount) as totalDirect FROM deposit_transactions")
                direct = cur.fetchone()["totalDirect"] or 0

                total_paid = initial + added + direct
                balance = total_paid - used

                cur.execute("SELECT COUNT(*) as completedCnt FROM matches WHERE status = 'COMPLETED'")
                completed = cur.fetchone()["completedCnt"]

                return self.send_json({
                    "totalPaid": total_paid,
                    "totalUsed": used,
                    "balance": balance,
                    "completedMatches": completed
                })

            else:
                return self.send_json({"error": "Not Found"}, 404)
        finally:
            conn.close()

    def handle_api_post(self, path):
        body = self.read_body()
        conn = get_connection()
        cur = conn.cursor()
        now = datetime.now().isoformat()

        try:
            if path == "/api/players":
                name = body.get("name", "").strip()
                if not name:
                    return self.send_json({"error": "Tên thành viên là bắt buộc"}, 400)
                
                player_id = "p-" + str(uuid.uuid4())[:8]
                nickname = body.get("nickname", "").strip() or None
                phone = body.get("phoneNumber", "").strip() or None
                initial_deposit = float(body.get("initialDeposit", 0))

                cur.execute("SELECT COUNT(*) as cnt FROM players")
                order = cur.fetchone()["cnt"] + 1

                cur.execute("""
                INSERT INTO players (id, name, nickname, phoneNumber, initialDeposit, isActive, displayOrder, createdAt, updatedAt)
                VALUES (?, ?, ?, ?, ?, 1, ?, ?, ?)
                """, (player_id, name, nickname, phone, initial_deposit, order, now, now))

                # Also insert records for all matches
                cur.execute("SELECT id FROM matches")
                for m in cur.fetchall():
                    rec_id = f"rec-{m['id']}-{player_id}"
                    cur.execute("""
                    INSERT INTO match_player_records (id, matchId, playerId, isPresent, hasDrinks, drinkAmount, pitchShare, feeCharged, addedDeposit, note, createdAt, updatedAt)
                    VALUES (?, ?, ?, 0, 0, 0, 0, 0, 0, '', ?, ?)
                    """, (rec_id, m["id"], player_id, now, now))

                conn.commit()
                return self.send_json({"success": True, "id": player_id}, 201)

            elif path == "/api/deposits":
                player_id = body.get("playerId")
                amount = float(body.get("amount", 0))
                note = body.get("note", "").strip() or "Nộp tiền quỹ"
                deposit_date = body.get("depositDate") or now

                if not player_id or amount <= 0:
                    return self.send_json({"error": "Vui lòng chọn thành viên và số tiền nạp hợp lệ"}, 400)

                dep_id = "dep-" + str(uuid.uuid4())[:8]
                cur.execute("""
                INSERT INTO deposit_transactions (id, playerId, amount, depositDate, note, createdAt)
                VALUES (?, ?, ?, ?, ?, ?)
                """, (dep_id, player_id, amount, deposit_date, note, now))
                conn.commit()
                return self.send_json({"success": True, "id": dep_id}, 201)

            elif path == "/api/matches":
                auto_next = body.get("autoNextSunday", False)
                title = body.get("title", "").strip()
                match_date = body.get("matchDate")

                if auto_next or not match_date:
                    # Calculate next Sunday from latest match or today
                    cur.execute("SELECT matchDate FROM matches ORDER BY matchDate DESC LIMIT 1")
                    last_row = cur.fetchone()
                    base = datetime.now()
                    if last_row:
                        try:
                            base = datetime.fromisoformat(last_row["matchDate"].split("T")[0])
                        except Exception:
                            pass
                    days_ahead = 6 - base.weekday()
                    if days_ahead <= 0:
                        days_ahead += 7
                    target = base + timedelta(days=days_ahead)
                    match_date = target.strftime("%Y-%m-%d") + "T06:00:00"
                    if not title:
                        title = f"Trận CN {target.day}/{target.month}"
                else:
                    if not title:
                        title = "Trận bóng mới"

                match_id = "m-" + str(uuid.uuid4())[:8]
                pitch_fee = float(body.get("pitchFee", 300000))
                drinks_fee = float(body.get("drinksFee", 0))
                default_drink = float(body.get("defaultDrinkPerPerson", 10000))
                time_slot = body.get("timeSlot", "06:00 - 07:30")
                stadium = body.get("stadiumName", "Sân bóng 6h50")

                # Validation Rule: Không cho 2 trận trùng nhau (trùng ngày, giờ)
                match_date_prefix = match_date[:10]
                cur.execute("""
                SELECT id, title, matchDate, timeSlot FROM matches 
                WHERE matchDate = ? OR (SUBSTR(matchDate, 1, 10) = ? AND timeSlot = ?)
                """, (match_date, match_date_prefix, time_slot))
                dup = cur.fetchone()
                if dup:
                    return self.send_json({
                        "error": f"Đã có trận '{dup['title']}' vào ngày {dup['matchDate'][:10]} khung giờ {dup['timeSlot']}. Không thể tạo 2 trận trùng ngày và giờ!"
                    }, 400)

                cur.execute("""
                INSERT INTO matches (id, matchDate, title, timeSlot, stadiumName, pitchFee, drinksFee, defaultDrinkPerPerson, totalCost, status, isHidden, notes, createdAt, updatedAt)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'SCHEDULED', 0, '', ?, ?)
                """, (match_id, match_date, title, time_slot, stadium, pitch_fee, drinks_fee, default_drink, pitch_fee + drinks_fee, now, now))

                # Add records for all active players
                cur.execute("SELECT id FROM players WHERE isActive = 1")
                for p in cur.fetchall():
                    rec_id = f"rec-{match_id}-{p['id']}"
                    cur.execute("""
                    INSERT INTO match_player_records (id, matchId, playerId, isPresent, hasDrinks, drinkAmount, pitchShare, feeCharged, addedDeposit, note, createdAt, updatedAt)
                    VALUES (?, ?, ?, 0, 0, 0, 0, 0, 0, '', ?, ?)
                    """, (rec_id, match_id, p["id"], now, now))

                conn.commit()
                return self.send_json({"success": True, "id": match_id}, 201)

            elif path == "/api/batch-save":
                updates = body.get("updates", [])
                for u in updates:
                    mid = u.get("matchId")
                    pid = u.get("playerId")
                    if not mid or not pid:
                        continue
                    added = float(u.get("addedDeposit", 0))
                    fee = float(u.get("feeCharged", 0))
                    if "isPresent" in u:
                        is_present = 1 if u.get("isPresent") else 0
                    else:
                        is_present = 1 if fee > 0 else 0
                    pitch_share = float(u.get("pitchShare", fee if is_present else 0))

                    rec_id = f"rec-{mid}-{pid}"
                    cur.execute("""
                    INSERT INTO match_player_records (id, matchId, playerId, isPresent, hasDrinks, drinkAmount, pitchShare, feeCharged, addedDeposit, note, createdAt, updatedAt)
                    VALUES (?, ?, ?, ?, 0, 0, ?, ?, ?, '', ?, ?)
                    ON CONFLICT(matchId, playerId) DO UPDATE SET
                        feeCharged = excluded.feeCharged,
                        pitchShare = excluded.pitchShare,
                        addedDeposit = excluded.addedDeposit,
                        isPresent = excluded.isPresent,
                        updatedAt = excluded.updatedAt
                    """, (rec_id, mid, pid, is_present, pitch_share, fee, added, now, now))

                conn.commit()
                return self.send_json({"success": True, "count": len(updates)})

            elif path == "/api/reseed":
                seed_db(conn)
                return self.send_json({"success": True, "message": "Đã reset về dữ liệu gốc ban đầu thành công!"})

            else:
                return self.send_json({"error": "Not Found"}, 404)
        finally:
            conn.close()

    def handle_api_put(self, path):
        body = self.read_body()
        conn = get_connection()
        cur = conn.cursor()
        now = datetime.now().isoformat()

        try:
            if path.startswith("/api/players/"):
                player_id = path.split("/api/players/")[1]
                name = body.get("name")
                nickname = body.get("nickname")
                phone = body.get("phoneNumber")
                initial_deposit = body.get("initialDeposit")

                cur.execute("""
                UPDATE players SET
                    name = COALESCE(?, name),
                    nickname = ?,
                    phoneNumber = COALESCE(?, phoneNumber),
                    initialDeposit = COALESCE(?, initialDeposit),
                    updatedAt = ?
                WHERE id = ?
                """, (name, nickname, phone, initial_deposit, now, player_id))
                conn.commit()
                return self.send_json({"success": True})

            elif path.startswith("/api/matches/"):
                match_id = path.split("/api/matches/")[1]
                title = body.get("title")
                match_date = body.get("matchDate")
                time_slot = body.get("timeSlot")
                stadium = body.get("stadiumName")
                pitch_fee = float(body.get("pitchFee", 0))
                drinks_fee = float(body.get("drinksFee", 0))
                default_drink = float(body.get("defaultDrinkPerPerson", 10000))
                status = body.get("status", "SCHEDULED")
                notes = body.get("notes")
                is_hidden = body.get("isHidden")

                if match_date or time_slot:
                    cur.execute("SELECT matchDate, timeSlot FROM matches WHERE id = ?", (match_id,))
                    curr = cur.fetchone()
                    if curr:
                        check_date = match_date or curr["matchDate"]
                        check_slot = time_slot or curr["timeSlot"]
                        check_prefix = check_date[:10]
                        cur.execute("""
                        SELECT id, title, matchDate, timeSlot FROM matches
                        WHERE id != ? AND (matchDate = ? OR (SUBSTR(matchDate, 1, 10) = ? AND timeSlot = ?))
                        """, (match_id, check_date, check_prefix, check_slot))
                        dup = cur.fetchone()
                        if dup:
                            return self.send_json({
                                "error": f"Trùng thời gian với trận '{dup['title']}' ({dup['matchDate'][:10]} lúc {dup['timeSlot']}). Không thể có 2 trận trùng ngày và giờ!"
                            }, 400)

                cur.execute("""
                UPDATE matches SET
                    title = COALESCE(?, title),
                    matchDate = COALESCE(?, matchDate),
                    timeSlot = COALESCE(?, timeSlot),
                    stadiumName = COALESCE(?, stadiumName),
                    pitchFee = ?,
                    drinksFee = ?,
                    defaultDrinkPerPerson = ?,
                    totalCost = ?,
                    status = COALESCE(?, status),
                    isHidden = COALESCE(?, isHidden),
                    notes = COALESCE(?, notes),
                    updatedAt = ?
                WHERE id = ?
                """, (title, match_date, time_slot, stadium, pitch_fee, drinks_fee, default_drink, pitch_fee + drinks_fee, status, is_hidden, notes, now, match_id))

                # Update player records if provided
                records = body.get("playerRecords", [])
                for r in records:
                    pid = r.get("playerId")
                    is_present = 1 if r.get("isPresent") else 0
                    has_drinks = 1 if r.get("hasDrinks") else 0
                    drink_amount = float(r.get("drinkAmount", 0))
                    pitch_share = float(r.get("pitchShare", 0))
                    fee_charged = float(r.get("feeCharged", 0))
                    added_deposit = float(r.get("addedDeposit", 0))
                    note = r.get("note", "")

                    rec_id = f"rec-{match_id}-{pid}"
                    cur.execute("""
                    INSERT INTO match_player_records (id, matchId, playerId, isPresent, hasDrinks, drinkAmount, pitchShare, feeCharged, addedDeposit, note, createdAt, updatedAt)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(matchId, playerId) DO UPDATE SET
                        isPresent = excluded.isPresent,
                        hasDrinks = excluded.hasDrinks,
                        drinkAmount = excluded.drinkAmount,
                        pitchShare = excluded.pitchShare,
                        feeCharged = excluded.feeCharged,
                        addedDeposit = excluded.addedDeposit,
                        note = excluded.note,
                        updatedAt = excluded.updatedAt
                    """, (rec_id, match_id, pid, is_present, has_drinks, drink_amount, pitch_share, fee_charged, added_deposit, note, now, now))

                conn.commit()
                return self.send_json({"success": True})

            elif path == "/api/config":
                club_name = body.get("clubName")
                bank_code = body.get("bankCode")
                bank_account = body.get("bankAccount")
                account_holder = body.get("accountHolder")
                cur.execute("""
                UPDATE club_config SET
                    clubName = COALESCE(?, clubName),
                    bankCode = COALESCE(?, bankCode),
                    bankAccount = COALESCE(?, bankAccount),
                    accountHolder = COALESCE(?, accountHolder)
                WHERE id = 'default'
                """, (club_name, bank_code, bank_account, account_holder))
                conn.commit()
                return self.send_json({"success": True})

            else:
                return self.send_json({"error": "Not Found"}, 404)
        finally:
            conn.close()

    def handle_api_delete(self, path):
        conn = get_connection()
        cur = conn.cursor()

        try:
            if path.startswith("/api/players/"):
                player_id = path.split("/api/players/")[1]
                cur.execute("DELETE FROM match_player_records WHERE playerId = ?", (player_id,))
                cur.execute("DELETE FROM players WHERE id = ?", (player_id,))
                conn.commit()
                return self.send_json({"success": True, "message": "Đã xóa thành viên"})

            elif path.startswith("/api/matches/"):
                match_id = path.split("/api/matches/")[1]
                cur.execute("DELETE FROM match_player_records WHERE matchId = ?", (match_id,))
                cur.execute("DELETE FROM matches WHERE id = ?", (match_id,))
                conn.commit()
                return self.send_json({"success": True, "message": "Đã xóa trận đấu"})

            elif path.startswith("/api/deposits/"):
                dep_id = path.split("/api/deposits/")[1]
                cur.execute("DELETE FROM deposit_transactions WHERE id = ?", (dep_id,))
                conn.commit()
                return self.send_json({"success": True, "message": "Đã xóa giao dịch nạp quỹ"})

            else:
                return self.send_json({"error": "Not Found"}, 404)
        finally:
            conn.close()

def run():
    init_db()
    os.makedirs(PUBLIC_DIR, exist_ok=True)
    server_address = ("0.0.0.0", PORT)
    
    # Allow socket reuse so restart doesn't get Address already in use
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(server_address, FCRequestHandler) as httpd:
        print("==================================================")
        print("FC 6H SANG CHU NHAT - WEB SERVER RUNNING AT:")
        print(f"-> Desktop PC:   http://localhost:{PORT}")
        print(f"-> Mobile Phone: http://172.18.60.233:{PORT}")
        print("==================================================")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nStopping server...")
            httpd.server_close()

if __name__ == "__main__":
    run()
