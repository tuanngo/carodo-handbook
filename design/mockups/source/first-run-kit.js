// Shared drawing kit for the first-run mockups (first-run-day0.html, first-run-day1.html).
// Hand-drawn HTML, not generated assets: colours are CarodoColor / CarodoSurface
// (carodo-ios docs/design-system.md); icons are simple stand-ins for the SF Symbols named in comments.

const css = `
:root { --charcoal:#242321; --copper:#BD8053; --ivory:#F3EEE5; --stone:#77736D; }
* { box-sizing:border-box; }
body { margin:0; font:15px/1.35 -apple-system,"SF Pro Text",system-ui,sans-serif; background:#fff; color:var(--charcoal); }
.sheet { padding:40px 44px 56px; width:max-content; }
h1 { font-size:30px; margin:0 0 4px; letter-spacing:-.3px; }
.lede { color:var(--stone); margin:0 0 30px; max-width:1200px; }
section { margin-bottom:46px; }
section > h2 { font-size:20px; margin:0 0 2px; }
section > p.sub { color:var(--stone); margin:0 0 18px; max-width:1300px; }
.row { display:flex; gap:28px; align-items:flex-start; }
.cap { width:390px; margin-top:10px; font-size:13px; color:var(--stone); }
.cap b { color:var(--charcoal); }
.notes { width:380px; font-size:13.5px; color:#4a4844; padding-top:6px; }
.notes h3 { font-size:14px; margin:0 0 6px; color:var(--charcoal); }
.notes ul { margin:0 0 14px; padding-left:18px; } .notes li { margin-bottom:5px; }
.notes code { font-size:12px; background:#f2eee7; padding:1px 4px; border-radius:4px; }

/* surfaces */
.light { --bg:#F3EEE5; --el:#FAF7F1; --card:#FFFCF7; --stroke:#DED6C9; --t1:#242321; --t2:#77736D; --acc:#965E36; --shadow:0 6px 22px rgba(60,45,30,.13);
  --map:#ECE6DA; --road:#FFFFFF; --road2:#F8F4EC; --roadEdge:#DCD3C4; --water:#C9DAE3; --park:#DCE4CC; --block:#E6DFD2; }
.dark { --bg:#242321; --el:#2E2C29; --card:#373430; --stroke:#4E4A44; --t1:#F3EEE5; --t2:#A49E95; --acc:#D09264; --shadow:0 6px 22px rgba(0,0,0,.45);
  --map:#2A2926; --road:#3D3B37; --road2:#35332F; --roadEdge:#2A2926; --water:#1F2629; --park:#2A2E27; --block:#302E2A; }

.phone { width:390px; height:844px; border-radius:52px; position:relative; overflow:hidden; background:var(--bg); color:var(--t1);
  box-shadow:0 0 0 10px #1b1a19, 0 0 0 11px #3a3836, 0 18px 40px rgba(0,0,0,.25); flex:none; }
.phone.crop { height:300px; border-radius:0 0 52px 52px; }
.phone.crop .status { display:none; }
.status { position:absolute; top:0; left:0; right:0; height:50px; display:flex; justify-content:space-between; align-items:center; padding:6px 34px 0 44px;
  font-weight:600; font-size:16px; z-index:20; color:var(--t1); }
.status .isl { position:absolute; left:50%; top:11px; width:122px; height:36px; margin-left:-61px; background:#000; border-radius:20px; }
.home { position:absolute; bottom:8px; left:50%; width:136px; height:5px; margin-left:-68px; border-radius:3px; background:var(--t1); opacity:.85; z-index:30; }

.ic { width:1em; height:1em; display:inline-block; vertical-align:-.13em; fill:none; stroke:currentColor; stroke-width:2; stroke-linecap:round; stroke-linejoin:round; }
.ic.fill { fill:currentColor; stroke:none; }
.acc { color:var(--acc); } .t2 { color:var(--t2); }

/* onboarding step */
.ob { position:absolute; inset:0; display:flex; flex-direction:column; }
.ob .top { height:96px; display:flex; align-items:flex-end; justify-content:space-between; padding:0 22px 10px; }
.dots { display:flex; gap:7px; } .dots i { width:7px; height:7px; border-radius:4px; background:var(--t2); opacity:.35; } .dots i.on { opacity:1; background:var(--t1); width:18px; }
.wheelwrap { height:150px; display:flex; flex-direction:column; align-items:center; justify-content:center; }
.wheelwrap .shadow { width:88px; height:9px; border-radius:50%; background:rgba(0,0,0,.18); filter:blur(4px); margin-top:4px; }
.dark .wheelwrap .shadow { background:rgba(0,0,0,.6); }
.ob h1 { font-size:28px; text-align:center; margin:6px 0 6px; }
.ob .lead { text-align:center; color:var(--t2); font-size:17px; margin:0 30px 20px; line-height:1.3; }
.cardg { background:var(--el); border:.5px solid color-mix(in srgb,var(--stroke) 60%,transparent); border-radius:20px; margin:0 24px; padding:2px 16px; }
.rowi { display:flex; align-items:center; gap:14px; padding:13px 0; min-height:52px; }
.rowi + .rowi { border-top:.5px solid color-mix(in srgb,var(--stroke) 70%,transparent); }
.rowi .ico { width:24px; text-align:center; color:var(--acc); font-size:18px; flex:none; }
.rowi .lbl { font-weight:600; font-size:17px; }
.rowi .det { color:var(--t2); font-size:15px; }
.rowi .grow { flex:1; min-width:0; }
.seg { display:inline-flex; background:color-mix(in srgb,var(--t2) 16%,transparent); border-radius:9px; padding:2px; flex:none; }
.seg span { padding:6px 12px; font-size:14px; font-weight:500; border-radius:7px; white-space:nowrap; display:flex; align-items:center; gap:5px; }
.seg span.on { background:var(--card); box-shadow:0 1px 3px rgba(0,0,0,.14); font-weight:600; }
.dark .seg span.on { background:#5a5651; }
.seg.wide { display:flex; } .seg.wide span { flex:1; justify-content:center; }
.btnp { margin:0 24px; height:54px; border-radius:27px; background:var(--copper); color:var(--charcoal); font-weight:600; font-size:17px; display:flex; align-items:center; justify-content:center; gap:8px; }
.btns { text-align:center; color:var(--acc); font-weight:600; font-size:17px; padding:15px 0 22px; }
.spacer { flex:1; }

/* vehicle card: the one shared object */
.vc { display:flex; align-items:center; gap:14px; }
.badge { width:52px; height:52px; border-radius:26px; background:color-mix(in srgb,var(--acc) 14%,var(--card)); color:var(--acc); display:grid; place-items:center; font-size:25px; flex:none;
  border:.5px solid color-mix(in srgb,var(--acc) 30%,transparent); }
.badge.sm { width:44px; height:44px; font-size:21px; }
.badge.none { background:transparent; border:1.5px dashed color-mix(in srgb,var(--t2) 60%,transparent); color:var(--t2); }
.vc .nm { font-size:17px; font-weight:600; } .vc .nm.ph { color:color-mix(in srgb,var(--t2) 75%,transparent); font-weight:600; }
.vc .sb { font-size:15px; color:var(--t2); }
.vc .fg { font-size:12.5px; font-weight:600; color:var(--acc); margin-top:2px; }
.caret { display:inline-block; width:2px; height:20px; background:var(--acc); vertical-align:-4px; margin-right:1px; }

/* map + chrome */
.map { position:absolute; inset:0; background:var(--map); }
.map svg { width:100%; height:100%; display:block; }
.float { background:color-mix(in srgb,var(--el) 88%,transparent); backdrop-filter:blur(12px); border:.5px solid color-mix(in srgb,var(--stroke) 70%,transparent); box-shadow:var(--shadow); }
.chip { position:absolute; left:16px; top:62px; height:38px; border-radius:19px; padding:0 14px; display:flex; align-items:center; gap:7px; font-size:15px; font-weight:600; z-index:5; }
.ctrls { position:absolute; right:16px; top:62px; width:46px; border-radius:23px; z-index:5; display:flex; flex-direction:column; }
.ctrls span { height:46px; display:grid; place-items:center; color:var(--t1); font-size:19px; }
.ctrls span + span { border-top:.5px solid color-mix(in srgb,var(--stroke) 70%,transparent); }
.me { position:absolute; width:20px; height:20px; border-radius:10px; background:var(--copper); border:3px solid var(--ivory); box-shadow:0 0 0 30px color-mix(in srgb,var(--copper) 14%,transparent),0 2px 6px rgba(0,0,0,.3); z-index:3; }
.bar { position:absolute; left:16px; right:16px; bottom:30px; height:66px; display:flex; align-items:center; gap:10px; z-index:10; }
.bar .tabs { flex:1; height:62px; border-radius:31px; display:flex; align-items:center; justify-content:space-around; padding:0 10px; }
.bar .tab { display:flex; flex-direction:column; align-items:center; gap:2px; font-size:10.5px; font-weight:600; color:var(--t2); width:70px; }
.bar .tab .ic { font-size:22px; } .bar .tab.on { color:var(--acc); }
.startbtn { width:62px; height:62px; border-radius:31px; background:var(--copper); color:var(--charcoal); display:grid; place-items:center; font-size:28px; box-shadow:0 6px 16px rgba(120,70,30,.35); flex:none; position:relative; }
.legend { position:absolute; left:16px; bottom:110px; }

/* status line (the one quiet line) */
.sline { position:absolute; left:16px; right:16px; bottom:108px; border-radius:18px; padding:11px 14px; display:flex; align-items:center; gap:10px; z-index:9; font-size:15px; }
.sline .si { font-size:17px; flex:none; }
.sline .st { flex:1; line-height:1.25; }
.sline .sa { color:var(--acc); font-weight:600; flex:none; }
.sline .dot { width:8px; height:8px; border-radius:4px; background:#4aa66a; flex:none; }

/* panels */
.panel { position:absolute; left:12px; right:12px; bottom:108px; border-radius:24px; padding:16px; z-index:12; }
.panel .hd { display:flex; align-items:center; justify-content:space-between; margin-bottom:14px; }
.panel .hd b { font-size:17px; display:flex; gap:8px; align-items:center; }
.xbtn { width:32px; height:32px; border-radius:16px; background:var(--card); color:var(--t2); display:grid; place-items:center; font-size:13px; }
.box { background:var(--card); border-radius:14px; padding:12px 14px; }
.box + .box, .box + .seg, .seg + .btnp, .box + .btnp { margin-top:10px; }
.panel .btnp { margin:12px 0 0; }
.kv { display:flex; align-items:center; gap:10px; font-size:15px; }
.kv .k { color:var(--t2); flex:1; } .kv .v { font-weight:600; }
.kv + .kv { margin-top:10px; padding-top:10px; border-top:.5px solid color-mix(in srgb,var(--stroke) 70%,transparent); }
.miss { color:var(--acc); }
.foot { font-size:12.5px; color:var(--t2); text-align:center; margin-top:10px; line-height:1.3; }
.menu { position:absolute; z-index:15; border-radius:14px; width:262px; background:color-mix(in srgb,var(--el) 94%,transparent); backdrop-filter:blur(20px); box-shadow:0 12px 40px rgba(0,0,0,.25); overflow:hidden; font-size:16px; }
.menu div { padding:11px 14px; display:flex; align-items:center; gap:10px; } .menu div + div { border-top:.5px solid color-mix(in srgb,var(--stroke) 70%,transparent); }
.menu .ck { width:16px; color:var(--acc); font-size:14px; } .menu .mi { margin-left:auto; color:var(--t2); font-size:17px; }
.menu .sep { border-top:6px solid color-mix(in srgb,var(--stroke) 35%,transparent) !important; }
.compact { position:absolute; left:12px; right:12px; bottom:108px; border-radius:22px; padding:12px 14px; z-index:12; }
.recdot { width:9px; height:9px; border-radius:5px; background:#E0533D; display:inline-block; }
.undo { border:1.5px solid var(--acc); color:var(--acc); font-weight:600; border-radius:16px; padding:5px 12px; font-size:15px; display:flex; align-items:center; gap:6px; }
.vpill { white-space:nowrap; display:flex; align-items:center; gap:6px; background:var(--card); padding:5px 10px 5px 7px; border-radius:15px; font-weight:600; font-size:15px; }
.metrics { display:flex; justify-content:space-between; margin-top:10px; }
.metrics div { font-variant-numeric:tabular-nums; } .metrics b { font-size:22px; display:block; } .metrics small { color:var(--t2); font-size:12px; }

/* journeys */
.nav { position:absolute; top:50px; left:0; right:0; height:52px; display:flex; align-items:center; justify-content:space-between; padding:0 16px; z-index:5; }
.navbtn { width:40px; height:40px; border-radius:20px; display:grid; place-items:center; font-size:18px; }
.segn { display:flex; background:color-mix(in srgb,var(--t2) 16%,transparent); border-radius:20px; padding:3px; }
.segn span { padding:7px 22px; border-radius:17px; font-size:14px; font-weight:600; } .segn span.on { background:var(--card); box-shadow:0 1px 3px rgba(0,0,0,.12); }
.content { position:absolute; top:108px; left:0; right:0; bottom:0; padding:0 16px; }
.fmenu { display:inline-flex; float:right; align-items:center; gap:6px; padding:7px 13px; border-radius:16px; background:var(--el); border:.5px solid var(--stroke); font-size:14px; font-weight:600; }
.sum { clear:both; display:flex; background:var(--el); border-radius:18px; padding:14px 6px; margin:12px 0 18px; border:.5px solid color-mix(in srgb,var(--stroke) 60%,transparent); }
.sum div { flex:1; text-align:center; } .sum b { display:block; font-size:22px; font-variant-numeric:tabular-nums; } .sum small { color:var(--t2); font-size:12px; }
.dayh { font-size:14px; font-weight:600; color:var(--t2); margin:0 2px 8px; }
.jrow { display:flex; gap:12px; align-items:center; background:var(--el); border-radius:18px; padding:10px; border:.5px solid color-mix(in srgb,var(--stroke) 60%,transparent); }
.thumb { width:64px; height:64px; border-radius:12px; background:var(--map); overflow:hidden; flex:none; }
.jrow .tt { font-weight:600; font-size:16px; } .jrow .mm { color:var(--t2); font-size:13.5px; margin-top:3px; font-variant-numeric:tabular-nums; }
.newtag { font-size:11px; font-weight:700; color:var(--acc); letter-spacing:.4px; text-transform:uppercase; }

/* detail */
.dmap { position:absolute; top:0; left:0; right:0; height:470px; }
.dsheet { position:absolute; top:440px; left:0; right:0; bottom:0; background:var(--bg); border-radius:24px 24px 0 0; padding:20px 18px; }
.dsheet h2 { font-size:24px; margin:0 0 4px; }
.dsheet .when { color:var(--t2); font-size:14px; margin-bottom:12px; }
.narr { font-size:16px; line-height:1.4; margin-bottom:16px; }
.skel { height:12px; border-radius:6px; background:color-mix(in srgb,var(--t2) 22%,transparent); margin:7px 0; }
.tiles { display:flex; gap:8px; margin-bottom:14px; }
.tiles div { flex:1; background:var(--el); border-radius:14px; padding:10px 12px; border:.5px solid color-mix(in srgb,var(--stroke) 60%,transparent); }
.tiles b { display:block; font-size:19px; font-variant-numeric:tabular-nums; } .tiles small { font-size:11.5px; color:var(--t2); }
.vsec { background:var(--el); border-radius:18px; padding:12px 14px; border:.5px solid color-mix(in srgb,var(--stroke) 60%,transparent); }
.mapbtn { position:absolute; top:60px; width:40px; height:40px; border-radius:20px; display:grid; place-items:center; font-size:17px; z-index:4; }

/* accessibility sizes */
.ax { font-size:150%; }
.ax .ob h1 { font-size:40px; } .ax .ob .lead { font-size:25px; }
.ax .rowi .lbl, .ax .vc .nm { font-size:25px; } .ax .rowi .det, .ax .vc .sb { font-size:22px; }
.ax .seg span { font-size:19px; padding:8px 14px; }
.ax .btnp { font-size:25px; height:66px; border-radius:33px; } .ax .btns { font-size:25px; }
`;

