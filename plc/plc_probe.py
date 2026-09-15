#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ทดสอบว่าอ่านอะไรจาก PLC S7-300/400 ได้บ้าง — อ่านอย่างเดียว (READ-ONLY)
------------------------------------------------------------------------
ไม่เขียนค่า ไม่ Download ไม่สั่ง RUN/STOP ไม่แก้โปรแกรม
สคริปต์นี้เรียกใช้ PLC ผ่านตัวห่อ ReadOnlyPLC ที่เปิดให้ใช้ได้เฉพาะคำสั่งอ่านเท่านั้น
คำสั่งเขียน/สั่งงานทุกตัวถูกบล็อกตั้งแต่ในโค้ด (เรียกแล้ว error ทันที ไม่ถึง PLC)

ใช้งาน:  python plc_probe.py 192.168.0.50 [192.168.0.52 ...]
ผลลัพธ์: Desktop\\PLC_probe.txt
"""
import os, sys, socket, subprocess, datetime, pathlib, time

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

OUT = pathlib.Path(os.environ.get("PLC_PROBE_OUT") or pathlib.Path(os.path.expanduser("~")) / "Desktop" / "PLC_probe.txt")
lines = []


def w(s=""):
    print(s)
    lines.append(str(s))


def section(t):
    w("")
    w("=" * 70)
    w("  " + t)
    w("=" * 70)


def port_open(ip, port, timeout=3):
    try:
        with socket.create_connection((ip, port), timeout=timeout):
            return True
    except Exception:
        return False


def ping(ip):
    try:
        r = subprocess.run(["ping", "-n", "2", "-w", "1500", ip], capture_output=True, text=True,
                           encoding="mbcs" if os.name == "nt" else "utf-8", errors="replace", timeout=15)
        return r.returncode == 0 and "TTL=" in r.stdout.upper()
    except Exception:
        return False


class ReadOnlyPLC:
    """เปิดให้ใช้เฉพาะคำสั่งอ่าน — คำสั่งอื่นทั้งหมดของ snap7 เรียกไม่ได้"""
    ALLOWED = {"connect", "disconnect", "get_connected", "get_cpu_state", "get_cpu_info",
               "get_order_code", "get_cp_info", "get_protection", "get_plc_datetime",
               "list_blocks", "list_blocks_of_type", "get_block_info", "get_pdu_length",
               "read_diagnostic_buffer", "db_read", "mb_read", "eb_read", "ab_read"}

    def __init__(self):
        from snap7.client import Client
        self._c = Client()

    def __getattr__(self, name):
        if name not in self.ALLOWED:
            raise PermissionError(f"blocked (read-only probe): {name}")
        return getattr(self._c, name)


def txt(v):
    if isinstance(v, (bytes, bytearray)):
        return v.split(b"\x00")[0].decode("latin-1", "replace").strip()
    return str(v).strip()


def try_call(label, fn):
    try:
        v = fn()
        w(f"  {label:<22}: {v}")
        return v
    except PermissionError:
        raise
    except Exception as e:
        w(f"  {label:<22}: (อ่านไม่ได้: {type(e).__name__} {str(e)[:80]})")
        return None


def probe_plc(ip):
    try:
        import snap7  # noqa: F401
        from snap7.type import Block
    except Exception as e:
        w(f"  snap7 not installed: {e}")
        return
    combos = [(0, 2), (0, 3), (0, 1), (0, 0), (0, 4), (0, 5)]
    plc = None
    for rack, slot in combos:
        p = ReadOnlyPLC()
        try:
            p.connect(ip, rack, slot)
            if p.get_connected():
                w(f"  เชื่อมต่อสำเร็จ  rack={rack} slot={slot}")
                plc = p
                break
        except PermissionError:
            raise
        except Exception as e:
            w(f"  rack={rack} slot={slot}: ต่อไม่ได้ ({str(e)[:70]})")
        try:
            p.disconnect()
        except Exception:
            pass
        time.sleep(0.5)
    if not plc:
        w("  !! เชื่อมต่อ S7 ไม่สำเร็จทุก rack/slot")
        return

    try:
        section(f"PLC {ip} - ข้อมูล CPU")
        try_call("สถานะ CPU", plc.get_cpu_state)
        info = try_call("CPU info (raw)", plc.get_cpu_info)
        if info is not None:
            for f in ("ModuleTypeName", "ModuleName", "ASName", "SerialNumber", "Copyright"):
                if hasattr(info, f):
                    w(f"    {f:<18}: {txt(getattr(info, f))}")
        oc = try_call("Order code (raw)", plc.get_order_code)
        if oc is not None and hasattr(oc, "OrderCode"):
            w(f"    OrderCode         : {txt(oc.OrderCode)}  FW V{oc.V1}.{oc.V2}.{oc.V3}")
        try_call("เวลาใน PLC", plc.get_plc_datetime)
        prot = try_call("Protection (raw)", plc.get_protection)
        try_call("PDU length", plc.get_pdu_length)
        cp = try_call("CP info (raw)", plc.get_cp_info)

        section(f"PLC {ip} - รายการ Block ในโปรแกรม")
        bl = try_call("จำนวน Block", plc.list_blocks)
        dbs = []
        try:
            dbs = sorted(plc.list_blocks_of_type(Block.DB, 1024))
            w(f"  DB ทั้งหมด {len(dbs)} ตัว: {dbs[:200]}")
        except Exception as e:
            w(f"  รายการ DB อ่านไม่ได้: {e}")
        if dbs:
            w("")
            w("  รายละเอียด DB (ขนาด / ชื่อ / ผู้เขียน / Family)  -- ไว้เดาว่า DB ไหนเป็นของระบบ Lubrication")
            for n in dbs[:150]:
                try:
                    bi = plc.get_block_info(Block.DB, n)
                    name = txt(getattr(bi, "BlockName", b"")) if hasattr(bi, "BlockName") else ""
                    w(f"   DB{n:<5} size={getattr(bi, 'MC7Size', '?'):<6} name={name:<10} "
                      f"author={txt(getattr(bi, 'Author', b'')):<10} family={txt(getattr(bi, 'Family', b''))}")
                except Exception as e:
                    w(f"   DB{n:<5} (info อ่านไม่ได้: {str(e)[:60]})")
                time.sleep(0.05)

        section(f"PLC {ip} - Diagnostic buffer (ล่าสุด 15 รายการ)")
        try:
            diag = plc.read_diagnostic_buffer()
            for d in (diag or [])[:15]:
                w(f"  {d}")
            if not diag:
                w("  (ว่าง)")
        except Exception as e:
            w(f"  อ่านไม่ได้: {e}")
    finally:
        try:
            plc.disconnect()
            w("")
            w("  ตัดการเชื่อมต่อแล้ว")
        except Exception:
            pass


def main():
    ips = sys.argv[1:] or ["192.168.0.50", "192.168.0.52"]
    section("PLC READ-ONLY PROBE")
    w(f"เวลา     : {datetime.datetime.now():%Y-%m-%d %H:%M:%S}")
    w(f"คอม      : {os.environ.get('COMPUTERNAME', '?')}")
    w("หมายเหตุ  : อ่านอย่างเดียว ไม่มีการเขียนค่า / สั่งงาน PLC")
    try:
        out = subprocess.run(["ipconfig"], capture_output=True, text=True, encoding="mbcs", errors="replace").stdout
        v4 = [l.strip() for l in out.splitlines() if "IPv4" in l]
        w("IPv4 ของคอมนี้: " + " | ".join(v4))
    except Exception:
        pass

    for ip in ips:
        section(f"เครือข่าย {ip}")
        w(f"  ping          : {'ได้' if ping(ip) else 'ไม่ได้'}")
        opened = {}
        for port, what in ((102, "S7 (ISO-on-TCP)"), (80, "Web"), (443, "Web https"), (5900, "VNC / Sm@rtServer")):
            opened[port] = port_open(ip, port)
            w(f"  port {port:<5} {what:<18}: {'เปิด' if opened[port] else 'ปิด'}")
        if opened[102]:
            probe_plc(ip)
        else:
            w("  -> พอร์ต 102 ปิด: อ่าน S7 จากเครื่องนี้ไม่ได้ (ถ้าเป็น HMI ถือว่าปกติ)")

    try:
        OUT.write_text("\n".join(lines), encoding="utf-8-sig")
        print(f"\nบันทึกผลที่ {OUT}")
    except Exception as e:
        print(f"บันทึกไฟล์ไม่ได้: {e}")


if __name__ == "__main__":
    main()
