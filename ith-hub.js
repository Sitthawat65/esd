/* ITH hub — shared top bar for the Bearing Temp pages
 * - same navbar (links + theme + Visitor/Developer Mode) as the other hub dashboards
 * - remembers theme across all dashboards (localStorage "ith_theme")
 * - Developer Mode uses the same login/session as Overhaul & Fiber (sessionStorage "fo_auth")
 * - opened from disk (file://) -> temperature data is read from the live GitHub Pages site
 * - machine drawings are scaled so the whole page fits one screen
 * Usage: <script src="ith-hub.js"></script> in <head>, then <script>ITHHUB.nav()</script> right after <body>.
 */
(function () {
  var LIVE_BASE = 'https://sitthawat65.github.io/ith-hongsa-overhaul-dashboard/';
  var AUTH_HASH = '5d5cde11a3ee1966f86d8abbabd795a8f77d7129e21f7c329f337db471ff244c';

  // ---- scale whole page (layout designed for 1920px; same on every hub dashboard) ----
  (function(){var d=document.documentElement;function z(){var w=window.innerWidth,v=w<900?1:Math.max(.6,Math.min(2,w/1920));d.style.zoom=v;d.setAttribute('data-basez',v);d.style.setProperty('--ithz',v);}z();window.addEventListener('resize',z);})();

  // ---- theme before first paint ----
  try {
    var t = localStorage.getItem('ith_theme');
    if (t === 'light' || t === 'dark') document.documentElement.setAttribute('data-theme', t);
  } catch (e) {}

  // ---- local files cannot fetch JSON next to them; use the live copy instead ----
  if (location.protocol === 'file:' && window.fetch) {
    var nativeFetch = window.fetch.bind(window);
    window.fetch = function (url, opts) {
      if (typeof url === 'string' && /^(\.\/)?temps(_history)?\.json/.test(url)) {
        url = LIVE_BASE + url.replace(/^\.\//, '');
      }
      return nativeFetch(url, opts);
    };
  }

  function sha256(ascii){function r(v,a){return (v>>>a)|(v<<(32-a));}var mp=Math.pow,mw=mp(2,32),out="";var words=[],bitLen=ascii.length*8;var h=sha256.h=sha256.h||[],k=sha256.k=sha256.k||[],pc=k.length,comp={};for(var cand=2;pc<64;cand++){if(!comp[cand]){for(var i=0;i<313;i+=cand){comp[i]=cand;}h[pc]=(mp(cand,.5)*mw)|0;k[pc++]=(mp(cand,1/3)*mw)|0;}}ascii+="\x80";while(ascii.length%64-56)ascii+="\x00";for(var i=0;i<ascii.length;i++){var j=ascii.charCodeAt(i);if(j>>8)return;words[i>>2]|=j<<((3-i)%4)*8;}words[words.length]=((bitLen/mw)|0);words[words.length]=(bitLen);for(var j=0;j<words.length;){var w=words.slice(j,j+=16),oh=h;h=h.slice(0,8);for(var i=0;i<64;i++){var w15=w[i-15],w2=w[i-2],a=h[0],e=h[4];var t1=h[7]+(r(e,6)^r(e,11)^r(e,25))+((e&h[5])^((~e)&h[6]))+k[i]+(w[i]=i<16?w[i]:(w[i-16]+(r(w15,7)^r(w15,18)^(w15>>>3))+w[i-7]+(r(w2,17)^r(w2,19)^(w2>>>10)))|0);var t2=(r(a,2)^r(a,13)^r(a,22))+((a&h[1])^(a&h[2])^(h[1]&h[2]));h=[(t1+t2)|0].concat(h);h[4]=(h[4]+t1)|0;}for(var i=0;i<8;i++){h[i]=(h[i]+oh[i])|0;}}for(var i=0;i<8;i++){for(var j=3;j+1;j--){var b=(h[i]>>(j*8))&255;out+=((b<16)?0:"")+b.toString(16);}}return out;}

  var editMode = false;
  try { editMode = sessionStorage.getItem('fo_auth') === '1'; } catch (e) {}

  function $(id) { return document.getElementById(id); }

  function applyMode() {
    var b = $('ithBadge'), e = $('ithDev');
    if (!b || !e) return;
    if (editMode) { b.className = 'mbadge on'; b.textContent = '✔ Developer Mode'; e.className = 'mEditBtn out'; e.textContent = '🔓 Exit Developer Mode'; }
    else { b.className = 'mbadge'; b.textContent = '👁 Visitor Mode'; e.className = 'mEditBtn'; e.textContent = '🔒 Developer Mode'; }
    document.documentElement.setAttribute('data-medit', editMode ? '1' : '0');
  }

  function openLogin() {
    var o = $('ithLogin'); if (!o) return;
    $('ithErr').textContent = ''; $('ithPw').value = '';
    o.classList.add('show'); $('ithId').focus();
  }
  function closeLogin() { var o = $('ithLogin'); if (o) o.classList.remove('show'); }

  function nav() {
    var html =
      '<nav class="ithnav">' +
        '<a href="index.html">← หน้าหลัก</a>' +
        '<a href="Dashboard.html">⚙️ Overhaul Motor</a>' +
        '<a href="FiberOptic_Report.html">🔬 Fiber Optic</a>' +
        '<a href="iso-ee.html">📋 ISO EE</a>' +
        '<a href="home.html" class="on">🌡️ BEARING TEMP PL</a>' +
        '<span class="navsp"></span>' +
        '<button type="button" id="ithTheme" title="สลับธีม สว่าง / มืด">◐ สลับธีม</button>' +
        '<span class="mbadge" id="ithBadge">👁 Visitor Mode</span>' +
        '<button type="button" class="mEditBtn" id="ithDev">🔒 Developer Mode</button>' +
      '</nav>';
    var s = document.currentScript;
    if (s && s.parentNode) s.insertAdjacentHTML('afterend', html);
    else document.body.insertAdjacentHTML('afterbegin', html);
    applyMode();
  }

  // ---- everything on one screen ----
  // machine pages: shrink the drawing so nav + header + drawing + footer fit the viewport height
  // chart / table pages: scale the whole page down until it fits
  var fitting = false;
  function fit() {
    if (fitting) return; fitting = true;
    try {
      var stages = document.querySelectorAll('.stage'), hasStage = false;
      for (var i = 0; i < stages.length; i++) {
        var st = stages[i], img = st.querySelector('img');
        if (!img) continue;
        hasStage = true;
        if (!img.naturalWidth || !st.offsetWidth) continue;
        if (!st.dataset.baseMax) {
          st.style.maxWidth = '';
          st.dataset.baseMax = parseFloat(getComputedStyle(st).maxWidth) || 1100;
        }
        var r = st.getBoundingClientRect();
        var z = r.width / st.offsetWidth || 1;                 // visual px per CSS px
        var below = 0, ft = document.querySelector('body > footer');
        if (ft && ft.offsetHeight) below = (ft.offsetHeight + parseFloat(getComputedStyle(ft).marginTop || 0)) * z;
        var avail = window.innerHeight - (r.top + window.scrollY) - below - 14 * z;
        var w = (avail * img.naturalWidth / img.naturalHeight) / z;
        w = Math.max(220, Math.min(+st.dataset.baseMax, w));
        if (Math.abs(st.offsetWidth - w) > 2) st.style.maxWidth = Math.round(w) + 'px';
      }
      if (!hasStage) {
        var d = document.documentElement, base = +d.getAttribute('data-basez') || 1;
        d.style.zoom = base;
        var b = document.body.getBoundingClientRect();
        var need = b.bottom + window.scrollY + 2;
        var sw = d.scrollWidth;
        var k = Math.min(1, window.innerHeight / need, window.innerWidth / sw);
        // wide tables (phones): shrink until the whole table is inside its box
        var tbs = document.querySelectorAll('table');
        for (var t = 0; t < tbs.length; t++) {
          var par = tbs[t].parentElement, have = par ? par.clientWidth : 0, want = tbs[t].scrollWidth;
          if (have && want > have + 1) k = Math.min(k, have / want);
        }
        if (k < 0.995) d.style.zoom = Math.max(0.4, base * k);
      }
    } finally { fitting = false; }
  }

  function init() {
    // login dialog (overlay — never affects layout)
    document.body.insertAdjacentHTML('beforeend',
      '<div class="ithlogin" id="ithLogin"><form id="ithForm" autocomplete="off">' +
      '<h3>🔒 Developer Mode</h3><p>เฉพาะผู้มีรหัสเท่านั้น — กรอก ID และรหัสผ่าน</p>' +
      '<label for="ithId">ID</label><input id="ithId" type="text" autocomplete="off" autocapitalize="characters" spellcheck="false">' +
      '<label for="ithPw">Password</label><input id="ithPw" type="password" autocomplete="new-password">' +
      '<div class="err" id="ithErr"></div>' +
      '<div class="acts"><button type="button" id="ithCancel">ยกเลิก</button><button type="submit" class="pri">เข้าสู่ระบบ</button></div>' +
      '</form></div>');

    var dev = $('ithDev'), th = $('ithTheme');
    if (dev) dev.addEventListener('click', function () {
      if (editMode) { try { sessionStorage.removeItem('fo_auth'); } catch (e) {} editMode = false; applyMode(); }
      else openLogin();
    });
    if (th) th.addEventListener('click', function () {
      var light = document.documentElement.getAttribute('data-theme') !== 'light';
      document.documentElement.setAttribute('data-theme', light ? 'light' : 'dark');
      try { localStorage.setItem('ith_theme', light ? 'light' : 'dark'); } catch (e) {}
    });
    $('ithCancel').addEventListener('click', closeLogin);
    $('ithLogin').addEventListener('click', function (ev) { if (ev.target === this) closeLogin(); });
    $('ithForm').addEventListener('submit', function (ev) {
      ev.preventDefault();
      var id = $('ithId').value.trim().toUpperCase(), pw = $('ithPw').value.trim();
      if (sha256(id + ':' + pw) === AUTH_HASH) {
        try { sessionStorage.setItem('fo_auth', '1'); } catch (e) {}
        editMode = true; closeLogin(); applyMode();
      } else $('ithErr').textContent = 'ID หรือรหัสผ่านไม่ถูกต้อง';
    });

    var qm = new URLSearchParams(location.search).get('mode');
    if (qm === 'view' && editMode) { try { sessionStorage.removeItem('fo_auth'); } catch (e) {} editMode = false; }
    applyMode();
    if (qm === 'edit' && !editMode) openLogin();

    var imgs = document.querySelectorAll('.stage img');
    for (var i = 0; i < imgs.length; i++) {
      if (imgs[i].complete) fit(); else imgs[i].addEventListener('load', fit);
    }
    window.addEventListener('resize', fit);
    window.addEventListener('load', fit);
    // weather widget / fonts load later and push the drawing down -> fit again
    if (window.ResizeObserver) {
      var ro = new ResizeObserver(function () { fit(); });
      ['.ithnav', '.topnav', 'body > header', 'body > footer', '#chartwrap', 'table.temps', '#wx'].forEach(function (q) { var el = document.querySelector(q); if (el) ro.observe(el); });
      setTimeout(fit, 1500); setTimeout(fit, 4000);
    }
    fit();
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();

  window.ITHHUB = { nav: nav, fit: fit };
})();
