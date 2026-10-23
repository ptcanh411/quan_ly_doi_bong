import http.server
import socketserver
import json
import urllib.parse
import os
import uuid
import sys
import io
import secrets
import hmac
import time
import threading
from datetime import datetime, timedelta
import sqlite3
from db import get_connection, init_db, seed_db

PORT = int(os.environ.get("PORT", 8000))
PUBLIC_DIR = os.path.join(os.path.dirname(__file__), "public")
DEFAULT_ADMIN_PASSWORD = "ptcanh411"
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", DEFAULT_ADMIN_PASSWORD)

MAX_BODY_BYTES = 10 * 1024 * 1024      # Giới hạn body request (đủ cho file backup JSON)
MAX_DEPOSIT_AMOUNT = 100_000_000       # Chặn số tiền nạp phi lý (100 triệu)

# ---------------- Chống brute-force đăng nhập Admin ----------------
LOGIN_MAX_FAILS_PER_IP = 5
LOGIN_MAX_FAILS_GLOBAL = 30
LOGIN_WINDOW_SECONDS = 300
_login_fails = {}                      # ip -> [timestamps thất bại]
_login_lock = threading.Lock()


def get_client_ip(handler):
    """IP client, dùng chung cho server.py (client_address) và wsgi.py (environ)."""
    fwd = handler.get_header("X-Forwarded-For")
    if fwd:
        return fwd.split(",")[0].strip()
    addr = getattr(handler, "client_address", None)
    if addr:
        return addr[0]
    env = getattr(handler, "environ", None)
    if env:
        return env.get("REMOTE_ADDR", "unknown")
    return "unknown"


def _recent_fails(ip, now):
    fails = [t for t in _login_fails.get(ip, []) if now - t < LOGIN_WINDOW_SECONDS]
    if fails:
        _login_fails[ip] = fails
    else:
        _login_fails.pop(ip, None)
    return fails


def login_blocked(ip):
    now = time.time()
    with _login_lock:
        if len(_recent_fails(ip, now)) >= LOGIN_MAX_FAILS_PER_IP:
            return True
        total = sum(len(_recent_fails(k, now)) for k in list(_login_fails.keys()))
        return total >= LOGIN_MAX_FAILS_GLOBAL


def record_login_fail(ip):
    with _login_lock:
        _login_fails.setdefault(ip, []).append(time.time())


def clear_login_fails(ip):
    with _login_lock:
        _login_fails.pop(ip, None)

