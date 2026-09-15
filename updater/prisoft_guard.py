#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ตัวเฝ้า Prisoft ให้พร้อมใช้งานตลอดเวลา (รันบนคอม PRISOFT-SERVER ทุก 1 นาที)
---------------------------------------------------------------------------
ทำแทนคนที่ต้องมาเปิดโปรแกรม Prisoft แล้วกด OFF -> ON:

  1. หลังเครื่องรีสตาร์ท  -> แจ้ง Telegram ว่ารีสตาร์ทเพราะอะไร แล้วรอให้ Prisoft เปิดเอง
                           (Primus-task-control อยู่ใน Startup และตั้ง autostart ไว้)
                           ถ้าครบเวลาแล้ว Backend ยังไม่ขึ้น -> เปิดให้เอง
  2. Backend หายไประหว่างวัน -> เปิดใหม่ให้เอง
  3. ระบบรันอยู่แต่ค่าไม่มา  -> ส่งข้อความพร้อมปุ่มให้เลือก
        🔄 รีเซต Prisoft (OFF -> ON)   🔧 PM / ย้ายเครื่องจักร / ดับไฟ   ✖️ ไม่ต้องทำอะไร
     ไม่มีใครกดภายใน auto_reset_minutes -> รีเซตให้เองหนึ่งครั้ง
  4. ค่ากลับมา -> แจ้งว่ากลับมาปกติ แล้วล้างสถานะ (ออกจากโหมด PM อัตโนมัติ)

"รีเซต" = ปิด Primus-task-control (ปิด Backend ที่มันเปิดไว้ไปด้วย) แล้วเปิดใหม่
ให้ autostart ของโปรแกรมเปิด Backend เอง — หน้าจอ Prisoft จึงยังแสดงสถานะถูกต้อง
ถ้าเปิดโปรแกรมแล้ว Backend ไม่ขึ้น จะสั่ง `node backend/server.js` เองเป็นทางสำรอง
(ปุ่ม Database กดแล้วไม่มีผลบนเครื่องนี้ เพราะ MongoDB รันเป็น Windows service อยู่แล้ว)

ปุ่มใน Telegram ถูกรับโดย telegram_listener.py แล้วเขียนคำสั่งลง .prisoft_request.json
ตัวนี้อ่านคำสั่งทุกรอบแล้วทำตาม

ใช้งาน:
  pythonw prisoft_guard.py            รอบปกติ (Task Scheduler เรียกทุก 1 นาที)
  python  prisoft_guard.py --status   ดูสถานะ ไม่แก้อะไร
  python  prisoft_guard.py --reset    รีเซต Prisoft เดี๋ยวนี้
  python  prisoft_guard.py --ask      ส่งข้อความพร้อมปุ่มเข้า Telegram (ทดสอบปุ่ม)
  python  prisoft_guard.py --init     ใช้ตอนติดตั้ง (จำเวลาบูตปัจจุบัน)
