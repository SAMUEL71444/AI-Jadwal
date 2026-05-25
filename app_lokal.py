from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import json, os, subprocess
from datetime import datetime

app = Flask(__name__, static_folder='static')
CORS(app)

BASE = r"D:\AI_Workspace\scripts"
FILE_TUGAS = os.path.join(BASE, "tugas.json")

JADWAL = {
    "Senin": [
        {"mata_kuliah": "Software Engineering (LS01)", "jam": "09.20-11.00", "ruang": "Anggrek - 403"},
        {"mata_kuliah": "Software Engineering (LS01)", "jam": "11.20-13.00", "ruang": "Anggrek - 403"},
        {"mata_kuliah": "Server and Network Administration (LC07)", "jam": "13.20-15.00", "ruang": "Anggrek - 504"},
    ],
    "Selasa": [
        {"mata_kuliah": "Cyber Law (LC07)", "jam": "09.20-11.00", "ruang": "Syahdan - L3B"},
        {"mata_kuliah": "Software Security (LC07)", "jam": "11.20-13.00", "ruang": "Anggrek - 406"},
        {"mata_kuliah": "Research Methodology (LS01)", "jam": "13.20-15.00", "ruang": "Anggrek - 514"},
    ],
    "Rabu": [
        {"mata_kuliah": "Research Methodology (LS01)", "jam": "15.20-17.00", "ruang": "Anggrek - 514"},
    ],
    "Kamis": [
        {"mata_kuliah": "Mobile Penetration Testing (LC07)", "jam": "11.20-13.00", "ruang": "Anggrek - 709"},
        {"mata_kuliah": "Mobile Penetration Testing (BE07)", "jam": "13.20-15.00", "ruang": "Anggrek - 708"},
        {"mata_kuliah": "Software Engineering (TS01)", "jam": "15.20-17.00", "ruang": "Anggrek - 403"},
    ],
    "Jumat": [],
    "Sabtu": [
        {"mata_kuliah": "Computational Biology (LA05)", "jam": "11.20-13.00", "ruang": "Anggrek - 502"},
        {"mata_kuliah": "Computational Biology (BA05)", "jam": "13.20-15.00", "ruang": "Anggrek - 601"},
    ],
    "Minggu": []
}

HARI_INDO = {
    "Monday": "Senin", "Tuesday": "Selasa", "Wednesday": "Rabu",
    "Thursday": "Kamis", "Friday": "Jumat", "Saturday": "Sabtu", "Sunday": "Minggu"
}

MATKUL_LIST = [
    "Software Security",
    "Mobile Penetration Testing",
    "Cyber Law",
    "Software Engineering",
    "Server and Network Administration",
    "Research Methodology",
    "Computational Biology",
]

def load_tugas():
    if not os.path.exists(FILE_TUGAS):
        return []
    with open(FILE_TUGAS, "r", encoding="utf-8") as f:
        return json.load(f)

def save_tugas(tugas):
    with open(FILE_TUGAS, "w", encoding="utf-8") as f:
        json.dump(tugas, f, indent=2, ensure_ascii=False)

# ── Jadwal ──────────────────────────────────────────────────────────────────

@app.route("/api/jadwal")
def get_jadwal():
    hari_param = request.args.get("hari")
    if hari_param:
        hari = hari_param
    else:
        hari = HARI_INDO[datetime.now().strftime("%A")]
    return jsonify({"hari": hari, "jadwal": JADWAL.get(hari, []), "semua": JADWAL})

# ── Tugas ────────────────────────────────────────────────────────────────────

@app.route("/api/tugas", methods=["GET"])
def get_tugas():
    tugas = load_tugas()
    aktif = [t for t in tugas if not t.get("selesai")]
    for t in aktif:
        try:
            deadline = datetime.strptime(t["deadline"], "%d/%m/%Y")
            t["sisa_hari"] = (deadline - datetime.now()).days
        except:
            t["sisa_hari"] = None
    aktif.sort(key=lambda x: x.get("sisa_hari") if x.get("sisa_hari") is not None else 999)
    return jsonify(aktif)

@app.route("/api/tugas/selesai", methods=["GET"])
def get_tugas_selesai():
    tugas = load_tugas()
    selesai = [t for t in tugas if t.get("selesai")]
    return jsonify(selesai)

@app.route("/api/tugas", methods=["POST"])
def tambah_tugas():
    data = request.json
    if not data.get("nama") or not data.get("deadline"):
        return jsonify({"ok": False, "msg": "Nama dan deadline wajib diisi"}), 400
    tugas = load_tugas()
    # Cek duplikat nama
    if any(t["nama"] == data["nama"] for t in tugas if not t.get("selesai")):
        return jsonify({"ok": False, "msg": "Tugas dengan nama yang sama sudah ada"}), 409
    tugas.append({
        "nama": data["nama"],
        "matkul": data["matkul"],
        "deadline": data["deadline"],
        "catatan": data.get("catatan", ""),
        "prioritas": data.get("prioritas", "normal"),
        "selesai": False,
        "dibuat": datetime.now().strftime("%d/%m/%Y %H:%M")
    })
    save_tugas(tugas)
    return jsonify({"ok": True})

@app.route("/api/tugas/<nama>/selesai", methods=["POST"])
def selesai_tugas(nama):
    tugas = load_tugas()
    found = False
    for t in tugas:
        if t["nama"] == nama and not t.get("selesai"):
            t["selesai"] = True
            t["selesai_pada"] = datetime.now().strftime("%d/%m/%Y %H:%M")
            found = True
    if not found:
        return jsonify({"ok": False, "msg": "Tugas tidak ditemukan"}), 404
    save_tugas(tugas)
    return jsonify({"ok": True})