const I = {
  // SF Symbol stand-ins
  car: '<svg class="ic" viewBox="0 0 24 24"><path d="M3 13l2-5.2A2 2 0 0 1 6.9 6.5h10.2a2 2 0 0 1 1.9 1.3L21 13v4.5a1 1 0 0 1-1 1h-1.5a1 1 0 0 1-1-1V16.5h-11v1a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1z" fill="currentColor" stroke="none"/><circle cx="7.3" cy="13.2" r="1.3" fill="var(--bg)" stroke="none"/><circle cx="16.7" cy="13.2" r="1.3" fill="var(--bg)" stroke="none"/><path d="M5.8 11l1.3-3h9.8l1.3 3z" fill="var(--bg)" stroke="none" opacity=".5"/></svg>',
  moto: '<svg class="ic" viewBox="0 0 24 24"><circle cx="5.5" cy="16" r="3.2"/><circle cx="18.5" cy="16" r="3.2"/><path d="M5.5 16l4-5h4.5l2.5 5M13 7.5h2.5l3 8.5M9 11L8 8.5H5.5"/></svg>',
  ruler: '<svg class="ic fill" viewBox="0 0 24 24"><path d="M2.5 8.5h19v7h-19z" opacity=".95"/><path d="M6 8.5v3.2M9.5 8.5v2.2M13 8.5v3.2M16.5 8.5v2.2M20 8.5v3.2" stroke="var(--el)" stroke-width="1.4" fill="none"/></svg>',
  lock: '<svg class="ic fill" viewBox="0 0 24 24"><rect x="5" y="10.5" width="14" height="10" rx="2.5"/><path d="M8 10.5V8a4 4 0 0 1 8 0v2.5" fill="none" stroke="currentColor" stroke-width="2.2"/></svg>',
  loc: '<svg class="ic fill" viewBox="0 0 24 24"><path d="M20.5 3.5L3.5 10.6l7.2 2.1 2.1 7.3z"/></svg>',
  locoff: '<svg class="ic" viewBox="0 0 24 24"><path d="M20.5 3.5L3.5 10.6l7.2 2.1 2.1 7.3zM3 3l18 18"/></svg>',
  rec: '<svg class="ic" viewBox="0 0 24 24" style="stroke-width:2.2"><circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="4.6" fill="currentColor" stroke="none"/></svg>',
  stop: '<svg class="ic fill" viewBox="0 0 24 24"><rect x="6" y="6" width="12" height="12" rx="2.5"/></svg>',
  map: '<svg class="ic fill" viewBox="0 0 24 24"><path d="M3 6l6-2.5 6 2.5 6-2.5v14.5l-6 2.5-6-2.5-6 2.5z"/><path d="M9 3.5v14.5M15 6v14.5" stroke="var(--el)" stroke-width="1.3"/></svg>',
  list: '<svg class="ic" viewBox="0 0 24 24"><path d="M8.5 6h12M8.5 12h12M8.5 18h12"/><circle cx="4" cy="6" r="1.2" fill="currentColor"/><circle cx="4" cy="12" r="1.2" fill="currentColor"/><circle cx="4" cy="18" r="1.2" fill="currentColor"/></svg>',
  people: '<svg class="ic fill" viewBox="0 0 24 24"><circle cx="9" cy="8" r="3.6"/><path d="M2 19.5c0-3.6 3.1-6 7-6s7 2.4 7 6z"/><circle cx="17" cy="8.6" r="2.8" opacity=".75"/><path d="M15.8 13.6c3.4-.4 6.2 1.8 6.2 5.4h-4.4" opacity=".75"/></svg>',
  x: '<svg class="ic" viewBox="0 0 24 24" style="stroke-width:2.6"><path d="M6 6l12 12M18 6L6 18"/></svg>',
  chev: '<svg class="ic" viewBox="0 0 24 24" style="stroke-width:2.4"><path d="M9 5l7 7-7 7"/></svg>',
  updown: '<svg class="ic" viewBox="0 0 24 24" style="stroke-width:2.2"><path d="M8 9l4-4 4 4M8 15l4 4 4-4"/></svg>',
  down: '<svg class="ic" viewBox="0 0 24 24" style="stroke-width:2.4"><path d="M6 9l6 6 6-6"/></svg>',
  back: '<svg class="ic" viewBox="0 0 24 24" style="stroke-width:2.4"><path d="M15 5l-7 7 7 7"/></svg>',
  check: '<svg class="ic" viewBox="0 0 24 24" style="stroke-width:2.6"><path d="M5 12.5l4.5 4.5L19 7.5"/></svg>',
  plus: '<svg class="ic" viewBox="0 0 24 24" style="stroke-width:2.4"><path d="M12 5v14M5 12h14"/></svg>',
  auto: '<svg class="ic fill" viewBox="0 0 24 24"><path d="M12 2.5l1.9 5.6 5.6 1.9-5.6 1.9L12 17.5l-1.9-5.6L4.5 10l5.6-1.9z"/><path d="M18.5 15l.8 2.2 2.2.8-2.2.8-.8 2.2-.8-2.2-2.2-.8 2.2-.8z"/></svg>',
  hand: '<svg class="ic" viewBox="0 0 24 24"><path d="M9 11V5a1.5 1.5 0 0 1 3 0v5M12 9.5V4a1.5 1.5 0 0 1 3 0v6M15 9a1.5 1.5 0 0 1 3 0v5.5a6.5 6.5 0 0 1-6.5 6.5h-.5a6 6 0 0 1-4.8-2.4L3.5 15a1.5 1.5 0 0 1 2.3-1.9L9 15.5V11"/></svg>',
  flag: '<svg class="ic" viewBox="0 0 24 24"><path d="M5 21V4M5 4h13l-2.5 4.5L18 13H5"/></svg>',
  motion: '<svg class="ic" viewBox="0 0 24 24"><circle cx="13.5" cy="4" r="2" fill="currentColor"/><path d="M7 21l3-6 3 2v4M10 15l1-5 4 3 3 1M11 10l-4 1-2 3"/></svg>',
  target: '<svg class="ic" viewBox="0 0 24 24"><circle cx="12" cy="12" r="7"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3"/><circle cx="12" cy="12" r="1.5" fill="currentColor"/></svg>',
  undo: '<svg class="ic" viewBox="0 0 24 24" style="stroke-width:2.3"><path d="M9 14L4 9l5-5"/><path d="M4 9h10.5a5.5 5.5 0 0 1 0 11H11"/></svg>',
  layers: '<svg class="ic" viewBox="0 0 24 24"><path d="M12 3l9 5-9 5-9-5zM3 13l9 5 9-5"/></svg>',
  cube: '<svg class="ic" viewBox="0 0 24 24"><path d="M12 2.8l8 4.6v9.2l-8 4.6-8-4.6V7.4zM4 7.4l8 4.6 8-4.6M12 12v9.2"/></svg>',
  share: '<svg class="ic" viewBox="0 0 24 24"><path d="M12 15V3M7.5 7.5L12 3l4.5 4.5M5 11v8.5a1.5 1.5 0 0 0 1.5 1.5h11a1.5 1.5 0 0 0 1.5-1.5V11"/></svg>',
  dots: '<svg class="ic fill" viewBox="0 0 24 24"><circle cx="5" cy="12" r="2"/><circle cx="12" cy="12" r="2"/><circle cx="19" cy="12" r="2"/></svg>',
  play: '<svg class="ic fill" viewBox="0 0 24 24"><path d="M7 4.5v15l12.5-7.5z"/></svg>',
  warn: '<svg class="ic" viewBox="0 0 24 24"><path d="M12 3.5l9.5 16.5h-19z"/><path d="M12 10v4.5"/><circle cx="12" cy="17.3" r=".6" fill="currentColor"/></svg>',
  stamp: '<svg class="ic" viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5.5" stroke-dasharray="2 2"/><circle cx="12" cy="12" r="1.6" fill="currentColor"/></svg>',
  gauge: '<svg class="ic" viewBox="0 0 24 24"><path d="M4 17a8 8 0 1 1 16 0"/><path d="M12 17l4-5"/></svg>',
};

