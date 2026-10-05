/*
 * 광역의회 정책 이슈 확산 분석 시스템 — 프로젝트 사이트 스크립트
 * 라이브러리 없이 동작한다. 모듈 순서:
 *   공용 도구 → nav → reveal → countUp → heroMap → charts(7.2~7.6) → steps → tabs(레인) → sortTable → timeline → bars → print
 * 페이지의 숫자는 HTML에 최종값으로 들어 있고, 이 스크립트는 그 값을 움직이거나 그림으로 옮기기만 한다.
 */
(function () {
  'use strict';

  var doc = document;
  var root = doc.documentElement;
  var SVGNS = 'http://www.w3.org/2000/svg';
  var mqReduce = window.matchMedia('(prefers-reduced-motion: reduce)');
  var EASE_OUT_CSS = 'cubic-bezier(0.22, 0.61, 0.36, 1)';
  var EASE_IN_OUT_CSS = 'cubic-bezier(0.65, 0, 0.35, 1)';
  var hasIO = 'IntersectionObserver' in window;

  /* ---------- 공용 도구 ---------- */
  function reduced() { return mqReduce.matches; }
  function $(sel, ctx) { return (ctx || doc).querySelector(sel); }
  function $$(sel, ctx) { return Array.prototype.slice.call((ctx || doc).querySelectorAll(sel)); }
  function fmt(n) { return Math.round(n).toLocaleString('ko-KR'); }
  function clamp01(v) { return v < 0 ? 0 : (v > 1 ? 1 : v); }

  function bezier(x1, y1, x2, y2) {
    var cx = 3 * x1, bx = 3 * (x2 - x1) - cx, ax = 1 - cx - bx;
    var cy = 3 * y1, by = 3 * (y2 - y1) - cy, ay = 1 - cy - by;
    function sx(t) { return ((ax * t + bx) * t + cx) * t; }
    function sy(t) { return ((ay * t + by) * t + cy) * t; }
    function dsx(t) { return (3 * ax * t + 2 * bx) * t + cx; }
    return function (x) {
      if (x <= 0) return 0;
      if (x >= 1) return 1;
      var t = x, i, e, d;
      for (i = 0; i < 8; i++) {
        e = sx(t) - x;
        if (Math.abs(e) < 1e-5) return sy(t);
        d = dsx(t);
        if (Math.abs(d) < 1e-6) break;
        t -= e / d;
      }
      var lo = 0, hi = 1;
      t = x;
      for (i = 0; i < 30; i++) {
        e = sx(t);
        if (Math.abs(e - x) < 1e-5) break;
        if (x > e) lo = t; else hi = t;
        t = (lo + hi) / 2;
      }
      return sy(t);
    };
  }
  var easeOut = bezier(0.22, 0.61, 0.36, 1);
  var easeInOut = bezier(0.65, 0, 0.35, 1);
  function easeOutCubic(t) { return 1 - Math.pow(1 - t, 3); }

  var uidN = 0;
  function uid(p) { uidN += 1; return (p || 'u') + uidN; }

  function svgEl(name, attrs, parent) {
    var e = doc.createElementNS(SVGNS, name);
    if (attrs) {
      for (var k in attrs) {
        if (Object.prototype.hasOwnProperty.call(attrs, k) && attrs[k] !== undefined && attrs[k] !== null) {
          e.setAttribute(k, attrs[k]);
        }
      }
    }
    if (parent) parent.appendChild(e);
    return e;
  }
  function svgText(parent, x, y, str, cls, extra) {
    var a = { x: r2(x), y: r2(y) };
    if (cls) a['class'] = cls;
    if (extra) for (var k in extra) a[k] = extra[k];
    var t = svgEl('text', a, parent);
    t.textContent = str;
    return t;
  }
  function r2(v) { return Math.round(v * 100) / 100; }

  /* 값 쪽 끝만 둥근 막대. dir: 'r' (가로, 오른쪽 둥금), 't' (세로, 위 둥금), 'n' (모서리 없음) */
  function barPath(x, y, w, h, dir, r) {
    r = r === undefined ? 3 : r;
    if (w <= 0 || h <= 0) return 'M' + r2(x) + ' ' + r2(y) + 'Z';
    if (dir === 'r') {
      r = Math.min(r, w, h / 2);
      return 'M' + r2(x) + ' ' + r2(y) + 'H' + r2(x + w - r) + 'Q' + r2(x + w) + ' ' + r2(y) + ' ' + r2(x + w) + ' ' + r2(y + r) +
        'V' + r2(y + h - r) + 'Q' + r2(x + w) + ' ' + r2(y + h) + ' ' + r2(x + w - r) + ' ' + r2(y + h) + 'H' + r2(x) + 'Z';
    }
    if (dir === 't') {
      r = Math.min(r, h, w / 2);
      return 'M' + r2(x) + ' ' + r2(y + h) + 'V' + r2(y + r) + 'Q' + r2(x) + ' ' + r2(y) + ' ' + r2(x + r) + ' ' + r2(y) +
        'H' + r2(x + w - r) + 'Q' + r2(x + w) + ' ' + r2(y) + ' ' + r2(x + w) + ' ' + r2(y + r) + 'V' + r2(y + h) + 'Z';
    }
    return 'M' + r2(x) + ' ' + r2(y) + 'H' + r2(x + w) + 'V' + r2(y + h) + 'H' + r2(x) + 'Z';
  }

  function makeSvg(box, W, H, title, desc, decorative) {
    var svg = svgEl('svg', { width: r2(W), height: H, viewBox: '0 0 ' + r2(W) + ' ' + H, 'class': 'c-svg', focusable: 'false' });
    if (decorative) {
      svg.setAttribute('aria-hidden', 'true');
    } else {
      var tid = uid('t'), did = uid('d');
      svg.setAttribute('role', 'img');
      svg.setAttribute('aria-labelledby', tid + ' ' + did);
      svgEl('title', { id: tid }, svg).textContent = title;
      svgEl('desc', { id: did }, svg).textContent = desc;
    }
    box.appendChild(svg);
    return svg;
  }

  function anim(node, frames, opts) {
    if (!node || typeof node.animate !== 'function') return null;
    try {
      var o = { duration: opts.duration || 400, delay: opts.delay || 0, easing: opts.easing || EASE_OUT_CSS, fill: opts.fill || 'backwards' };
      return node.animate(frames, o);
    } catch (e) { return null; }
  }
  function growX(node, delay, dur) {
    return anim(node, [{ transform: 'scaleX(0)' }, { transform: 'scaleX(1)' }], { duration: dur || 600, delay: delay });
  }
  function growY(node, delay, dur) {
    return anim(node, [{ transform: 'scaleY(0)' }, { transform: 'scaleY(1)' }], { duration: dur || 560, delay: delay });
  }
  function fadeIn(node, delay, dur) {
    return anim(node, [{ opacity: 0 }, { opacity: 1 }], { duration: dur || 240, delay: delay, easing: 'linear' });
  }
  function popIn(node, delay) {
    return anim(node, [{ opacity: 0, transform: 'scale(0.6)' }, { opacity: 1, transform: 'scale(1)' }], { duration: 240, delay: delay });
  }
  /* 실선 그리기 (dashoffset) */
  function drawStroke(path, delay, dur) {
    var len = path.getTotalLength ? path.getTotalLength() : 0;
    if (!len) return;
    path.style.strokeDasharray = len + ' ' + len;
    path.style.strokeDashoffset = '0px';
    anim(path, [{ strokeDashoffset: len + 'px' }, { strokeDashoffset: '0px' }], { duration: dur || 500, delay: delay, easing: EASE_IN_OUT_CSS });
  }
  /* 점선 드러내기: 같은 경로를 흰 실선으로 그린 마스크를 dashoffset으로 연다 */
  function maskedDash(svg, d, cls, W, H) {
    var defs = svg.querySelector('defs') || svgEl('defs', null, svg);
    var id = uid('m');
    var mask = svgEl('mask', { id: id, maskUnits: 'userSpaceOnUse', x: -20, y: -20, width: r2(W + 40), height: H + 40 }, defs);
    var mp = svgEl('path', { d: d, fill: 'none', stroke: '#fff', 'stroke-width': 6, 'stroke-linecap': 'round' }, mask);
    var p = svgEl('path', { d: d, 'class': cls, mask: 'url(#' + id + ')' }, svg);
    return { path: p, maskPath: mp };
  }
  function revealDash(maskPath, visiblePath, delay, dur) {
    var len = visiblePath.getTotalLength ? visiblePath.getTotalLength() : 0;
    if (!len) return;
    maskPath.style.strokeDasharray = len + ' ' + len;
    maskPath.style.strokeDashoffset = '0px';
    anim(maskPath, [{ strokeDashoffset: len + 'px' }, { strokeDashoffset: '0px' }], { duration: dur || 500, delay: delay, easing: EASE_IN_OUT_CSS });
  }

  var fontsReady = (doc.fonts && doc.fonts.ready) ? Promise.race([
    doc.fonts.ready,
    new Promise(function (res) { setTimeout(res, 1500); })
  ]) : Promise.resolve();

  /* ======================================================================
     1. nav: 배경 상태, 현재 섹션, 모바일 메뉴
     ====================================================================== */
  function initNav() {
    var header = $('#site-header');
    if (!header) return;
    var sections = $$('main > section[data-surface], .site-footer');
    var links = $$('.nav-links a[data-nav]');
    var menuBtn = $('.menu-btn', header);
    var sheet = $('#menu-sheet');
    var menuOpen = false;
    var ticking = false;

    function update() {
      ticking = false;
      var h = header.offsetHeight;
      var cur = null;
      for (var i = 0; i < sections.length; i++) {
        var r = sections[i].getBoundingClientRect();
        if (r.top <= h && r.bottom > h) { cur = sections[i]; break; }
      }
      var surface = cur ? cur.getAttribute('data-surface') : 'dark';
      var atTop = window.scrollY <= 8 && (!cur || cur.id === 'top');
      header.setAttribute('data-surface', surface === 'dark' ? 'dark' : 'light');
      header.setAttribute('data-state', (atTop && !menuOpen) ? 'top' : 'solid');
      var id = cur ? cur.id : '';
      if (id === 'meetings') id = 'data';
      links.forEach(function (a) {
        if (a.getAttribute('data-nav') === id) a.setAttribute('aria-current', 'true');
        else a.removeAttribute('aria-current');
      });
    }
    function onScroll() {
      if (!ticking) { ticking = true; window.requestAnimationFrame(update); }
    }
    window.addEventListener('scroll', onScroll, { passive: true });
    window.addEventListener('resize', onScroll, { passive: true });
    update();

    if (!menuBtn || !sheet) return;
    var focusables = function () {
      return [menuBtn].concat($$('a[href], button:not([disabled])', sheet));
    };
    function onKey(e) {
      if (e.key === 'Escape') { e.preventDefault(); closeMenu(true); return; }
      if (e.key === 'Tab') {
        var f = focusables();
        var first = f[0], last = f[f.length - 1];
        if (e.shiftKey && doc.activeElement === first) { e.preventDefault(); last.focus(); }
        else if (!e.shiftKey && doc.activeElement === last) { e.preventDefault(); first.focus(); }
        else if (f.indexOf(doc.activeElement) === -1) { e.preventDefault(); first.focus(); }
      }
    }
    function openMenu() {
      menuOpen = true;
      sheet.hidden = false;
      window.requestAnimationFrame(function () {
        window.requestAnimationFrame(function () { sheet.classList.add('is-open'); });
      });
      menuBtn.setAttribute('aria-expanded', 'true');
      menuBtn.setAttribute('aria-label', '메뉴 닫기');
      root.style.overflow = 'hidden';
      doc.addEventListener('keydown', onKey);
      update();
      var firstLink = $('a', sheet);
      if (firstLink) firstLink.focus({ preventScroll: true });
    }
    function closeMenu(returnFocus) {
      if (!menuOpen) return;
      menuOpen = false;
      sheet.classList.remove('is-open');
      sheet.hidden = true;
      menuBtn.setAttribute('aria-expanded', 'false');
      menuBtn.setAttribute('aria-label', '메뉴 열기');
      root.style.overflow = '';
      doc.removeEventListener('keydown', onKey);
      update();
      if (returnFocus) menuBtn.focus();
    }
    menuBtn.addEventListener('click', function () { if (menuOpen) closeMenu(true); else openMenu(); });
    $$('a', sheet).forEach(function (a) {
      a.addEventListener('click', function () { closeMenu(false); });
    });
    var mqWide = window.matchMedia('(min-width: 1120px)');
    var onWide = function () { if (mqWide.matches) closeMenu(false); };
    if (mqWide.addEventListener) mqWide.addEventListener('change', onWide);
    else if (mqWide.addListener) mqWide.addListener(onWide);
  }

  /* ======================================================================
     2. reveal: 스크롤 진입 (한 번만)
     ====================================================================== */
  function initReveal() {
    if (reduced() || !hasIO) return;
    $$('[data-reveal-group]').forEach(function (g) {
      var kids = $$('[data-reveal]', g).filter(function (c) { return c.parentElement === g; });
      kids.forEach(function (c, i) {
        if (!c.style.getPropertyValue('--rd')) c.style.setProperty('--rd', (Math.min(i, 5) * 80) + 'ms');
      });
    });
    var vh = window.innerHeight || 800;
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (!e.isIntersecting) return;
        if (e.intersectionRatio >= 0.15 || e.intersectionRect.height >= vh * 0.3) {
          e.target.classList.add('is-in');
          io.unobserve(e.target);
        }
      });
    }, { threshold: [0, 0.15, 0.3], rootMargin: '0px 0px -10% 0px' });
    $$('[data-reveal]').forEach(function (n) { io.observe(n); });
    root.classList.add('reveal-on');
  }

  /* ======================================================================
     3. countUp: 지표 띠 (화면 아래에 있을 때만 0에서 센다)
     ====================================================================== */
  function initCountUp() {
    var strip = $('[data-countup]');
    if (!strip || reduced() || !hasIO) return;
    if (strip.getBoundingClientRect().top < (window.innerHeight || 800)) return;
    var items = $$('[data-count], [data-count-man]', strip);
    function setMan(el, v) {
      var eok = Math.floor(v / 10000), man = v % 10000;
      var eokN = $('.n-eok', el), units = $$('.u-in', el), manN = $('.n-man', el);
      var showEok = eok > 0;
      eokN.textContent = String(eok);
      eokN.style.display = showEok ? '' : 'none';
      if (units[0]) units[0].style.display = showEok ? '' : 'none';
      manN.textContent = fmt(man);
    }
    items.forEach(function (el) {
      if (el.hasAttribute('data-count-man')) setMan(el, 0);
      else el.textContent = '0';
    });
    var io = new IntersectionObserver(function (entries) {
      if (!entries.some(function (e) { return e.isIntersecting; })) return;
      io.disconnect();
      var t0 = performance.now();
      function frame(now) {
        var done = true;
        items.forEach(function (el, i) {
          var p = clamp01((now - t0 - i * 120) / 1400);
          if (p < 1) done = false;
          var k = easeOutCubic(p);
          if (el.hasAttribute('data-count-man')) {
            setMan(el, Math.round(Number(el.getAttribute('data-count-man')) * k));
          } else {
            el.textContent = fmt(Number(el.getAttribute('data-count')) * k);
          }
        });
        if (!done) window.requestAnimationFrame(frame);
      }
      window.requestAnimationFrame(frame);
    }, { threshold: 0.4 });
    io.observe(strip);
  }

  /* ======================================================================
     4. heroMap: 17개 시도 타일 지도와 예시 시나리오
     ====================================================================== */
  var TILES = [
    ['인천', 0, 0], ['서울', 0, 1], ['경기', 0, 2], ['강원', 0, 3],
    ['충남', 1, 0], ['세종', 1, 1], ['충북', 1, 2], ['경북', 1, 3],
    ['전북', 2, 0], ['대전', 2, 1], ['대구', 2, 2], ['울산', 2, 3],
    ['광주', 3, 0], ['전남', 3, 1], ['경남', 3, 2], ['부산', 3, 3],
    ['제주', 4, 0]
  ];
  var SCENARIOS = [
    {
      // 시나리오 1: 순차 확산형 (세종 시작, 0장 조정 반영)
      resetAt: 17600, end: 18400, total: 5,
      obs: [['세종', 300, 1], ['충남', 4100, 2], ['충북', 7300, 3], ['대전', 10500, 4]],
      lines: [['세종', '충남', 'ref', 3500], ['세종', '충북', 'time', 6700], ['세종', '대전', 'time', 9900]],
      pred: [['전북', 13100, 0.6], ['경북', 13100, 0.35]],
      rings: false,
      caps: [
        [300, 'T월: 세종시의회에서 이슈 A를 처음 관측했습니다 (예시)'],
        [3500, 'T+2개월: 충남도의회 회의록에 세종의 사례를 언급한 원문이 있습니다. 명시적 참조로 표시합니다 (예시)'],
        [6700, 'T+3개월: 충북도의회에서 후행 관측되었습니다. 원문상 참조가 없으므로 시간 선후만 표시합니다 (예시)'],
        [9900, 'T+5개월: 대전시의회에서 후행 관측되었습니다 (예시)'],
        [13100, '아직 관측되지 않은 의회마다 다음 기간에 논의가 나타날 확률을 계산합니다 (예시)']
      ]
    },
    {
      // 시나리오 2: 공통 외부요인형 (선과 번호 없음)
      resetAt: 6000, end: 6800, total: 1,
      obs: [['서울', 0], ['부산', 40], ['인천', 80], ['경기', 120], ['강원', 160], ['전남', 200], ['경북', 240], ['경남', 280], ['제주', 320]],
      lines: [],
      pred: [],
      rings: true,
      caps: [
        [0, 'T월: 9개 의회에서 같은 달에 관측되었고, 상위법 개정 단서가 함께 나타났습니다. 공통 외부요인형으로 분류하고 의회 간 경로를 그리지 않습니다 (예시)']
      ]
    }
  ];

  var heroCtl = null;

  function initHeroMap() {
    var panel = $('.map-panel');
    if (!panel) return;
    var fig = $('.map-figure', panel);
    var body = $('.map-body', panel);
    var cap = $('.map-caption', panel);
    var capStep = $('.map-caption__step', cap);
    var capText = $('.map-caption__text', cap);
    var capList = $('.map-caption__list', cap);
    var tabs = $$('.seg__btn', panel);
    var pauseBtn = $('.pause-btn', panel);

    var st = {
      scen: 0, t: 0, mode: 'loop', userPaused: false, autoPaused: false, ended: false,
      raf: 0, last: 0, T: 0, nodes: null, capIdx: -2, started: false, offscreen: false
    };

    function tileSize() {
      var w = body.clientWidth || 312;
      if (w >= 312) return 72;
      if (w >= 280) return 64;
      return 60;
    }

    function build() {
      var T = tileSize();
      st.T = T;
      var G = 8, P = T + G;
      var jejuY = 3 * P + T + (T === 72 ? 20 : 16);
      var W = 3 * P + T, H = jejuY + T;
      fig.style.minHeight = H + 'px';
      fig.innerHTML = '';
      var svg = svgEl('svg', { width: W, height: H, viewBox: '0 0 ' + W + ' ' + H, 'class': 'hmap', focusable: 'false', 'aria-hidden': 'true' }, fig);
      var defs = svgEl('defs', null, svg);
      var gTiles = svgEl('g', null, svg);
      var gLines = svgEl('g', null, svg);
      var gBadges = svgEl('g', null, svg);
      var nameSize = T === 72 ? 13 : 12;
      var nameDy = T === 72 ? 20 : 18;
      var tiles = {};
      TILES.forEach(function (d) {
        var name = d[0], r = d[1], c = d[2];
        var x = c * P, y = (r === 4) ? jejuY : r * P;
        var g = svgEl('g', null, gTiles);
        svgEl('rect', { x: x + 0.5, y: y + 0.5, width: T - 1, height: T - 1, rx: 8, 'class': 'm-idle' }, g);
        var obs = svgEl('rect', { x: x, y: y, width: T, height: T, rx: 8, 'class': 'm-obs', opacity: 0 }, g);
        var pred = svgEl('rect', { x: x + 0.75, y: y + 0.75, width: T - 1.5, height: T - 1.5, rx: 8, 'class': 'm-pred', opacity: 0 }, g);
        var nIdle = svgText(g, x + 10, y + nameDy, name, 'm-name', { 'font-size': nameSize });
        var nObs = svgText(g, x + 10, y + nameDy, name, 'm-name m-name--obs', { 'font-size': nameSize, opacity: 0 });
        var nPred = svgText(g, x + 10, y + nameDy, name, 'm-name m-name--pred', { 'font-size': nameSize, opacity: 0 });
        var cx = x + T / 2, cy = y + T / 2 + 4;
        var dot = svgEl('circle', { cx: cx, cy: cy, r: 4, 'class': 'm-dot', opacity: 0 }, g);
        var predG = svgEl('g', { opacity: 0 }, g);
        svgEl('rect', { x: x + 10, y: y + T - 14, width: T - 20, height: 4, rx: 2, 'class': 'm-track' }, predG);
        var bar = svgEl('rect', { x: x + 10, y: y + T - 14, width: 0, height: 4, rx: 2, 'class': 'm-bar' }, predG);
        var ring = svgEl('rect', { x: x + 1, y: y + 1, width: T - 2, height: T - 2, rx: 8, 'class': 'm-ring', opacity: 0 }, g);
        var badge = svgEl('g', { 'class': 'm-badge', opacity: 0 }, gBadges);
        svgEl('circle', { cx: x + T - 13, cy: y + 13, r: 9, 'class': 'm-badge-bg' }, badge);
        var bt = svgText(badge, x + T - 13, y + 17, '', 'm-badge-tx');
        tiles[name] = { x: x, y: y, cx: cx, cy: cy, obs: obs, pred: pred, nIdle: nIdle, nObs: nObs, nPred: nPred, dot: dot, predG: predG, bar: bar, ring: ring, badge: badge, badgeText: bt, T: T };
      });

      // 연결선 (시나리오 1만 있음)
      var lines = [];
      SCENARIOS.forEach(function (S, si) {
        S.lines.forEach(function (L) {
          var A = tiles[L[0]], B = tiles[L[1]];
          var dx = B.cx - A.cx, dy = B.cy - A.cy, len = Math.sqrt(dx * dx + dy * dy);
          var nx = -dy / len, ny = dx / len;
          if (ny < 0 || (ny === 0 && nx < 0)) { nx = -nx; ny = -ny; }
          var Cx = (A.cx + B.cx) / 2 + nx * 0.18 * len, Cy = (A.cy + B.cy) / 2 + ny * 0.18 * len;
          var ux = Cx - A.cx, uy = Cy - A.cy, ul = Math.sqrt(ux * ux + uy * uy);
          var Sx = A.cx + ux / ul * 8, Sy = A.cy + uy / ul * 8;
          var vx = Cx - B.cx, vy = Cy - B.cy, vl = Math.sqrt(vx * vx + vy * vy);
          var Ex = B.cx + vx / vl * 12, Ey = B.cy + vy / vl * 12;
          var ex = Ex - Cx, ey = Ey - Cy, el = Math.sqrt(ex * ex + ey * ey);
          ex /= el; ey /= el;
          var item = { scen: si, kind: L[2], t0: L[3] };
          if (L[2] === 'ref') {
            var Ex2 = Ex - ex * 6, Ey2 = Ey - ey * 6;
            var d = 'M' + r2(Sx) + ' ' + r2(Sy) + ' Q' + r2(Cx) + ' ' + r2(Cy) + ' ' + r2(Ex2) + ' ' + r2(Ey2);
            var p = svgEl('path', { d: d, 'class': 'm-ref', opacity: 0 }, gLines);
            var bx = Ex - ex * 8, by = Ey - ey * 8, px = -ey * 4, py = ex * 4;
            var head = svgEl('path', {
              d: 'M' + r2(bx + px) + ' ' + r2(by + py) + ' L' + r2(Ex) + ' ' + r2(Ey) + ' L' + r2(bx - px) + ' ' + r2(by - py) + ' Z',
              'class': 'm-arrow', opacity: 0
            }, gLines);
            item.path = p; item.head = head;
            item.len = p.getTotalLength();
            p.style.strokeDasharray = item.len + ' ' + item.len;
          } else {
            var d2 = 'M' + r2(Sx) + ' ' + r2(Sy) + ' Q' + r2(Cx) + ' ' + r2(Cy) + ' ' + r2(Ex) + ' ' + r2(Ey);
            var id = uid('hm');
            var mask = svgEl('mask', { id: id, maskUnits: 'userSpaceOnUse', x: -10, y: -10, width: W + 20, height: H + 20 }, defs);
            var mp = svgEl('path', { d: d2, fill: 'none', stroke: '#fff', 'stroke-width': 6, 'stroke-linecap': 'round' }, mask);
            var p2 = svgEl('path', { d: d2, 'class': 'm-time', mask: 'url(#' + id + ')', opacity: 0 }, gLines);
            item.path = p2; item.maskPath = mp;
            item.len = p2.getTotalLength();
            mp.style.strokeDasharray = item.len + ' ' + item.len;
          }
          lines.push(item);
        });
      });
      st.nodes = { tiles: tiles, lines: lines };
      st.capIdx = -2;
      render();
    }

    function setOp(node, v) {
      var s = v <= 0.001 ? '0' : (v >= 0.999 ? '1' : String(Math.round(v * 1000) / 1000));
      if (node.getAttribute('opacity') !== s) node.setAttribute('opacity', s);
    }

    function render() {
      if (!st.nodes) return;
      var S = SCENARIOS[st.scen], t = st.t;
      var R = t < S.resetAt ? 1 : 1 - clamp01((t - S.resetAt) / 500);
      var tiles = st.nodes.tiles;
      var state = {};
      TILES.forEach(function (d) { state[d[0]] = { o: 0, b: 0, n: 0, p: 0, bar: 0, ring: -1 }; });
      S.obs.forEach(function (o) {
        var s = state[o[0]];
        s.o = R * easeOut(clamp01((t - o[1]) / 360));
        if (o[2]) { s.n = o[2]; s.b = R * easeOut(clamp01((t - o[1]) / 240)); }
        if (S.rings && t < S.resetAt) {
          var q = (t - o[1] - 360) / 900;
          if (q >= 0 && q <= 1) s.ring = easeOut(q);
        }
      });
      S.pred.forEach(function (p) {
        var s = state[p[0]];
        s.p = R * clamp01((t - p[1]) / 300);
        s.bar = p[2] * easeOut(clamp01((t - p[1] - 150) / 600));
      });
      TILES.forEach(function (d) {
        var n = tiles[d[0]], s = state[d[0]];
        setOp(n.obs, s.o);
        setOp(n.nObs, s.o);
        setOp(n.dot, s.o);
        setOp(n.pred, s.p);
        setOp(n.nPred, s.p * (1 - s.o));
        setOp(n.nIdle, (1 - s.o) * (1 - s.p));
        setOp(n.predG, s.p);
        var bw = r2((n.T - 20) * s.bar);
        if (n.bar.getAttribute('width') !== String(bw)) n.bar.setAttribute('width', bw);
        setOp(n.badge, s.b);
        if (s.n && n.badgeText.textContent !== String(s.n)) n.badgeText.textContent = String(s.n);
        var sc = 0.6 + 0.4 * s.b;
        n.badge.style.transform = s.b > 0 && s.b < 1 ? 'scale(' + r2(sc) + ')' : '';
        if (s.ring >= 0) {
          setOp(n.ring, 0.6 * (1 - s.ring));
          n.ring.style.transform = 'scale(' + r2(1 + 0.12 * s.ring) + ')';
        } else {
          setOp(n.ring, 0);
          n.ring.style.transform = '';
        }
      });
      st.nodes.lines.forEach(function (L) {
        if (L.scen !== st.scen) { setOp(L.path, 0); if (L.head) setOp(L.head, 0); return; }
        var p = easeInOut(clamp01((t - L.t0) / 700));
        setOp(L.path, p > 0 ? R : 0);
        if (L.kind === 'ref') {
          L.path.style.strokeDashoffset = r2(L.len * (1 - p)) + 'px';
          setOp(L.head, R * clamp01((t - L.t0 - 600) / 160));
        } else {
          L.maskPath.style.strokeDashoffset = r2(L.len * (1 - p)) + 'px';
        }
      });
      // 캡션
      var idx = -1;
      if (t < S.resetAt) {
        for (var i = 0; i < S.caps.length; i++) if (t >= S.caps[i][0]) idx = i;
      }
      var key = st.scen * 10 + idx;
      if (key !== st.capIdx && !cap.classList.contains('is-static')) {
        st.capIdx = key;
        if (idx < 0) {
          capStep.textContent = '';
          capText.textContent = '';
        } else {
          capStep.textContent = (idx + 1) + ' / ' + S.total;
          capText.textContent = S.caps[idx][1];
          cap.classList.remove('is-swap');
          void cap.offsetWidth;
          cap.classList.add('is-swap');
        }
      }
    }

    function setStaticCaptions(on) {
      cap.classList.toggle('is-static', on);
      capList.hidden = !on;
      if (on) {
        capList.innerHTML = '';
        SCENARIOS[st.scen].caps.forEach(function (c) {
          var li = doc.createElement('li');
          li.textContent = c[1];
          capList.appendChild(li);
        });
      } else {
        st.capIdx = -2;
      }
    }

    function syncTabs() {
      tabs.forEach(function (b, i) {
        var on = i === st.scen;
        b.setAttribute('aria-selected', on ? 'true' : 'false');
        b.tabIndex = on ? 0 : -1;
      });
      body.setAttribute('aria-labelledby', tabs[st.scen] ? tabs[st.scen].id : 'hero-tab-1');
    }

    function running() {
      return st.started && !st.userPaused && !st.autoPaused && !st.ended && !reduced();
    }
    function updatePauseBtn() {
      if (!pauseBtn) return;
      var paused = !running() && (st.userPaused || st.ended);
      pauseBtn.setAttribute('data-state', paused ? 'paused' : 'playing');
      pauseBtn.setAttribute('aria-label', paused ? '애니메이션 재생' : '애니메이션 일시정지');
    }
    function tick(now) {
      st.raf = 0;
      if (!running()) return;
      var dt = st.last ? Math.min(now - st.last, 100) : 16;
      st.last = now;
      st.t += dt;
      var S = SCENARIOS[st.scen];
      if (st.mode === 'loop') {
        if (st.t >= S.end) {
          st.t -= S.end;
          st.scen = (st.scen + 1) % SCENARIOS.length;
          syncTabs();
        }
      } else if (st.t >= S.resetAt - 1) {
        st.t = S.resetAt - 1;
        st.ended = true;
        updatePauseBtn();
      }
      render();
      if (running()) st.raf = window.requestAnimationFrame(tick);
    }
    function ensureLoop() {
      if (running() && !st.raf) {
        st.last = 0;
        st.raf = window.requestAnimationFrame(tick);
      }
    }
    function showStaticScene() {
      st.t = SCENARIOS[st.scen].resetAt - 1;
      setStaticCaptions(true);
      render();
    }

    function select(i, focus) {
      st.scen = i;
      syncTabs();
      if (focus && tabs[i]) tabs[i].focus();
      if (reduced()) { showStaticScene(); return; }
      st.mode = 'single';
      st.t = 0;
      st.ended = false;
      st.userPaused = false;
      st.started = true;
      st.capIdx = -2;
      render();
      updatePauseBtn();
      ensureLoop();
    }

    tabs.forEach(function (b, i) {
      b.addEventListener('click', function () { select(i, false); });
      b.addEventListener('keydown', function (e) {
        var n = tabs.length, j = -1;
        if (e.key === 'ArrowRight' || e.key === 'ArrowDown') j = (i + 1) % n;
        else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') j = (i - 1 + n) % n;
        else if (e.key === 'Home') j = 0;
        else if (e.key === 'End') j = n - 1;
        if (j >= 0) { e.preventDefault(); select(j, true); }
      });
    });
    if (pauseBtn) {
      pauseBtn.addEventListener('click', function () {
        if (st.ended) {
          st.ended = false; st.t = 0; st.userPaused = false; st.capIdx = -2;
        } else {
          st.userPaused = !st.userPaused;
        }
        st.started = true;
        updatePauseBtn();
        render();
        ensureLoop();
      });
    }

    // 화면 밖이거나 탭이 숨겨지면 멈춘다
    function syncAuto() {
      st.autoPaused = doc.hidden || st.offscreen;
      updatePauseBtn();
      ensureLoop();
    }
    if (hasIO) {
      var io = new IntersectionObserver(function (entries) {
        entries.forEach(function (e) { st.offscreen = e.intersectionRatio < 0.2; });
        syncAuto();
      }, { threshold: [0, 0.2, 0.4] });
      io.observe(panel);
    }
    doc.addEventListener('visibilitychange', syncAuto);

    // 크기 변화: 타일 크기가 바뀔 때만 다시 만든다
    if ('ResizeObserver' in window) {
      var rTimer = 0;
      new ResizeObserver(function () {
        clearTimeout(rTimer);
        rTimer = setTimeout(function () { if (tileSize() !== st.T) build(); }, 100);
      }).observe(body);
    }

    build();
    syncTabs();
    if (reduced()) {
      if (pauseBtn) pauseBtn.hidden = true;
      showStaticScene();
    } else {
      updatePauseBtn();
      var delay = root.classList.contains('reveal-on') ? 1040 : 200;
      setTimeout(function () { st.started = true; updatePauseBtn(); ensureLoop(); }, delay);
    }

    heroCtl = {
      printOn: function () {
        heroCtl._saved = { scen: st.scen, t: st.t, userPaused: st.userPaused, isStatic: cap.classList.contains('is-static') };
        st.userPaused = true;
        st.scen = 0;
        st.t = SCENARIOS[0].resetAt - 1;
        setStaticCaptions(true);
        cap.classList.add('is-print');
        render();
      },
      printOff: function () {
        var s = heroCtl._saved;
        if (!s) return;
        cap.classList.remove('is-print');
        st.scen = s.scen; st.t = s.t; st.userPaused = s.userPaused;
        if (!s.isStatic) setStaticCaptions(false);
        else setStaticCaptions(true);
        syncTabs();
        render();
        updatePauseBtn();
        ensureLoop();
      }
    };
  }

  /* ======================================================================
     5. charts: 7.2 ~ 7.6 (컨테이너 폭으로 다시 그린다)
     ====================================================================== */
  var chartList = [];

  function registerChart(box, render) {
    var c = { box: box, render: render, drawn: false, w: 0 };
    chartList.push(c);
    return c;
  }
  function drawChart(c, animate) {
    var W = Math.floor(c.box.clientWidth);
    if (W < 40) return;
    c.w = W;
    c.box.innerHTML = '';
    c.render(c.box, W, !!animate && !reduced());
    c.drawn = true;
  }
  function initCharts() {
    var renders = {
      refine: renderRefine,
      dedupe: renderDedupe,
      monthly: renderMonthly,
      funnel: renderFunnel,
      lanes: function (box, W, a) { renderLanes(box, W, a, laneState.type, false); },
      'lanes-mini': function (box, W, a) { renderLanes(box, W, a, 'mini', true); }
    };
    $$('[data-chart]').forEach(function (box) {
      var fn = renders[box.getAttribute('data-chart')];
      if (fn) {
        var c = registerChart(box, fn);
        box._chart = c;
      }
    });
    fontsReady.then(function () {
      if (hasIO) {
        var io = new IntersectionObserver(function (entries) {
          entries.forEach(function (e) {
            if (!e.isIntersecting) return;
            var c = e.target._chart;
            if (c && !c.drawn) drawChart(c, true);
            io.unobserve(e.target);
          });
        }, { threshold: 0.3 });
        chartList.forEach(function (c) { io.observe(c.box); });
      } else {
        chartList.forEach(function (c) { drawChart(c, false); });
      }
      if ('ResizeObserver' in window) {
        var timers = new WeakMap();
        var ro = new ResizeObserver(function (entries) {
          entries.forEach(function (e) {
            var c = e.target._chart;
            if (!c || !c.drawn) return;
            var w = Math.floor(e.target.clientWidth);
            if (Math.abs(w - c.w) <= 1) return;
            clearTimeout(timers.get(e.target));
            timers.set(e.target, setTimeout(function () { drawChart(c, false); }, 100));
          });
        });
        chartList.forEach(function (c) { ro.observe(c.box); });
      }
    });
  }
  function drawAllStatic() {
    chartList.forEach(function (c) { if (!c.drawn) drawChart(c, false); });
  }

  /* 7.2 정제 단계 막대 */
  function renderRefine(box, W, animate) {
    var compact = W < 400;
    var H = compact ? 288 : 296;
    var bh = compact ? 20 : 22;
    var svg = makeSvg(box, W, H, '원자료에서 분석 대상까지',
      '원자료 회의록 10,263건 가운데 HTML이 완전히 같은 중복 378건을 제외하면 9,885건, 본문이 같은 사본 2,117건을 더 제외하면 7,768건이 남습니다. 분석 대상 7,768건은 2024년 4,004건과 2025년 3,764건입니다.');
    var s = W / 10263;
    var rows = [
      { y0: 20, name: '원자료', desc: '2024·2025년 압축 파일의 회의록', val: '10,263건' },
      { y0: 112, name: '완전 중복 제외', desc: 'HTML이 완전히 같은 회의록', val: '9,885건' },
      { y0: 204, name: '본문 사본 제외', desc: '남은 회의록이 분석 대상입니다', val: '7,768건' }
    ];
    rows.forEach(function (r, i) {
      svgText(svg, 0, r.y0, r.name, 'c15 w7 f1');
      svgText(svg, W, r.y0, r.val, 'c15 w7 f1 end');
      svgText(svg, 0, r.y0 + 19, r.desc, 'c13 f3');
      var by = r.y0 + 32;
      var grow = svgEl('g', { 'class': 'c-grow' }, svg);
      var after = svgEl('g', null, svg);
      var labY = by + bh + 18;
      if (i === 0) {
        svgEl('path', { d: barPath(0, by, 10263 * s, bh, 'r'), 'class': 'c-context' }, grow);
      } else if (i === 1) {
        svgEl('path', { d: barPath(0, by, 9885 * s - 1, bh, 'n'), 'class': 'c-context' }, grow);
        svgEl('path', { d: barPath(9885 * s + 1.5, by + 0.5, 10263 * s - 9885 * s - 2, bh - 1, 'r'), 'class': 'c-ghost' }, after);
        svgText(after, 10263 * s, labY, '378건 제외', 'c13 w5 f2 end');
      } else {
        var x24 = 4004 * s - 1, x25s = 4004 * s + 1, x25e = 7768 * s - 1;
        svgEl('path', { d: barPath(0, by, x24, bh, 'n'), 'class': 'c-signal' }, grow);
        svgEl('path', { d: barPath(x25s, by, x25e - x25s, bh, 'n'), 'class': 'c-signal' }, grow);
        svgEl('path', { d: barPath(7768 * s + 1.5, by + 0.5, 9885 * s - 7768 * s - 2, bh - 1, 'r'), 'class': 'c-ghost' }, after);
        svgText(after, 9885 * s, labY, '2,117건 제외', 'c13 w5 f2 end');
        var t1 = svgText(after, 8, by + bh / 2 + 4, '2024년 4,004', 'c12 w6 fon');
        var t2 = svgText(after, x25s + 8, by + bh / 2 + 4, '2025년 3,764', 'c12 w6 fon');
        var w1 = t1.getComputedTextLength ? t1.getComputedTextLength() : 0;
        var w2 = t2.getComputedTextLength ? t2.getComputedTextLength() : 0;
        if (w1 > x24 - 16 || w2 > (x25e - x25s) - 16) {
          after.removeChild(t1);
          after.removeChild(t2);
          svgText(after, 0, labY, '2024년 4,004 · 2025년 3,764', 'c12 w6 f2');
        }
      }
      if (animate) {
        growX(grow, i * 160, 700);
        if (after.childNodes.length) fadeIn(after, i * 160 + 700, 240);
      }
    });
  }

  /* 7.3 2025년 사본 제거 전후 */
  function renderDedupe(box, W, animate) {
    var compact = W < 400;
    var data = [['서울', 715, 356], ['강원', 624, 275], ['인천', 455, 221], ['경북', 404, 211], ['울산', 358, 196]];
    var nameCol = compact ? 40 : 52, x0 = nameCol + 8, PW = W - x0 - 44, s = PW / 800;
    var rowH = compact ? 52 : 56;
    var gridB = 8 + rowH * 5;
    var H = compact ? 296 : 316;
    var svg = makeSvg(box, W, H, '2025년 사본 제거 전후 회의록 수',
      '본문이 같은 사본을 제외하기 전과 후의 2025년 회의록 수입니다. 서울 715건에서 356건, 강원 624건에서 275건, 인천 455건에서 221건, 경북 404건에서 211건, 울산 358건에서 196건으로 줄었습니다.');
    var ticks = compact ? [0, 400, 800] : [0, 200, 400, 600, 800];
    ticks.forEach(function (v) {
      var x = Math.round(x0 + v * s) + 0.5;
      svgEl('line', { x1: x, x2: x, y1: 0, y2: gridB, 'class': v === 0 ? 'c-axis' : 'c-grid' }, svg);
      svgText(svg, x0 + v * s, gridB + 18, v === 800 ? '800건' : String(v), 'c12 f3 mid');
    });
    var befores = [], afters = [];
    data.forEach(function (d, i) {
      var y = 8 + rowH * i;
      svgText(svg, 0, y + 26, d[0], (compact ? 'c13' : 'c14') + ' w6 f1');
      var gb = svgEl('g', null, svg);
      var pb = svgEl('path', { d: barPath(x0, y + 4, d[1] * s, 16, 'r'), 'class': 'c-context c-grow' }, gb);
      var vb = svgText(gb, x0 + d[1] * s + 6, y + 16, fmt(d[1]), 'c12 w5 f3');
      var ga = svgEl('g', null, svg);
      var pa = svgEl('path', { d: barPath(x0, y + 24, d[2] * s, 16, 'r'), 'class': 'c-signal c-grow' }, ga);
      var va = svgText(ga, x0 + d[2] * s + 6, y + 36, fmt(d[2]), 'c12 w7 f1');
      befores.push([pb, vb]);
      afters.push([pa, va]);
    });
    if (animate) {
      befores.forEach(function (b, i) { growX(b[0], i * 60, 600); fadeIn(b[1], i * 60 + 600, 120); });
      var start = 60 * (data.length - 1) + 600 + 300;
      afters.forEach(function (a, i) { growX(a[0], start + i * 60, 600); fadeIn(a[1], start + i * 60 + 600, 120); });
    }
  }

  /* 7.4 월별 회의록 수 묶음 막대 */
  function renderMonthly(box, W, animate) {
    var y24 = [229, 215, 201, 247, 173, 494, 387, 116, 297, 224, 1112, 309];
    var y25 = [64, 389, 211, 273, 76, 498, 294, 95, 347, 204, 942, 371];
    var compact = W < 480;
    var plotL = 44, plotR = W - 8, band = (plotR - plotL) / 12;
    var gw = Math.min(40, band * 0.72), bw = (gw - 2) / 2;
    var PH = compact ? 168 : 220, top = 28, yb = top + PH, H = yb + 28;
    function Y(v) { return yb - v / 1200 * PH; }
    var svg = makeSvg(box, W, H, '월별 회의록 수 (2024~2025년)',
      '중복과 사본을 제외한 분석 대상 회의록 수입니다. 2024년은 1월부터 차례로 229, 215, 201, 247, 173, 494, 387, 116, 297, 224, 1,112, 309건이고, 2025년은 64, 389, 211, 273, 76, 498, 294, 95, 347, 204, 942, 371건입니다. 행정사무감사가 있는 11월과 결산 정례회가 있는 6월에 회의록이 많습니다.');
    var attnLabels = { 6: '정례회(결산)', 11: '행정사무감사' };
    [6, 11].forEach(function (m) {
      svgEl('rect', { x: r2(plotL + (m - 1) * band), y: 4, width: r2(band), height: yb - 4, 'class': 'c-attn' }, svg);
    });
    var ticks = compact ? [0, 600, 1200] : [0, 300, 600, 900, 1200];
    ticks.forEach(function (v) {
      var y = Math.round(Y(v)) + 0.5;
      if (v > 0) svgEl('line', { x1: plotL, x2: r2(plotR), y1: y, y2: y, 'class': 'c-grid' }, svg);
      svgText(svg, 36, Y(v) + 4, fmt(v), 'c12 f3 end');
    });
    var groups = [], lateTexts = [];
    for (var m = 1; m <= 12; m++) {
      var gx = plotL + (m - 1) * band + (band - gw) / 2;
      var g = svgEl('g', { 'class': 'c-bars' }, svg);
      var b1 = svgEl('path', { d: barPath(gx, Y(y24[m - 1]), bw, yb - Y(y24[m - 1]), 't'), 'class': 'c-y24 c-grow-y' }, g);
      var b2 = svgEl('path', { d: barPath(gx + bw + 2, Y(y25[m - 1]), bw, yb - Y(y25[m - 1]), 't'), 'class': 'c-y25 c-grow-y' }, g);
      groups.push({ g: g, b1: b1, b2: b2, cx: plotL + (m - 0.5) * band, x1: gx + bw / 2, x2: gx + bw + 2 + bw / 2 });
      svgText(svg, plotL + (m - 0.5) * band, yb + 18, compact ? String(m) : m + '월', 'c12 f3 mid');
    }
    svgEl('line', { x1: plotL, x2: r2(plotR), y1: yb + 0.5, y2: yb + 0.5, 'class': 'c-axis' }, svg);
    [6, 11].forEach(function (m) {
      lateTexts.push(svgText(svg, plotL + (m - 0.5) * band, 18, attnLabels[m], 'c12 w6 fe mid'));
    });
    // 값 표기
    if (compact) {
      lateTexts.push(svgText(svg, groups[10].x1, Y(y24[10]) - 6, fmt(y24[10]), 'c12 w7 f1 mid halo-attn'));
    } else {
      [6, 11].forEach(function (m) {
        var a = y24[m - 1], b = y25[m - 1];
        var ya = Y(a) - 6, yb2 = Y(b) - 6, G = groups[m - 1];
        if (Math.abs(ya - yb2) < 16) {
          lateTexts.push(svgText(svg, G.cx, Math.min(ya, yb2), fmt(a) + ' · ' + fmt(b), 'c12 w7 f1 mid halo-attn'));
        } else {
          lateTexts.push(svgText(svg, G.x1, ya, fmt(a), 'c12 w7 f1 mid halo-attn'));
          lateTexts.push(svgText(svg, G.x2, yb2, fmt(b), 'c12 w7 f1 mid halo-attn'));
        }
      });
    }
    // 툴팁 (값은 아래 표에도 있다)
    var tip = doc.createElement('div');
    tip.className = 'chart-tip';
    tip.setAttribute('aria-hidden', 'true');
    box.appendChild(tip);
    var hits = svgEl('g', null, svg);
    groups.forEach(function (G, i) {
      var hit = svgEl('rect', { x: r2(plotL + i * band), y: top, width: r2(band), height: PH, 'class': 'c-hit' }, hits);
      function show() {
        groups.forEach(function (o, j) { o.g.classList.toggle('is-dim', j !== i); });
        tip.innerHTML = '<p class="chart-tip__m">' + (i + 1) + '월</p>' +
          '<p class="chart-tip__row"><i style="background:var(--viz-2)"></i>2024년<b>' + fmt(y24[i]) + '건</b></p>' +
          '<p class="chart-tip__row"><i style="background:var(--viz-3)"></i>2025년<b>' + fmt(y25[i]) + '건</b></p>';
        tip.classList.add('is-on');
        var tw = tip.offsetWidth, th = tip.offsetHeight;
        var left = Math.max(0, Math.min(W - tw, G.cx - tw / 2));
        var topY = Math.max(0, Math.min(Y(y24[i]), Y(y25[i])) - 8 - th);
        tip.style.left = r2(left) + 'px';
        tip.style.top = r2(topY) + 'px';
      }
      function hide() {
        groups.forEach(function (o) { o.g.classList.remove('is-dim'); });
        tip.classList.remove('is-on');
      }
      hit.addEventListener('pointerenter', show);
      hit.addEventListener('pointerdown', show);
      hit.addEventListener('pointerleave', hide);
    });
    if (animate) {
      groups.forEach(function (G, i) {
        growY(G.b1, i * 35, 560);
        growY(G.b2, i * 35 + 60, 560);
      });
      var after = 11 * 35 + 60 + 560;
      lateTexts.forEach(function (t) { fadeIn(t, after, 240); });
    }
  }

  /* 7.5 근거 수준 레인 도식 (P7 본 도식, P4 기능 2 축소판) */
  var LANE_DATA = {
    seq: {
      pts: { A: 2, B: 4, C: 6, D: 8, E: 9 },
      links: [['A', 'B', 'ref'], ['A', 'C', 'ref'], ['C', 'D', 'time'], ['C', 'E', 'time']],
      notes: { A: '최초 관측', B: 'A 언급', C: 'A 언급', D: '참조 없음', E: '참조 없음' },
      title: '순차 확산형 예시',
      desc: '가상의 의회 A에서 2개월째에 처음 관측된 뒤, A를 직접 언급한 B(4개월)와 C(6개월)는 실선 화살표로 잇고, 참조 표현 없이 C 뒤에 관측된 D(8개월)와 E(9개월)는 점선으로만 잇습니다.'
    },
    common: {
      pts: { A: 5, B: 5, C: 5, D: 5, E: 6 },
      links: [],
      notes: {},
      title: '공통 외부요인형 예시',
      desc: '가상의 의회 A부터 D가 5개월째, E가 6개월째에 상위법 개정 단서와 함께 관측되어 의회 사이에 선을 긋지 않습니다.'
    },
    single: {
      pts: { C: 4 },
      links: [],
      notes: {},
      marks: [6, 7, 9],
      title: '단일 지역형 예시',
      desc: '가상의 의회 C에서만 4개월째에 관측되고 이후 같은 의회에서 언급이 이어지며, 다른 의회에서는 관측되지 않습니다.'
    },
    mini: {
      lanes: ['A', 'B', 'C'],
      pts: { A: 2, B: 5, C: 8 },
      links: [['A', 'B', 'ref'], ['B', 'C', 'time']],
      notes: {}
    }
  };
  var laneState = { type: 'seq' };

  function renderLanes(box, W, animate, type, decorative) {
    var D = LANE_DATA[type];
    var lanes = D.lanes || ['A', 'B', 'C', 'D', 'E'];
    var compact = W < 400;
    var nameCol = compact ? 40 : 56;
    var plotL = nameCol + 8, plotR = W - 8, mw = (plotR - plotL) / 12;
    var gap = compact ? 36 : 40;
    function X(m) { return plotL + (m - 0.5) * mw; }
    function Yr(i) { return 24 + gap * i; }
    var axisY = Yr(lanes.length - 1) + 28;
    var H = type === 'mini' ? 170 : (compact ? 220 : 236);
    var svg = makeSvg(box, W, H, D.title || '', D.desc || '', decorative);
    var laneIdx = {};
    lanes.forEach(function (n, i) {
      laneIdx[n] = i;
      var y = Yr(i);
      svgEl('line', { x1: plotL, x2: r2(plotR), y1: y + 0.5, y2: y + 0.5, 'class': 'c-grid' }, svg);
      svgText(svg, 0, y + 4, compact ? n : '의회 ' + n, 'c13 w6 f2');
    });
    svgEl('line', { x1: plotL, x2: r2(plotR), y1: axisY + 0.5, y2: axisY + 0.5, 'class': 'c-axis' }, svg);
    [1, 4, 7, 10].forEach(function (m) {
      svgText(svg, X(m), axisY + 16, compact ? String(m) : m + '개월', 'c12 f3 mid');
    });

    var content = svgEl('g', null, svg);
    var fadeLater = [];
    if (type === 'common') {
      var bx = plotL + 4 * mw, bx2 = plotL + 6 * mw;
      svgEl('rect', { x: r2(bx), y: 14, width: r2(bx2 - bx), height: axisY - 14, 'class': 'c-attn' }, content);
      svgEl('line', { x1: r2(bx), x2: r2(bx), y1: 14, y2: axisY, 'class': 'c-vline' }, content);
      svgText(content, bx, 11, '상위법 개정 (예시)', 'c12 w6 f2 mid halo');
      var ny = Yr(2);
      fadeLater.push(svgText(content, bx2 + 10, ny - 4, '같은 시기 관측', 'c12 w5 f2 halo'));
      fadeLater.push(svgText(content, bx2 + 10, ny + 12, '경로 없음', 'c12 w5 f2 halo'));
    }
    if (type === 'single') {
      var cy = Yr(laneIdx.C);
      D.marks.forEach(function (m) {
        fadeLater.push(svgEl('rect', { x: r2(X(m) - 1), y: cy - 5, width: 2, height: 10, 'class': 'c-mark' }, content));
      });
      lanes.forEach(function (n, i) {
        if (n === 'C') return;
        fadeLater.push(svgText(content, plotR, Yr(i) + 4, '관측 없음', 'c12 f3 end halo'));
      });
    }

    var lineEls = [];
    D.links.forEach(function (L) {
      var xS = X(D.pts[L[0]]), yS = Yr(laneIdx[L[0]]);
      var xT = X(D.pts[L[1]]), yT = Yr(laneIdx[L[1]]);
      var head = null, dd;
      if (L[2] === 'ref') {
        dd = 'M' + r2(xS) + ' ' + (yS + 8) + ' V' + (yT - 6) + ' Q' + r2(xS) + ' ' + yT + ' ' + r2(xS + 6) + ' ' + yT + ' H' + r2(xT - 15);
        var p = svgEl('path', { d: dd, 'class': 'c-ref' }, content);
        head = svgEl('path', { d: 'M' + r2(xT - 17) + ' ' + (yT - 4) + ' L' + r2(xT - 9) + ' ' + yT + ' L' + r2(xT - 17) + ' ' + (yT + 4) + ' Z', 'class': 'c-arrow' }, content);
        lineEls.push({ kind: 'ref', path: p, head: head });
      } else {
        dd = 'M' + r2(xS) + ' ' + (yS + 8) + ' V' + (yT - 6) + ' Q' + r2(xS) + ' ' + yT + ' ' + r2(xS + 6) + ' ' + yT + ' H' + r2(xT - 9);
        var md = maskedDash(svg, dd, 'c-time', W, H);
        content.appendChild(md.path);
        lineEls.push({ kind: 'time', path: md.path, maskPath: md.maskPath });
      }
    });

    var dots = [];
    lanes.forEach(function (n) {
      if (D.pts[n] === undefined) return;
      var x = X(D.pts[n]), y = Yr(laneIdx[n]);
      var g = svgEl('g', { 'class': 'c-pop' }, content);
      svgEl('circle', { cx: r2(x), cy: y, r: 7, 'class': 'c-halo-dot' }, g);
      svgEl('circle', { cx: r2(x), cy: y, r: 5, 'class': 'c-signal' }, g);
      dots.push(g);
      if (D.notes[n]) fadeLater.push(svgText(content, x + 10, y + 4, D.notes[n], 'c12 w5 f2 halo'));
    });

    if (animate) {
      dots.forEach(function (g, i) { popIn(g, i * 60); });
      var lineStart = dots.length * 60 + 180;
      lineEls.forEach(function (L, i) {
        var d0 = lineStart + i * 100;
        if (L.kind === 'ref') {
          drawStroke(L.path, d0, 500);
          fadeIn(L.head, d0 + 420, 120);
        } else {
          revealDash(L.maskPath, L.path, d0, 500);
        }
      });
      fadeLater.forEach(function (n) { fadeIn(n, lineStart + 200, 240); });
    }
    return svg;
  }

  /* 7.6 탐색 결과 확대 연결 막대 */
  function renderFunnel(box, W, animate) {
    var H = 424;
    var svg = makeSvg(box, W, H, '문단에서 정책 참조 후보까지',
      '전체 문단 3,563,803개 가운데 30자 이상 문단은 2,266,277개이고, 그중 다른 시도의 이름을 언급한 문단은 37,169개(30자 이상 문단의 1.6%)입니다. 두 번째 단은 37,169개 막대를 약 96배로 확대해 그린 것으로, 이 가운데 의원 측 발언은 23,709개, 규칙상 정책 참조 후보는 4,456개(의회별 118~568개)입니다. 사람이 검수하기 전의 규칙 후보 수입니다.');
    var s1 = W / 3563803;
    var tier1 = [
      { y0: 20, name: '전체 문단', v: 3563803, cls: 'c-context' },
      { y0: 80, name: '30자 이상 문단', v: 2266277, cls: 'c-context' },
      { y0: 140, name: '다른 시도의 이름을 언급한 문단', v: 37169, cls: 'c-signal' }
    ];
    var g1 = [];
    tier1.forEach(function (r, i) {
      var nameT = svgText(svg, 0, r.y0, r.name, 'c14 w7 f1');
      var valT = svgText(svg, W, r.y0, fmt(r.v), 'c15 w7 f1 end');
      var w = Math.max(3, r.v * s1);
      var p = svgEl('path', { d: barPath(0, r.y0 + 14, w, 20, 'r', w < 6 ? 1 : 3), 'class': r.cls + ' c-grow' }, svg);
      g1.push(p);
      if (i === 2) {
        var nw = nameT.getComputedTextLength ? nameT.getComputedTextLength() : 0;
        var vw = valT.getComputedTextLength ? valT.getComputedTextLength() : 0;
        var note = svgText(svg, W - vw - 12, r.y0, '30자 이상 문단의 1.6%', 'c13 w5 f3 end');
        var noteW = note.getComputedTextLength ? note.getComputedTextLength() : 0;
        if (W - vw - 12 - noteW < nw + 12) {
          svg.removeChild(note);
          svgText(svg, w + 8, r.y0 + 28, '30자 이상 문단의 1.6%', 'c13 w5 f3');
        }
      }
    });
    var w3 = Math.max(3, 37169 * s1);
    var trap = svgEl('g', null, svg);
    svgEl('path', { d: 'M0 178 L' + r2(w3) + ' 178 L' + r2(W) + ' 242 L0 242 Z', 'class': 'c-trap' }, trap);
    svgEl('line', { x1: r2(w3), y1: 178, x2: r2(W), y2: 242, 'class': 'c-trap-edge' }, trap);
    svgText(trap, W - 8, 216, '같은 막대를 약 96배로 확대', 'c12 w5 f2 end halo');

    var s2 = W / 37169;
    var g2 = [];
    var full = svgEl('g', { 'class': 'c-grow' }, svg);
    svgEl('path', { d: barPath(0, 246, W, 20, 'r'), 'class': 'c-signal' }, full);
    svgText(full, 8, 260, '37,169 = 100%', 'c12 w6 fon');
    g2.push(full);
    [
      { y0: 300, name: '그중 의원 측 발언', v: 23709 },
      { y0: 360, name: '그중 규칙상 ‘정책 참조’ 후보', v: 4456 }
    ].forEach(function (r) {
      svgText(svg, 0, r.y0, r.name, 'c14 w7 f1');
      svgText(svg, W, r.y0, fmt(r.v), 'c15 w7 f1 end');
      g2.push(svgEl('path', { d: barPath(0, r.y0 + 14, r.v * s2, 20, 'r'), 'class': 'c-signal c-grow' }, svg));
    });
    svgText(svg, 0, 412, '의회별 118~568개', 'c13 f3');

    if (animate) {
      g1.forEach(function (p, i) { growX(p, i * 120, 600); });
      var tStart = 2 * 120 + 600;
      fadeIn(trap, tStart, 300);
      g2.forEach(function (p, i) { growX(p, tStart + 300 + i * 120, 600); });
    }
  }

  /* ======================================================================
     6. steps: 작동 방식 (1024 이상 탭, 그 아래 아코디언)
     ====================================================================== */
  function initSteps() {
    var wrap = $('.steps-wrap');
    var list = $('#steps');
    if (!wrap || !list) return;
    var items = $$('.step', list);
    var current = 0;
    var mq = window.matchMedia('(min-width: 1024px)');
    var KIND = { dl: '딥러닝 판정 계층', rule: '규칙·집계 계층' };
    var ST = { done: '완료', doing: '진행', plan: '계획' };

    // 아코디언
    function setOpen(i, open) {
      var li = items[i];
      li.classList.toggle('is-open', open);
      $('.step__toggle', li).setAttribute('aria-expanded', open ? 'true' : 'false');
    }
    items.forEach(function (li, i) {
      $('.step__toggle', li).addEventListener('click', function () {
        var willOpen = !li.classList.contains('is-open');
        items.forEach(function (_, j) { if (j !== i) setOpen(j, false); });
        setOpen(i, willOpen);
        if (willOpen) current = i;
      });
    });

    // 단계 선택기
    var desk = doc.createElement('div');
    desk.className = 'steps-desk';
    var tablist = doc.createElement('div');
    tablist.className = 'steps-tabs';
    tablist.setAttribute('role', 'tablist');
    tablist.setAttribute('aria-label', '처리 단계');
    tablist.setAttribute('aria-orientation', 'vertical');
    var panel = doc.createElement('div');
    panel.className = 'steps-panel';
    panel.id = 'steps-panel';
    panel.setAttribute('role', 'tabpanel');
    panel.tabIndex = 0;
    var panelInner = doc.createElement('div');
    panel.appendChild(panelInner);
    desk.appendChild(tablist);
    desk.appendChild(panel);
    wrap.appendChild(desk);

    function stIcon(status, size) {
      return '<svg class="st st--' + status + '" width="' + size + '" height="' + size + '" aria-hidden="true" focusable="false"><use href="#st-' + status + '"/></svg>';
    }
    var tabs = items.map(function (li, i) {
      var id = li.getAttribute('data-step'), kind = li.getAttribute('data-kind'), status = li.getAttribute('data-status');
      var b = doc.createElement('button');
      b.type = 'button';
      b.className = 'steps-tab';
      b.id = 'steps-tab-' + id;
      b.setAttribute('role', 'tab');
      b.setAttribute('aria-controls', 'steps-panel');
      b.setAttribute('aria-selected', i === 0 ? 'true' : 'false');
      b.tabIndex = i === 0 ? 0 : -1;
      b.innerHTML = '<span class="pill pill--' + kind + '">' + id + '</span>' +
        '<span class="steps-tab__name">' + $('.step__name', li).textContent + '</span>' +
        '<span class="steps-tab__st">' + stIcon(status, 12) + ST[status] + '</span>';
      tablist.appendChild(b);
      return b;
    });

    function fillPanel(i) {
      var li = items[i];
      var id = li.getAttribute('data-step'), kind = li.getAttribute('data-kind'), status = li.getAttribute('data-status');
      var frag = doc.createDocumentFragment();
      var head = doc.createElement('div');
      head.className = 'sp-head';
      head.innerHTML = '<span class="pill pill--lg pill--' + kind + '">' + id + '</span>' +
        '<span class="sp-kind">' + KIND[kind] + '</span>' +
        '<span class="tag tag--st">' + stIcon(status, 12) + ST[status] + '</span>';
      frag.appendChild(head);
      var h = doc.createElement('h3');
      h.className = 'sp-title';
      h.textContent = $('.step__name', li).textContent;
      frag.appendChild(h);
      Array.prototype.forEach.call($('.step__inner', li).children, function (c) { frag.appendChild(c.cloneNode(true)); });
      panelInner.innerHTML = '';
      panelInner.appendChild(frag);
      panel.setAttribute('aria-labelledby', tabs[i].id);
    }

    var swapAnim = null;
    function select(i, focus, instant) {
      if (i === current && !instant && panelInner.childNodes.length) {
        if (focus) tabs[i].focus();
        return;
      }
      current = i;
      tabs.forEach(function (b, j) {
        b.setAttribute('aria-selected', j === i ? 'true' : 'false');
        b.tabIndex = j === i ? 0 : -1;
      });
      if (focus) tabs[i].focus();
      if (instant || reduced() || typeof panelInner.animate !== 'function') {
        fillPanel(i);
        return;
      }
      if (swapAnim) swapAnim.cancel();
      swapAnim = panelInner.animate([{ opacity: 1 }, { opacity: 0 }], { duration: 120, easing: 'linear', fill: 'forwards' });
      swapAnim.onfinish = function () {
        fillPanel(current);
        if (swapAnim) swapAnim.cancel();
        swapAnim = panelInner.animate([{ opacity: 0, transform: 'translateY(8px)' }, { opacity: 1, transform: 'none' }], { duration: 220, easing: EASE_OUT_CSS });
      };
    }

    var canHover = window.matchMedia('(hover: hover)').matches;
    tabs.forEach(function (b, i) {
      b.addEventListener('click', function () { select(i, false); });
      var timer = 0;
      if (canHover) {
        b.addEventListener('pointerenter', function () {
          clearTimeout(timer);
          timer = setTimeout(function () { select(i, false); }, 80);
        });
        b.addEventListener('pointerleave', function () { clearTimeout(timer); });
      }
      b.addEventListener('keydown', function (e) {
        var n = tabs.length, j = -1;
        if (e.key === 'ArrowDown' || e.key === 'ArrowRight') j = (i + 1) % n;
        else if (e.key === 'ArrowUp' || e.key === 'ArrowLeft') j = (i - 1 + n) % n;
        else if (e.key === 'Home') j = 0;
        else if (e.key === 'End') j = n - 1;
        if (j >= 0) { e.preventDefault(); select(j, true); }
      });
    });

    function applyMode() {
      if (mq.matches) {
        wrap.classList.add('is-desk');
        select(current, false, true);
      } else {
        wrap.classList.remove('is-desk');
        items.forEach(function (_, j) { setOpen(j, j === current); });
      }
    }
    if (mq.addEventListener) mq.addEventListener('change', applyMode);
    else if (mq.addListener) mq.addListener(applyMode);
    applyMode();
  }

  /* ======================================================================
     7. tabs: P7 유형 전환 (레인 도식)
     ====================================================================== */
  function initLaneTabs() {
    var card = $('.lane-card');
    if (!card) return;
    var tabs = $$('.seg__btn', card);
    var panel = $('#lane-panel');
    var box = $('[data-chart="lanes"]', card);
    var descs = $$('.lane-desc', card);
    function select(i, focus) {
      var type = tabs[i].getAttribute('data-type');
      tabs.forEach(function (b, j) {
        b.setAttribute('aria-selected', j === i ? 'true' : 'false');
        b.tabIndex = j === i ? 0 : -1;
      });
      if (focus) tabs[i].focus();
      panel.setAttribute('aria-labelledby', tabs[i].id);
      descs.forEach(function (d) { d.hidden = d.getAttribute('data-type') !== type; });
      if (type === laneState.type) return;
      laneState.type = type;
      var c = box._chart;
      if (!c) return;
      if (!c.drawn) { drawChart(c, !reduced()); return; }
      var old = box.firstElementChild;
      if (old && !reduced() && typeof old.animate === 'function') {
        var a = old.animate([{ opacity: 1 }, { opacity: 0 }], { duration: 160, easing: 'linear', fill: 'forwards' });
        a.onfinish = function () { drawChart(c, true); };
      } else {
        drawChart(c, false);
      }
    }
    tabs.forEach(function (b, i) {
      b.addEventListener('click', function () { select(i, false); });
      b.addEventListener('keydown', function (e) {
        var n = tabs.length, j = -1;
        if (e.key === 'ArrowRight') j = (i + 1) % n;
        else if (e.key === 'ArrowLeft') j = (i - 1 + n) % n;
        else if (e.key === 'Home') j = 0;
        else if (e.key === 'End') j = n - 1;
        if (j >= 0) { e.preventDefault(); select(j, true); }
      });
    });
  }

  /* ======================================================================
     8. sortTable: 의회별 규모 표
     ====================================================================== */
  function initSortTables() {
    $$('table[data-sortable]').forEach(function (table) {
      var tbody = table.tBodies[0];
      var heads = $$('th[data-sort-col]', table);
      var rows = Array.prototype.slice.call(tbody.rows).map(function (r, i) { return { r: r, i: i }; });
      function num(row, col) {
        var c = row.cells[col];
        return c ? parseFloat(c.textContent.replace(/[^0-9.\-]/g, '')) || 0 : 0;
      }
      heads.forEach(function (th) {
        var btn = $('button', th);
        if (!btn) return;
        btn.addEventListener('click', function () {
          var col = Number(th.getAttribute('data-sort-col'));
          var dir = th.getAttribute('aria-sort') === 'descending' ? 'ascending' : 'descending';
          heads.forEach(function (h) { h.removeAttribute('aria-sort'); });
          th.setAttribute('aria-sort', dir);
          rows.sort(function (a, b) {
            var d = num(a.r, col) - num(b.r, col);
            if (d === 0) return a.i - b.i;
            return dir === 'ascending' ? d : -d;
          });
          rows.forEach(function (o) { tbody.appendChild(o.r); });
        });
      });
    });
  }

  /* ======================================================================
     9. timeline: 상태 집계와 오늘 표시
     ====================================================================== */
  function initTimeline() {
    var tl = $('.timeline');
    if (!tl) return;
    var asof = tl.getAttribute('data-asof');
    var items = $$('.tl-item', tl);
    ['done', 'doing', 'plan'].forEach(function (s) {
      var n = items.filter(function (it) { return it.getAttribute('data-status') === s; }).length;
      var el = $('[data-count-status="' + s + '"]');
      if (el) el.textContent = String(n);
    });
    var today = $('.tl-today', tl);
    var firstFuture = null;
    for (var i = 0; i < items.length; i++) {
      if (items[i].getAttribute('data-end') > asof) { firstFuture = items[i]; break; }
    }
    if (today && firstFuture) tl.insertBefore(today, firstFuture);
    items.forEach(function (it) {
      var next = it.nextElementSibling;
      var nextDone = !!next && next.classList.contains('tl-item') && next.getAttribute('data-status') === 'done';
      it.classList.toggle('is-next-done', nextDone);
    });
    if (!reduced() && hasIO) {
      items.forEach(function (it, i) {
        it.setAttribute('data-reveal', '');
        it.style.setProperty('--rd', Math.min(i, 10) * 60 + 'ms');
      });
    }
  }

  /* ======================================================================
     10. bars: 의회별·지역별 후보 막대 지연값
     ====================================================================== */
  function initBars() {
    $$('.hbar tbody tr').forEach(function (tr) {
      tr.style.setProperty('--i', String(tr.sectionRowIndex));
    });
  }

  /* ======================================================================
     11. print: 접는 영역을 펼치고, 그리지 않은 차트를 최종 상태로 그린다
     ====================================================================== */
  function initPrint() {
    var opened = [];
    function buildLanePrint() {
      var holder = $('.lane-print');
      if (!holder) return;
      holder.innerHTML = '';
      var box = $('[data-chart="lanes"]');
      var W = Math.max(280, Math.min(560, (box && box.clientWidth) || 524));
      [['seq', '순차 확산형'], ['common', '공통 외부요인형'], ['single', '단일 지역형']].forEach(function (t) {
        var item = doc.createElement('div');
        item.className = 'lane-print__item';
        var h = doc.createElement('p');
        h.className = 'lane-print__title';
        h.textContent = t[1] + ' (예시)';
        item.appendChild(h);
        var c = doc.createElement('div');
        c.className = 'chart';
        item.appendChild(c);
        var d = $('.lane-desc[data-type="' + t[0] + '"]');
        if (d) {
          var p = doc.createElement('p');
          p.className = 'lane-print__desc';
          p.textContent = d.textContent;
          item.appendChild(p);
        }
        holder.appendChild(item);
        renderLanes(c, W, false, t[0], true);
      });
    }
    function before() {
      opened = $$('details:not([open])');
      opened.forEach(function (d) { d.open = true; });
      drawAllStatic();
      buildLanePrint();
      if (heroCtl) heroCtl.printOn();
    }
    function after() {
      opened.forEach(function (d) { d.open = false; });
      opened = [];
      if (heroCtl) heroCtl.printOff();
    }
    window.addEventListener('beforeprint', before);
    window.addEventListener('afterprint', after);
  }

  /* ---------- 시작 ---------- */
  function start() {
    var steps = [initNav, initTimeline, initBars, initReveal, initCountUp, initHeroMap, initCharts, initSteps, initLaneTabs, initSortTables, initPrint];
    steps.forEach(function (fn) {
      try { fn(); } catch (err) {
        if (window.console && console.error) console.error('[site] ' + (fn.name || 'init') + ' 실패:', err);
      }
    });
  }
  if (doc.readyState === 'loading') doc.addEventListener('DOMContentLoaded', start);
  else start();
})();