def is_admin_request(handler):
    token = handler.get_header("X-Admin-Token")
    if not token:
        auth_header = handler.get_header("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()
    if not token:
        return False
    
    conn = get_connection()
    cur = conn.cursor()
    try:
        now_iso = datetime.now().isoformat()
        cur.execute("SELECT token FROM admin_tokens WHERE token = ? AND (expiresAt IS NULL OR expiresAt > ?)", (token, now_iso))
        row = cur.fetchone()
        return bool(row)
    except Exception:
        return False
    finally:
        conn.close()

def require_admin(handler):
    if not is_admin_request(handler):
        handler.send_json({"error": "Yêu cầu quyền Admin (Thủ quỹ). Vui lòng đăng nhập lại."}, 401)
        return False
    return True

class ThreadingHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True

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
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Admin-Token, Authorization")

    def send_json(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_cors_headers()
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

    def get_header(self, name, default=None):
        if hasattr(self, "headers") and self.headers:
            return self.headers.get(name, default)
        return default

    def read_body(self):
        try:
            content_length = int(self.headers.get("Content-Length", 0))
        except (ValueError, TypeError):
            content_length = 0
        if content_length <= 0 or content_length > MAX_BODY_BYTES:
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
                cur.execute("SELECT * FROM players WHERE isActive = 1 ORDER BY displayOrder ASC")
                players = [dict(row) for row in cur.fetchall()]

                cur.execute("SELECT * FROM match_player_records")
                records = [dict(row) for row in cur.fetchall()]

                records_by_player = {}
                for r in records:
                    pid = r["playerId"]
                    if pid not in records_by_player:
                        records_by_player[pid] = {}
                    records_by_player[pid][r["matchId"]] = r

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

            elif path.startswith("/api/deposit-requests"):
                cur.execute("""
                SELECT r.*, p.name as playerName, p.nickname as playerNickname
                FROM deposit_requests r
                JOIN players p ON r.playerId = p.id
                ORDER BY CASE WHEN r.status = 'PENDING' THEN 0 ELSE 1 END, r.createdAt DESC
                """)
                return self.send_json([dict(row) for row in cur.fetchall()])

            elif path == "/api/matches":
                cur.execute("SELECT * FROM matches ORDER BY matchDate ASC")
                matches = [dict(row) for row in cur.fetchall()]

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

            elif path == "/api/auth/verify":
                is_admin = is_admin_request(self)
                return self.send_json({"valid": is_admin, "role": "admin" if is_admin else "user"})

            elif path == "/api/backup":
                if not require_admin(self):
                    return
                backup_data = {
                    "version": 1,
                    "exportedAt": datetime.now().isoformat(),
                    "club_config": [dict(r) for r in cur.execute("SELECT * FROM club_config").fetchall()],
                    "players": [dict(r) for r in cur.execute("SELECT * FROM players").fetchall()],
                    "matches": [dict(r) for r in cur.execute("SELECT * FROM matches").fetchall()],
                    "match_player_records": [dict(r) for r in cur.execute("SELECT * FROM match_player_records").fetchall()],
                    "deposit_transactions": [dict(r) for r in cur.execute("SELECT * FROM deposit_transactions").fetchall()],
                    "deposit_requests": [dict(r) for r in cur.execute("SELECT * FROM deposit_requests").fetchall()],
                }
                return self.send_json(backup_data)

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
            # 1. Admin Authentication Login
            if path == "/api/auth/login":
                ip = get_client_ip(self)
                if login_blocked(ip):
                    return self.send_json({"error": "Đăng nhập sai quá nhiều lần. Vui lòng thử lại sau 5 phút."}, 429)

                pwd = (body.get("password") or "").strip()
                if hmac.compare_digest(pwd.encode("utf-8"), ADMIN_PASSWORD.encode("utf-8")):
                    clear_login_fails(ip)
                    # Dọn các token đã hết hạn (garbage collection)
                    cur.execute("DELETE FROM admin_tokens WHERE expiresAt IS NOT NULL AND expiresAt <= ?", (now,))
                    token = "tok-" + secrets.token_hex(24)
                    expires = (datetime.now() + timedelta(days=30)).isoformat()
                    cur.execute("INSERT INTO admin_tokens (token, createdAt, expiresAt) VALUES (?, ?, ?)", (token, now, expires))
                    conn.commit()
                    return self.send_json({
                        "success": True,
                        "token": token,
                        "role": "admin",
                        "message": "Đăng nhập Admin thành công!"
                    })
                else:
                    record_login_fail(ip)
                    return self.send_json({"error": "Mật khẩu Admin không chính xác!"}, 401)

            elif path == "/api/auth/logout":
                token = self.get_header("X-Admin-Token") or body.get("token")
                if token:
                    cur.execute("DELETE FROM admin_tokens WHERE token = ?", (token,))
                    conn.commit()
                return self.send_json({"success": True, "message": "Đã đăng xuất"})

            # 2. Player Deposit Requests (Public to all members)
            elif path == "/api/deposit-requests":
                player_id = body.get("playerId")
                amount = float(body.get("amount", 0))
                note = (body.get("note") or "").strip()[:200] or "Chuyển khoản nạp quỹ"
                deposit_date = body.get("depositDate") or now[:10]

                if not player_id or amount <= 0 or amount > MAX_DEPOSIT_AMOUNT:
                    return self.send_json({"error": "Vui lòng chọn thành viên và số tiền nạp hợp lệ"}, 400)

                cur.execute("SELECT id FROM players WHERE id = ? AND isActive = 1", (player_id,))
                if not cur.fetchone():
                    return self.send_json({"error": "Thành viên không tồn tại"}, 400)
                req_id = "req-" + str(uuid.uuid4())[:8]
                cur.execute("""
                INSERT INTO deposit_requests (id, playerId, amount, depositDate, note, status, createdAt)
                VALUES (?, ?, ?, ?, ?, 'PENDING', ?)
                """, (req_id, player_id, amount, deposit_date, note, now))
                conn.commit()
                return self.send_json({
                    "success": True,
                    "id": req_id,
                    "message": "Đã gửi thông báo chuyển khoản! Chờ Thủ quỹ tick duyệt."
                }, 201)

            elif path.startswith("/api/deposit-requests/") and path.endswith("/approve"):
                if not require_admin(self):
                    return
                req_id = path.split("/api/deposit-requests/")[1].split("/approve")[0]
                cur.execute("SELECT * FROM deposit_requests WHERE id = ?", (req_id,))
                req = cur.fetchone()
                if not req:
                    return self.send_json({"error": "Yêu cầu không tồn tại"}, 404)

                if req["status"] != "PENDING":
                    return self.send_json({"error": "Yêu cầu này đã được xử lý trước đó!"}, 400)

                dep_id = "dep-" + str(uuid.uuid4())[:8]
                cur.execute("""
                INSERT INTO deposit_transactions (id, playerId, amount, depositDate, note, createdAt)
                VALUES (?, ?, ?, ?, ?, ?)
                """, (dep_id, req["playerId"], req["amount"], req["depositDate"], req["note"], now))

                cur.execute("UPDATE deposit_requests SET status = 'APPROVED', reviewedAt = ? WHERE id = ?", (now, req_id))
                conn.commit()
                return self.send_json({"success": True, "message": f"Đã duyệt nạp quỹ +{req['amount']:,.0f}đ thành công!"})

            elif path.startswith("/api/deposit-requests/") and path.endswith("/reject"):
                if not require_admin(self):
                    return
                req_id = path.split("/api/deposit-requests/")[1].split("/reject")[0]
                cur.execute("UPDATE deposit_requests SET status = 'REJECTED', reviewedAt = ? WHERE id = ?", (now, req_id))
                conn.commit()
                return self.send_json({"success": True, "message": "Đã từ chối yêu cầu chuyển khoản"})

            # 3. Protected Operations (Require Admin)
            elif path == "/api/players":
                if not require_admin(self):
                    return
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
                if not require_admin(self):
                    return
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
                if not require_admin(self):
                    return
                auto_next = body.get("autoNextSunday", False)
                title = body.get("title", "").strip()
                match_date = body.get("matchDate")

                if auto_next or not match_date:
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
                if not require_admin(self):
                    return
                updates = body.get("updates", [])
                if not isinstance(updates, list):
                    return self.send_json({"error": "Dữ liệu cập nhật không hợp lệ"}, 400)
                try:
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
                except (ValueError, TypeError, sqlite3.Error) as e:
                    conn.rollback()
                    return self.send_json({"error": f"Lưu thất bại, đã hoàn tác toàn bộ thay đổi: {e}"}, 400)
                return self.send_json({"success": True, "count": len(updates)})

            elif path == "/api/reseed":
                if not require_admin(self):
                    return
                seed_db(conn)
                return self.send_json({"success": True, "message": "Đã reset về dữ liệu gốc ban đầu thành công!"})

            elif path == "/api/restore":
                if not require_admin(self):
                    return
                data = body.get("data") or body
                if not isinstance(data, dict) or "players" not in data or "matches" not in data:
                    return self.send_json({"error": "Dữ liệu sao lưu không đúng định dạng!"}, 400)

                cur.execute("DELETE FROM match_player_records")
                cur.execute("DELETE FROM deposit_requests")
                cur.execute("DELETE FROM deposit_transactions")
                cur.execute("DELETE FROM matches")
                cur.execute("DELETE FROM players")
                cur.execute("DELETE FROM club_config")

                for c in data.get("club_config", []):
                    cur.execute("INSERT INTO club_config (id, clubName, bankCode, bankAccount, accountHolder, defaultTimeSlot) VALUES (?, ?, ?, ?, ?, ?)",
                                (c.get("id", "default"), c.get("clubName"), c.get("bankCode"), c.get("bankAccount"), c.get("accountHolder"), c.get("defaultTimeSlot")))

                for p in data.get("players", []):
                    cur.execute("INSERT INTO players (id, name, nickname, phoneNumber, initialDeposit, isActive, displayOrder, createdAt, updatedAt) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                                (p["id"], p["name"], p.get("nickname"), p.get("phoneNumber"), p.get("initialDeposit", 0), p.get("isActive", 1), p.get("displayOrder", 0), p.get("createdAt"), p.get("updatedAt")))

                for m in data.get("matches", []):
                    cur.execute("INSERT INTO matches (id, matchDate, title, timeSlot, stadiumName, pitchFee, drinksFee, defaultDrinkPerPerson, totalCost, status, isHidden, notes, createdAt, updatedAt) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                                (m["id"], m["matchDate"], m.get("title"), m.get("timeSlot"), m.get("stadiumName"), m.get("pitchFee", 0), m.get("drinksFee", 0), m.get("defaultDrinkPerPerson", 10000), m.get("totalCost", 0), m.get("status", "SCHEDULED"), m.get("isHidden", 0), m.get("notes"), m.get("createdAt"), m.get("updatedAt")))

                for r in data.get("match_player_records", []):
                    cur.execute("INSERT INTO match_player_records (id, matchId, playerId, isPresent, hasDrinks, drinkAmount, pitchShare, feeCharged, addedDeposit, note, createdAt, updatedAt) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                                (r["id"], r["matchId"], r["playerId"], r.get("isPresent", 0), r.get("hasDrinks", 0), r.get("drinkAmount", 0), r.get("pitchShare", 0), r.get("feeCharged", 0), r.get("addedDeposit", 0), r.get("note"), r.get("createdAt"), r.get("updatedAt")))

                for d in data.get("deposit_transactions", []):
                    cur.execute("INSERT INTO deposit_transactions (id, playerId, amount, depositDate, note, createdAt) VALUES (?, ?, ?, ?, ?, ?)",
                                (d["id"], d["playerId"], d["amount"], d["depositDate"], d.get("note"), d.get("createdAt")))

                for dr in data.get("deposit_requests", []):
                    cur.execute("INSERT INTO deposit_requests (id, playerId, amount, depositDate, note, status, createdAt, reviewedAt) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                                (dr["id"], dr["playerId"], dr["amount"], dr["depositDate"], dr.get("note"), dr.get("status", "PENDING"), dr.get("createdAt"), dr.get("reviewedAt")))

                conn.commit()
                return self.send_json({"success": True, "message": "Đã khôi phục toàn bộ cơ sở dữ liệu thành công!"})

            else:
                return self.send_json({"error": "Not Found"}, 404)
        except (KeyError, TypeError, ValueError, sqlite3.Error) as e:
            conn.rollback()
            return self.send_json({"error": f"Dữ liệu không hợp lệ hoặc lỗi xử lý, đã hoàn tác thay đổi: {e}"}, 400)
        finally:
            conn.close()

    def handle_api_put(self, path):
        if not require_admin(self):
            return
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
        except (KeyError, TypeError, ValueError, sqlite3.Error) as e:
            conn.rollback()
            return self.send_json({"error": f"Dữ liệu không hợp lệ hoặc lỗi xử lý, đã hoàn tác thay đổi: {e}"}, 400)
        finally:
            conn.close()

    def handle_api_delete(self, path):
        if not require_admin(self):
            return
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

            elif path.startswith("/api/deposit-requests/"):
                req_id = path.split("/api/deposit-requests/")[1]
                cur.execute("DELETE FROM deposit_requests WHERE id = ?", (req_id,))
                conn.commit()
                return self.send_json({"success": True, "message": "Đã xóa yêu cầu nạp quỹ"})

            else:
                return self.send_json({"error": "Not Found"}, 404)
        finally:
            conn.close()

def run():
    init_db()
    os.makedirs(PUBLIC_DIR, exist_ok=True)
    if ADMIN_PASSWORD == DEFAULT_ADMIN_PASSWORD:
        print("[CẢNH BÁO] Đang dùng mật khẩu Admin mặc định. Hãy đặt biến môi trường ADMIN_PASSWORD trước khi đưa lên mạng!")
    server_address = ("0.0.0.0", PORT)
    
    with ThreadingHTTPServer(server_address, FCRequestHandler) as httpd:
        print("==================================================")
        print("FC 6H SANG CHU NHAT - MULTI-THREADED SERVER READY")
        print(f"-> Desktop PC:   http://localhost:{PORT}")
        print("==================================================")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nStopping server...")
            httpd.server_close()

if __name__ == "__main__":
    run()