const wheel = (size = 110) => `
<svg width="${size}" height="${size}" viewBox="0 0 100 100">
  <circle cx="50" cy="50" r="43" fill="none" stroke="var(--t1)" stroke-width="7"/>
  <circle cx="50" cy="50" r="37.5" fill="none" stroke="var(--t2)" stroke-width="1.4" opacity=".55"/>
  ${[0, 72, 144, 216, 288].map(a => `<path d="M46.5 49 L44.6 14 Q50 12.2 55.4 14 L53.5 49 Z" fill="var(--t1)" transform="rotate(${a + 18} 50 50)"/>`).join('')}
  <circle cx="50" cy="50" r="13.6" fill="var(--t1)"/><circle cx="50" cy="50" r="7.6" fill="var(--copper)"/>
</svg>`;

const status = () => `<div class="status"><span>9:41</span><span class="isl"></span><span style="letter-spacing:2px">▮▮▮ ▰</span></div><div class="home"></div>`;

const phone = (theme, inner, extra = '') => `<div class="phone ${theme} ${extra}">${status()}${inner}</div>`;

// A synthetic street grid: no real place (P5).
const mapSvg = (opts = {}) => `
<svg viewBox="0 0 390 844" preserveAspectRatio="xMidYMid slice">
  <rect width="390" height="844" fill="var(--map)"/>
  <path d="M-20 620 C 90 590 140 700 250 690 S 380 610 420 640 L420 900 L-20 900Z" fill="var(--water)"/>
  <rect x="210" y="170" width="120" height="90" rx="10" fill="var(--park)"/>
  <rect x="40" y="300" width="90" height="70" rx="8" fill="var(--park)"/>
  ${Array.from({ length: 9 }, (_, i) => `<rect x="${20 + (i % 3) * 120}" y="${120 + Math.floor(i / 3) * 140}" width="80" height="60" rx="6" fill="var(--block)"/>`).join('')}
  <g fill="none" stroke-linecap="round">
    <path d="M-10 250 C 120 230 260 280 400 240" stroke="var(--roadEdge)" stroke-width="15"/>
    <path d="M-10 250 C 120 230 260 280 400 240" stroke="var(--road)" stroke-width="12"/>
    <path d="M170 -10 C 160 200 200 420 150 860" stroke="var(--roadEdge)" stroke-width="15"/>
    <path d="M170 -10 C 160 200 200 420 150 860" stroke="var(--road)" stroke-width="12"/>
    ${[80, 400, 520].map(y => `<path d="M-10 ${y} L400 ${y + 20}" stroke="var(--road2)" stroke-width="6"/>`).join('')}
    ${[60, 290, 350].map(x => `<path d="M${x} -10 L${x - 30} 860" stroke="var(--road2)" stroke-width="6"/>`).join('')}
  </g>
  ${opts.route ? `<path d="${opts.route}" fill="none" stroke="${opts.routeColor || 'var(--acc)'}" stroke-width="${opts.routeWidth || 6}" stroke-linecap="round" stroke-linejoin="round"/>` : ''}
</svg>`;

