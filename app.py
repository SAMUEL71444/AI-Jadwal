"""
FLOWIA OS — app.py (PostgreSQL version)
Flask backend untuk dashboard Koman (Binus Cybersecurity)
"""

import json
import os
import subprocess
from datetime import datetime, date
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import psycopg2
from psycopg2.extras import RealDictCursor

# ─── INISIALISASI ─────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__, static_folder=os.path.join(BASE_DIR, 'static'), static_url_path='')
CORS(app)

DATABASE_URL = os.environ.get('DATABASE_URL')

# ─── DATABASE CONNECTION ──────────────────────────────────────────────────────
def get_conn():
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)

def init_db():
    """Buat semua tabel kalau belum ada."""
    conn = get_conn()
    cur  = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS tugas (
            id        SERIAL PRIMARY KEY,
            nama      TEXT NOT NULL,
            matkul    TEXT,
            deadline  TEXT,
            catatan   TEXT,
            prioritas TEXT DEFAULT 'normal',
            selesai   BOOLEAN DEFAULT FALSE,
            dibuat    TEXT,
            selesai_pada TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id         TEXT PRIMARY KEY,
            nama       TEXT NOT NULL,
            kategori   TEXT,
            deadline   TEXT,
            status     TEXT DEFAULT 'aktif',
            peran      TEXT,
            tim        TEXT,
            deskripsi  TEXT,
            milestones TEXT DEFAULT '[]',
            catatan    TEXT,
            dibuat     TEXT,
            selesai    BOOLEAN DEFAULT FALSE,
            hasil      TEXT,
            selesai_pada TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS goals (
            id             TEXT PRIMARY KEY,
            nama           TEXT NOT NULL,
            kategori       TEXT,
            deadline       TEXT,
            progress       INTEGER DEFAULT 0,
            deskripsi      TEXT,
            milestones     TEXT DEFAULT '[]',
            linked_events  TEXT DEFAULT '[]',
            catatan        TEXT,
            dibuat         TEXT,
            selesai        BOOLEAN DEFAULT FALSE,
            selesai_pada   TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS ideas (
            id           TEXT PRIMARY KEY,
            judul        TEXT NOT NULL,
            konten       TEXT,
            tags         TEXT DEFAULT '[]',
            kategori     TEXT DEFAULT 'umum',
            dibuat       TEXT,
            diupdate     TEXT,
            linked_goal  TEXT,
            favorit      BOOLEAN DEFAULT FALSE
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS notes (
            id      TEXT PRIMARY KEY,
            konten  TEXT NOT NULL,
            dibuat  TEXT,
            selesai BOOLEAN DEFAULT FALSE
        )
    """)

    conn.commit()
    cur.close()
    conn.close()

# ─── JADWAL KULIAH ────────────────────────────────────────────────────────────
JADWAL = {
    "Senin": [
        {"mata_kuliah": "Software Engineering (LS01)",              "jam": "09.20-11.00", "ruang": "Anggrek - 403"},
        {"mata_kuliah": "Software Engineering (LS01)",              "jam": "11.20-13.00", "ruang": "Anggrek - 403"},
        {"mata_kuliah": "Server and Network Administration (LC07)", "jam": "13.20-15.00", "ruang": "Anggrek - 504"},
    ],
    "Selasa": [
        {"mata_kuliah": "Cyber Law (LC07)",            "jam": "09.20-11.00", "ruang": "Syahdan - L3B"},
        {"mata_kuliah": "Software Security (LC07)",    "jam": "11.20-13.00", "ruang": "Anggrek - 406"},
        {"mata_kuliah": "Research Methodology (LS01)", "jam": "13.20-15.00", "ruang": "Anggrek - 514"},
    ],
    "Rabu": [
        {"mata_kuliah": "Research Methodology (LS01)", "jam": "15.20-17.00", "ruang": "Anggrek - 514"},
    ],
    "Kamis": [
        {"mata_kuliah": "Mobile Penetration Testing (LC07)", "jam": "11.20-13.00", "ruang": "Anggrek - 709"},
        {"mata_kuliah": "Mobile Penetration Testing (BE07)", "jam": "13.20-15.00", "ruang": "Anggrek - 708"},
        {"mata_kuliah": "Software Engineering (TS01)",       "jam": "15.20-17.00", "ruang": "Anggrek - 403"},
    ],
    "Jumat":  [],
    "Sabtu": [
        {"mata_kuliah": "Computational Biology (LA05)", "jam": "11.20-13.00", "ruang": "Anggrek - 502"},
        {"mata_kuliah": "Computational Biology (BA05)", "jam": "13.20-15.00", "ruang": "Anggrek - 601"},
    ],
    "Minggu": [],
}

# ─── SYSTEM PROMPTS ───────────────────────────────────────────────────────────
SYSTEM_PROMPTS = {
    "general": None,
    "lomba_ai": "Kamu adalah mentor kompetisi AI/ML berpengalaman. Bantu Koman analisis problem statement lomba, brainstorm pendekatan teknis, dan identifikasi risiko. Fokus pada solusi yang bisa diimplementasi dalam waktu lomba.",
    "bisnis":   "Kamu adalah advisor bisnis yang kritis. Jadilah devil's advocate untuk ide Koman. Pertanyakan asumsi, identifikasi lubang di model bisnis, tanya soal target pasar dan monetisasi.",
    "riset":    "Kamu adalah pembimbing riset akademik. Bantu Koman strukturkan argumen, identifikasi gap di literatur, dan pastikan metodologi solid.",
    "ctf":      "Kamu adalah mentor CTF. Bantu Koman breakdown challenge, identifikasi kategori, dan berpikir step-by-step tentang attack vector. Jangan kasih jawaban langsung.",
    "planner":  "Kamu adalah personal planner Koman. Dia mahasiswa Cybersecurity Binus yang aktif lomba AI, riset, dan bisnis. Bantu prioritaskan task dan buat rencana eksekusi realistis.",
}

# ─── HELPERS ─────────────────────────────────────────────────────────────────
def hitung_sisa_hari(deadline_str):
    if not deadline_str:
        return None
    try:
        d = datetime.strptime(deadline_str.strip(), "%d/%m/%Y").date()
        return (d - date.today()).days
    except:
        return None

def generate_id(prefix):
    return f"{prefix}_{datetime.now().strftime('%Y%m%d%H%M%S%f')[:18]}"

def now_str():
    return datetime.now().strftime("%d/%m/%Y %H:%M")

def today_str():
    return datetime.now().strftime("%d/%m/%Y")

def hari_ini():
    days = ['Senin','Selasa','Rabu','Kamis','Jumat','Sabtu','Minggu']
    return days[datetime.now().weekday()]

def row_to_dict(row):
    """Convert psycopg2 RealDictRow to plain dict."""
    if row is None:
        return None
    d = dict(row)
    # Parse JSON fields yang disimpan sebagai string
    for field in ['milestones', 'linked_events', 'tags', 'tim']:
        if field in d and isinstance(d[field], str):
            try:
                d[field] = json.loads(d[field])
            except:
                d[field] = []
    return d

# ─── SERVE FRONTEND ───────────────────────────────────────────────────────────
@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

# ─────────────────────────────────────────────────────────────────────────────
# JADWAL
# ─────────────────────────────────────────────────────────────────────────────
@app.route('/api/jadwal')
def get_jadwal():
    hari = request.args.get('hari', hari_ini())
    return jsonify(JADWAL.get(hari, []))

# ─────────────────────────────────────────────────────────────────────────────
# TUGAS
# ─────────────────────────────────────────────────────────────────────────────
@app.route('/api/tugas', methods=['GET'])
def get_tugas():
    conn = get_conn(); cur = conn.cursor()
    cur.execute("SELECT * FROM tugas WHERE selesai=FALSE ORDER BY id")
    rows = [dict(r) for r in cur.fetchall()]
    cur.close(); conn.close()
    for t in rows:
        t['sisa_hari'] = hitung_sisa_hari(t.get('deadline'))
    return jsonify(rows)

@app.route('/api/tugas/selesai', methods=['GET'])
def get_tugas_selesai():
    conn = get_conn(); cur = conn.cursor()
    cur.execute("SELECT * FROM tugas WHERE selesai=TRUE ORDER BY id DESC")
    rows = [dict(r) for r in cur.fetchall()]
    cur.close(); conn.close()
    return jsonify(rows)

@app.route('/api/tugas', methods=['POST'])
def add_tugas():
    body = request.get_json(silent=True) or {}
    nama = body.get('nama','').strip()
    if not nama:
        return jsonify({'ok': False, 'msg': 'Nama tugas wajib'}), 400
    conn = get_conn(); cur = conn.cursor()
    cur.execute("""
        INSERT INTO tugas (nama, matkul, deadline, catatan, prioritas, selesai, dibuat)
        VALUES (%s, %s, %s, %s, %s, FALSE, %s)
    """, (nama, body.get('matkul',''), body.get('deadline',''),
          body.get('catatan',''), body.get('prioritas','normal'), now_str()))
    conn.commit(); cur.close(); conn.close()
    return jsonify({'ok': True, 'msg': 'Tugas ditambahkan'}), 201

@app.route('/api/tugas/<nama>/selesai', methods=['POST'])
def selesai_tugas(nama):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("UPDATE tugas SET selesai=TRUE, selesai_pada=%s WHERE nama=%s AND selesai=FALSE",
                (now_str(), nama))
    found = cur.rowcount > 0
    conn.commit(); cur.close(); conn.close()
    if found:
        return jsonify({'ok': True})
    return jsonify({'ok': False, 'msg': 'Tugas tidak ditemukan'}), 404

@app.route('/api/tugas/<nama>', methods=['DELETE'])
def hapus_tugas(nama):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("DELETE FROM tugas WHERE nama=%s", (nama,))
    found = cur.rowcount > 0
    conn.commit(); cur.close(); conn.close()
    if found:
        return jsonify({'ok': True})
    return jsonify({'ok': False, 'msg': 'Tidak ditemukan'}), 404

@app.route('/api/stats')
def get_stats():
    conn = get_conn(); cur = conn.cursor()
    cur.execute("SELECT * FROM tugas WHERE selesai=FALSE")
    aktif = [dict(r) for r in cur.fetchall()]
    cur.execute("SELECT COUNT(*) as c FROM tugas WHERE selesai=TRUE")
    selesai_count = cur.fetchone()['c']
    cur.close(); conn.close()
    for t in aktif:
        t['sisa_hari'] = hitung_sisa_hari(t.get('deadline'))
    mendesak = sum(1 for t in aktif if t['sisa_hari'] is not None and t['sisa_hari'] <= 3)
    per_matkul = {}
    for t in aktif:
        mk = t.get('matkul') or 'Lainnya'
        per_matkul[mk] = per_matkul.get(mk, 0) + 1
    return jsonify({'total_aktif': len(aktif), 'total_selesai': selesai_count,
                    'mendesak': mendesak, 'per_matkul': per_matkul})

@app.route('/api/matkul')
def get_matkul():
    conn = get_conn(); cur = conn.cursor()
    cur.execute("SELECT DISTINCT matkul FROM tugas WHERE matkul IS NOT NULL AND matkul != ''")
    rows = [r['matkul'] for r in cur.fetchall()]
    cur.close(); conn.close()
    return jsonify(sorted(rows))

# ─────────────────────────────────────────────────────────────────────────────
# EVENTS
# ─────────────────────────────────────────────────────────────────────────────
@app.route('/api/events', methods=['GET'])
def get_events():
    conn = get_conn(); cur = conn.cursor()
    cur.execute("SELECT * FROM events WHERE selesai=FALSE ORDER BY deadline")
    rows = [row_to_dict(r) for r in cur.fetchall()]
    cur.close(); conn.close()
    for e in rows:
        e['sisa_hari'] = hitung_sisa_hari(e.get('deadline'))
        for ms in e.get('milestones', []):
            ms['sisa_hari'] = hitung_sisa_hari(ms.get('deadline'))
    return jsonify(rows)

@app.route('/api/events', methods=['POST'])
def add_event():
    body = request.get_json(silent=True) or {}
    nama = body.get('nama','').strip()
    if not nama:
        return jsonify({'ok': False, 'msg': 'Nama event wajib'}), 400
    tim_raw = body.get('tim','')
    tim = tim_raw if isinstance(tim_raw, list) else [x.strip() for x in tim_raw.split(',') if x.strip()]
    eid = generate_id('evt')
    conn = get_conn(); cur = conn.cursor()
    cur.execute("""
        INSERT INTO events (id, nama, kategori, deadline, status, peran, tim, deskripsi, milestones, catatan, dibuat, selesai, hasil)
        VALUES (%s,%s,%s,%s,'aktif',%s,%s,%s,'[]',%s,%s,FALSE,'')
    """, (eid, nama, body.get('kategori','deadline_penting'), body.get('deadline',''),
          body.get('peran',''), json.dumps(tim), body.get('deskripsi',''),
          body.get('catatan',''), now_str()))
    conn.commit(); cur.close(); conn.close()
    return jsonify({'ok': True, 'msg': 'Event ditambahkan', 'id': eid}), 201

@app.route('/api/events/<eid>', methods=['PUT'])
def update_event(eid):
    body = request.get_json(silent=True) or {}
    conn = get_conn(); cur = conn.cursor()
    tim_raw = body.get('tim','')
    tim = tim_raw if isinstance(tim_raw, list) else [x.strip() for x in tim_raw.split(',') if x.strip()]
    cur.execute("""
        UPDATE events SET nama=%s, kategori=%s, deadline=%s, peran=%s, tim=%s, deskripsi=%s, catatan=%s
        WHERE id=%s
    """, (body.get('nama',''), body.get('kategori',''), body.get('deadline',''),
          body.get('peran',''), json.dumps(tim), body.get('deskripsi',''),
          body.get('catatan',''), eid))
    found = cur.rowcount > 0
    conn.commit(); cur.close(); conn.close()
    if found:
        return jsonify({'ok': True})
    return jsonify({'ok': False, 'msg': 'Event tidak ditemukan'}), 404

@app.route('/api/events/<eid>', methods=['DELETE'])
def hapus_event(eid):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("DELETE FROM events WHERE id=%s", (eid,))
    found = cur.rowcount > 0
    conn.commit(); cur.close(); conn.close()
    if found:
        return jsonify({'ok': True})
    return jsonify({'ok': False, 'msg': 'Tidak ditemukan'}), 404

@app.route('/api/events/<eid>/selesai', methods=['POST'])
def selesai_event(eid):
    body = request.get_json(silent=True) or {}
    conn = get_conn(); cur = conn.cursor()
    cur.execute("UPDATE events SET selesai=TRUE, status='selesai', hasil=%s, selesai_pada=%s WHERE id=%s",
                (body.get('hasil',''), now_str(), eid))
    found = cur.rowcount > 0
    conn.commit(); cur.close(); conn.close()
    if found:
        return jsonify({'ok': True})
    return jsonify({'ok': False, 'msg': 'Tidak ditemukan'}), 404

@app.route('/api/events/<eid>/milestone', methods=['POST'])
def add_milestone(eid):
    body = request.get_json(silent=True) or {}
    nama = body.get('nama','').strip()
    if not nama:
        return jsonify({'ok': False, 'msg': 'Nama milestone wajib'}), 400
    conn = get_conn(); cur = conn.cursor()
    cur.execute("SELECT milestones FROM events WHERE id=%s", (eid,))
    row = cur.fetchone()
    if not row:
        cur.close(); conn.close()
        return jsonify({'ok': False, 'msg': 'Event tidak ditemukan'}), 404
    ms = json.loads(row['milestones']) if isinstance(row['milestones'], str) else row['milestones']
    ms.append({'nama': nama, 'deadline': body.get('deadline',''), 'selesai': False})
    cur.execute("UPDATE events SET milestones=%s WHERE id=%s", (json.dumps(ms), eid))
    conn.commit(); cur.close(); conn.close()
    return jsonify({'ok': True})

@app.route('/api/events/<eid>/milestone/<int:idx>/selesai', methods=['POST'])
def toggle_milestone(eid, idx):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("SELECT milestones FROM events WHERE id=%s", (eid,))
    row = cur.fetchone()
    if not row:
        cur.close(); conn.close()
        return jsonify({'ok': False, 'msg': 'Tidak ditemukan'}), 404
    ms = json.loads(row['milestones']) if isinstance(row['milestones'], str) else row['milestones']
    if idx >= len(ms):
        cur.close(); conn.close()
        return jsonify({'ok': False, 'msg': 'Index salah'}), 400
    ms[idx]['selesai'] = not ms[idx]['selesai']
    cur.execute("UPDATE events SET milestones=%s WHERE id=%s", (json.dumps(ms), eid))
    conn.commit(); cur.close(); conn.close()
    return jsonify({'ok': True, 'selesai': ms[idx]['selesai']})

@app.route('/api/events/stats')
def stats_events():
    conn = get_conn(); cur = conn.cursor()
    cur.execute("SELECT kategori FROM events WHERE selesai=FALSE")
    rows = cur.fetchall()
    cur.close(); conn.close()
    per_kat = {}
    for r in rows:
        k = r['kategori'] or 'lainnya'
        per_kat[k] = per_kat.get(k, 0) + 1
    return jsonify({'total_aktif': len(rows), 'per_kategori': per_kat})

# ─────────────────────────────────────────────────────────────────────────────
# GOALS
# ─────────────────────────────────────────────────────────────────────────────
@app.route('/api/goals', methods=['GET'])
def get_goals():
    conn = get_conn(); cur = conn.cursor()
    cur.execute("SELECT * FROM goals WHERE selesai=FALSE ORDER BY progress DESC")
    rows = [row_to_dict(r) for r in cur.fetchall()]
    cur.close(); conn.close()
    return jsonify(rows)

@app.route('/api/goals', methods=['POST'])
def add_goal():
    body = request.get_json(silent=True) or {}
    nama = body.get('nama','').strip()
    if not nama:
        return jsonify({'ok': False, 'msg': 'Nama goal wajib'}), 400
    gid = generate_id('goal')
    conn = get_conn(); cur = conn.cursor()
    cur.execute("""
        INSERT INTO goals (id, nama, kategori, deadline, progress, deskripsi, milestones, linked_events, catatan, dibuat, selesai)
        VALUES (%s,%s,%s,%s,%s,%s,'[]','[]',%s,%s,FALSE)
    """, (gid, nama, body.get('kategori','personal'), body.get('deadline',''),
          int(body.get('progress',0)), body.get('deskripsi',''),
          body.get('catatan',''), today_str()))
    conn.commit(); cur.close(); conn.close()
    return jsonify({'ok': True, 'id': gid}), 201

@app.route('/api/goals/<gid>', methods=['PUT'])
def update_goal(gid):
    body = request.get_json(silent=True) or {}
    conn = get_conn(); cur = conn.cursor()
    cur.execute("""
        UPDATE goals SET nama=%s, kategori=%s, deadline=%s, progress=%s, deskripsi=%s, catatan=%s
        WHERE id=%s
    """, (body.get('nama',''), body.get('kategori',''), body.get('deadline',''),
          max(0, min(100, int(body.get('progress',0)))),
          body.get('deskripsi',''), body.get('catatan',''), gid))
    found = cur.rowcount > 0
    conn.commit(); cur.close(); conn.close()
    if found:
        return jsonify({'ok': True})
    return jsonify({'ok': False, 'msg': 'Tidak ditemukan'}), 404

@app.route('/api/goals/<gid>', methods=['DELETE'])
def hapus_goal(gid):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("DELETE FROM goals WHERE id=%s", (gid,))
    found = cur.rowcount > 0
    conn.commit(); cur.close(); conn.close()
    if found:
        return jsonify({'ok': True})
    return jsonify({'ok': False, 'msg': 'Tidak ditemukan'}), 404

@app.route('/api/goals/<gid>/selesai', methods=['POST'])
def selesai_goal(gid):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("UPDATE goals SET selesai=TRUE, progress=100, selesai_pada=%s WHERE id=%s",
                (today_str(), gid))
    found = cur.rowcount > 0
    conn.commit(); cur.close(); conn.close()
    if found:
        return jsonify({'ok': True})
    return jsonify({'ok': False, 'msg': 'Tidak ditemukan'}), 404

@app.route('/api/goals/<gid>/milestone/<int:idx>/selesai', methods=['POST'])
def toggle_goal_milestone(gid, idx):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("SELECT milestones FROM goals WHERE id=%s", (gid,))
    row = cur.fetchone()
    if not row:
        cur.close(); conn.close()
        return jsonify({'ok': False, 'msg': 'Tidak ditemukan'}), 404
    ms = json.loads(row['milestones']) if isinstance(row['milestones'], str) else row['milestones']
    if idx >= len(ms):
        cur.close(); conn.close()
        return jsonify({'ok': False, 'msg': 'Index salah'}), 400
    ms[idx]['selesai'] = not ms[idx]['selesai']
    done = sum(1 for m in ms if m['selesai'])
    progress = round(done / len(ms) * 100) if ms else 0
    cur.execute("UPDATE goals SET milestones=%s, progress=%s WHERE id=%s",
                (json.dumps(ms), progress, gid))
    conn.commit(); cur.close(); conn.close()
    return jsonify({'ok': True, 'selesai': ms[idx]['selesai'], 'progress': progress})

# ─────────────────────────────────────────────────────────────────────────────
# IDEAS
# ─────────────────────────────────────────────────────────────────────────────
@app.route('/api/ideas', methods=['GET'])
def get_ideas():
    conn = get_conn(); cur = conn.cursor()
    cur.execute("SELECT * FROM ideas ORDER BY dibuat DESC")
    rows = [row_to_dict(r) for r in cur.fetchall()]
    cur.close(); conn.close()
    search = request.args.get('search','').lower().strip()
    if search:
        rows = [i for i in rows if
                search in (i.get('judul') or '').lower() or
                search in (i.get('konten') or '').lower() or
                any(search in t.lower() for t in i.get('tags', []))]
    return jsonify(rows)

@app.route('/api/ideas', methods=['POST'])
def add_idea():
    body = request.get_json(silent=True) or {}
    judul = body.get('judul','').strip()
    if not judul:
        return jsonify({'ok': False, 'msg': 'Judul wajib'}), 400
    tags_raw = body.get('tags','')
    tags = tags_raw if isinstance(tags_raw, list) else [t.strip() for t in tags_raw.split(',') if t.strip()]
    iid = generate_id('idea')
    conn = get_conn(); cur = conn.cursor()
    cur.execute("""
        INSERT INTO ideas (id, judul, konten, tags, kategori, dibuat, diupdate, linked_goal, favorit)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,FALSE)
    """, (iid, judul, body.get('konten',''), json.dumps(tags),
          body.get('kategori','umum'), now_str(), now_str(), body.get('linked_goal','')))
    conn.commit(); cur.close(); conn.close()
    return jsonify({'ok': True, 'id': iid}), 201

@app.route('/api/ideas/<iid>', methods=['PUT'])
def update_idea(iid):
    body = request.get_json(silent=True) or {}
    tags_raw = body.get('tags','')
    tags = tags_raw if isinstance(tags_raw, list) else [t.strip() for t in tags_raw.split(',') if t.strip()]
    conn = get_conn(); cur = conn.cursor()
    cur.execute("""
        UPDATE ideas SET judul=%s, konten=%s, tags=%s, kategori=%s, diupdate=%s WHERE id=%s
    """, (body.get('judul',''), body.get('konten',''), json.dumps(tags),
          body.get('kategori','umum'), now_str(), iid))
    found = cur.rowcount > 0
    conn.commit(); cur.close(); conn.close()
    if found:
        return jsonify({'ok': True})
    return jsonify({'ok': False, 'msg': 'Tidak ditemukan'}), 404

@app.route('/api/ideas/<iid>', methods=['DELETE'])
def hapus_idea(iid):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("DELETE FROM ideas WHERE id=%s", (iid,))
    found = cur.rowcount > 0
    conn.commit(); cur.close(); conn.close()
    if found:
        return jsonify({'ok': True})
    return jsonify({'ok': False, 'msg': 'Tidak ditemukan'}), 404

@app.route('/api/ideas/<iid>/favorit', methods=['POST'])
def toggle_favorit(iid):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("SELECT favorit FROM ideas WHERE id=%s", (iid,))
    row = cur.fetchone()
    if not row:
        cur.close(); conn.close()
        return jsonify({'ok': False, 'msg': 'Tidak ditemukan'}), 404
    new_fav = not row['favorit']
    cur.execute("UPDATE ideas SET favorit=%s WHERE id=%s", (new_fav, iid))
    conn.commit(); cur.close(); conn.close()
    return jsonify({'ok': True, 'favorit': new_fav})

# ─────────────────────────────────────────────────────────────────────────────
# NOTES
# ─────────────────────────────────────────────────────────────────────────────
@app.route('/api/notes', methods=['GET'])
def get_notes():
    conn = get_conn(); cur = conn.cursor()
    cur.execute("SELECT * FROM notes WHERE selesai=FALSE ORDER BY dibuat DESC")
    rows = [dict(r) for r in cur.fetchall()]
    cur.close(); conn.close()
    return jsonify(rows)

@app.route('/api/notes', methods=['POST'])
def add_note():
    body = request.get_json(silent=True) or {}
    konten = body.get('konten','').strip()
    if not konten:
        return jsonify({'ok': False, 'msg': 'Konten wajib'}), 400
    nid = generate_id('note')
    conn = get_conn(); cur = conn.cursor()
    cur.execute("INSERT INTO notes (id, konten, dibuat, selesai) VALUES (%s,%s,%s,FALSE)",
                (nid, konten, now_str()))
    conn.commit(); cur.close(); conn.close()
    return jsonify({'ok': True, 'id': nid}), 201

@app.route('/api/notes/<nid>/done', methods=['POST'])
def done_note(nid):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("UPDATE notes SET selesai=TRUE WHERE id=%s", (nid,))
    conn.commit(); cur.close(); conn.close()
    return jsonify({'ok': True})

@app.route('/api/notes/<nid>', methods=['DELETE'])
def hapus_note(nid):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("DELETE FROM notes WHERE id=%s", (nid,))
    conn.commit(); cur.close(); conn.close()
    return jsonify({'ok': True})

# ─────────────────────────────────────────────────────────────────────────────
# DASHBOARD
# ─────────────────────────────────────────────────────────────────────────────
@app.route('/api/dashboard')
def get_dashboard():
    hari   = hari_ini()
    jadwal = JADWAL.get(hari, [])
    conn   = get_conn(); cur = conn.cursor()

    # Tugas aktif
    cur.execute("SELECT * FROM tugas WHERE selesai=FALSE")
    tugas_aktif = [dict(r) for r in cur.fetchall()]
    for t in tugas_aktif:
        t['sisa_hari'] = hitung_sisa_hari(t.get('deadline'))
    tugas_mendesak = sorted(
        [t for t in tugas_aktif if t['sisa_hari'] is not None and t['sisa_hari'] <= 7],
        key=lambda x: x['sisa_hari']
    )
    mendesak_count = sum(1 for t in tugas_aktif if t.get('sisa_hari') is not None and t['sisa_hari'] <= 3)

    # Events
    cur.execute("SELECT * FROM events WHERE selesai=FALSE")
    events_aktif = [row_to_dict(r) for r in cur.fetchall()]
    for e in events_aktif:
        e['sisa_hari'] = hitung_sisa_hari(e.get('deadline'))
    events_mendatang = sorted(
        [e for e in events_aktif if e['sisa_hari'] is not None and e['sisa_hari'] <= 30],
        key=lambda x: x['sisa_hari']
    )

    # Goals top 3
    cur.execute("SELECT * FROM goals WHERE selesai=FALSE ORDER BY progress DESC LIMIT 3")
    goals_aktif = [row_to_dict(r) for r in cur.fetchall()]

    # Quick notes terbaru
    cur.execute("SELECT * FROM notes WHERE selesai=FALSE ORDER BY dibuat DESC LIMIT 3")
    notes_aktif = [dict(r) for r in cur.fetchall()]

    # Per matkul
    per_matkul = {}
    for t in tugas_aktif:
        mk = t.get('matkul') or 'Lainnya'
        per_matkul[mk] = per_matkul.get(mk, 0) + 1

    # Goals count
    cur.execute("SELECT COUNT(*) as c FROM goals WHERE selesai=FALSE")
    goals_count = cur.fetchone()['c']

    cur.close(); conn.close()

    return jsonify({
        'hari':             hari,
        'jadwal':           jadwal,
        'tugas_mendesak':   tugas_mendesak,
        'events_mendatang': events_mendatang,
        'goals_aktif':      goals_aktif,
        'per_matkul':       per_matkul,
        'quicknotes':       notes_aktif,
        'stats': {
            'tugas_aktif':     len(tugas_aktif),
            'events_aktif':    len(events_aktif),
            'goals_aktif':     goals_count,
            'kuliah_hari_ini': len(jadwal),
            'mendesak':        mendesak_count,
        }
    })

# ─────────────────────────────────────────────────────────────────────────────
# CHAT AI (Ollama — hanya jalan di localhost)
# ─────────────────────────────────────────────────────────────────────────────
@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        import ollama
    except ImportError:
        return jsonify({'ok': False, 'msg': 'Ollama tidak tersedia di server online. Gunakan versi lokal untuk fitur Chat AI.'}), 500

    body  = request.get_json(silent=True) or {}
    pesan = body.get('pesan','').strip()
    if not pesan:
        return jsonify({'ok': False, 'msg': 'Pesan kosong'}), 400

    messages = []
    sys_prompt = SYSTEM_PROMPTS.get(body.get('mode','general'))
    if sys_prompt:
        messages.append({'role':'system','content': sys_prompt})
    messages.extend(body.get('history',[]))
    messages.append({'role':'user','content': pesan})

    try:
        import ollama as ol
        resp  = ol.chat(model='qwen2.5:14b', messages=messages)
        return jsonify({'ok': True, 'reply': resp['message']['content']})
    except Exception as e:
        return jsonify({'ok': False, 'msg': f'Ollama error: {str(e)}'}), 500

# ─────────────────────────────────────────────────────────────────────────────
# FLASHCARD
# ─────────────────────────────────────────────────────────────────────────────
@app.route('/api/flashcard', methods=['POST'])
def flashcard():
    try:
        import ollama
    except ImportError:
        return jsonify({'ok': False, 'msg': 'Ollama tidak tersedia di server online.'}), 500

    body = request.get_json(silent=True) or {}
    teks = body.get('teks','').strip()
    if not teks:
        return jsonify({'ok': False, 'msg': 'Teks kosong'}), 400

    prompt = f"""Buat flashcard dari teks berikut. Format WAJIB:
Q: [pertanyaan]
A: [jawaban]

Buat 5-10 flashcard paling penting.

Teks:
{teks[:3000]}"""

    try:
        import ollama as ol
        resp = ol.chat(model='qwen2.5:14b', messages=[{'role':'user','content': prompt}])
        return jsonify({'ok': True, 'flashcards': resp['message']['content']})
    except Exception as e:
        return jsonify({'ok': False, 'msg': str(e)}), 500

# ─────────────────────────────────────────────────────────────────────────────
# BRIEFING
# ─────────────────────────────────────────────────────────────────────────────
@app.route('/api/briefing', methods=['POST'])
def trigger_briefing():
    briefing_script = os.path.join(BASE_DIR, 'daily_briefing.py')
    if not os.path.exists(briefing_script):
        return jsonify({'ok': False, 'msg': 'daily_briefing.py tidak ditemukan'}), 404
    try:
        import sys
        result = subprocess.run([sys.executable, briefing_script, '--force'],
                                capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            return jsonify({'ok': True, 'msg': 'Briefing terkirim!'})
        return jsonify({'ok': False, 'msg': result.stderr or 'Gagal'}), 500
    except Exception as e:
        return jsonify({'ok': False, 'msg': str(e)}), 500

# ─────────────────────────────────────────────────────────────────────────────
# LAUNCHER
# ─────────────────────────────────────────────────────────────────────────────
APPS = {
    'zotero':      r'C:\Program Files\Zotero\zotero.exe',
    'anki':        r'D:\AI_Workspace\Anki\anki.exe',
    'anythingllm': r'D:\AI_Workspace\AnythingLLM\AnythingLLM.exe',
}

@app.route('/api/buka/<app_name>', methods=['POST'])
def buka_app(app_name):
    path = APPS.get(app_name.lower())
    if not path:
        return jsonify({'ok': False, 'msg': 'App tidak dikenal'}), 400
    if not os.path.exists(path):
        return jsonify({'ok': False, 'msg': f'File tidak ditemukan: {path}'}), 404
    try:
        subprocess.Popen([path])
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'ok': False, 'msg': str(e)}), 500

# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    init_db()
    print("FLOWIA OS — PostgreSQL ready")
    print("Akses: http://localhost:5000")
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False, use_reloader=False)

# Untuk Railway/Gunicorn — init DB saat startup
init_db()
