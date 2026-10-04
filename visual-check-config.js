// Visual Check — ตั้งค่ากลาง (ใช้ร่วมกันทั้งฟอร์มและ Dashboard)
window.VC_CONFIG = {
  // URL ของ Google Apps Script Web App (ดู visual-check-backend.gs)
  // ถ้าเว้นว่าง = โหมดทดสอบ ข้อมูลเก็บเฉพาะในเครื่องที่กรอก
  API_URL: '',

  // เวลาที่ให้กรอกฟอร์มหลังแตะ tag (นาที)
  SESSION_MIN: 15,

  // รอบตรวจ (ชั่วโมง) — เกินนี้ Dashboard จะขึ้น "เลยกำหนด"
  CHECK_INTERVAL_H: 8,

  // รายชื่อสำรอง ใช้เมื่อยังไม่ต่อ API (เมื่อต่อแล้วจะดึงจากชีต Names แทน)
  NAMES: ['พนักงาน 1', 'พนักงาน 2', 'พนักงาน 3'],

  // รายการตรวจมาตรฐาน — จุดไหนต่างออกไปให้ใส่ items ของจุดนั้นเอง
  DEFAULT_ITEMS: [
    'สายเมนมอเตอร์ปกติหรือไม่',
    'แรงดันไฟฟ้าอยู่ในเกณฑ์ปกติหรือไม่',
    'เสียงและการสั่นสะเทือนปกติหรือไม่',
    'ไม่มีกลิ่นไหม้ / ความร้อนผิดปกติ',
    'ไม่มีคราบน้ำมัน จาระบีรั่ว หรือฝุ่นสะสมผิดปกติ'
  ],

  // จุดตรวจ: key = ค่า ?p= ที่เขียนลง NFC tag
  POINTS: {
    'SPD-MD1-DCV': { name: 'SPD · MD1 DCV', area: 'Spreader' },
    'SPD-MD2-DCV': { name: 'SPD · MD2 DCV', area: 'Spreader' },
    'SPD-MD1-RCV': { name: 'SPD · MD1 RCV', area: 'Spreader' },
    'SPD-MD2-RCV': { name: 'SPD · MD2 RCV', area: 'Spreader' }
  }
};
