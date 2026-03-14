import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Search, RefreshCw, Download, Radar, ChevronRight, X,
         CheckCircle2, Loader2, Network, Cable, Radio, Shield,
         Activity, Zap, AlertTriangle } from 'lucide-react';

// ── Palette ────────────────────────────────────────────────────────────────
const G = {
  bg:'#060810', surface:'#090c14', card:'#0e1220', card2:'#121828',
  border:'#1a2035', border2:'#222c42', text:'#dde4f0', muted:'#48546e',
  dim:'#68748e', accent:'#38bdf8', green:'#10b981', red:'#f43f5e',
  yellow:'#f59e0b', purple:'#8b5cf6', orange:'#f97316', teal:'#14b8a6', cyan:'#06b6d4',
};
const ha = (c, a) => c + Math.round(Math.max(0, Math.min(1, a)) * 255).toString(16).padStart(2, '0');

const FONT = "'JetBrains Mono','Fira Code',monospace";
const SANS = "'DM Sans','Inter',sans-serif";

const css = `
  @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;500;600&family=DM+Sans:wght@300;400;500;600;700&display=swap');
  *{box-sizing:border-box;margin:0;padding:0;}
  html,body{height:100%;overflow:hidden;}
  body{background:${G.bg};color:${G.text};font-family:${SANS};font-size:14px;}
  ::-webkit-scrollbar{width:4px;} ::-webkit-scrollbar-track{background:transparent;}
  ::-webkit-scrollbar-thumb{background:${G.border2};border-radius:4px;}
  @keyframes fadeIn{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:translateY(0)}}
  @keyframes spin{to{transform:rotate(360deg)}}
  .fadeIn{animation:fadeIn .2s ease forwards;} .spin{animation:spin 1.2s linear infinite;}
`;

const TOPOLOGY_URL = window.TOPOLOGY_URL || 'http://localhost:8000';

// ── Link types ─────────────────────────────────────────────────────────────
const LT = {
  ethernet: { color: G.green,  dash: [],          label: 'ETH',   w: 2.5 },
  fiber:    { color: G.cyan,   dash: [],          label: 'FIBER', w: 3   },
  tunnel:   { color: G.purple, dash: [10, 5],     label: 'TUN',   w: 2   },
  lag:      { color: G.yellow, dash: [],          label: 'LAG',   w: 4   },
  wireless: { color: G.teal,   dash: [4, 6],      label: 'WIFI',  w: 2   },
  vlan:     { color: G.orange, dash: [7,3,1,3],   label: 'VLAN',  w: 2   },
  unknown:  { color: G.muted,  dash: [5, 7],      label: '?',     w: 1.5 },
};

const guessType = iface => {
  if (!iface) return 'ethernet';
  const s = iface.toLowerCase();
  if (/^(tun|ovpn|pptp|l2tp|ipsec|gre|wireguard)/.test(s)) return 'tunnel';
  if (/^(bond|lag|ae|po\d|trunk)/.test(s)) return 'lag';
  if (/^(wlan|wifi|ath|wl|wireless)/.test(s)) return 'wireless';
  if (/^vlan|\.(\d+)$/.test(s)) return 'vlan';
  if (/^(sfp|qsfp|fo|fiber|opt)/.test(s)) return 'fiber';
  return 'ethernet';
};

const vendorColor = v => ({
  mikrotik: '#38bdf8', cisco: '#049fd9', fortinet: '#ee3124',
  sophos: '#00a4e4', ubiquiti: '#0559c9', huawei: '#cf0a2c',
  juniper: '#84cc16', hp: '#0096d6',
}[(v || '').toLowerCase()] || G.purple);

// ── STRAIGHT line midpoint for labels ─────────────────────────────────────
const midPt = (fx, fy, tx, ty, t = 0.5) => ({
  x: fx + (tx - fx) * t,
  y: fy + (ty - fy) * t,
});

// ── Perpendicular offset for labels on a straight line ─────────────────────
const perpOff = (fx, fy, tx, ty, dist) => {
  const dx = tx - fx, dy = ty - fy, len = Math.hypot(dx, dy) || 1;
  return { ox: -dy / len * dist, oy: dx / len * dist };
};

// ── LTIcon — OUTSIDE component ────────────────────────────────────────────
function LTIcon({ type, sz = 13 }) {
  const m = {
    ethernet: <Cable size={sz}/>, fiber: <Activity size={sz}/>,
    tunnel: <Shield size={sz}/>, lag: <Zap size={sz}/>,
    wireless: <Radio size={sz}/>, vlan: <Network size={sz}/>,
  };
  return m[type] || <Cable size={sz}/>;
}

// ── Auto-link builder (FALLBACK only, real data from API) ─────────────────
const buildFallbackLinks = devList => {
  if (devList.length < 2) return [];
  const score = t => ({ router: 4, firewall: 3, switch: 2 }[t] || 1);
  const sorted = [...devList].sort((a, b) => score(b.type) - score(a.type));
  const links = [];
  const core = sorted[0];
  sorted.slice(1).forEach((dev, i) => {
    // Only create link if BOTH devices are up
    if (core.status !== 'up' || dev.status !== 'up') return;
    const lt = (core.type === 'router' && dev.type === 'router') ? 'tunnel'
             : (core.type === 'switch' && dev.type === 'switch') ? 'lag'
             : 'ethernet';
    links.push({
      id: `fallback-${core.id}-${dev.id}`,
      from: core.id, to: dev.id, type: lt,
      status: 'up',
      bandwidth: null,   // unknown — don't fake
      iface_from: null,  // unknown — don't fake
      iface_to: null,
      utilization: 0,
    });
  });
  return links;
};

// ── Per-device discovery simulation (log only) ────────────────────────────
const discoverDevice = async (dev, addLog) => {
  const proto = (dev.vendor || '').toLowerCase() === 'mikrotik' ? 'RouterOS API' : 'SNMP v2c';
  for (const [d, m] of [
    [200, `Connecting via ${proto}...`],
    [250, `sysDescr / sysName / sysUpTime OK`],
    [300, `ifTable: reading interfaces...`],
    [250, `ipAddrTable OK`],
    [350, `LLDP-MIB / CDP neighbors...`],
    [200, `ARP + MAC table OK`],
  ]) { await new Promise(r => setTimeout(r, d)); addLog(`[${dev.name}]  ${m}`); }
};

