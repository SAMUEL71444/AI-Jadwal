import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from telegram import Bot

TOKEN = "8851029373:AAH6XGHA0RXmiAlAIh-UmuYa9U97uI86nd0"
CHAT_ID = "7440661416"    

# Path semua file sekarang di dashboard\ (satu folder dengan app.py)
BASE_DIR    = r"D:\AI_Workspace\dashboard"
FILE_TUGAS  = os.path.join(BASE_DIR, "tugas.json")
FILE_EVENTS = os.path.join(BASE_DIR, "events.json")
FILE_GOALS  = os.path.join(BASE_DIR, "goals.json")
FILE_LOG    = os.path.join(BASE_DIR, "briefing.log")
FILE_LAST   = os.path.join(BASE_DIR, "briefing_last.txt")

# Jam boleh kirim otomatis (tanpa --force): 06.00 – 09.59
JAM_MULAI   = 6
JAM_SELESAI = 9

# ── Jadwal kuliah ─────────────────────────────────────────────────────────────
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

HARI_INDO = {
    "Monday": "Senin", "Tuesday": "Selasa", "Wednesday": "Rabu",
    "Thursday": "Kamis", "Friday": "Jumat", "Saturday": "Sabtu", "Sunday": "Minggu",
}

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    filename=FILE_LOG,
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%d/%m/%Y %H:%M:%S",
    encoding="utf-8",
)

def log(msg: str):
    logging.info(msg)
    print(msg)

# ── Helper JSON ───────────────────────────────────────────────────────────────
def baca_json(path: str, default=None):
    if default is None:
        default = []
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        log(f"WARN: gagal baca {path}: {e}")
        return default

