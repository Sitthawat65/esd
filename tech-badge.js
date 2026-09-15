/* ============================================================
   ป้าย "TECHNICIAN ควรเข้าตรวจสอบ" — ใช้ร่วมกันทุกหน้า
   ------------------------------------------------------------
   - ตัวเลข ≥ 80 °C กะพริบสลับ แดง ⇄ ส้ม (อ่านค่าได้ตลอด ไม่หายไป)
   - หน้ารูปเครื่องจักร: ใส่ <div class="tech [up]" data-pair="BASE" style="left:..;top:.."></div>
     ใน .stage แล้วสคริปต์นี้จะแสดงป้ายเมื่อ #BASE_L หรือ #BASE_R มี class "alarm"
       .up  = วางเหนือตาราง (top = ขอบบนตาราง)   ไม่มี = วางใต้ตาราง (top = ขอบล่างตาราง)
       left = กึ่งกลางตาราง
   - หน้า Table: เรียก techBadgeHTML(side) ในช่องที่ ≥ 80
   - ?demo=1 ต่อท้าย URL = โหมดตัวอย่าง จำลองค่าเกิน 80 ให้ดูหน้าตาป้าย (ไม่กระทบข้อมูลจริง)
   ============================================================ */
(function () {
  'use strict';

  var ICON = 'tech-alert.png';
  var DEMO = /[?&]demo=1\b/.test(location.search);

  var css = ''
    /* ตัวเลขร้อน: สลับแดง/ส้ม */
    + '.tv.alarm{font-weight:800!important;animation:tb-hot 1s steps(1,end) infinite!important}'
    + '.num.alarm .v{animation:tb-hot 1s steps(1,end) infinite!important}'
    + '@keyframes tb-hot{0%,49%{color:#e00000;opacity:1}50%,100%{color:#ff8a00;opacity:1}}'
    + '.num.alarm .v{text-shadow:none}'
    /* ป้ายบนรูปเครื่องจักร — แถบเล็กติดตาราง */
    + '.tech{position:absolute;transform:translate(-50%,0);display:flex;align-items:center;gap:.35cqw;'
    +   'padding:.2cqw .55cqw .2cqw .25cqw;border-radius:0 0 .5cqw .5cqw;background:#fff;'
    +   'border:.1cqw solid #d10000;border-top:0;box-shadow:0 .15cqw .45cqw rgba(0,0,0,.18);'
    +   'cursor:help;z-index:2;white-space:nowrap}'
    + '.tech.up{transform:translate(-50%,-100%);border-radius:.5cqw .5cqw 0 0;'
    +   'border-top:.1cqw solid #d10000;border-bottom:0;box-shadow:0 -.15cqw .45cqw rgba(0,0,0,.18)}'
    + '.tech[hidden]{display:none!important}'
    + '.tech.tight{padding-top:.1cqw;padding-bottom:.1cqw}.tech.tight img{width:2.3cqw;height:2.3cqw}'
    + '.tech img{width:2.9cqw;height:2.9cqw;display:block;flex:none;animation:tb-ic 1s steps(1,end) infinite}'
    + '.tech .tl{display:flex;flex-direction:column;line-height:1.1;animation:tb-lbl 1s steps(1,end) infinite}'
    + '.tech .tl b{font-size:max(8px,.78cqw);letter-spacing:.05cqw}'
    + '.tech .tl span{font-size:max(8px,.74cqw);font-weight:600}'
    /* ป้ายในหน้า Table */
    + '.tbadge{display:inline-flex;align-items:center;gap:5px;flex:none;padding:3px 8px 3px 4px;border-radius:9px;'
    +   'background:rgba(224,36,36,.12);border:1px solid rgba(224,36,36,.55);cursor:help;white-space:nowrap;width:122px;box-sizing:border-box}'
    + '.tslot{display:inline-block;width:122px;flex:none}'
    + '.tbadge img{width:28px;height:28px;display:block;animation:tb-ic 1s steps(1,end) infinite}'
    + '.tbadge .tl{display:flex;flex-direction:column;align-items:flex-start;line-height:1.15;animation:tb-lbl2 1s steps(1,end) infinite}'
    + '.tbadge .tl b{font-size:9.5px;letter-spacing:.6px}'
    + '.tbadge .tl span{font-size:10px;font-weight:600}'
    + '@media (max-width:600px){.tbadge .tl{display:none}.tbadge{padding:3px;width:auto}.tslot{width:36px}}'
    + '@keyframes tb-ic{0%,49%{opacity:1}50%,100%{opacity:.35}}'
    + '@keyframes tb-lbl{0%,49%{color:#d10000}50%,100%{color:#ff7a00}}'
    + '@keyframes tb-lbl2{0%,49%{color:#ff6b6b}50%,100%{color:#ffb14a}}'
    + '.tb-demo{max-width:1100px;margin:0 auto 12px;text-align:center;background:#7a4b00;'
    +   'color:#ffe6bf;border:1px solid #f5a623;border-radius:10px;padding:7px 16px;font:700 13px "Segoe UI",Tahoma,sans-serif}'
    + '@media print{.tech img,.tech .tl,.tbadge img,.tbadge .tl,.tv.alarm,.num.alarm .v{animation:none!important}'
    +   '.tech .tl{color:#d10000}.tv.alarm{color:#d10000!important}.tb-demo{display:none}}';
  var st = document.createElement('style');
  st.textContent = css;
  document.head.appendChild(st);

  // ค่า animation-delay ที่ทำให้ทุกอย่างกะพริบพร้อมกัน (อิงวินาทีของนาฬิกา)
  function syncDelay(){ return -(Date.now() % 1000) + 'ms'; }
  var LABEL = '<div class="tl"><b>TECHNICIAN</b><span>ควรเข้าตรวจสอบ</span></div>';

  // ---------- หน้า Table ----------
  window.techBadgeHTML = function (title) {
    var d = syncDelay();
    return '<span class="tbadge" title="' + (title || 'ช่างเทคนิคควรเข้าตรวจสอบแบริ่งพูลเลย์') + '">'
      + '<img src="' + ICON + '" alt="" style="animation-delay:' + d + '">'
      + LABEL.replace('class="tl"', 'class="tl" style="animation-delay:' + d + '"') + '</span>';
  };

  // ---------- หน้ารูปเครื่องจักร ----------
  function sideText(el, th){
    return th + ' ' + (el.textContent || '').replace('*', '') + ' °C';
  }
  function tick(){
    var d = null;
    document.querySelectorAll('.tv').forEach(function (el) {
      var hot = el.classList.contains('alarm');
      if (hot && !el.dataset.tbSync) { el.style.animationDelay = d || (d = syncDelay()); el.dataset.tbSync = '1'; }
      if (!hot && el.dataset.tbSync) { el.style.animationDelay = ''; delete el.dataset.tbSync; }
    });
    document.querySelectorAll('.tech[data-pair]').forEach(function (box) {
      var p = box.dataset.pair;
      var L = document.getElementById(p + '_L'), R = document.getElementById(p + '_R');
      var hot = [];
      if (L && L.classList.contains('alarm')) hot.push(sideText(L, 'ซ้าย'));
      if (R && R.classList.contains('alarm')) hot.push(sideText(R, 'ขวา'));
      var show = hot.length > 0;
      if (show && box.hidden !== false) {
        if (!box.firstChild) box.innerHTML = '<img src="' + ICON + '" alt="">' + LABEL;
        var dd = d || (d = syncDelay());
        box.querySelectorAll('img,.tl').forEach(function (e) { e.style.animationDelay = dd; });
      }
      box.hidden = !show;
      box.title = show ? (box.dataset.name || p.replace(/_/g, ' ')) + ' · ' + hot.join(', ')
        + ' (≥ 80 °C)\nช่างเทคนิคควรเข้าตรวจสอบแบริ่งพูลเลย์' : '';
    });
  }

  // ---------- โหมดตัวอย่าง ----------
  // จำลอง: คู่ที่ 1 ร้อนฝั่งซ้าย · คู่ที่ 2 ร้อนฝั่งขวา · คู่ที่ 3 ร้อนทั้งคู่ · วนไป
  function demoVal(i, side){
    var k = i % 3, hot = (k === 0 && side === 'L') || (k === 1 && side === 'R') || k === 2;
    return hot ? 82.4 + (i * 3.1) % 9 : 55.2 + (i * 4.7) % 12;
  }
  function demoStage(){
    var pairs = [];
    document.querySelectorAll('.stage .tv[id$="_L"]').forEach(function (el) { pairs.push(el.id.slice(0, -2)); });
    pairs.forEach(function (p, i) {
      ['L', 'R'].forEach(function (s) {
        var el = document.getElementById(p + '_' + s); if (!el) return;
        var v = demoVal(i, s);
        el.textContent = v.toFixed(1);
        el.className = 'tv ' + (v >= 80 ? 'alarm' : 'ok');
      });
    });
  }
  function demoData(){
    /* global DATA */
    if (typeof DATA === 'undefined' || !DATA || !DATA.groups) return;
    var now = new Date().toISOString();
    Object.keys(DATA.groups).forEach(function (g) {
      var idx = {}, n = 0;
      (DATA.groups[g] || []).forEach(function (it) {
        var m = /^(.*)_(L|R)$/.exec(it.tag); if (!m) return;
        if (!(m[1] in idx)) idx[m[1]] = n++;
        it.value = demoVal(idx[m[1]], m[2]);
        it.seen = now;
      });
    });
    DATA.updated = now;
  }
  if (DEMO) {
    var orig = window.render;
    if (typeof orig === 'function') {
      window.render = function () {
        var isStage = !!document.querySelector('.stage .tv');
        if (!isStage) demoData();
        var r = orig.apply(this, arguments);
        if (isStage) demoStage();
        return r;
      };
    }
    var tag = document.createElement('div');
    tag.className = 'tb-demo';
    tag.textContent = 'โหมดตัวอย่าง (DEMO) — ค่าจำลอง ไม่ใช่ค่าจริง';
    document.body.insertBefore(tag, document.body.firstChild);
    if (document.querySelector('.stage .tv')) demoStage();
    else if (typeof window.render === 'function') window.render();
  }

  tick();
  setInterval(tick, 400);
})();