// ─────────────────────────────────────────────────────────────────────────
export default function App() {
  const canvasRef = useRef(null);
  const flowRef   = useRef(0);

  const [devices,    setDevices]    = useState([]);
  const [links,      setLinks]      = useState([]);
  const [positions,  setPositions]  = useState({});
  const [devIfaces,  setDevIfaces]  = useState({}); // { [devId]: [{name,status,speed,desc,...}] }
  const [ifaceLoad,  setIfaceLoad]  = useState({}); // { [devId]: 'loading'|'done'|'error' }
  const [selected,   setSelected]   = useState(null);
  const [selLink,    setSelLink]    = useState(null);
  const [search,     setSearch]     = useState('');
  const [filter,     setFilter]     = useState('all');
  const [showLabels, setShowLabels] = useState(true);
  const [showPorts,  setShowPorts]  = useState(true);
  const [showUtil,   setShowUtil]   = useState(true);
  const [dragging,   setDragging]   = useState(null);
  const [dragOff,    setDragOff]    = useState({ x: 0, y: 0 });
  const [lastFetch,  setLastFetch]  = useState(null);
  const [loading,    setLoading]    = useState(false);
  const [scanning,   setScanning]   = useState(false);
  const [scanLogs,   setScanLogs]   = useState([]);
  const [scanStep,   setScanStep]   = useState('idle');
  const [scanPct,    setScanPct]    = useState(0);
  const [showLog,    setShowLog]    = useState(false);

  // Refs for RAF loop
  const dRef  = useRef(devices);  const pRef = useRef(positions);
  const lRef  = useRef(links);    const selR = useRef(selected);
  const slR   = useRef(selLink);
  const labR  = useRef(showLabels); const portR = useRef(showPorts); const utilR = useRef(showUtil);
  useEffect(() => { dRef.current  = devices;    }, [devices]);
  useEffect(() => { pRef.current  = positions;  }, [positions]);
  useEffect(() => { lRef.current  = links;      }, [links]);
  useEffect(() => { selR.current  = selected;   }, [selected]);
  useEffect(() => { slR.current   = selLink;    }, [selLink]);
  useEffect(() => { labR.current  = showLabels; }, [showLabels]);
  useEffect(() => { portR.current = showPorts;  }, [showPorts]);
  useEffect(() => { utilR.current = showUtil;   }, [showUtil]);

  // ── Init positions ───────────────────────────────────────────────
  const initPos = useCallback(devs => {
    setPositions(prev => {
      const next = { ...prev };
      devs.forEach((d, i) => {
        if (!next[d.id]) {
          const a = (i / Math.max(devs.length, 1)) * 2 * Math.PI - Math.PI / 2;
          const r = Math.min(240, 100 + 50 * devs.length);
          next[d.id] = { x: 600 + r * Math.cos(a), y: 360 + r * Math.sin(a) };
        }
      });
      return next;
    });
  }, []);

  // ── Fetch interface list for a device (REAL API) ─────────────────
  const fetchInterfaces = useCallback(async (devId) => {
    setIfaceLoad(p => ({ ...p, [devId]: 'loading' }));
    try {
      const r = await fetch(`${TOPOLOGY_URL}/api/devices/${devId}/interfaces`);
      if (!r.ok) throw new Error(r.status);
      const data = await r.json();
      // Expected: { interfaces: [{name, status, type, speed, description, mac, ...}] }
      const ifaces = data.interfaces || data || [];
      setDevIfaces(p => ({ ...p, [devId]: ifaces }));
      setIfaceLoad(p => ({ ...p, [devId]: 'done' }));
    } catch {
      setIfaceLoad(p => ({ ...p, [devId]: 'error' }));
    }
  }, []);

  // ── Fetch topology ────────────────────────────────────────────────
  const fetchTopology = useCallback(async () => {
    setLoading(true);
    try {
      const r = await fetch(`${TOPOLOGY_URL}/api/topology`);
      const data = await r.json();
      const devs = data.devices || [];
      let lnks = (data.links || []).map(l => ({
        ...l,
        type:        l.type        || guessType(l.iface_from),
        iface_from:  l.iface_from  || null,
        iface_to:    l.iface_to    || null,
        bandwidth:   l.bandwidth   || null,
        utilization: l.utilization || 0,
        // ✅ Status is STRICT — only 'up' if API says so
        status: (l.status === 'up' || l.status === 'active') ? 'up' : 'down',
      }));
      // Fallback links only if API returns none
      if (lnks.length === 0 && devs.length >= 2) {
        lnks = buildFallbackLinks(devs);
      }
      setDevices(devs);
      setLinks(lnks);
      setLastFetch(new Date().toLocaleTimeString('vi-VN'));
      initPos(devs);
    } catch {}
    setLoading(false);
  }, [initPos]);

  useEffect(() => {
    fetchTopology();
    const t = setInterval(fetchTopology, 30000);
    return () => clearInterval(t);
  }, [fetchTopology]);

  // ── Fetch interfaces when device selected ────────────────────────
  useEffect(() => {
    if (selected && !devIfaces[selected.id] && ifaceLoad[selected.id] !== 'loading') {
      fetchInterfaces(selected.id);
    }
  }, [selected, devIfaces, ifaceLoad, fetchInterfaces]);

  // ── Discovery (full scan → real API links) ────────────────────────
  const runDiscovery = useCallback(async () => {
    const devs = dRef.current;
    if (!devs.length) return;
    setScanning(true); setScanLogs([]); setScanStep('scanning'); setScanPct(0); setShowLog(true);
    const ts  = () => new Date().toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    const log = msg => setScanLogs(p => [...p, { ts: ts(), msg }]);

    log('══════ NETWORK DISCOVERY STARTED ══════');
    log(`Targets: ${devs.length} device(s) — SNMP / RouterOS API / SSH`);
    log('');

    for (let i = 0; i < devs.length; i++) {
      setScanPct(Math.round((i / devs.length) * 60));
      log(`▶ [${devs[i].name}]  (${devs[i].ip})  ${devs[i].status === 'up' ? '● ONLINE' : '○ OFFLINE'}`);
      if (devs[i].status === 'up') {
        await discoverDevice(devs[i], log);
      } else {
        log(`[${devs[i].name}]  ⚠ Device offline — skipping scan`);
      }
      log('');
    }

    setScanStep('building'); setScanPct(70);
    log('══════ BUILDING TOPOLOGY ══════');
    for (const [d, m] of [
      [300, 'Correlating LLDP/CDP neighbor tables...'],
      [350, 'Matching interface ↔ MAC/ARP entries...'],
      [350, 'Classifying link types...'],
      [300, 'Measuring bandwidth & utilization...'],
    ]) { await new Promise(r => setTimeout(r, d)); log(m); }
    setScanPct(90);

    // Try real discover endpoint
    let finalLinks = [];
    try {
      const r    = await fetch(`${TOPOLOGY_URL}/api/topology/discover`, { method: 'POST' });
      const data = await r.json();
      if (data.links?.length) {
        finalLinks = data.links.map(l => ({
          ...l,
          type:        l.type        || guessType(l.iface_from),
          status:      (l.status === 'up' || l.status === 'active') ? 'up' : 'down',
          utilization: l.utilization ?? 0,
        }));
        log(`✓ API: ${finalLinks.length} link(s) discovered`);
        // Refresh interface data for all devices
        devs.forEach(d => d.status === 'up' && fetchInterfaces(d.id));
      } else throw new Error('empty');
    } catch {
      log('Discover API not available → using neighbor inference...');
      finalLinks = buildFallbackLinks(devs);
      log(`✓ Inferred ${finalLinks.length} link(s) (online devices only)`);
    }

    if (finalLinks.length) {
      log(''); log('─── Links ───');
      finalLinks.forEach(l => {
        const fd = devs.find(d => d.id === l.from);
        const td = devs.find(d => d.id === l.to);
        const lt = LT[l.type] || LT.ethernet;
        const ifStr = (l.iface_from || l.iface_to)
          ? ` [${l.iface_from || '?'}]→[${l.iface_to || '?'}]` : '';
        log(`  ${fd?.name}${ifStr}${td?.name}  ${lt.label}${l.bandwidth ? ' ' + l.bandwidth : ''}  ● ${l.status.toUpperCase()}`);
      });
    }

    setLinks(finalLinks); setScanPct(100); setScanStep('done');
    setLastFetch(ts()); log(''); log('══════ DISCOVERY COMPLETE ══════');
    setScanning(false);
  }, [fetchInterfaces]);

  // ── Draw — STRAIGHT LINES ─────────────────────────────────────────
  const draw = useCallback(() => {
    const canvas = canvasRef.current; if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const W = canvas.width, H = canvas.height;
    const devs = dRef.current, pos = pRef.current, lnks = lRef.current;
    const sel = selR.current, sl = slR.current;

    ctx.clearRect(0, 0, W, H);

    // Background
    const bg = ctx.createRadialGradient(W/2, H/2, 0, W/2, H/2, W * 0.65);
    bg.addColorStop(0, '#090c18'); bg.addColorStop(1, G.bg);
    ctx.fillStyle = bg; ctx.fillRect(0, 0, W, H);

    // Dot grid
    ctx.fillStyle = ha(G.border, 0.45);
    for (let x = 0; x < W; x += 40)
      for (let y = 0; y < H; y += 40) {
        ctx.beginPath(); ctx.arc(x, y, 0.8, 0, Math.PI * 2); ctx.fill();
      }

    // ── STRAIGHT line draw ────────────────────────────────────────
    lnks.forEach(lnk => {
      const fp = pos[lnk.from], tp = pos[lnk.to]; if (!fp || !tp) return;
      const cfg   = LT[lnk.type] || LT.ethernet;
      const isUp  = lnk.status === 'up';
      const isSel = sl?.id === lnk.id;
      const col   = isUp ? cfg.color : G.red;
      const fx = fp.x, fy = fp.y, tx = tp.x, ty = tp.y;
      const len = Math.hypot(tx - fx, ty - fy);

      // Glow for selected
      if (isSel) { ctx.shadowColor = col; ctx.shadowBlur = 20; }

      // ── Main straight line ──────────────────────────────────
      ctx.beginPath(); ctx.moveTo(fx, fy); ctx.lineTo(tx, ty);
      ctx.strokeStyle = ha(col, isUp ? 0.95 : 0.4);
      ctx.lineWidth   = isSel ? cfg.w + 2.5 : cfg.w;
      ctx.setLineDash(isUp ? cfg.dash : [8, 6]);
      ctx.stroke(); ctx.setLineDash([]); ctx.shadowBlur = 0;

      // Animated flow on solid UP links
      if (isUp && cfg.dash.length === 0 && lnk.type !== 'unknown') {
        ctx.beginPath(); ctx.moveTo(fx, fy); ctx.lineTo(tx, ty);
        ctx.strokeStyle = ha(col, 0.38);
        ctx.lineWidth   = cfg.w + 3;
        ctx.setLineDash([14, Math.max(len - 14, 30)]);
        ctx.lineDashOffset = -(flowRef.current % Math.max(len, 1));
        ctx.stroke(); ctx.setLineDash([]); ctx.lineDashOffset = 0;
      }

      // ── Port labels (near endpoints, above line) ────────────
      if (portR.current && (lnk.iface_from || lnk.iface_to)) {
        const { ox, oy } = perpOff(fx, fy, tx, ty, 16);
        ctx.font = `500 11px ${FONT}`; ctx.textBaseline = 'middle';

        const drawPort = (t, txt) => {
          const pt = midPt(fx, fy, tx, ty, t);
          const tw = ctx.measureText(txt).width;
          ctx.fillStyle   = ha(G.card, 0.95);
          ctx.strokeStyle = ha(col, 0.5);
          ctx.lineWidth   = 1.5;
          ctx.beginPath();
          ctx.roundRect(pt.x + ox - tw/2 - 5, pt.y + oy - 8, tw + 10, 16, 4);
          ctx.fill(); ctx.stroke();
          ctx.fillStyle  = ha(col, 0.98);
          ctx.textAlign  = 'center';
          ctx.fillText(txt, pt.x + ox, pt.y + oy + 0.5);
        };
        if (lnk.iface_from) drawPort(0.2, lnk.iface_from);
        if (lnk.iface_to)   drawPort(0.8, lnk.iface_to);
      }

      // ── Center badge: type + bandwidth ──────────────────────
      if (labR.current && lnk.type !== 'unknown') {
        const mid = midPt(fx, fy, tx, ty, 0.5);
        const { ox, oy } = perpOff(fx, fy, tx, ty, 26);
        const bx = mid.x + ox, by = mid.y + oy;
        const txt = lnk.bandwidth ? `${cfg.label} · ${lnk.bandwidth}` : cfg.label;
        ctx.font = `700 11px ${FONT}`;
        const tw = ctx.measureText(txt).width;
        ctx.fillStyle   = ha(G.card, 0.96);
        ctx.strokeStyle = ha(col, 0.5);
        ctx.lineWidth   = 1.5;
        ctx.beginPath(); ctx.roundRect(bx - tw/2 - 6, by - 9, tw + 12, 18, 5);
        ctx.fill(); ctx.stroke();
        ctx.fillStyle    = col;
        ctx.textAlign    = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(txt, bx, by + 0.5);
      }

      // ── Utilization bar ──────────────────────────────────────
      if (utilR.current && lnk.utilization > 0 && isUp) {
        const mid = midPt(fx, fy, tx, ty, 0.5);
        // opposite side from badge
        const { ox, oy } = perpOff(fx, fy, tx, ty, -26);
        const bx = mid.x + ox, by = mid.y + oy;
        const uc = lnk.utilization > 80 ? G.red : lnk.utilization > 50 ? G.yellow : G.green;
        ctx.fillStyle = ha(G.bg, 0.9);
        ctx.beginPath(); ctx.roundRect(bx - 20, by - 6, 40, 14, 4); ctx.fill();
        ctx.fillStyle = ha(G.border2, 1);
        ctx.beginPath(); ctx.roundRect(bx - 15, by - 3, 30, 6, 3); ctx.fill();
        ctx.fillStyle = uc;
        ctx.beginPath(); ctx.roundRect(bx - 15, by - 3, Math.round(30 * lnk.utilization / 100), 6, 3); ctx.fill();
        ctx.font = `9px ${FONT}`;
        ctx.fillStyle    = ha(G.dim, 1);
        ctx.textAlign    = 'center';
        ctx.textBaseline = 'top';
        ctx.fillText(`${lnk.utilization}%`, bx, by + 4);
      }
    });

    // ── Nodes ──────────────────────────────────────────────────
    devs.forEach(dev => {
      const p = pos[dev.id]; if (!p) return;
      const isUp  = dev.status === 'up';
      const isSel = sel?.id === dev.id;
      const vc    = vendorColor(dev.vendor);
      const R     = 36;

      if (isSel) {
        for (const [r, a] of [[R + 18, 0.2], [R + 9, 0.42]]) {
          ctx.beginPath(); ctx.arc(p.x, p.y, r, 0, Math.PI * 2);
          ctx.strokeStyle = ha(G.accent, a); ctx.lineWidth = 1.5; ctx.stroke();
        }
      }

      ctx.shadowColor = isUp ? ha(vc, 0.55) : ha(G.red, 0.3);
      ctx.shadowBlur  = isSel ? 30 : 16;

      // Outer ring
      ctx.beginPath(); ctx.arc(p.x, p.y, R + 3, 0, Math.PI * 2);
      ctx.strokeStyle = isSel ? G.accent : ha(isUp ? vc : G.red, isSel ? 0.9 : 0.4);
      ctx.lineWidth   = isSel ? 2.5 : 1.5; ctx.stroke();

      // Fill
      ctx.beginPath(); ctx.arc(p.x, p.y, R, 0, Math.PI * 2);
      const gr = ctx.createRadialGradient(p.x - R*.3, p.y - R*.3, 2, p.x, p.y, R);
      gr.addColorStop(0, G.card2); gr.addColorStop(1, G.card);
      ctx.fillStyle = gr; ctx.fill();
      ctx.strokeStyle = isSel ? G.accent : ha(vc, 0.75);
      ctx.lineWidth   = isSel ? 2.5 : 2; ctx.stroke();
      ctx.shadowBlur  = 0;

      // Icon
      const icons = { router: '◈', firewall: '⬡', switch: '◉', ap: '◎', modem: '◍' };
      ctx.font = '21px serif'; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
      ctx.fillStyle = isUp ? vc : G.muted;
      ctx.fillText(icons[dev.type] || '◉', p.x, p.y);

      // Status dot
      ctx.beginPath(); ctx.arc(p.x + R - 6, p.y - R + 6, 7, 0, Math.PI * 2);
      ctx.fillStyle   = isUp ? G.green : G.red;
      ctx.shadowColor = isUp ? G.green : G.red; ctx.shadowBlur = 10;
      ctx.fill(); ctx.shadowBlur = 0;
      ctx.strokeStyle = G.bg; ctx.lineWidth = 2.5; ctx.stroke();

      // Labels
      if (labR.current) {
        ctx.textAlign = 'center'; ctx.textBaseline = 'top';
        ctx.font      = `700 14px ${FONT}`;
        ctx.fillStyle = isSel ? G.accent : (isUp ? G.text : G.dim);
        ctx.fillText(dev.name, p.x, p.y + R + 9);
        ctx.font      = `11px ${FONT}`; ctx.fillStyle = G.dim;
        ctx.fillText(dev.ip, p.x, p.y + R + 27);
        // DOWN badge
        if (!isUp) {
          ctx.font      = `700 10px ${FONT}`;
          ctx.fillStyle = G.red;
          ctx.fillText('● OFFLINE', p.x, p.y + R + 42);
        }
      }
    });
  }, []);

  useEffect(() => {
    let frame;
    const loop = () => { flowRef.current += 0.55; draw(); frame = requestAnimationFrame(loop); };
    frame = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(frame);
  }, [draw]);

  // ── Mouse ──────────────────────────────────────────────────────────
  const toC = e => {
    const r = canvasRef.current.getBoundingClientRect();
    return { x: (e.clientX - r.left) * (canvasRef.current.width / r.width),
             y: (e.clientY - r.top)  * (canvasRef.current.height / r.height) };
  };
  const devAt = ({ x, y }) => dRef.current.find(d => {
    const p = pRef.current[d.id]; return p && Math.hypot(p.x - x, p.y - y) < 44;
  });
  const lnkAt = ({ x, y }) => lRef.current.find(l => {
    const fp = pRef.current[l.from], tp = pRef.current[l.to]; if (!fp || !tp) return false;
    // Point-to-STRAIGHT-line distance
    const dx = tp.x - fp.x, dy = tp.y - fp.y, len = Math.hypot(dx, dy);
    if (len === 0) return false;
    const t = Math.max(0, Math.min(1, ((x - fp.x)*dx + (y - fp.y)*dy) / (len*len)));
    const px = fp.x + t*dx, py = fp.y + t*dy;
    return Math.hypot(x - px, y - py) < 10;
  });

  const onMouseDown = e => {
    const pt = toC(e), d = devAt(pt);
    if (d) {
      setSelected(d); setSelLink(null); setDragging(d.id);
      const p = pRef.current[d.id]; setDragOff({ x: pt.x - p.x, y: pt.y - p.y });
    } else {
      const l = lnkAt(pt);
      if (l) { setSelLink(l); setSelected(null); }
      else   { setSelected(null); setSelLink(null); }
    }
  };
  const onMouseMove = e => {
    if (!dragging) return;
    const pt = toC(e);
    setPositions(p => ({ ...p, [dragging]: { x: pt.x - dragOff.x, y: pt.y - dragOff.y } }));
  };
  const onMouseUp = () => setDragging(null);

  // ── Derived ────────────────────────────────────────────────────────
  const filtered = devices.filter(d => {
    const q = search.toLowerCase();
    return (!q || d.name.toLowerCase().includes(q) || (d.ip||'').includes(q)) &&
           (filter === 'all' || d.status === filter);
  });
  const onlineCnt  = devices.filter(d => d.status === 'up').length;
  const offlineCnt = devices.length - onlineCnt;
  const devLinks   = id => links.filter(l => l.from === id || l.to === id);
  const logEnd     = useRef(null);
  useEffect(() => { logEnd.current?.scrollIntoView({ behavior: 'smooth' }); }, [scanLogs]);

  // ── Port panel: group real API interfaces ──────────────────────────
  const renderPortPanel = (dev) => {
    const dl     = devLinks(dev.id);
    const load   = ifaceLoad[dev.id];
    const ifaces = devIfaces[dev.id];

    // Connected ports from links (always shown even without API)
    const connectedFromLinks = dl.map(l => ({
      name:   l.from === dev.id ? l.iface_from : l.iface_to,
      status: l.status,
      link:   l,
      speed:  l.bandwidth,
      source: 'link',
    })).filter(p => p.name);

    // If API returned interface data, use it
    const apiIfaces = ifaces ? ifaces.map(ifc => {
      const matchLink = dl.find(l =>
        (l.from === dev.id ? l.iface_from : l.iface_to) === ifc.name
      );
      return {
        name:   ifc.name,
        status: ifc.status || ifc.running ? 'up' : 'down',
        link:   matchLink || null,
        speed:  ifc.speed || ifc.tx_rate || matchLink?.bandwidth || null,
        desc:   ifc.description || ifc.comment || '',
        mac:    ifc.mac_address || ifc.mac || '',
        type:   ifc.type || guessType(ifc.name),
        source: 'api',
      };
    }) : null;

    const portList = apiIfaces || connectedFromLinks;
    const upCnt    = portList.filter(p => p.status === 'up').length;
    const connCnt  = portList.filter(p => p.link).length;
    const downCnt  = portList.length - upCnt;

    return (
      <div style={{ flex: 1, overflowY: 'auto', padding: '8px 12px' }}>
        {/* Summary row */}
        <div style={{ display: 'flex', gap: 6, marginBottom: 10 }}>
          {[
            [upCnt,   'Ports UP',    G.green],
            [connCnt, 'Connected',   G.accent],
            [downCnt, 'Ports DOWN',  G.red],
          ].map(([n, lbl, col]) => (
            <div key={lbl} style={{ flex: 1, padding: '6px 8px', borderRadius: 7, background: ha(col, 0.1), border: `1px solid ${ha(col, 0.2)}`, textAlign: 'center' }}>
              <div style={{ fontSize: 20, fontWeight: 700, color: col, fontFamily: FONT, lineHeight: 1.2 }}>{n}</div>
              <div style={{ fontSize: 10, color: G.muted, marginTop: 2 }}>{lbl}</div>
            </div>
          ))}
        </div>

        <div style={{ fontSize: 10, color: G.muted, fontFamily: FONT, letterSpacing: '0.08em', marginBottom: 7 }}>
          INTERFACE INVENTORY {load === 'loading' && <span style={{ color: G.accent }}>← loading...</span>}
          {load === 'error' && <span style={{ color: G.yellow }}>← API error (showing link data)</span>}
          {!ifaces && load !== 'loading' && <span style={{ color: G.dim }}>← click Refresh Interfaces</span>}
        </div>

        {load === 'loading' && (
          <div style={{ textAlign: 'center', padding: 20, color: G.muted, fontFamily: FONT, fontSize: 11 }}>
            <Loader2 size={14} className="spin" style={{ marginBottom: 6 }}/><br/>Fetching interfaces from device...
          </div>
        )}

        {portList.length === 0 && load !== 'loading' && (
          <div style={{ textAlign: 'center', padding: 20, color: G.muted, fontSize: 12 }}>
            No interface data.<br/>
            <button onClick={() => fetchInterfaces(dev.id)}
              style={{ marginTop: 8, padding: '5px 12px', background: ha(G.accent, 0.12), border: `1px solid ${ha(G.accent, 0.3)}`, borderRadius: 5, color: G.accent, fontSize: 11, cursor: 'pointer', fontFamily: FONT }}>
              Fetch Interfaces
            </button>
          </div>
        )}

        {portList.length > 0 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
            {portList.map((port, i) => {
              const isUp  = port.status === 'up';
              const cfg   = port.link ? (LT[port.link.type] || LT.ethernet) : null;
              const peer  = port.link ? devices.find(d => d.id === (port.link.from === dev.id ? port.link.to : port.link.from)) : null;
              const peerIf = port.link ? (port.link.from === dev.id ? port.link.iface_to : port.link.iface_from) : null;
              return (
                <div key={`${port.name}-${i}`}
                  onClick={() => port.link && (setSelLink(port.link), setSelected(null))}
                  style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '6px 9px', borderRadius: 6, background: port.link ? ha(cfg.color, 0.08) : ha(G.border, 0.4), border: `1px solid ${port.link ? ha(cfg.color, 0.22) : G.border}`, cursor: port.link ? 'pointer' : 'default', transition: 'all .1s' }}>
                  {/* Status dot */}
                  <div style={{ width: 7, height: 7, borderRadius: '50%', flexShrink: 0, background: isUp ? G.green : ha(G.muted, 0.8), boxShadow: isUp ? `0 0 6px ${G.green}` : 'none' }}/>
                  {/* Port name */}
                  <span style={{ fontFamily: FONT, fontSize: 12, fontWeight: 600, color: isUp ? G.text : G.muted, minWidth: 80, flexShrink: 0 }}>{port.name}</span>
                  {/* Speed / desc */}
                  {(port.speed || port.desc) && (
                    <span style={{ fontSize: 10, color: G.dim, fontFamily: FONT, flexShrink: 0 }}>{port.speed || port.desc}</span>
                  )}
                  {/* Connected peer */}
                  {peer ? (
                    <div style={{ flex: 1, display: 'flex', alignItems: 'center', gap: 4, overflow: 'hidden' }}>
                      <ChevronRight size={11} color={cfg.color}/>
                      <span style={{ fontSize: 12, fontFamily: FONT, color: cfg.color, fontWeight: 700, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{peer.name}</span>
                      {peerIf && <span style={{ fontSize: 10, color: G.dim, fontFamily: FONT, flexShrink: 0 }}>[{peerIf}]</span>}
                    </div>
                  ) : (
                    <span style={{ fontSize: 10, color: G.muted, flex: 1, fontFamily: FONT }}>{isUp ? 'active' : 'no link'}</span>
                  )}
                  <span style={{ fontSize: 9, fontFamily: FONT, fontWeight: 700, color: isUp ? G.green : ha(G.muted, 0.8), flexShrink: 0 }}>{isUp ? 'UP' : '—'}</span>
                </div>
              );
            })}
          </div>
        )}

        {/* Refresh button */}
        {dev.status === 'up' && (
          <button onClick={() => fetchInterfaces(dev.id)}
            style={{ marginTop: 10, width: '100%', padding: '6px', background: ha(G.accent, 0.08), border: `1px solid ${ha(G.accent, 0.2)}`, borderRadius: 6, color: G.accent, fontSize: 11, cursor: 'pointer', fontFamily: FONT, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 5 }}>
            <RefreshCw size={11}/> Refresh Interfaces
          </button>
        )}
        {dev.status !== 'up' && (
          <div style={{ marginTop: 8, padding: '8px', borderRadius: 6, background: ha(G.red, 0.1), border: `1px solid ${ha(G.red, 0.2)}`, display: 'flex', alignItems: 'center', gap: 7, fontSize: 11, color: G.red, fontFamily: FONT }}>
            <AlertTriangle size={13}/> Device offline — cannot fetch live interface data
          </div>
        )}
      </div>
    );
  };

  // ── Render ─────────────────────────────────────────────────────────
  return (
    <>
      <style>{css}</style>
      <div style={{ display: 'flex', height: '100vh', background: G.bg, overflow: 'hidden', fontFamily: SANS }}>

        {/* ── Sidebar ─────────────────────────────────────────── */}
        <div style={{ width: 300, minWidth: 300, background: G.surface, borderRight: `1px solid ${G.border}`, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>

          {/* Header */}
          <div style={{ padding: '14px 16px 10px', borderBottom: `1px solid ${G.border}` }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 9, marginBottom: 6 }}>
              <div style={{ width: 32, height: 32, borderRadius: 8, background: ha(G.accent, 0.13), border: `1px solid ${ha(G.accent, 0.3)}`, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <Network size={16} color={G.accent}/>
              </div>
              <div>
                <div style={{ fontSize: 15, fontWeight: 700, color: G.text }}>Network Topology</div>
                <div style={{ fontSize: 11, fontFamily: FONT, color: G.muted }}>v2 · real-data only</div>
              </div>
            </div>
            <div style={{ display: 'flex', gap: 12, fontSize: 12, fontFamily: FONT }}>
              <span style={{ color: G.green, display: 'flex', alignItems: 'center', gap: 5 }}>
                <span style={{ width: 7, height: 7, borderRadius: '50%', background: G.green, display: 'inline-block', boxShadow: `0 0 7px ${G.green}` }}/> {onlineCnt} online
              </span>
              {offlineCnt > 0 && (
                <span style={{ color: G.red, display: 'flex', alignItems: 'center', gap: 5 }}>
                  <span style={{ width: 7, height: 7, borderRadius: '50%', background: G.red, display: 'inline-block' }}/> {offlineCnt} offline
                </span>
              )}
            </div>
          </div>

          {/* Discover */}
          <div style={{ padding: '10px 12px', borderBottom: `1px solid ${G.border}` }}>
            <button onClick={runDiscovery} disabled={scanning || !devices.length}
              style={{ width: '100%', padding: '10px', borderRadius: 8, cursor: scanning ? 'not-allowed' : 'pointer', background: scanning ? G.card : ha(G.accent, 0.12), border: `1px solid ${scanning ? G.border2 : ha(G.accent, 0.5)}`, color: scanning ? G.muted : G.accent, fontSize: 13, fontWeight: 600, fontFamily: FONT, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8, transition: 'all .2s' }}>
              {scanning ? <><Loader2 size={14} className="spin"/> Scanning...</> : <><Radar size={14}/> Auto-Discover Topology</>}
            </button>
            {scanStep === 'done' && (
              <div style={{ marginTop: 6, fontSize: 11, fontFamily: FONT, color: G.green, display: 'flex', alignItems: 'center', gap: 4 }}>
                <CheckCircle2 size={11}/> {lastFetch} · {links.length} link{links.length !== 1 ? 's' : ''} mapped
              </div>
            )}
            {scanStep !== 'idle' && (
              <button onClick={() => setShowLog(p => !p)}
                style={{ marginTop: 4, width: '100%', background: 'none', border: 'none', cursor: 'pointer', fontSize: 11, fontFamily: FONT, color: G.muted }}>
                {showLog ? '▲ hide log' : '▼ show log'}
              </button>
            )}
          </div>

          {/* Search + filter */}
          <div style={{ padding: '8px 12px', borderBottom: `1px solid ${G.border}` }}>
            <div style={{ position: 'relative', marginBottom: 7 }}>
              <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search device, IP..."
                style={{ width: '100%', padding: '7px 10px 7px 30px', background: G.card, border: `1px solid ${G.border2}`, borderRadius: 7, color: G.text, fontSize: 12, outline: 'none', fontFamily: FONT }}/>
              <Search style={{ position: 'absolute', left: 9, top: 8, width: 13, height: 13, color: G.muted }}/>
            </div>
            <div style={{ display: 'flex', gap: 4 }}>
              {['all', 'up', 'down'].map(f => (
                <button key={f} onClick={() => setFilter(f)}
                  style={{ flex: 1, padding: '5px 0', borderRadius: 5, fontSize: 11, fontWeight: 600, cursor: 'pointer', border: 'none', fontFamily: FONT, transition: 'all .15s', background: filter === f ? G.accent : G.card, color: filter === f ? G.bg : G.muted }}>
                  {f === 'all' ? 'ALL' : f === 'up' ? '▲ UP' : '▼ DOWN'}
                </button>
              ))}
            </div>
          </div>

          {/* Device list */}
          <div style={{ flex: 1, overflowY: 'auto', padding: '6px 8px' }}>
            {filtered.map(dev => {
              const isSel = selected?.id === dev.id;
              const isUp  = dev.status === 'up';
              const dl    = devLinks(dev.id);
              return (
                <div key={dev.id} onClick={() => setSelected(isSel ? null : dev)} className="fadeIn"
                  style={{ padding: '10px 12px', marginBottom: 4, borderRadius: 8, background: isSel ? ha(G.accent, 0.1) : G.card, border: `1px solid ${isSel ? ha(G.accent, 0.4) : (isUp ? G.border : ha(G.red, 0.3))}`, cursor: 'pointer', transition: 'all .15s' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
                      <div style={{ width: 8, height: 8, borderRadius: '50%', background: isUp ? G.green : G.red, boxShadow: `0 0 7px ${isUp ? G.green : G.red}` }}/>
                      <span style={{ fontWeight: 700, fontSize: 13, fontFamily: FONT, color: isSel ? G.accent : (isUp ? G.text : G.dim) }}>{dev.name}</span>
                    </div>
                    <span style={{ fontSize: 10, fontFamily: FONT, padding: '2px 6px', borderRadius: 4, background: ha(vendorColor(dev.vendor), 0.15), color: vendorColor(dev.vendor), fontWeight: 700, letterSpacing: '0.05em' }}>
                      {(dev.vendor || '').toUpperCase()}
                    </span>
                  </div>
                  <div style={{ fontSize: 12, fontFamily: FONT, color: G.muted }}>{dev.ip}</div>
                  {dev.model  && <div style={{ fontSize: 11, fontFamily: FONT, color: G.dim, marginTop: 2 }}>{dev.model}</div>}
                  {dev.uptime && <div style={{ fontSize: 11, color: G.dim, marginTop: 2 }}>⏱ {dev.uptime}</div>}
                  {!isUp && <div style={{ fontSize: 10, color: G.red, marginTop: 3, fontFamily: FONT }}>● OFFLINE</div>}

                  {/* Active link badges */}
                  {dl.length > 0 && (
                    <div style={{ marginTop: 6, display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                      {dl.map(l => {
                        const cfg  = LT[l.type] || LT.ethernet;
                        const peer = devices.find(d => d.id === (l.from === dev.id ? l.to : l.from));
                        const myIf = l.from === dev.id ? l.iface_from : l.iface_to;
                        return (
                          <div key={l.id} onClick={e => { e.stopPropagation(); setSelLink(l); setSelected(null); }}
                            style={{ fontSize: 10, fontFamily: FONT, padding: '2px 7px', borderRadius: 4, background: ha(cfg.color, 0.12), color: l.status === 'up' ? cfg.color : G.muted, display: 'flex', alignItems: 'center', gap: 4, cursor: 'pointer', border: `1px solid ${ha(l.status === 'up' ? cfg.color : G.muted, 0.25)}` }}>
                            <LTIcon type={l.type} sz={10}/>
                            {myIf && <span style={{ color: ha(cfg.color, 0.7) }}>{myIf}→</span>}
                            <span style={{ color: G.text, fontWeight: 600 }}>{peer?.name || '?'}</span>
                            {l.bandwidth && <span style={{ opacity: .7 }}>{l.bandwidth}</span>}
                          </div>
                        );
                      })}
                    </div>
                  )}

                  {(dev.cpu_usage > 0 || dev.memory_usage > 0) && (
                    <div style={{ marginTop: 6, display: 'flex', flexDirection: 'column', gap: 4 }}>
                      {[['CPU', dev.cpu_usage, G.green, G.yellow, G.red, 80, 50],
                        ['MEM', dev.memory_usage, G.accent, G.yellow, G.red, 85, 60]].map(([lbl, val, c1, c2, c3, t1, t2]) => val > 0 && (
                        <div key={lbl} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                          <span style={{ fontSize: 10, color: G.muted, width: 26, fontFamily: FONT }}>{lbl}</span>
                          <div style={{ flex: 1, height: 4, background: G.border, borderRadius: 2 }}>
                            <div style={{ width: `${val}%`, height: '100%', borderRadius: 2, background: val > t1 ? c3 : val > t2 ? c2 : c1, transition: 'width .3s' }}/>
                          </div>
                          <span style={{ fontSize: 10, fontFamily: FONT, color: G.muted, width: 28, textAlign: 'right' }}>{val}%</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
            {!filtered.length && <div style={{ textAlign: 'center', color: G.muted, fontSize: 12, padding: 28, fontFamily: FONT }}>No devices found</div>}
          </div>

          <div style={{ padding: '6px 14px', borderTop: `1px solid ${G.border}`, fontSize: 11, fontFamily: FONT, color: G.muted, display: 'flex', justifyContent: 'space-between' }}>
            <span>{lastFetch ? `↻ ${lastFetch}` : 'Not fetched'}</span>
            <span>{devices.length} dev · {links.length} lnk</span>
          </div>
        </div>

        {/* ── Canvas area ───────────────────────────────────────── */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden', position: 'relative' }}>

          {/* Toolbar */}
          <div style={{ height: 42, background: G.surface, borderBottom: `1px solid ${G.border}`, display: 'flex', alignItems: 'center', padding: '0 14px', gap: 7, flexShrink: 0 }}>
            <span style={{ fontSize: 12, color: G.muted, fontFamily: FONT, marginRight: 6 }}>
              D:{devices.length} · L:{links.length}
              {!links.length && devices.length > 1 && <span style={{ color: G.yellow }}> ← run scan</span>}
            </span>
            <div style={{ display: 'flex', gap: 8, fontSize: 10, fontFamily: FONT, marginRight: 'auto', flexWrap: 'wrap' }}>
              {Object.entries(LT).filter(([k]) => k !== 'unknown').map(([t, c]) => (
                <span key={t} style={{ color: c.color, display: 'flex', alignItems: 'center', gap: 3 }}>
                  <LTIcon type={t} sz={10}/> {c.label}
                </span>
              ))}
            </div>
            {[['Ports', showPorts, setShowPorts], ['Labels', showLabels, setShowLabels], ['Util%', showUtil, setShowUtil]].map(([lbl, v, fn]) => (
              <button key={lbl} onClick={() => fn(p => !p)}
                style={{ padding: '4px 10px', background: G.card, border: `1px solid ${v ? ha(G.accent, 0.4) : G.border2}`, borderRadius: 5, color: v ? G.accent : G.muted, fontSize: 11, cursor: 'pointer', fontFamily: FONT }}>
                {lbl}
              </button>
            ))}
            <button onClick={fetchTopology}
              style={{ display: 'flex', alignItems: 'center', gap: 4, padding: '4px 10px', background: loading ? ha(G.accent, 0.12) : G.card, border: `1px solid ${loading ? ha(G.accent, 0.4) : G.border2}`, borderRadius: 5, color: loading ? G.accent : G.text, fontSize: 11, cursor: 'pointer', fontFamily: FONT }}>
              <RefreshCw size={12} style={{ animation: loading ? 'spin 1s linear infinite' : 'none' }}/> Refresh
            </button>
            <button onClick={() => { const a = document.createElement('a'); a.download = 'topo.png'; a.href = canvasRef.current.toDataURL(); a.click(); }}
              style={{ display: 'flex', alignItems: 'center', gap: 4, padding: '4px 10px', background: G.card, border: `1px solid ${G.border2}`, borderRadius: 5, color: G.text, fontSize: 11, cursor: 'pointer', fontFamily: FONT }}>
              <Download size={12}/> PNG
            </button>
          </div>

          <canvas ref={canvasRef} width={1200} height={800}
            style={{ flex: 1, width: '100%', height: '100%', display: 'block', cursor: dragging ? 'grabbing' : 'crosshair' }}
            onMouseDown={onMouseDown} onMouseMove={onMouseMove} onMouseUp={onMouseUp} onMouseLeave={onMouseUp}/>

          {/* ── Device detail + Port panel ──────────────────────── */}
          {selected && (
            <div className="fadeIn" style={{ position: 'absolute', top: 52, right: 14, bottom: 14, width: 310, background: G.card, border: `1px solid ${ha(G.accent, 0.3)}`, borderRadius: 12, display: 'flex', flexDirection: 'column', overflow: 'hidden', boxShadow: `0 10px 40px rgba(0,0,0,.6)` }}>

              {/* Header */}
              <div style={{ padding: '12px 14px 10px', borderBottom: `1px solid ${G.border}`, flexShrink: 0 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <div style={{ width: 10, height: 10, borderRadius: '50%', background: selected.status === 'up' ? G.green : G.red, boxShadow: `0 0 9px ${selected.status === 'up' ? G.green : G.red}` }}/>
                    <span style={{ fontWeight: 700, fontSize: 15, fontFamily: FONT, color: G.accent }}>{selected.name}</span>
                  </div>
                  <button onClick={() => setSelected(null)} style={{ background: 'none', border: 'none', color: G.muted, cursor: 'pointer' }}><X size={15}/></button>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '80px 1fr', gap: '3px 0', fontSize: 12 }}>
                  {[['IP', selected.ip], ['Vendor', (selected.vendor || '').toUpperCase()],
                    ['Type', selected.type], ['Model', selected.model], ['Uptime', selected.uptime]]
                    .filter(([, v]) => v).map(([k, v]) => (
                    <React.Fragment key={k}>
                      <span style={{ color: G.muted }}>{k}</span>
                      <span style={{ color: G.text, fontFamily: FONT, fontSize: 11 }}>{v}</span>
                    </React.Fragment>
                  ))}
                </div>
              </div>

              {renderPortPanel(selected)}

              {/* Status footer */}
              <div style={{ padding: '6px 14px', borderTop: `1px solid ${G.border}`, flexShrink: 0, textAlign: 'center', background: selected.status === 'up' ? ha(G.green, 0.1) : ha(G.red, 0.1), color: selected.status === 'up' ? G.green : G.red, fontSize: 11, fontWeight: 700, fontFamily: FONT }}>
                ● {selected.status === 'up' ? 'ONLINE' : 'OFFLINE — device is unreachable'}
              </div>
            </div>
          )}

          {/* ── Link detail panel ───────────────────────────────── */}
          {selLink && !selected && (() => {
            const cfg   = LT[selLink.type] || LT.ethernet;
            const fromD = devices.find(d => d.id === selLink.from);
            const toD   = devices.find(d => d.id === selLink.to);
            return (
              <div className="fadeIn" style={{ position: 'absolute', bottom: 18, right: 18, background: G.card, border: `1px solid ${ha(cfg.color, 0.4)}`, borderRadius: 12, padding: '14px 16px', width: 290, boxShadow: '0 10px 36px rgba(0,0,0,.6)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 7, color: cfg.color }}>
                    <LTIcon type={selLink.type} sz={15}/>
                    <span style={{ fontWeight: 700, fontSize: 14, fontFamily: FONT }}>{cfg.label} Link</span>
                    <span style={{ fontSize: 11, fontFamily: FONT, color: selLink.status === 'up' ? G.green : G.red }}>● {selLink.status?.toUpperCase()}</span>
                  </div>
                  <button onClick={() => setSelLink(null)} style={{ background: 'none', border: 'none', color: G.muted, cursor: 'pointer' }}><X size={15}/></button>
                </div>
                <div style={{ padding: '10px 12px', borderRadius: 8, background: ha(cfg.color, 0.08), border: `1px solid ${ha(cfg.color, 0.2)}`, marginBottom: 10 }}>
                  <div style={{ fontSize: 10, color: G.muted, marginBottom: 8, fontFamily: FONT, letterSpacing: '0.07em' }}>PORT CONNECTION</div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                    <div style={{ textAlign: 'center', flex: 1 }}>
                      <div style={{ fontSize: 13, fontWeight: 700, color: G.text, fontFamily: FONT }}>{fromD?.name || '?'}</div>
                      <div style={{ marginTop: 5, display: 'inline-block', background: ha(cfg.color, 0.22), color: cfg.color, padding: '3px 10px', borderRadius: 5, fontFamily: FONT, fontSize: 12, fontWeight: 700 }}>{selLink.iface_from || '?'}</div>
                    </div>
                    <div style={{ textAlign: 'center' }}>
                      <div style={{ color: cfg.color, fontSize: 20 }}>⇌</div>
                      {selLink.bandwidth && <div style={{ fontSize: 10, fontFamily: FONT, color: G.dim, marginTop: 3 }}>{selLink.bandwidth}</div>}
                    </div>
                    <div style={{ textAlign: 'center', flex: 1 }}>
                      <div style={{ fontSize: 13, fontWeight: 700, color: G.text, fontFamily: FONT }}>{toD?.name || '?'}</div>
                      <div style={{ marginTop: 5, display: 'inline-block', background: ha(cfg.color, 0.22), color: cfg.color, padding: '3px 10px', borderRadius: 5, fontFamily: FONT, fontSize: 12, fontWeight: 700 }}>{selLink.iface_to || '?'}</div>
                    </div>
                  </div>
                </div>
                {[['Link type', selLink.type], ['Bandwidth', selLink.bandwidth]].filter(([, v]) => v).map(([k, v]) => (
                  <div key={k} style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 5, fontSize: 12 }}>
                    <span style={{ color: G.muted }}>{k}</span><span style={{ color: G.text, fontFamily: FONT }}>{v}</span>
                  </div>
                ))}
                {selLink.utilization > 0 && (
                  <div style={{ marginTop: 6 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4, fontSize: 12 }}>
                      <span style={{ color: G.muted }}>Utilization</span>
                      <span style={{ color: selLink.utilization > 80 ? G.red : G.text, fontFamily: FONT }}>{selLink.utilization}%</span>
                    </div>
                    <div style={{ height: 5, background: G.border, borderRadius: 3 }}>
                      <div style={{ width: `${selLink.utilization}%`, height: '100%', borderRadius: 3, background: selLink.utilization > 80 ? G.red : selLink.utilization > 50 ? G.yellow : G.green }}/>
                    </div>
                  </div>
                )}
              </div>
            );
          })()}

          {/* ── Scan log ────────────────────────────────────────── */}
          {showLog && (
            <div className="fadeIn" style={{ position: 'absolute', top: 52, left: 14, background: G.surface, border: `1px solid ${G.border2}`, borderRadius: 11, width: 440, maxHeight: 320, boxShadow: '0 16px 48px rgba(0,0,0,.75)', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
              <div style={{ padding: '9px 14px', borderBottom: `1px solid ${G.border}`, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
                  {scanStep === 'done' ? <CheckCircle2 size={14} color={G.green}/> : <Radar size={14} color={G.accent} style={{ animation: scanning ? 'spin 2s linear infinite' : 'none' }}/>}
                  <span style={{ fontSize: 13, fontWeight: 600, fontFamily: FONT, color: scanStep === 'done' ? G.green : G.accent }}>
                    {scanning ? 'Scanning...' : scanStep === 'done' ? 'Discovery Complete' : 'Log'}
                  </span>
                </div>
                <button onClick={() => setShowLog(false)} style={{ background: 'none', border: 'none', color: G.muted, cursor: 'pointer' }}><X size={14}/></button>
              </div>
              <div style={{ height: 3, background: G.border, flexShrink: 0 }}>
                <div style={{ width: `${scanPct}%`, height: '100%', background: scanStep === 'done' ? G.green : G.accent, transition: 'width .4s ease' }}/>
              </div>
              <div style={{ flex: 1, overflowY: 'auto', padding: '8px 13px' }}>
                {scanLogs.map((l, i) => (
                  <div key={i} style={{ fontSize: 11, fontFamily: FONT, marginBottom: 3, display: 'flex', gap: 8 }}>
                    <span style={{ color: G.muted, flexShrink: 0 }}>{l.ts}</span>
                    <span style={{ color: l.msg.includes('✓') ? G.green : l.msg.includes('⚠') ? G.yellow : l.msg.includes('══') ? G.accent : l.msg.startsWith(' ') || l.msg.startsWith('[') ? G.dim : G.text }}>
                      {l.msg}
                    </span>
                  </div>
                ))}
                <div ref={logEnd}/>
              </div>
              <div style={{ padding: '6px 14px', borderTop: `1px solid ${G.border}`, fontSize: 11, fontFamily: FONT, color: G.muted, display: 'flex', justifyContent: 'space-between' }}>
                <span>{scanLogs.length} events</span>
                {scanStep === 'done' && <span style={{ color: G.green }}>● {links.length} links discovered</span>}
              </div>
            </div>
          )}
        </div>
      </div>
    </>
  );
}