const routeD = 'M115 560 C 140 520 175 470 178 410 S 175 300 195 255 S 260 240 300 220 S 330 150 300 120';
const speedRoute = () => `
  <path d="M115 560 C 140 520 175 470 178 410" stroke="#5B9EDB" stroke-width="7" fill="none" stroke-linecap="round"/>
  <path d="M178 410 C 178 360 175 300 195 255" stroke="#54BD85" stroke-width="7" fill="none" stroke-linecap="round"/>
  <path d="M195 255 C 215 245 260 240 300 220" stroke="#F2B840" stroke-width="7" fill="none" stroke-linecap="round"/>
  <path d="M300 220 C 330 200 330 150 300 120" stroke="#54BD85" stroke-width="7" fill="none" stroke-linecap="round"/>
  <circle cx="115" cy="560" r="7" fill="var(--ivory)" stroke="var(--charcoal)" stroke-width="3"/>
  <circle cx="300" cy="120" r="7" fill="var(--charcoal)" stroke="var(--ivory)" stroke-width="3"/>`;

const bar = (tab = 0, btn = 'rec') => `
<div class="bar">
  <div class="tabs float">
    <div class="tab ${tab === 0 ? 'on' : ''}">${I.map}Map</div>
    <div class="tab ${tab === 1 ? 'on' : ''}">${I.list}Journeys</div>
    <div class="tab ${tab === 2 ? 'on' : ''}">${I.people}Feed</div>
  </div>
  <div class="startbtn">${btn === 'rec' ? I.rec : I.stop}</div>
</div>`;

