"""
FLOWIA OS — evening_alert.py
Kirim alert Telegram jam 20.00 HANYA kalau ada deadline mendesak (≤ 3 hari).
Taruh di: D:\AI_Workspace\dashboard\
Jalankan manual untuk test: python evening_alert.py --force
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime

from telegram import Bot

# ── Konfigurasi ───────────────────────────────────────────────────────────────
TOKEN   = "ISI_TOKEN_BOT_TELEGRAM_KAMU"
CHAT_ID = "ISI_CHAT_ID_KAMU"

BASE_DIR    = r"D:\AI_Workspace\dashboard"
FILE_TUGAS  = os.path.join(BASE_DIR, "tugas.json")
FILE_EVENTS = os.path.join(BASE_DIR, "events.json")
FILE_LOG    = os.path.join(BASE_DIR, "evening_alert.log")
FILE_LAST   = os.path.join(BASE_DIR, "evening_last.txt")

# Jam boleh kirim otomatis (tanpa --force): 19.00 – 21.59
JAM_MULAI   = 19
JAM_SELESAI = 21

# Batas hari untuk dianggap mendesak
BATAS_HARI_TUGAS  = 3   # tugas deadline <= 3 hari
BATAS_HARI_EVENTS = 7   # event deadline <= 7 hari

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

# ── Helper ────────────────────────────────────────────────────────────────────
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

def sisa_hari(deadline_str: str):
    try:
        dl = datetime.strptime(deadline_str.strip(), "%d/%m/%Y")
        return (dl.date() - datetime.now().date()).days
    except:
        return None

def esc(text: str) -> str:
    for ch in r"\_*[]()~`>#+-=|{}.!":
        text = text.replace(ch, f"\\{ch}")
    return text

# ── Guard waktu ───────────────────────────────────────────────────────────────
def boleh_kirim(force: bool) -> bool:
    if force:
        return True
    jam = datetime.now().hour
    if JAM_MULAI <= jam <= JAM_SELESAI:
        return True
    log(f"SKIP: jam {jam:02d}:xx di luar window {JAM_MULAI}–{JAM_SELESAI}. Pakai --force untuk test.")
    return False

# ── Anti duplikat ─────────────────────────────────────────────────────────────
def sudah_kirim_malam_ini(force: bool) -> bool:
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

# ── Kumpulkan item mendesak ───────────────────────────────────────────────────
def cari_tugas_mendesak():
    tugas = baca_json(FILE_TUGAS, [])
    hasil = []
    for t in tugas:
        if t.get("selesai"):
            continue
        sisa = sisa_hari(t.get("deadline", ""))
        if sisa is not None and sisa <= BATAS_HARI_TUGAS:
            hasil.append({
                "nama":     t["nama"],
                "sub":      t.get("matkul", ""),
                "deadline": t.get("deadline", ""),
                "sisa":     sisa,
                "tipe":     "tugas",
                "prioritas": t.get("prioritas", "normal"),
            })
    return sorted(hasil, key=lambda x: x["sisa"])

def cari_events_mendesak():
    events = baca_json(FILE_EVENTS, [])
    hasil = []
    for e in events:
        if e.get("selesai"):
            continue
        sisa = sisa_hari(e.get("deadline", ""))
        if sisa is not None and sisa <= BATAS_HARI_EVENTS:
            hasil.append({
                "nama":     e["nama"],
                "sub":      e.get("peran", ""),
                "deadline": e.get("deadline", ""),
                "sisa":     sisa,
                "tipe":     "event",
                "kategori": e.get("kategori", ""),
            })
    return sorted(hasil, key=lambda x: x["sisa"])

# ── Format label sisa hari ────────────────────────────────────────────────────
def label_sisa(sisa: int) -> str:
    if sisa < 0:   return "❌ *LEWAT DEADLINE*"
    if sisa == 0:  return "🚨 *HARI INI\\!*"
    if sisa == 1:  return "🔥 *BESOK\\!*"
    if sisa == 2:  return "⚠️ *2 hari lagi*"
    if sisa == 3:  return "⚡ 3 hari lagi"
    return f"· {sisa} hari lagi"

# ── Bangun pesan ──────────────────────────────────────────────────────────────
def bangun_pesan(tugas_list, events_list) -> str:
    bagian = [
        "🌙 *Evening Alert — Flowia OS*",
        f"_{datetime.now().strftime('%d/%m/%Y %H:%M')}_",
        "─────────────────────",
    ]

    # Tugas mendesak
    if tugas_list:
        bagian.append("📝 *Tugas Mendesak:*")
        for t in tugas_list:
            prio_icon = "🔴" if t["prioritas"] == "tinggi" else "🟡"
            bagian.append(f"  {prio_icon} *{esc(t['nama'])}* — {label_sisa(t['sisa'])}")
            bagian.append(f"     _{esc(t['sub'])}_ · {esc(t['deadline'])}")
    
    if tugas_list and events_list:
        bagian.append("─────────────────────")

    # Events mendesak
    if events_list:
        bagian.append("🏆 *Events Mendesak:*")
        for e in events_list:
            icon = {
                "lomba_ai": "🤖", "ctf": "🔐", "hackathon": "💻",
                "jurnal": "📄", "bisnis": "💼", "organisasi": "🏛️",
            }.get(e["kategori"], "📌")
            bagian.append(f"  {icon} *{esc(e['nama'])}* — {label_sisa(e['sisa'])}")
            if e["sub"]:
                bagian.append(f"     Peran: _{esc(e['sub'])}_")

    bagian += [
        "─────────────────────",
        "💪 _Selesaikan yang bisa diselesaikan malam ini\\!_",
    ]

    return "\n\n".join(bagian)

# ── Main ──────────────────────────────────────────────────────────────────────
async def kirim(force: bool):
    if not boleh_kirim(force):
        return
    if sudah_kirim_malam_ini(force):
        log("SKIP: evening alert sudah terkirim hari ini.")
        return

    tugas_list  = cari_tugas_mendesak()
    events_list = cari_events_mendesak()

    # Tidak ada yang mendesak = tidak kirim sama sekali
    if not tugas_list and not events_list:
        log("SKIP: tidak ada deadline mendesak. Tidak perlu kirim.")
        tandai_sudah_kirim()
        return

    pesan = bangun_pesan(tugas_list, events_list)
    log(f"Mengirim alert: {len(tugas_list)} tugas, {len(events_list)} events mendesak")

    try:
        bot = Bot(token=TOKEN)
        await bot.send_message(
            chat_id=CHAT_ID,
            text=pesan,
            parse_mode="MarkdownV2",
        )
        tandai_sudah_kirim()
        log("OK: evening alert terkirim.")
    except Exception as e:
        log(f"ERROR: {e}")
        raise

if __name__ == "__main__":
    force = "--force" in sys.argv
    asyncio.run(kirim(force))
