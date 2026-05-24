"""
FLOWIA OS — app.py
Flask backend untuk dashboard Koman (Binus Cybersecurity)
Jalankan: python app.py
Akses: http://localhost:5000
"""

import json
import os
import subprocess
from datetime import datetime, date
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

# ─── INISIALISASI ────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__, static_folder=os.path.join(BASE_DIR, 'static'), static_url_path='')
CORS(app)

# ─── PATH FILE JSON ───────────────────────────────────────────────────────────
TUGAS_FILE     = os.path.join(BASE_DIR, 'tugas.json')
EVENTS_FILE    = os.path.join(BASE_DIR, 'events.json')
GOALS_FILE     = os.path.join(BASE_DIR, 'goals.json')
IDEAS_FILE     = os.path.join(BASE_DIR, 'ideas.json')
NOTES_FILE     = os.path.join(BASE_DIR, 'quicknotes.json')

# ─── JADWAL KULIAH (hardcoded) ────────────────────────────────────────────────
JADWAL = {
    "Senin": [
        {"mata_kuliah": "Software Engineering (LS01)",              "jam": "09.20-11.00", "ruang": "Anggrek - 403"},
        {"mata_kuliah": "Software Engineering (LS01)",              "jam": "11.20-13.00", "ruang": "Anggrek - 403"},
        {"mata_kuliah": "Server and Network Administration (LC07)", "jam": "13.20-15.00", "ruang": "Anggrek - 504"},
    ],
    "Selasa": [
        {"mata_kuliah": "Cyber Law (LC07)",             "jam": "09.20-11.00", "ruang": "Syahdan - L3B"},
        {"mata_kuliah": "Software Security (LC07)",     "jam": "11.20-13.00", "ruang": "Anggrek - 406"},
        {"mata_kuliah": "Research Methodology (LS01)",  "jam": "13.20-15.00", "ruang": "Anggrek - 514"},
    ],
    "Rabu": [
        {"mata_kuliah": "Research Methodology (LS01)",  "jam": "15.20-17.00", "ruang": "Anggrek - 514"},
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

# ─── SYSTEM PROMPTS AI MODE ────────────────────────────────────────────────────
SYSTEM_PROMPTS = {
    "general": None,
    "lomba_ai": (
        "Kamu adalah mentor kompetisi AI/ML berpengalaman. Bantu Koman analisis problem statement lomba, "
        "brainstorm pendekatan teknis, dan identifikasi risiko. Tanya balik kalau butuh klarifikasi. "
        "Fokus pada solusi yang bisa diimplementasi dalam waktu lomba. Koman adalah mahasiswa Cybersecurity "
        "Binus yang aktif ikut kompetisi AI — ini adalah konteks utamanya."
    ),
    "bisnis": (
        "Kamu adalah advisor bisnis yang kritis dan jujur. Tugasmu adalah menjadi devil's advocate untuk ide Koman. "
        "Pertanyakan asumsi, identifikasi lubang di model bisnis, tanya soal target pasar dan monetisasi. "
        "Jangan hanya setuju — bantu Koman berpikir lebih tajam tentang ide bisnisnya."
    ),
    "riset": (
        "Kamu adalah pembimbing riset akademik. Bantu Koman strukturkan argumen, identifikasi gap di literatur, "
        "dan pastikan metodologi penelitian solid. Gunakan bahasa akademik tapi tetap mudah dipahami. "
        "Koman belajar di jurusan Cybersecurity Binus dan sedang mengerjakan penelitian."
    ),
    "ctf": (
        "Kamu adalah mentor CTF berpengalaman. Bantu Koman breakdown challenge, identifikasi kategori "
        "(web, crypto, forensic, reverse, pwn, dll), dan berpikir step-by-step tentang attack vector. "
        "Jangan kasih jawaban langsung — bantu proses berpikir dan reasoning-nya."
    ),
    "planner": (
        "Kamu adalah personal planner dan productivity coach untuk Koman. Kamu tahu Koman adalah mahasiswa "
        "Cybersecurity Binus yang juga aktif ikut lomba AI, riset jurnal, dan merintis bisnis. "
        "Bantu prioritaskan task, identifikasi bottleneck, buat rencana eksekusi yang realistis, "
        "dan ingat bahwa lomba AI adalah fokus utamanya."
    ),
}

# ─── HELPERS JSON ─────────────────────────────────────────────────────────────
def baca_json(path, default=None):
    if default is None:
        default = []
    if not os.path.exists(path):
        tulis_json(path, default)
        return default
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return default

def tulis_json(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def hitung_sisa_hari(deadline_str):
    """Hitung sisa hari dari deadline format DD/MM/YYYY."""
    if not deadline_str:
        return None
    try:
        d = datetime.strptime(deadline_str.strip(), "%d/%m/%Y").date()
        return (d - date.today()).days
    except ValueError:
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

# ─── SERVE FRONTEND ────────────────────────────────────────────────────────────
@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

# ─────────────────────────────────────────────────────────────────────────────
# ENDPOINT: JADWAL
# ─────────────────────────────────────────────────────────────────────────────
@app.route('/api/jadwal')
def get_jadwal():
    hari = request.args.get('hari', hari_ini())
    data = JADWAL.get(hari, [])
    return jsonify(data)

# ─────────────────────────────────────────────────────────────────────────────
# ENDPOINT: TUGAS
# ─────────────────────────────────────────────────────────────────────────────
@app.route('/api/tugas', methods=['GET'])
def get_tugas():
    data = baca_json(TUGAS_FILE)
    aktif = [t for t in data if not t.get('selesai', False)]
    for t in aktif:
        t['sisa_hari'] = hitung_sisa_hari(t.get('deadline'))
    return jsonify(aktif)

@app.route('/api/tugas/selesai', methods=['GET'])
def get_tugas_selesai():
    data = baca_json(TUGAS_FILE)
    return jsonify([t for t in data if t.get('selesai', False)])

@app.route('/api/tugas', methods=['POST'])
def add_tugas():
    body = request.get_json(silent=True) or {}
    nama = body.get('nama', '').strip()
    if not nama:
        return jsonify({'ok': False, 'msg': 'Nama tugas wajib diisi'}), 400
    data = baca_json(TUGAS_FILE)
    tugas = {
        'nama':      nama,
        'matkul':    body.get('matkul', '').strip(),
        'deadline':  body.get('deadline', '').strip(),
        'catatan':   body.get('catatan', '').strip(),
        'prioritas': body.get('prioritas', 'normal'),
        'selesai':   False,
        'dibuat':    now_str(),
    }
    data.append(tugas)
    tulis_json(TUGAS_FILE, data)
    return jsonify({'ok': True, 'msg': 'Tugas ditambahkan'}), 201

@app.route('/api/tugas/<nama>/selesai', methods=['POST'])
def selesai_tugas(nama):
    data = baca_json(TUGAS_FILE)
    for t in data:
        if t['nama'] == nama:
            t['selesai'] = True
            t['selesai_pada'] = now_str()
            tulis_json(TUGAS_FILE, data)
            return jsonify({'ok': True, 'msg': 'Tugas diselesaikan'})
    return jsonify({'ok': False, 'msg': 'Tugas tidak ditemukan'}), 404

@app.route('/api/tugas/<nama>', methods=['DELETE'])
def hapus_tugas(nama):
    data = baca_json(TUGAS_FILE)
    baru = [t for t in data if t['nama'] != nama]
    if len(baru) == len(data):
        return jsonify({'ok': False, 'msg': 'Tugas tidak ditemukan'}), 404
    tulis_json(TUGAS_FILE, baru)
    return jsonify({'ok': True, 'msg': 'Tugas dihapus'})

@app.route('/api/stats')
def get_stats():
    data = baca_json(TUGAS_FILE)
    aktif = [t for t in data if not t.get('selesai')]
    for t in aktif:
        t['sisa_hari'] = hitung_sisa_hari(t.get('deadline'))
    mendesak = sum(1 for t in aktif if t['sisa_hari'] is not None and t['sisa_hari'] <= 3)
    per_matkul = {}
    for t in aktif:
        mk = t.get('matkul', 'Lainnya') or 'Lainnya'
        per_matkul[mk] = per_matkul.get(mk, 0) + 1
    return jsonify({
        'total_aktif':  len(aktif),
        'total_selesai': len(data) - len(aktif),
        'mendesak':     mendesak,
        'per_matkul':   per_matkul,
    })

@app.route('/api/matkul')
def get_matkul():
    data = baca_json(TUGAS_FILE)
    mk = list({t.get('matkul','') for t in data if t.get('matkul')})
    return jsonify(sorted(mk))

# ─────────────────────────────────────────────────────────────────────────────
# ENDPOINT: EVENTS
# ─────────────────────────────────────────────────────────────────────────────
@app.route('/api/events', methods=['GET'])
def get_events():
    data = baca_json(EVENTS_FILE)
    aktif = [e for e in data if not e.get('selesai', False)]
    for e in aktif:
        e['sisa_hari'] = hitung_sisa_hari(e.get('deadline'))
        for ms in e.get('milestones', []):
            ms['sisa_hari'] = hitung_sisa_hari(ms.get('deadline'))
    return jsonify(aktif)

@app.route('/api/events', methods=['POST'])
def add_event():
    body = request.get_json(silent=True) or {}
    nama = body.get('nama', '').strip()
    if not nama:
        return jsonify({'ok': False, 'msg': 'Nama event wajib diisi'}), 400
    data = baca_json(EVENTS_FILE)
    tim_raw = body.get('tim', '')
    if isinstance(tim_raw, str):
        tim = [x.strip() for x in tim_raw.split(',') if x.strip()]
    else:
        tim = tim_raw
    event = {
        'id':         generate_id('evt'),
        'nama':       nama,
        'kategori':   body.get('kategori', 'deadline_penting'),
        'deadline':   body.get('deadline', '').strip(),
        'status':     'aktif',
        'peran':      body.get('peran', '').strip(),
        'tim':        tim,
        'deskripsi':  body.get('deskripsi', '').strip(),
        'milestones': [],
        'catatan':    body.get('catatan', '').strip(),
        'dibuat':     now_str(),
        'selesai':    False,
        'hasil':      '',
    }
    data.append(event)
    tulis_json(EVENTS_FILE, data)
    return jsonify({'ok': True, 'msg': 'Event ditambahkan', 'id': event['id']}), 201

@app.route('/api/events/<eid>', methods=['PUT'])
def update_event(eid):
    body = request.get_json(silent=True) or {}
    data = baca_json(EVENTS_FILE)
    for e in data:
        if e['id'] == eid:
            if 'nama'      in body: e['nama']      = body['nama'].strip()
            if 'kategori'  in body: e['kategori']  = body['kategori']
            if 'deadline'  in body: e['deadline']  = body['deadline'].strip()
            if 'peran'     in body: e['peran']     = body['peran'].strip()
            if 'tim'       in body:
                tim_raw = body['tim']
                e['tim'] = tim_raw if isinstance(tim_raw, list) else [x.strip() for x in tim_raw.split(',') if x.strip()]
            if 'deskripsi' in body: e['deskripsi'] = body['deskripsi'].strip()
            if 'catatan'   in body: e['catatan']   = body['catatan'].strip()
            if 'status'    in body: e['status']    = body['status']
            tulis_json(EVENTS_FILE, data)
            return jsonify({'ok': True, 'msg': 'Event diupdate'})
    return jsonify({'ok': False, 'msg': 'Event tidak ditemukan'}), 404

@app.route('/api/events/<eid>', methods=['DELETE'])
def hapus_event(eid):
    data = baca_json(EVENTS_FILE)
    baru = [e for e in data if e['id'] != eid]
    if len(baru) == len(data):
        return jsonify({'ok': False, 'msg': 'Event tidak ditemukan'}), 404
    tulis_json(EVENTS_FILE, baru)
    return jsonify({'ok': True, 'msg': 'Event dihapus'})

@app.route('/api/events/<eid>/selesai', methods=['POST'])
def selesai_event(eid):
    body = request.get_json(silent=True) or {}
    data = baca_json(EVENTS_FILE)
    for e in data:
        if e['id'] == eid:
            e['selesai']      = True
            e['status']       = 'selesai'
            e['hasil']        = body.get('hasil', '').strip()
            e['selesai_pada'] = now_str()
            tulis_json(EVENTS_FILE, data)
            return jsonify({'ok': True, 'msg': 'Event diselesaikan'})
    return jsonify({'ok': False, 'msg': 'Event tidak ditemukan'}), 404

@app.route('/api/events/<eid>/milestone', methods=['POST'])
def add_milestone(eid):
    body = request.get_json(silent=True) or {}
    nama = body.get('nama', '').strip()
    if not nama:
        return jsonify({'ok': False, 'msg': 'Nama milestone wajib'}), 400
    data = baca_json(EVENTS_FILE)
    for e in data:
        if e['id'] == eid:
            ms = {'nama': nama, 'deadline': body.get('deadline','').strip(), 'selesai': False}
            e.setdefault('milestones', []).append(ms)
            tulis_json(EVENTS_FILE, data)
            return jsonify({'ok': True, 'msg': 'Milestone ditambahkan'})
    return jsonify({'ok': False, 'msg': 'Event tidak ditemukan'}), 404

@app.route('/api/events/<eid>/milestone/<int:idx>/selesai', methods=['POST'])
def toggle_milestone(eid, idx):
    data = baca_json(EVENTS_FILE)
    for e in data:
        if e['id'] == eid:
            ms = e.get('milestones', [])
            if idx >= len(ms):
                return jsonify({'ok': False, 'msg': 'Index milestone salah'}), 400
            ms[idx]['selesai'] = not ms[idx]['selesai']
            tulis_json(EVENTS_FILE, data)
            return jsonify({'ok': True, 'selesai': ms[idx]['selesai']})
    return jsonify({'ok': False, 'msg': 'Event tidak ditemukan'}), 404

@app.route('/api/events/stats')
def stats_events():
    data = baca_json(EVENTS_FILE)
    aktif = [e for e in data if not e.get('selesai')]
    per_kat = {}
    for e in aktif:
        k = e.get('kategori', 'lainnya')
        per_kat[k] = per_kat.get(k, 0) + 1
    mendatang_30 = []
    for e in aktif:
        s = hitung_sisa_hari(e.get('deadline'))
        if s is not None and 0 <= s <= 30:
            mendatang_30.append(e)
    return jsonify({'total_aktif': len(aktif), 'per_kategori': per_kat, 'mendatang_30': len(mendatang_30)})

# ─────────────────────────────────────────────────────────────────────────────
# ENDPOINT: GOALS
# ─────────────────────────────────────────────────────────────────────────────
@app.route('/api/goals', methods=['GET'])
def get_goals():
    data = baca_json(GOALS_FILE)
    return jsonify([g for g in data if not g.get('selesai', False)])

@app.route('/api/goals', methods=['POST'])
def add_goal():
    body = request.get_json(silent=True) or {}
    nama = body.get('nama', '').strip()
    if not nama:
        return jsonify({'ok': False, 'msg': 'Nama goal wajib'}), 400
    data = baca_json(GOALS_FILE)
    goal = {
        'id':           generate_id('goal'),
        'nama':         nama,
        'kategori':     body.get('kategori', 'personal'),
        'deadline':     body.get('deadline', '').strip(),
        'progress':     int(body.get('progress', 0)),
        'deskripsi':    body.get('deskripsi', '').strip(),
        'milestones':   body.get('milestones', []),
        'linked_events': body.get('linked_events', []),
        'catatan':      body.get('catatan', '').strip(),
        'dibuat':       today_str(),
        'selesai':      False,
    }
    data.append(goal)
    tulis_json(GOALS_FILE, data)
    return jsonify({'ok': True, 'msg': 'Goal ditambahkan', 'id': goal['id']}), 201

@app.route('/api/goals/<gid>', methods=['PUT'])
def update_goal(gid):
    body = request.get_json(silent=True) or {}
    data = baca_json(GOALS_FILE)
    for g in data:
        if g['id'] == gid:
            for field in ['nama','kategori','deadline','deskripsi','catatan']:
                if field in body:
                    g[field] = body[field].strip() if isinstance(body[field], str) else body[field]
            if 'progress' in body:
                g['progress'] = max(0, min(100, int(body['progress'])))
            if 'milestones' in body:
                g['milestones'] = body['milestones']
            if 'linked_events' in body:
                g['linked_events'] = body['linked_events']
            tulis_json(GOALS_FILE, data)
            return jsonify({'ok': True, 'msg': 'Goal diupdate'})
    return jsonify({'ok': False, 'msg': 'Goal tidak ditemukan'}), 404

@app.route('/api/goals/<gid>', methods=['DELETE'])
def hapus_goal(gid):
    data = baca_json(GOALS_FILE)
    baru = [g for g in data if g['id'] != gid]
    if len(baru) == len(data):
        return jsonify({'ok': False, 'msg': 'Goal tidak ditemukan'}), 404
    tulis_json(GOALS_FILE, baru)
    return jsonify({'ok': True, 'msg': 'Goal dihapus'})

@app.route('/api/goals/<gid>/selesai', methods=['POST'])
def selesai_goal(gid):
    data = baca_json(GOALS_FILE)
    for g in data:
        if g['id'] == gid:
            g['selesai']      = True
            g['progress']     = 100
            g['selesai_pada'] = today_str()
            tulis_json(GOALS_FILE, data)
            return jsonify({'ok': True, 'msg': 'Goal selesai! 🎊'})
    return jsonify({'ok': False, 'msg': 'Goal tidak ditemukan'}), 404

@app.route('/api/goals/<gid>/milestone/<int:idx>/selesai', methods=['POST'])
def toggle_goal_milestone(gid, idx):
    data = baca_json(GOALS_FILE)
    for g in data:
        if g['id'] == gid:
            ms = g.get('milestones', [])
            if idx >= len(ms):
                return jsonify({'ok': False, 'msg': 'Index milestone salah'}), 400
            ms[idx]['selesai'] = not ms[idx]['selesai']
            # Auto-update progress dari milestone
            done = sum(1 for m in ms if m['selesai'])
            g['progress'] = round(done / len(ms) * 100) if ms else g['progress']
            tulis_json(GOALS_FILE, data)
            return jsonify({'ok': True, 'selesai': ms[idx]['selesai'], 'progress': g['progress']})
    return jsonify({'ok': False, 'msg': 'Goal tidak ditemukan'}), 404

# ─────────────────────────────────────────────────────────────────────────────
# ENDPOINT: IDEAS
# ─────────────────────────────────────────────────────────────────────────────
@app.route('/api/ideas', methods=['GET'])
def get_ideas():
    data = baca_json(IDEAS_FILE)
    search = request.args.get('search', '').lower().strip()
    tag    = request.args.get('tag', '').lower().strip()
    if search:
        data = [i for i in data if
                search in i.get('judul','').lower() or
                search in i.get('konten','').lower() or
                any(search in t.lower() for t in i.get('tags',[]))]
    if tag:
        data = [i for i in data if tag in [t.lower() for t in i.get('tags',[])] ]
    return jsonify(data)

@app.route('/api/ideas', methods=['POST'])
def add_idea():
    body = request.get_json(silent=True) or {}
    judul = body.get('judul', '').strip()
    if not judul:
        return jsonify({'ok': False, 'msg': 'Judul wajib diisi'}), 400
    data = baca_json(IDEAS_FILE)
    tags_raw = body.get('tags', '')
    if isinstance(tags_raw, str):
        tags = [t.strip() for t in tags_raw.split(',') if t.strip()]
    else:
        tags = tags_raw
    idea = {
        'id':           generate_id('idea'),
        'judul':        judul,
        'konten':       body.get('konten', '').strip(),
        'tags':         tags,
        'kategori':     body.get('kategori', 'umum'),
        'dibuat':       now_str(),
        'diupdate':     now_str(),
        'linked_goal':  body.get('linked_goal', ''),
        'favorit':      False,
    }
    data.append(idea)
    tulis_json(IDEAS_FILE, data)
    return jsonify({'ok': True, 'msg': 'Ide disimpan', 'id': idea['id']}), 201

@app.route('/api/ideas/<iid>', methods=['PUT'])
def update_idea(iid):
    body = request.get_json(silent=True) or {}
    data = baca_json(IDEAS_FILE)
    for i in data:
        if i['id'] == iid:
            for field in ['judul','konten','kategori','linked_goal']:
                if field in body:
                    i[field] = body[field].strip() if isinstance(body[field], str) else body[field]
            if 'tags' in body:
                tr = body['tags']
                i['tags'] = tr if isinstance(tr, list) else [t.strip() for t in tr.split(',') if t.strip()]
            i['diupdate'] = now_str()
            tulis_json(IDEAS_FILE, data)
            return jsonify({'ok': True, 'msg': 'Ide diupdate'})
    return jsonify({'ok': False, 'msg': 'Ide tidak ditemukan'}), 404

@app.route('/api/ideas/<iid>', methods=['DELETE'])
def hapus_idea(iid):
    data = baca_json(IDEAS_FILE)
    baru = [i for i in data if i['id'] != iid]
    if len(baru) == len(data):
        return jsonify({'ok': False, 'msg': 'Ide tidak ditemukan'}), 404
    tulis_json(IDEAS_FILE, baru)
    return jsonify({'ok': True, 'msg': 'Ide dihapus'})

@app.route('/api/ideas/<iid>/favorit', methods=['POST'])
def toggle_favorit(iid):
    data = baca_json(IDEAS_FILE)
    for i in data:
        if i['id'] == iid:
            i['favorit'] = not i.get('favorit', False)
            tulis_json(IDEAS_FILE, data)
            return jsonify({'ok': True, 'favorit': i['favorit']})
    return jsonify({'ok': False, 'msg': 'Ide tidak ditemukan'}), 404

# ─────────────────────────────────────────────────────────────────────────────
# ENDPOINT: QUICK NOTES
# ─────────────────────────────────────────────────────────────────────────────
@app.route('/api/notes', methods=['GET'])
def get_notes():
    data = baca_json(NOTES_FILE)
    return jsonify([n for n in data if not n.get('selesai', False)])

@app.route('/api/notes', methods=['POST'])
def add_note():
    body = request.get_json(silent=True) or {}
    konten = body.get('konten', '').strip()
    if not konten:
        return jsonify({'ok': False, 'msg': 'Konten wajib diisi'}), 400
    data = baca_json(NOTES_FILE)
    note = {
        'id':      generate_id('note'),
        'konten':  konten,
        'dibuat':  now_str(),
        'selesai': False,
    }
    data.append(note)
    tulis_json(NOTES_FILE, data)
    return jsonify({'ok': True, 'msg': 'Note disimpan', 'id': note['id']}), 201

@app.route('/api/notes/<nid>/done', methods=['POST'])
def done_note(nid):
    data = baca_json(NOTES_FILE)
    for n in data:
        if n['id'] == nid:
            n['selesai'] = True
            tulis_json(NOTES_FILE, data)
            return jsonify({'ok': True})
    return jsonify({'ok': False, 'msg': 'Note tidak ditemukan'}), 404

@app.route('/api/notes/<nid>', methods=['DELETE'])
def hapus_note(nid):
    data = baca_json(NOTES_FILE)
    baru = [n for n in data if n['id'] != nid]
    if len(baru) == len(data):
        return jsonify({'ok': False, 'msg': 'Note tidak ditemukan'}), 404
    tulis_json(NOTES_FILE, baru)
    return jsonify({'ok': True})

# ─────────────────────────────────────────────────────────────────────────────
# ENDPOINT: DASHBOARD (satu call untuk semua data)
# ─────────────────────────────────────────────────────────────────────────────
@app.route('/api/dashboard')
def get_dashboard():
    hari = hari_ini()
    jadwal = JADWAL.get(hari, [])

    # Tugas mendesak (sisa_hari <= 7)
    tugas_all  = baca_json(TUGAS_FILE)
    tugas_aktif = [t for t in tugas_all if not t.get('selesai')]
    for t in tugas_aktif:
        t['sisa_hari'] = hitung_sisa_hari(t.get('deadline'))
    tugas_mendesak = sorted(
        [t for t in tugas_aktif if t['sisa_hari'] is not None and t['sisa_hari'] <= 7],
        key=lambda x: x['sisa_hari']
    )
    mendesak_count = sum(1 for t in tugas_aktif if t.get('sisa_hari') is not None and t['sisa_hari'] <= 3)

    # Events mendatang (30 hari)
    events_all = baca_json(EVENTS_FILE)
    events_aktif = [e for e in events_all if not e.get('selesai')]
    for e in events_aktif:
        e['sisa_hari'] = hitung_sisa_hari(e.get('deadline'))
    events_mendatang = sorted(
        [e for e in events_aktif if e['sisa_hari'] is not None and e['sisa_hari'] <= 30],
        key=lambda x: x['sisa_hari']
    )

    # Goals aktif (top 3 by progress)
    goals_all = baca_json(GOALS_FILE)
    goals_aktif = sorted(
        [g for g in goals_all if not g.get('selesai')],
        key=lambda x: x.get('progress', 0), reverse=True
    )[:3]

    # Quick notes terbaru (3)
    notes_all = baca_json(NOTES_FILE)
    notes_aktif = [n for n in notes_all if not n.get('selesai')][-3:]

    # Per matkul
    per_matkul = {}
    for t in tugas_aktif:
        mk = t.get('matkul', 'Lainnya') or 'Lainnya'
        per_matkul[mk] = per_matkul.get(mk, 0) + 1

    return jsonify({
        'hari':             hari,
        'jadwal':           jadwal,
        'tugas_mendesak':   tugas_mendesak,
        'events_mendatang': events_mendatang,
        'goals_aktif':      goals_aktif,
        'per_matkul':       per_matkul,
        'quicknotes':       notes_aktif,
        'stats': {
            'tugas_aktif':    len(tugas_aktif),
            'events_aktif':   len(events_aktif),
            'goals_aktif':    len(goals_aktif),
            'kuliah_hari_ini': len(jadwal),
            'mendesak':       mendesak_count,
        }
    })

# ─────────────────────────────────────────────────────────────────────────────
# ENDPOINT: CHAT AI (Ollama)
# ─────────────────────────────────────────────────────────────────────────────
@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        import ollama
    except ImportError:
        return jsonify({'ok': False, 'msg': 'Ollama tidak terinstall. Jalankan: pip install ollama'}), 500

    body    = request.get_json(silent=True) or {}
    pesan   = body.get('pesan', '').strip()
    history = body.get('history', [])
    mode    = body.get('mode', 'general')

    if not pesan:
        return jsonify({'ok': False, 'msg': 'Pesan kosong'}), 400

    messages = []
    sys_prompt = SYSTEM_PROMPTS.get(mode)
    if sys_prompt:
        messages.append({'role': 'system', 'content': sys_prompt})
    messages.extend(history)
    messages.append({'role': 'user', 'content': pesan})

    try:
        resp = ollama.chat(model='qwen2.5:14b', messages=messages)
        reply = resp['message']['content']
        return jsonify({'ok': True, 'reply': reply})
    except Exception as e:
        return jsonify({'ok': False, 'msg': f'Ollama error: {str(e)}. Pastikan Ollama aktif dan model qwen2.5:14b sudah di-pull.'}), 500

# ─────────────────────────────────────────────────────────────────────────────
# ENDPOINT: FLASHCARD
# ─────────────────────────────────────────────────────────────────────────────
@app.route('/api/flashcard', methods=['POST'])
def flashcard():
    try:
        import ollama
    except ImportError:
        return jsonify({'ok': False, 'msg': 'Ollama tidak terinstall'}), 500

    body = request.get_json(silent=True) or {}
    teks = body.get('teks', '').strip()
    if not teks:
        return jsonify({'ok': False, 'msg': 'Teks kosong'}), 400

    prompt = f"""Buat flashcard dari teks berikut. Format WAJIB:
Q: [pertanyaan]
A: [jawaban]

Buat 5-10 flashcard yang paling penting. Satu baris per Q dan A.

Teks:
{teks[:3000]}"""

    try:
        resp = ollama.chat(model='qwen2.5:14b', messages=[{'role':'user','content': prompt}])
        return jsonify({'ok': True, 'flashcards': resp['message']['content']})
    except Exception as e:
        return jsonify({'ok': False, 'msg': f'Ollama error: {str(e)}'}), 500

# ─────────────────────────────────────────────────────────────────────────────
# ENDPOINT: BRIEFING (trigger manual)
# ─────────────────────────────────────────────────────────────────────────────
@app.route('/api/briefing', methods=['POST'])
def trigger_briefing():
    briefing_script = os.path.join(BASE_DIR, 'daily_briefing.py')
    if not os.path.exists(briefing_script):
        return jsonify({'ok': False, 'msg': 'daily_briefing.py tidak ditemukan di folder yang sama'}), 404
    try:
        import sys
        result = subprocess.run(
            [sys.executable, briefing_script, '--force'],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            return jsonify({'ok': True, 'msg': 'Briefing berhasil dikirim!'})
        else:
            return jsonify({'ok': False, 'msg': result.stderr or result.stdout or 'Gagal kirim briefing'}), 500
    except Exception as e:
        return jsonify({'ok': False, 'msg': str(e)}), 500

# ─────────────────────────────────────────────────────────────────────────────
# ENDPOINT: LAUNCHER
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
        return jsonify({'ok': False, 'msg': f'App "{app_name}" tidak dikenal'}), 400
    if not os.path.exists(path):
        return jsonify({'ok': False, 'msg': f'File tidak ditemukan: {path}'}), 404
    try:
        subprocess.Popen([path])
        return jsonify({'ok': True, 'msg': f'{app_name} dibuka!'})
    except Exception as e:
        return jsonify({'ok': False, 'msg': str(e)}), 500

# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    print("=" * 55)
    print("  FLOWIA OS — Backend Flask")
    print("  Akses: http://localhost:5000")
    print("=" * 55)
    print(f"  Base dir : {BASE_DIR}")
    print(f"  Tugas    : {os.path.exists(TUGAS_FILE)}")
    print(f"  Events   : {os.path.exists(EVENTS_FILE)}")
    print(f"  Goals    : {os.path.exists(GOALS_FILE)}")
    print(f"  Ideas    : {os.path.exists(IDEAS_FILE)}")
    print(f"  Notes    : {os.path.exists(NOTES_FILE)}")
    print("=" * 55)
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