const mapChrome = (chip) => `
  <div class="chip float">${chip}</div>
  <div class="ctrls float"><span>${I.map}</span><span class="acc">${I.loc}</span><span style="font-size:13px;font-weight:700">3D</span></div>`;

const sline = (icon, text, action, tone = '') => `
<div class="sline float">${icon === 'dot' ? '<span class="dot"></span>' : `<span class="si ${tone || 'acc'}">${icon}</span>`}
  <span class="st">${text}</span>${action ? `<span class="sa">${action}</span>` : ''}</div>`;

// The shared vehicle card. kind: car | moto | none; trailing: html.
const vcard = ({ kind = 'car', name = 'My car', placeholder = false, sub = 'Car', figures = '', trailing = '', small = false, caret = false }) => `
<div class="vc">
  <div class="badge ${small ? 'sm' : ''} ${kind === 'none' ? 'none' : ''}">${kind === 'moto' ? I.moto : kind === 'none' ? I.car : I.car}</div>
  <div style="flex:1;min-width:0">
    <div class="nm ${placeholder ? 'ph' : ''}">${caret ? '<span class="caret"></span>' : ''}${name}</div>
    ${sub ? `<div class="sb">${sub}</div>` : ''}
    ${figures ? `<div class="fg">${figures}</div>` : ''}
  </div>
  ${trailing}
</div>`;