def tulis_json(path: str, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# ── Guard waktu ───────────────────────────────────────────────────────────────
def boleh_kirim(force: bool) -> bool:
    if force:
        return True
    jam = datetime.now().hour
    if JAM_MULAI <= jam <= JAM_SELESAI:
        return True
    log(f"SKIP: jam sekarang {jam:02d}:xx, di luar window {JAM_MULAI:02d}–{JAM_SELESAI:02d}. Gunakan --force untuk tes.")
    return False

# ── Anti duplikat ─────────────────────────────────────────────────────────────
def sudah_kirim_hari_ini(force: bool) -> bool:
    if force:
        return False
    hari_ini = datetime.now().strftime("%d/%m/%Y")
    if not os.path.exists(FILE_LAST):
        return False
    try:
        with open(FILE_LAST, "r") as f:
            return f.read().strip() == hari_ini
    except:
        return False

def tandai_sudah_kirim():
    with open(FILE_LAST, "w") as f:
        f.write(datetime.now().strftime("%d/%m/%Y"))

# ── Auto hapus tugas expired ──────────────────────────────────────────────────
def auto_hapus_expired() -> list:
    tugas = baca_json(FILE_TUGAS, [])
    sisa, expired = [], []
    now = datetime.now()
    for t in tugas:
        try:
            dl = datetime.strptime(t["deadline"], "%d/%m/%Y")
            if dl.date() < now.date() and not t.get("selesai", False):
                expired.append(t["nama"])
                continue
        except:
            pass
        sisa.append(t)
    if expired:
        tulis_json(FILE_TUGAS, sisa)
        log(f"Auto-hapus {len(expired)} tugas expired: {expired}")
    return expired

# ── Escape karakter MarkdownV2 ────────────────────────────────────────────────
def esc(text: str) -> str:
    """Escape karakter khusus MarkdownV2 Telegram."""
    for ch in r"\_*[]()~`>#+-=|{}.!":
        text = text.replace(ch, f"\\{ch}")
    return text

# ── Section: Jadwal ───────────────────────────────────────────────────────────
def section_jadwal() -> str:
    hari = HARI_INDO[datetime.now().strftime("%A")]
    jadwal = JADWAL.get(hari, [])
    if not jadwal:
        return f"📅 *Jadwal {hari}:*\n_Bebas kuliah hari ini\\!_ 🎉"
    baris = [f"📅 *Jadwal {hari}:*"]
    for j in jadwal:
        baris.append(f"  `{j['jam']}` {esc(j['mata_kuliah'])}")
        baris.append(f"  📍 {esc(j['ruang'])}")
    return "\n".join(baris)

# ── Section: Tugas ────────────────────────────────────────────────────────────
def section_tugas() -> str:
    tugas = baca_json(FILE_TUGAS, [])
    aktif = [t for t in tugas if not t.get("selesai", False)]
    if not aktif:
        return "📝 *Tugas Kuliah:*\n_Semua bersih\\!_ ✅"

    aktif.sort(key=lambda x: datetime.strptime(x["deadline"], "%d/%m/%Y"))
    baris = ["📝 *Tugas Kuliah:*"]
    for t in aktif:
        try:
            dl = datetime.strptime(t["deadline"], "%d/%m/%Y")
            sisa = (dl.date() - datetime.now().date()).days
        except:
            sisa = None

        if sisa is None:       label = ""
        elif sisa < 0:         label = " ❌ Terlambat\\!"
        elif sisa == 0:        label = " 🚨 *HARI INI\\!*"
        elif sisa == 1:        label = " ⚠️ *BESOK\\!*"
        elif sisa <= 3:        label = f" ⚡ {sisa} hari lagi"
        else:                  label = f" · {sisa} hari lagi"

        prio = t.get("prioritas", "normal")
        prio_icon = "🔴" if prio == "tinggi" else ("🟡" if prio == "normal" else "🟢")

        baris.append(f"  {prio_icon} *{esc(t['nama'])}*{label}")
        baris.append(f"     _{esc(t['matkul'])}_ · {esc(t['deadline'])}")
        if t.get("catatan"):
            baris.append(f"     💬 {esc(t['catatan'])}")

    return "\n".join(baris)

# ── Section: Events ───────────────────────────────────────────────────────────
def section_events() -> str:
    events = baca_json(FILE_EVENTS, [])
    aktif = [e for e in events if not e.get("selesai", False)]
    if not aktif:
        return ""

    now = datetime.now()
    def sisa_event(e):
        try:
            return (datetime.strptime(e["deadline"], "%d/%m/%Y").date() - now.date()).days
        except:
            return 999

    aktif.sort(key=sisa_event)
    baris = ["🏆 *Events & Lomba:*"]
    for e in aktif[:5]:
        sisa = sisa_event(e)
        icon = {
            "lomba_ai": "🤖", "ctf": "🔐", "hackathon": "💻",
            "jurnal": "📄", "bisnis": "💼", "organisasi": "🏛️",
        }.get(e.get("kategori", ""), "📌")

        if sisa < 0:     label = "❌ Lewat"
        elif sisa == 0:  label = "🚨 *HARI INI\\!*"
        elif sisa == 1:  label = "⚠️ *BESOK\\!*"
        elif sisa <= 7:  label = f"⚡ {sisa} hari lagi"
        else:            label = f"· {sisa} hari lagi"

        baris.append(f"  {icon} *{esc(e['nama'])}* {label}")
        if e.get("peran"):
            baris.append(f"     Peran: _{esc(e['peran'])}_")
        if e.get("catatan"):
            baris.append(f"     💬 {esc(e['catatan'])}")

    return "\n".join(baris)

# ── Section: Goals ────────────────────────────────────────────────────────────
def section_goals() -> str:
    goals = baca_json(FILE_GOALS, [])
    aktif = [g for g in goals if not g.get("selesai", False)]
    if not aktif:
        return ""

    baris = ["🎯 *Goals Aktif:*"]
    for g in aktif[:3]:
        progress = g.get("progress", 0)
        bar = "█" * (progress // 10) + "░" * (10 - progress // 10)
        baris.append(f"  • *{esc(g['nama'])}* \\[{bar}\\] {progress}%")

    return "\n".join(baris)

# ── Section: Motivasi ─────────────────────────────────────────────────────────
def section_motivasi() -> str:
    from random import choice
    quotes = [
        "Lomba AI bukan soal siapa yang paling pintar — tapi siapa yang paling konsisten iterasi.",
        "Satu eksperimen kecil hari ini lebih baik dari rencana besar yang tidak dimulai.",
        "Bisnis yang baik dimulai dari masalah nyata. Kamu punya akses ke masalah nyata setiap hari.",
        "CTF itu mental game. Kalau stuck, tidur dulu — otak kamu masih kerja.",
        "Research methodology bukan hambatan, itu senjata. Kamu lagi diasah sekarang.",
        "Juara bukan yang tidak pernah gagal — tapi yang paling cepat pivot setelah gagal.",
        "Setiap tugas yang selesai hari ini adalah beban yang tidak kamu bawa besok.",
        "Ide bisnis terbaik lahir dari obsesi, bukan inspirasi sesaat. Terus building.",
        "Kamu sedang membangun sistem hidup yang bahkan para profesional belum punya.",
    ]
    return f'💡 *Quote hari ini:*\n_{esc(choice(quotes))}_'

# ── Bangun pesan lengkap ──────────────────────────────────────────────────────
def bangun_pesan(expired: list) -> str:
    now = datetime.now()
    hari_en = now.strftime("%A")
    hari_id = HARI_INDO.get(hari_en, hari_en)
    tanggal = f"{hari_id}, {now.strftime('%d/%m/%Y')}"

    jam = now.hour
    salam = "Selamat pagi" if jam < 12 else ("Selamat siang" if jam < 17 else "Selamat malam")

    bagian = [
        f"🌅 *{salam}, Koman\\!*",
        f"_{tanggal}_",
        "─────────────────────",
        section_jadwal(),
        "─────────────────────",
        section_tugas(),
    ]

    events_txt = section_events()
    if events_txt:
        bagian += ["─────────────────────", events_txt]

    goals_txt = section_goals()
    if goals_txt:
        bagian += ["─────────────────────", goals_txt]

    if expired:
        exp_list = "\n".join(f"  • {esc(n)}" for n in expired)
        bagian += [
            "─────────────────────",
            f"🗑️ *Auto\\-hapus expired:*\n{exp_list}",
        ]

    bagian += [
        "─────────────────────",
        section_motivasi(),
    ]

    return "\n\n".join(bagian)

# ── Kirim ke Telegram ─────────────────────────────────────────────────────────
async def kirim(force: bool):
    if not boleh_kirim(force):
        return
    if sudah_kirim_hari_ini(force):
        log("SKIP: briefing sudah terkirim hari ini.")
        return

    expired = auto_hapus_expired()
    pesan   = bangun_pesan(expired)

    try:
        bot = Bot(token=TOKEN)
        await bot.send_message(
            chat_id=CHAT_ID,
            text=pesan,
            parse_mode="MarkdownV2",
        )
        tandai_sudah_kirim()
        log("OK: briefing terkirim.")
    except Exception as e:
        log(f"ERROR kirim Telegram: {e}")
        raise

# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    force = "--force" in sys.argv
    asyncio.run(kirim(force))