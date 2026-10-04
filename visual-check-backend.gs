// Visual Check — หลังบ้าน (Google Apps Script)
// วิธีติดตั้ง:
//  1. สร้าง Google Sheet ใหม่ > ส่วนขยาย > Apps Script > วางโค้ดนี้ทับทั้งหมด
//  2. ทำให้ใช้งานได้ (Deploy) > การทำให้ใช้งานได้รายการใหม่ > ประเภท "เว็บแอป"
//     ดำเนินการในฐานะ: ฉัน / ผู้มีสิทธิ์เข้าถึง: ทุกคน
//  3. คัดลอก URL ที่ลงท้าย /exec ไปใส่ API_URL ใน visual-check-config.js
//  4. ใส่รายชื่อพนักงานในชีต "Names" คอลัมน์ A (แถวแรกเป็นหัวตาราง)

var HEAD = ['ts', 'point', 'name', 'result', 'abnormal', 'answers', 'note', 'openedAt', 'durationSec'];

function sheet_(name, head) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var s = ss.getSheetByName(name);
  if (!s) { s = ss.insertSheet(name); s.appendRow(head); }
  return s;
}

function out_(o) {
  return ContentService.createTextOutput(JSON.stringify(o)).setMimeType(ContentService.MimeType.JSON);
}

function doGet(e) {
  var action = (e.parameter.action || 'list');
  if (action === 'names') {
    var v = sheet_('Names', ['name']).getDataRange().getValues().slice(1);
    return out_({ ok: true, names: v.map(function (r) { return String(r[0]).trim(); }).filter(String) });
  }
  var rows = sheet_('Records', HEAD).getDataRange().getValues().slice(1).slice(-1000);
  var records = rows.map(function (r) {
    var o = {};
    HEAD.forEach(function (h, i) { o[h] = r[i] instanceof Date ? r[i].toISOString() : r[i]; });
    try { o.answers = JSON.parse(o.answers); } catch (err) { o.answers = []; }
    return o;
  });
  return out_({ ok: true, records: records });
}

function doPost(e) {
  try {
    var d = JSON.parse(e.postData.contents);
    if (!d.point || !d.name || !Array.isArray(d.answers) || !d.answers.length) throw new Error('ข้อมูลไม่ครบ');
    var now = new Date();                       // เวลาบันทึกใช้นาฬิกาของเซิร์ฟเวอร์ แก้จากมือถือไม่ได้
    var opened = d.openedAt ? new Date(d.openedAt) : now;
    var abnormal = d.answers.filter(function (a) { return !a.ok; }).length;
    sheet_('Records', HEAD).appendRow([
      now, String(d.point), String(d.name), abnormal ? 'ไม่ปกติ' : 'ปกติ', abnormal,
      JSON.stringify(d.answers), String(d.note || ''), opened, Math.round((now - opened) / 1000)
    ]);
    return out_({ ok: true, ts: now.toISOString() });
  } catch (err) {
    return out_({ ok: false, error: String(err.message || err) });
  }
}