function mount(html) {
  const s = document.createElement('style'); s.textContent = css; document.head.appendChild(s);
  document.body.innerHTML = html;
}

// Side-view vehicle drawings by body style and colour (stand-ins for the in-app renderer).
const paint = { white:'#EDEBE6', black:'#2A2A2C', silver:'#BFC3C7', grey:'#6E7378', red:'#B3322B', blue:'#2F5D9A',
  green:'#3E6B4C', yellow:'#E0B43A', orange:'#D7773A', brown:'#7A5640' };
const bodies = {
  sedan: { b:'M14 80 L18 64 Q22 56 36 54 L70 51 L94 33 Q100 29 110 29 L156 29 Q166 29 174 35 L196 51 L218 56 Q228 59 228 68 L228 80 Z',
           w:'M78 51 L98 36 Q102 33 108 33 L128 33 L128 51 Z M134 51 L134 33 L154 33 Q162 33 168 38 L186 51 Z', fx:62, rx:184 },
  hatch: { b:'M16 80 L18 64 Q22 56 34 54 L70 51 L96 31 Q102 27 112 27 L170 27 Q182 27 188 36 L204 56 Q210 60 210 68 L210 80 Z',
           w:'M78 51 L100 34 Q104 31 110 31 L132 31 L132 51 Z M138 51 L138 31 L168 31 Q176 31 180 38 L190 51 Z', fx:60, rx:172 },
  suv:   { b:'M14 82 L16 56 Q18 46 30 44 L60 42 L78 20 Q82 15 92 15 L180 15 Q190 15 196 23 L210 42 L222 46 Q230 49 230 60 L230 82 Z',
           w:'M68 42 L84 22 Q87 19 93 19 L128 19 L128 42 Z M134 42 L134 19 L178 19 Q185 19 189 25 L200 42 Z', fx:62, rx:186 },
};
const vehicleArt = ({ body = 'sedan', color = 'silver', w = 240 }) => {
  if (body === 'scooter') return `<svg width="${w}" viewBox="0 0 240 110">
    <ellipse cx="120" cy="100" rx="96" ry="5" fill="rgba(0,0,0,.14)"/>
    <path d="M58 82 Q60 58 84 56 L120 56 L132 40 L150 40 L160 64 Q170 60 184 68 L190 82 Z" fill="${paint[color]}"/>
    <path d="M150 40 L164 18 L178 16" stroke="#3a3836" stroke-width="5" fill="none" stroke-linecap="round"/>
    <path d="M86 56 Q96 44 118 46 L120 56 Z" fill="#2b2a28"/>
    ${[66, 178].map(x => `<circle cx="${x}" cy="84" r="15" fill="#1f1f1f"/><circle cx="${x}" cy="84" r="7" fill="#c9c9c9"/>`).join('')}</svg>`;
  const s = bodies[body];
  return `<svg width="${w}" viewBox="0 0 240 110">
    <ellipse cx="121" cy="100" rx="108" ry="5" fill="rgba(0,0,0,.14)"/>
    <path d="${s.b}" fill="${paint[color]}"/><path d="${s.w}" fill="#2b3036" opacity=".85"/>
    <path d="M14 72 L228 72" stroke="rgba(0,0,0,.12)" stroke-width="1.5"/>
    ${[s.fx, s.rx].map(x => `<circle cx="${x}" cy="82" r="18" fill="#1f1f1f"/><circle cx="${x}" cy="82" r="9.5" fill="#c9c9c9"/><circle cx="${x}" cy="82" r="3" fill="#777"/>`).join('')}</svg>`;
};