@app.route("/api/tugas/<nama>", methods=["DELETE"])
def hapus_tugas(nama):
    tugas = load_tugas()
    baru = [t for t in tugas if t["nama"] != nama]
    if len(baru) == len(tugas):
        return jsonify({"ok": False, "msg": "Tugas tidak ditemukan"}), 404
    save_tugas(baru)
    return jsonify({"ok": True})

# ── Stats ─────────────────────────────────────────────────────────────────────

@app.route("/api/stats")
def get_stats():
    tugas = load_tugas()
    aktif = [t for t in tugas if not t.get("selesai")]
    selesai = [t for t in tugas if t.get("selesai")]

    # Hitung deadline mendesak (≤3 hari)
    mendesak = 0
    for t in aktif:
        try:
            d = datetime.strptime(t["deadline"], "%d/%m/%Y")
            if (d - datetime.now()).days <= 3:
                mendesak += 1
        except:
            pass

    # Rekap per matkul
    per_matkul = {}
    for t in aktif:
        mk = t["matkul"]
        per_matkul[mk] = per_matkul.get(mk, 0) + 1

    return jsonify({
        "total_aktif": len(aktif),
        "total_selesai": len(selesai),
        "mendesak": mendesak,
        "per_matkul": per_matkul,
    })

# ── Matkul list ───────────────────────────────────────────────────────────────

@app.route("/api/matkul")
def get_matkul():
    return jsonify(MATKUL_LIST)

# ── Briefing ──────────────────────────────────────────────────────────────────

@app.route("/api/briefing", methods=["POST"])
def kirim_briefing():
    script = os.path.join(BASE, "daily_briefing.py")
    if not os.path.exists(script):
        return jsonify({"ok": False, "msg": f"Script tidak ditemukan: {script}"}), 404
    result = subprocess.run(
        [r"C:\Python314\python.exe", script],
        capture_output=True, text=True, timeout=30
    )
    if result.returncode == 0:
        return jsonify({"ok": True, "msg": "Briefing terkirim!"})
    return jsonify({"ok": False, "msg": result.stderr or "Unknown error"}), 500

# ── Chat AI ───────────────────────────────────────────────────────────────────

@app.route("/api/chat", methods=["POST"])
def chat():
    try:
        import ollama as ol
    except ImportError:
        return jsonify({"ok": False, "reply": "Ollama tidak terinstall. Jalankan: pip install ollama"}), 500
    data = request.json
    pesan = data.get("pesan", "").strip()
    if not pesan:
        return jsonify({"ok": False, "reply": "Pesan kosong"}), 400
    history = data.get("history", [])
    messages = history + [{"role": "user", "content": pesan}]
    try:
        response = ol.chat(model="qwen2.5:14b", messages=messages)
        return jsonify({"ok": True, "reply": response["message"]["content"]})
    except Exception as e:
        return jsonify({"ok": False, "reply": f"Error: {str(e)}"}), 500

# ── Flashcard ─────────────────────────────────────────────────────────────────

@app.route("/api/flashcard", methods=["POST"])
def generate_flashcard():
    try:
        import ollama as ol
    except ImportError:
        return jsonify({"ok": False, "kartu": [], "msg": "Ollama tidak terinstall"}), 500
    data = request.json
    teks = data.get("teks", "").strip()
    jumlah = min(max(int(data.get("jumlah", 10)), 3), 30)
    if not teks:
        return jsonify({"ok": False, "kartu": [], "msg": "Teks kosong"}), 400
    prompt = f"""Kamu adalah tutor Cybersecurity. Buat tepat {jumlah} flashcard dari teks berikut.

Format WAJIB untuk setiap flashcard (jangan ada format lain):
DEPAN: [pertanyaan singkat dan jelas]
BELAKANG: [jawaban singkat, padat, akurat]
---

Teks materi:
{teks[:4000]}

Buat {jumlah} flashcard sekarang:"""
    try:
        response = ol.chat(model="qwen2.5:14b", messages=[{"role": "user", "content": prompt}])
        raw = response["message"]["content"]
        kartu = []
        for blok in raw.split("---"):
            depan = belakang = ""
            for baris in blok.strip().split("\n"):
                if baris.startswith("DEPAN:"):
                    depan = baris.replace("DEPAN:", "").strip()
                elif baris.startswith("BELAKANG:"):
                    belakang = baris.replace("BELAKANG:", "").strip()
            if depan and belakang:
                kartu.append({"depan": depan, "belakang": belakang})
        return jsonify({"ok": True, "kartu": kartu})
    except Exception as e:
        return jsonify({"ok": False, "kartu": [], "msg": str(e)}), 500

# ── Buka App ──────────────────────────────────────────────────────────────────

@app.route("/api/buka/<app_name>", methods=["POST"])
def buka_app(app_name):
    apps = {
        "zotero":     r"C:\Program Files\Zotero\zotero.exe",
        "anki":       r"D:\AI_Workspace\Anki\anki.exe",
        "anythingllm": r"D:\AI_Workspace\AnythingLLM\AnythingLLM.exe",
    }
    path = apps.get(app_name)
    if not path:
        return jsonify({"ok": False, "msg": f"App tidak dikenal: {app_name}"}), 404
    if not os.path.exists(path):
        return jsonify({"ok": False, "msg": f"File tidak ditemukan: {path}"}), 404
    subprocess.Popen([path])
    return jsonify({"ok": True})

# ── Static ─────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return send_from_directory("static", "index.html")

@app.route("/<path:filename>")
def static_files(filename):
    return send_from_directory("static", filename)

# ── Main ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    os.makedirs("static", exist_ok=True)
    print("=" * 50)
    print("  Flowia OS — Backend Running")
    print("  http://localhost:5000")
    print("=" * 50)
    app.run(port=5000, debug=False, use_reloader=False)