"""
import json, os, sys, time, socket, pathlib, datetime, subprocess, ctypes

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# เครื่องหลัง proxy ที่ตรวจ SSL -> ข้าม verify เฉพาะเครื่องนี้ (แบบเดียวกับ listener)
if os.environ.get("TELEGRAM_INSECURE_SSL") == "1" or os.environ.get("PYTHONHTTPSVERIFY") == "0":
    try:
        import ssl as _ssl
        _ssl._create_default_https_context = _ssl._create_unverified_context
    except Exception:
        pass

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import telegram_alert as TA

TZ = datetime.timezone(datetime.timedelta(hours=7))
STATE   = HERE / ".prisoft_guard_state.json"
REQUEST = HERE / ".prisoft_request.json"
LOG     = HERE / "prisoft_guard.log"
BACKEND_LOG = HERE / "prisoft_backend.log"

# ---- ค่าตั้งต้น (แก้ได้ใน telegram_config.json -> "guard": {...}) -------------------
DEFAULTS = {
    "prisoft_dir": r"C:\Primus\Prisoft",
    "gui_exe": r"C:\Primus\Prisoft\Primus-task-control-win32-x64\Primus-task-control.exe",
    "node_exe": r"C:\nvm4w\nodejs\node.exe",
    "backend_args": ["--max-old-space-size=4096", "backend/server.js"],
    "backend_port": 5000,
    "boot_grace_minutes": 4,        # หลังเปิดเครื่อง รอให้ Prisoft เปิดเองก่อน
    "missing_minutes": 2,           # Backend หายนานเท่านี้ค่อยลงมือ
    "stale_minutes": 15,            # ค่าไม่มาเกินเท่านี้ -> ถามด้วยปุ่ม
    "auto_reset_minutes": 30,       # ถามแล้วไม่มีใครตอบ -> รีเซตเองเมื่อค่าหายครบเท่านี้ (0 = ไม่รีเซตเอง)
    "reprompt_minutes": 60,         # ยังไม่หาย -> ถามซ้ำทุกเท่านี้
    "updater_task": "ITH_Bearing_Temp_Update",
}
NO_WINDOW = 0x08000000
NEW_GROUP = 0x00000200
BREAKAWAY = 0x01000000


# ------------------------------------------------------------------ พื้นฐาน
def now():
    return time.time()


def hhmm(ts=None):
    return datetime.datetime.fromtimestamp(ts or now(), TZ).strftime("%H:%M")


def dmyhm(ts=None):
    return datetime.datetime.fromtimestamp(ts or now(), TZ).strftime("%d/%m/%Y %H:%M")


def log(msg):
    line = f"{datetime.datetime.now(TZ):%Y-%m-%d %H:%M:%S} {msg}"
    try:
        print(line)
    except Exception:
        pass
    try:
        if LOG.exists() and LOG.stat().st_size > 1_000_000:        # เก็บไว้ไม่เกิน ~1 MB
            LOG.replace(LOG.with_suffix(".old.log"))
        with LOG.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def load_json(p, default):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return default


def save_json(p, obj):
    try:
        p.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        log(f"write {p.name} failed: {e}")


def settings(cfg):
    s = dict(DEFAULTS)
    s.update((cfg or {}).get("guard") or {})
    return s


def uptime_sec():
    try:
        k = ctypes.windll.kernel32
        k.GetTickCount64.restype = ctypes.c_ulonglong
        return k.GetTickCount64() / 1000.0
    except Exception:
        return 10 ** 9


def minutes(sec):
    return int(round(sec / 60))


def human_dur(sec):
    m = minutes(sec)
    if m < 90:
        return f"{m} นาที"
    h, mm = divmod(m, 60)
    return f"{h} ชม. {mm} นาที"


# ------------------------------------------------------------------ Telegram
def tg_broadcast(cfg, text, markup=None):
    out = {}
    if not cfg:
        return out
    for chat in cfg.get("chat_ids") or []:
        body = {"chat_id": chat, "text": text[:4000], "disable_web_page_preview": True}
        if markup:
            body["reply_markup"] = markup
        r = TA.call(cfg, "sendMessage", body)
        if r and r.get("ok"):
            out[str(chat)] = r["result"]["message_id"]
    return out


def tg_edit(cfg, msgs, text):
    for chat, mid in (msgs or {}).items():
        TA.call(cfg, "editMessageText", {"chat_id": int(chat), "message_id": mid,
                                         "text": text[:4000], "disable_web_page_preview": True})


BUTTONS = {"inline_keyboard": [
    [{"text": "🔄 รีเซต Prisoft (OFF → ON)", "callback_data": "pg_reset"}],
    [{"text": "🔧 PM / ย้ายเครื่องจักร / ดับไฟ", "callback_data": "pg_pm"}],
    [{"text": "✖️ ไม่ต้องทำอะไร", "callback_data": "pg_ignore"}],
]}


# ------------------------------------------------------------------ สำรวจเครื่อง
def processes():
    """คืนรายการ node.exe / Primus-task-control.exe พร้อม command line
    คืน None ถ้าอ่านไม่ได้ — ห้ามตีความว่า "ไม่มีโปรแกรมรันอยู่" เด็ดขาด (จะไปปิด/เปิดซ้ำโดยไม่จำเป็น)"""
    ps = ("Get-CimInstance Win32_Process -Filter \"Name='node.exe' or Name='Primus-task-control.exe'\" | "
          "Select-Object ProcessId,ParentProcessId,Name,CommandLine | ConvertTo-Json -Compress")
    try:
        out = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True,
                             text=True, encoding="utf-8", errors="replace",
                             timeout=60, creationflags=NO_WINDOW).stdout.strip()
        if not out:
            return []
        data = json.loads(out)
        return data if isinstance(data, list) else [data]
    except Exception as e:
        log(f"process list failed: {e}")
        return None


def backend_pids(procs):
    return [p["ProcessId"] for p in (procs or []) if (p.get("Name") or "").lower() == "node.exe"
            and "server.js" in (p.get("CommandLine") or "").replace("\\", "/")
            and "backend/server.js" in (p.get("CommandLine") or "").replace("\\", "/")]


def gui_pids(procs):
    return [p["ProcessId"] for p in (procs or []) if (p.get("Name") or "") == "Primus-task-control.exe"
            and "--type=" not in (p.get("CommandLine") or "")]


def port_open(port):
    try:
        with socket.create_connection(("127.0.0.1", int(port)), timeout=3):
            return True
    except Exception:
        return False


def backend_ok(s, procs=None):
    """พอร์ต Backend ตอบ = ทำงานอยู่ (ไม่ต้องพึ่งรายชื่อ process ที่อาจอ่านพลาด)"""
    return port_open(s["backend_port"])


def data_age():
    """(อายุค่าล่าสุดที่อ่านได้จริง, อายุไฟล์ temps.json) เป็นวินาที"""
    d = load_json(TA.TEMPS_JSON, {})
    newest = 0.0
    for cards in (d.get("groups") or {}).values():
        for it in cards:
            if it.get("value") is None:
                continue
            try:
                newest = max(newest, datetime.datetime.fromisoformat(it.get("seen")).timestamp())
            except Exception:
                pass
    try:
        upd = datetime.datetime.fromisoformat(d.get("updated")).timestamp()
    except Exception:
        upd = 0.0
    t = now()
    return (t - newest if newest else 10 ** 9), (t - upd if upd else 10 ** 9)


def boot_reason():
    """เดาสาเหตุการรีสตาร์ทล่าสุดจาก Event Log"""
    ps = ("$b=(Get-CimInstance Win32_OperatingSystem).LastBootUpTime;"
          "$e=Get-WinEvent -FilterHashtable @{LogName='System';Id=1074,6008,41;StartTime=$b.AddHours(-12);EndTime=$b} "
          "-MaxEvents 5 -ErrorAction SilentlyContinue | Sort-Object TimeCreated -Descending | Select-Object -First 1;"
          "if($e){ '' + $e.Id + '|' + ($e.Message -replace '\\s+',' ') }")
    try:
        out = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True,
                             encoding="utf-8", errors="replace", timeout=60,
                             creationflags=NO_WINDOW).stdout.strip()
    except Exception:
        out = ""
    low = out.lower()
    if not out:
        return "ไม่ทราบสาเหตุ"
    if "mousocoreworker" in low or "trustedinstaller" in low or "wuauclt" in low or "upgrade" in low \
            or "service pack" in low:
        return "Windows Update รีสตาร์ทเครื่องเอง"
    if out.startswith("41|") or out.startswith("6008|"):
        return "เครื่องดับกะทันหัน (ไฟดับ/ไฟตก หรือเครื่องค้าง)"
    if "winlogon" in low and "power off" in low:
        return "เครื่องถูกสั่งปิด (น่าจะกดปุ่ม Power) แล้วเปิดใหม่"
    if "power off" in low:
        return "มีการสั่งปิดเครื่อง แล้วเปิดใหม่"
    return "มีการสั่งรีสตาร์ทเครื่อง"


# ------------------------------------------------------------------ ลงมือ
def _spawn(args, cwd, stdout=None):
    flags = NO_WINDOW | NEW_GROUP
    for extra in (BREAKAWAY, 0):              # หลุดจาก job ของ Task Scheduler ถ้าทำได้
        try:
            return subprocess.Popen(args, cwd=cwd, creationflags=flags | extra, close_fds=True,
                                    stdin=subprocess.DEVNULL, stdout=stdout or subprocess.DEVNULL,
                                    stderr=subprocess.STDOUT)
        except OSError:
            continue
    return None


def start_gui(s):
    exe = pathlib.Path(s["gui_exe"])
    if not exe.exists():
        log(f"GUI not found: {exe}")
        return False
    flags = NEW_GROUP
    for extra in (BREAKAWAY, 0):
        try:
            subprocess.Popen([str(exe)], cwd=str(exe.parent), creationflags=flags | extra, close_fds=True)
            log("started Primus-task-control")
            return True
        except OSError:
            continue
    return False


def start_backend_direct(s):
    node = s["node_exe"] if pathlib.Path(s["node_exe"]).exists() else "node"
    try:
        f = BACKEND_LOG.open("a", encoding="utf-8")
        f.write(f"\n==== {dmyhm()} started by prisoft_guard ====\n")
        f.flush()
    except Exception:
        f = None
    p = _spawn([node] + list(s["backend_args"]), s["prisoft_dir"], stdout=f)
    log(f"started backend directly pid={p.pid if p else None}")
    return p is not None


def kill_pid(pid):
    subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True,
                   timeout=30, creationflags=NO_WINDOW)


def wait_backend(s, seconds):
    end = now() + seconds
    while now() < end:
        if backend_ok(s):
            return True
        time.sleep(5)
    return False


def recover(s, full_reset):
    """เปิด Backend ให้ขึ้น — full_reset=True คือ OFF ทั้งหมดก่อนแล้วค่อย ON (เหมือนคนกด)
    คืน (สำเร็จไหม, วิธีที่ใช้)"""
    procs = processes()
    if procs is None:
        return False, "อ่านรายชื่อโปรแกรมในเครื่องไม่ได้ จึงไม่ได้สั่งปิด/เปิดอะไร"
    if full_reset:
        for pid in gui_pids(procs):
            kill_pid(pid)                    # /T ปิด Backend ที่โปรแกรมเปิดไว้ไปด้วย
        for pid in backend_pids(processes()):
            kill_pid(pid)                    # เผื่อ Backend ที่ไม่ได้เป็นลูกของโปรแกรม
        # ปิด Primus-task-control แล้วรอพอร์ตปิดจริง ก่อนเปิดใหม่ (กัน Backend ตัวใหม่ชนพอร์ต)
        for _ in range(12):
            if not port_open(s["backend_port"]):
                break
            time.sleep(2)
        log("reset: everything OFF")
        time.sleep(8)
        procs = processes()
    else:
        for pid in backend_pids(procs):      # มี process แต่พอร์ตไม่ตอบ = ค้าง
            if not port_open(s["backend_port"]):
                kill_pid(pid)
        procs = processes()
        if procs is None:
            return False, "อ่านรายชื่อโปรแกรมในเครื่องไม่ได้"

    guis = gui_pids(procs)
    if guis and not backend_pids(procs):
        for pid in guis:                     # เปิดโปรแกรมค้างไว้แต่ Backend ไม่ขึ้น -> เปิดโปรแกรมใหม่
            kill_pid(pid)
        time.sleep(3)
        guis = []
    if not guis:
        start_gui(s)
        if wait_backend(s, 90):
            return True, "เปิดโปรแกรม Prisoft ใหม่ (Backend เปิดเองตาม autostart)"
    elif wait_backend(s, 30):
        return True, "Backend กลับมาเอง"

    if not backend_pids(processes()):
        start_backend_direct(s)
        if wait_backend(s, 90):
            return True, "สั่งเปิด Backend โดยตรง (หน้าจอ Prisoft อาจแสดง OFF แต่ระบบทำงานอยู่)"
    return False, "เปิด Backend ไม่สำเร็จ"


# ------------------------------------------------------------------ รอบการทำงาน
def do_reset(cfg, s, st, who):
    t0 = now()
    msgs = st.get("prompt_msgs") or {}
    if msgs:
        tg_edit(cfg, msgs, f"🔄 กำลังรีเซต Prisoft (OFF → ON) · สั่งโดย {who} · {hhmm()} น.")
    else:
        tg_broadcast(cfg, f"🔄 กำลังรีเซต Prisoft (OFF → ON) · สั่งโดย {who} · {hhmm()} น.")
    ok, how = recover(s, full_reset=True)
    st.update(last_reset=now(), last_action=now())
    log(f"reset by {who}: ok={ok} ({how})")
    if ok:
        tg_broadcast(cfg, f"✅ รีเซต Prisoft เสร็จ ({human_dur(now() - t0)})\n{how}\n"
                          f"กำลังรอค่าใหม่ในรอบอัปเดตถัดไป (~5 นาที) — ค่ากลับมาแล้วจะแจ้งอีกครั้ง")
    else:
        tg_broadcast(cfg, "❌ รีเซต Prisoft ไม่สำเร็จ — Backend ไม่ขึ้น\n"
                          "ต้องให้คนเข้าไปดูที่เครื่อง PRISOFT-SERVER (192.168.101.9)\n"
                          f"ดูรายละเอียดใน {BACKEND_LOG}")
    return ok


def handle_request(cfg, s, st):
    req = load_json(REQUEST, None)
    if not req:
        return
    try:
        REQUEST.unlink()
    except Exception:
        pass
    action, who = req.get("action"), req.get("who") or "ไม่ทราบชื่อ"
    if now() - float(req.get("ts", 0)) > 3600:
        log(f"ignore old request {action}")
        return
    log(f"request {action} from {who}")
    msgs = st.get("prompt_msgs") or {}
    if action == "pg_reset":
        st["answered"] = "reset"
        do_reset(cfg, s, st, who)
    elif action == "pg_pm":
        st.update(pm={"since": now(), "who": who}, answered="pm")
        text = (f"🔧 โหมด PM / ย้ายเครื่องจักร / ดับไฟ · โดย {who} · {hhmm()} น.\n"
                "หยุดถามและไม่รีเซตอัตโนมัติ จนกว่าค่าจะกลับมาเอง (ระบบจะแจ้งเมื่อกลับมา)\n"
                "ถ้าอุณหภูมิเกิน 80°C ยังเตือนตามปกติ")
        if msgs:
            tg_edit(cfg, msgs, text)
        else:
            tg_broadcast(cfg, text)
    elif action == "pg_ignore":
        st["answered"] = "ignore"
        text = (f"✖️ {who} เลือกไม่ต้องทำอะไร · {hhmm()} น.\n"
                "จะไม่รีเซตอัตโนมัติในรอบนี้ — ถ้ายังไม่มีค่าจะถามอีกครั้งภายหลัง")
        if msgs:
            tg_edit(cfg, msgs, text)
        else:
            tg_broadcast(cfg, text)
        st["prompted_at"] = now()


def check_boot(cfg, s, st):
    up = uptime_sec()
    boot = now() - up
    if abs(boot - float(st.get("boot_ts", 0))) > 300:          # เปิดเครื่องใหม่ตั้งแต่รอบก่อน
        reason = boot_reason()
        st.update(boot_ts=boot, boot_pending=True, boot_reason=reason,
                  missing_since=None, answered=None, prompt_msgs={}, prompted_at=0,
                  stale_since=None, auto_reset_done=False)
        log(f"new boot at {dmyhm(boot)} ({reason})")
        tg_broadcast(cfg, f"🔁 คอม PRISOFT-SERVER เปิดใหม่เมื่อ {dmyhm(boot)} น.\n"
                          f"สาเหตุ: {reason}\n"
                          "ระบบกำลังเปิด Prisoft ให้อัตโนมัติ — ไม่ต้องมีคนไปกด ON")
    return up


def ensure_backend(cfg, s, st, up):
    if backend_ok(s):
        if st.get("missing_since"):
            log("backend is back")
        st["missing_since"] = None
        if st.get("boot_pending"):
            st.update(boot_pending=False)
            tg_broadcast(cfg, f"✅ Prisoft Backend ทำงานแล้ว (หลังเปิดเครื่อง {human_dur(up)})\n"
                              "ค่าอุณหภูมิจะกลับมาในรอบอัปเดตถัดไป (~5 นาที)")
        return True
    if up < s["boot_grace_minutes"] * 60:
        return False                                  # ให้ Prisoft เปิดเองตาม Startup ก่อน
    st["missing_since"] = st.get("missing_since") or now()
    if now() - st["missing_since"] < s["missing_minutes"] * 60:
        return False
    if now() - float(st.get("last_action", 0)) < 180:
        return False                                  # เพิ่งลงมือไป รอผลก่อน
    if processes() is None:
        log("backend port closed but process list unreadable -> skip this round")
        return False
    st["last_action"] = now()
    log("backend missing -> recover")
    ok, how = recover(s, full_reset=False)
    st["fail_count"] = 0 if ok else int(st.get("fail_count", 0)) + 1
    if ok:
        st.update(missing_since=None)
        if st.get("boot_pending"):
            st.update(boot_pending=False)
            tg_broadcast(cfg, f"✅ เปิด Prisoft ให้อัตโนมัติแล้ว (หลังเปิดเครื่อง {human_dur(uptime_sec())})\n{how}")
        else:
            tg_broadcast(cfg, f"⚠️ Prisoft Backend หยุดทำงาน — เปิดกลับให้อัตโนมัติแล้ว {hhmm()} น.\n{how}")
    elif st["fail_count"] in (1, 5, 20):
        tg_broadcast(cfg, f"❌ Prisoft Backend ไม่ทำงาน และเปิดอัตโนมัติไม่สำเร็จ (ครั้งที่ {st['fail_count']})\n"
                          "ต้องให้คนเข้าไปดูที่เครื่อง PRISOFT-SERVER (192.168.101.9)")
    return ok


def check_data(cfg, s, st, up):
    val_age, file_age = data_age()

    # ตัวดึงค่าเองหยุด (temps.json ไม่อัปเดต) -> สั่งให้ทำงาน ไม่ใช่ความผิดของ Prisoft
    if file_age > 15 * 60 and up > 10 * 60 and now() - float(st.get("updater_kick", 0)) > 15 * 60:
        st["updater_kick"] = now()
        log("temps.json old -> run updater task")
        subprocess.run(["schtasks", "/Run", "/TN", s["updater_task"]], capture_output=True,
                       timeout=30, creationflags=NO_WINDOW)

    stale = val_age >= s["stale_minutes"] * 60
    pm = st.get("pm")
    if not stale and pm and not pm.get("saw_stale"):
        # กดโหมด PM ไว้ล่วงหน้าตอนค่ายังปกติ -> รอให้งานเริ่ม (ค่าหาย) ก่อน ถ้าไม่เกิดใน 12 ชม. ก็ล้างทิ้งเงียบๆ
        if now() - float(pm.get("since", 0)) > 12 * 3600:
            st["pm"] = None
        return
    if not stale:
        if st.get("stale_since") or pm:
            gone = now() - float(st.get("stale_since") or (st.get("pm") or {}).get("since") or now())
            extra = "\nออกจากโหมด PM อัตโนมัติ" if st.get("pm") else ""
            text = f"✅ ค่าอุณหภูมิกลับมาแล้ว {hhmm()} น. (ขาดไป ~{human_dur(gone)}){extra}"
            if st.get("prompt_msgs") and not st.get("answered"):
                tg_edit(cfg, st["prompt_msgs"], text)
            else:
                tg_broadcast(cfg, text)
            log("data is back")
        st.update(stale_since=None, pm=None, answered=None, prompt_msgs={}, prompted_at=0,
                  auto_reset_done=False)
        return

    if up < 15 * 60:
        return                                         # เพิ่งเปิดเครื่อง ให้เวลาระบบเริ่มก่อน
    st["stale_since"] = st.get("stale_since") or (now() - val_age)
    if st.get("pm"):
        st["pm"]["saw_stale"] = True
        return                                         # งาน PM -> เงียบจนกว่าค่ากลับมา

    lost = now() - st["stale_since"]
    if not st.get("prompted_at") or (now() - st["prompted_at"] > s["reprompt_minutes"] * 60
                                     and st.get("answered") in (None, "ignore")):
        auto = s["auto_reset_minutes"]
        tail = (f"\n\nถ้าไม่มีใครกดภายใน ~{max(1, minutes(auto * 60 - lost))} นาที ระบบจะรีเซตให้เอง"
                if auto and not st.get("auto_reset_done") and st.get("answered") != "ignore" else "")
        backend = "ทำงานอยู่" if backend_ok(s) else "ไม่ทำงาน"
        st["prompt_msgs"] = tg_broadcast(
            cfg, f"⚠️ ค่าอุณหภูมิไม่เข้ามา {human_dur(lost)} (ตั้งแต่ {hhmm(st['stale_since'])} น.)\n"
                 f"Prisoft Backend: {backend}\n\nเกิดจากอะไรครับ?{tail}", BUTTONS)
        st.update(prompted_at=now(), answered=None if st.get("answered") != "ignore" else "ignore")
        log(f"stale {minutes(lost)} min -> asked")
        return

    auto = s["auto_reset_minutes"]
    if auto and lost >= auto * 60 and not st.get("auto_reset_done") and st.get("answered") is None \
            and now() - float(st.get("last_reset", 0)) > 30 * 60:
        st["auto_reset_done"] = True
        log("no answer -> auto reset")
        do_reset(cfg, s, st, "ระบบอัตโนมัติ (ไม่มีใครกดปุ่ม)")


def run_once():
    cfg = TA.load_config()
    s = settings(cfg)
    st = load_json(STATE, {})
    try:
        up = check_boot(cfg, s, st)
        save_json(STATE, st)
        handle_request(cfg, s, st)
        save_json(STATE, st)
        ensure_backend(cfg, s, st, up)
        save_json(STATE, st)
        check_data(cfg, s, st, up)
    except Exception as e:
        log(f"error {type(e).__name__}: {e}")
    finally:
        st["last_run"] = now()
        save_json(STATE, st)


def single_instance():
    """กันรันซ้อน (การรีเซตใช้เวลาเกิน 1 นาทีได้)"""
    lock = HERE / ".prisoft_guard.lock"
    try:
        if lock.exists() and now() - lock.stat().st_mtime < 600:
            return None
        lock.write_text(str(os.getpid()))
        return lock
    except Exception:
        return None


def main():
    args = sys.argv[1:]
    cfg = TA.load_config()
    s = settings(cfg)
    if "--status" in args:
        procs = processes()
        val_age, file_age = data_age()
        print(f"uptime          : {human_dur(uptime_sec())}")
        print(f"GUI pids        : {gui_pids(procs)}")
        print(f"backend pids    : {backend_pids(procs)}")
        print(f"port {s['backend_port']} open   : {port_open(s['backend_port'])}")
        print(f"newest value    : {human_dur(val_age)} ago")
        print(f"temps.json      : {human_dur(file_age)} ago")
        print(f"telegram chats  : {len((cfg or {}).get('chat_ids') or [])}")
        print(f"state           : {json.dumps(load_json(STATE, {}), ensure_ascii=False)}")
        return
    if "--init" in args:                     # ตอนติดตั้ง: จำการบูตปัจจุบันไว้ ไม่ต้องแจ้งว่า "เพิ่งเปิดเครื่อง"
        st = load_json(STATE, {})
        st.update(boot_ts=now() - uptime_sec(), boot_pending=False)
        save_json(STATE, st)
        print("guard state initialised")
        return
    lock = single_instance()
    if not lock:
        return
    try:
        if "--reset" in args:
            st = load_json(STATE, {})
            do_reset(cfg, s, st, "คำสั่งที่เครื่อง")
            save_json(STATE, st)
        elif "--ask" in args:
            st = load_json(STATE, {})
            st["prompt_msgs"] = tg_broadcast(cfg, "🧪 ทดสอบปุ่มควบคุม Prisoft\n(กดได้จริง — "
                                                  "🔄 จะรีเซต Prisoft จริง)\n\nเลือกคำสั่ง:", BUTTONS)
            st["prompted_at"] = now()
            save_json(STATE, st)
            print("sent:", st["prompt_msgs"])
        else:
            run_once()
    finally:
        try:
            lock.unlink()
        except Exception:
            pass


if __name__ == "__main__":
    main()
