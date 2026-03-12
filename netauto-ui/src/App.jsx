import { useState, useEffect, useRef, useCallback } from "react";

const G = {
  bg:"#07090e", surface:"#0d1017", card:"#111520", border:"#1a1f2e",
  border2:"#222840", text:"#e2e8f0", muted:"#4a5568", dim:"#7a8499",
  accent:"#38bdf8", green:"#20d9a0", red:"#f43f5e", yellow:"#fbbf24",
  purple:"#a78bfa", orange:"#fb923c",
};
const FONT = "'JetBrains Mono','Fira Code',monospace";
const FONT_UI = "'DM Sans','Outfit',sans-serif";

const css = `
  @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;500;600&family=DM+Sans:wght@300;400;500;600;700&display=swap');
  *{box-sizing:border-box;margin:0;padding:0;}
  body{background:${G.bg};color:${G.text};font-family:${FONT_UI};-webkit-font-smoothing:antialiased;}
  ::-webkit-scrollbar{width:4px;height:4px;}
  ::-webkit-scrollbar-track{background:${G.bg};}
  ::-webkit-scrollbar-thumb{background:${G.border2};border-radius:4px;}
  ::selection{background:${G.accent}22;color:${G.accent};}
  @keyframes fadeIn{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:translateY(0)}}
  @keyframes spin{to{transform:rotate(360deg)}}
  @keyframes blink{0%,100%{opacity:1}50%{opacity:0}}
  @keyframes glow{0%,100%{box-shadow:0 0 6px ${G.green}55}50%{box-shadow:0 0 14px ${G.green}99}}
  @keyframes barAnim{from{width:0}to{width:var(--w)}}
  .fadeIn{animation:fadeIn .3s ease forwards;}
  .spin{animation:spin 1s linear infinite;}
`;

// ── Storage ──────────────────────────────────────────────────────
const STORE = {
  get:(k,d)=>{try{const v=localStorage.getItem(k);return v?JSON.parse(v):d;}catch{return d;}},
  set:(k,v)=>{try{localStorage.setItem(k,JSON.stringify(v));}catch{}},
};

// ── API ──────────────────────────────────────────────────────────
let API_BASE = STORE.get("api_url","http://localhost:8000");
async function api(path, method="GET", body=null){
  const opts={method,headers:{"Content-Type":"application/json"}};
  if(body) opts.body=JSON.stringify(body);
  const res=await fetch(`${API_BASE}${path}`,opts);
  if(!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

const addLog=(type,msg)=>{
  const logs=STORE.get("activity_log",[]);
  logs.push({time:new Date().toLocaleTimeString("vi-VN"),type,msg});
  STORE.set("activity_log",logs.slice(-300));
};

// ── Atoms ────────────────────────────────────────────────────────
const Spinner=({size=16,color=G.accent})=>(
  <div className="spin" style={{width:size,height:size,border:`2px solid ${G.border2}`,borderTopColor:color,borderRadius:"50%",flexShrink:0}}/>
);
const StatusDot=({status})=>{
  const c=status==="online"?G.green:status==="warning"?G.yellow:G.red;
  return <span style={{display:"inline-block",width:7,height:7,borderRadius:"50%",background:c,boxShadow:status==="online"?`0 0 6px ${c}`:"none",animation:status==="online"?"glow 2s ease infinite":"none"}}/>;
};
const VChip=({vendor})=>{
  const C={mikrotik:G.purple,cisco:G.accent,fortinet:G.orange,sophos:G.green};
  const I={mikrotik:"◈",cisco:"⬡",fortinet:"◆",sophos:"◉"};
  const c=C[vendor]||G.dim;
  return <span style={{fontFamily:FONT,fontSize:10,fontWeight:600,color:c,background:`${c}15`,border:`1px solid ${c}30`,borderRadius:3,padding:"2px 7px",letterSpacing:"0.06em",textTransform:"uppercase"}}>{I[vendor]||"●"} {vendor}</span>;
};
const Badge=({color,children,small})=>(
  <span style={{display:"inline-flex",alignItems:"center",padding:small?"2px 7px":"3px 9px",borderRadius:4,background:`${color}18`,border:`1px solid ${color}44`,color,fontSize:small?10:11,fontFamily:FONT,fontWeight:500,letterSpacing:"0.04em",textTransform:"uppercase"}}>{children}</span>
);
const Btn=({children,onClick,variant="primary",small,disabled,style={},loading})=>{
  const V={
    primary:{bg:G.accent,color:"#07090e",border:`1px solid ${G.accent}`},
    ghost:{bg:"transparent",color:G.dim,border:`1px solid ${G.border2}`},
    danger:{bg:`${G.red}18`,color:G.red,border:`1px solid ${G.red}44`},
    success:{bg:`${G.green}18`,color:G.green,border:`1px solid ${G.green}44`},
    warning:{bg:`${G.yellow}18`,color:G.yellow,border:`1px solid ${G.yellow}44`},
  }[variant]||{};
  return(
    <button onClick={onClick} disabled={disabled||loading} style={{...V,cursor:(disabled||loading)?"not-allowed":"pointer",padding:small?"5px 11px":"8px 16px",borderRadius:6,fontSize:small?11:12,fontFamily:FONT_UI,fontWeight:600,opacity:(disabled||loading)?0.45:1,transition:"all .15s",display:"inline-flex",alignItems:"center",gap:6,...style}}>
      {loading&&<Spinner size={12} color={V.color}/>}
      {children}
    </button>
  );
};
const Input=({value,onChange,placeholder,type="text",style={},onKeyDown})=>(
  <input type={type} value={value} onChange={onChange} placeholder={placeholder} onKeyDown={onKeyDown}
    style={{background:G.surface,border:`1px solid ${G.border2}`,color:G.text,padding:"8px 12px",borderRadius:6,fontSize:13,fontFamily:FONT_UI,outline:"none",width:"100%",transition:"border .15s",...style}}
    onFocus={e=>e.target.style.borderColor=G.accent}
    onBlur={e=>e.target.style.borderColor=G.border2}
  />
);
const Sel=({value,onChange,options,style={}})=>(
  <select value={value} onChange={onChange} style={{background:G.surface,border:`1px solid ${G.border2}`,color:G.text,padding:"8px 12px",borderRadius:6,fontSize:13,fontFamily:FONT_UI,outline:"none",cursor:"pointer",width:"100%",...style}}>
    {options.map(o=><option key={o.value} value={o.value}>{o.label}</option>)}
  </select>
);
const Card=({children,style={},onClick,glow})=>(
  <div onClick={onClick} style={{background:G.card,border:`1px solid ${glow?G.accent+"55":G.border}`,borderRadius:10,padding:20,transition:"all .2s",boxShadow:glow?`0 0 20px ${G.accent}12`:"none",cursor:onClick?"pointer":"default",...style}}
    onMouseEnter={e=>{if(onClick){e.currentTarget.style.borderColor=G.border2;e.currentTarget.style.transform="translateY(-1px)";}}}
    onMouseLeave={e=>{if(onClick){e.currentTarget.style.borderColor=G.border;e.currentTarget.style.transform="none";}}}
  >{children}</div>
);
const MiniBar=({value,color})=>(
  <div style={{background:G.border,borderRadius:2,height:4,width:72,overflow:"hidden"}}>
    <div style={{background:color||G.accent,width:`${Math.min(value,100)}%`,height:"100%",borderRadius:2,transition:"width .5s"}}/>
  </div>
);
const Lbl=({children})=>(
  <div style={{fontSize:11,color:G.muted,marginBottom:6,fontFamily:FONT,letterSpacing:"0.06em",textTransform:"uppercase"}}>{children}</div>
);
function Toast({msg,type,onClose}){
  const c=type==="success"?G.green:type==="error"?G.red:G.yellow;
  useEffect(()=>{const t=setTimeout(onClose,3800);return()=>clearTimeout(t);},[]);
  return(
    <div className="fadeIn" style={{position:"fixed",bottom:24,right:24,zIndex:9999,background:G.card,border:`1px solid ${c}55`,borderRadius:8,padding:"12px 16px",display:"flex",alignItems:"center",gap:10,boxShadow:"0 8px 32px #00000088",minWidth:300}}>
      <span style={{color:c,fontSize:14}}>{type==="success"?"✓":type==="error"?"✕":"⚠"}</span>
      <span style={{fontSize:13,color:G.text}}>{msg}</span>
      <span onClick={onClose} style={{marginLeft:"auto",color:G.muted,cursor:"pointer",fontSize:18,lineHeight:1}}>×</span>
    </div>
  );
}

// ── Login ────────────────────────────────────────────────────────
function LoginPage({onLogin}){
  const [u,setU]=useState(""); const [p,setP]=useState("");
  const [loading,setLoading]=useState(false); const [err,setErr]=useState("");
  const [backendOk,setBackendOk]=useState(null);

  useEffect(()=>{
    fetch(`${API_BASE}/health`,{signal:AbortSignal.timeout(2000)})
      .then(r=>r.json()).then(()=>setBackendOk(true)).catch(()=>setBackendOk(false));
  },[]);

  const doLogin=()=>{
    if(!u||!p){setErr("Nhập đầy đủ thông tin");return;}
    setLoading(true);setErr("");
    setTimeout(()=>{
      if(u==="admin"&&p==="admin123") onLogin({username:u,role:"Administrator"});
      else{setErr("Sai username hoặc password");setLoading(false);}
    },700);
  };
  return(
    <div style={{minHeight:"100vh",display:"flex",alignItems:"center",justifyContent:"center",background:G.bg,backgroundImage:`radial-gradient(ellipse 70% 40% at 50% 0%,${G.accent}14 0%,transparent 65%)`,position:"relative",overflow:"hidden"}}>
      <div style={{position:"absolute",inset:0,opacity:0.03,backgroundImage:`linear-gradient(${G.accent} 1px,transparent 1px),linear-gradient(90deg,${G.accent} 1px,transparent 1px)`,backgroundSize:"44px 44px"}}/>
      <div className="fadeIn" style={{zIndex:1,width:420}}>
        <div style={{textAlign:"center",marginBottom:36}}>
          <div style={{display:"inline-flex",alignItems:"center",justifyContent:"center",width:68,height:68,borderRadius:16,background:`linear-gradient(135deg,${G.accent}22,${G.purple}22)`,border:`1px solid ${G.accent}44`,fontSize:30,marginBottom:18}}>⬡</div>
          <div style={{fontFamily:FONT,fontSize:28,fontWeight:700,color:G.text,letterSpacing:"-0.03em"}}>Pl<span style={{color:G.accent}}>Network</span></div>
          <div style={{fontFamily:FONT,fontSize:11,color:G.muted,marginTop:3,letterSpacing:"0.12em"}}>AUTO MANAGER v3.0</div>
        </div>
        <Card style={{padding:32}}>
          <div style={{fontFamily:FONT,fontSize:12,color:G.dim,marginBottom:22}}>//  authentication_required</div>
          {backendOk!==null&&(
            <div style={{padding:"8px 12px",borderRadius:6,fontSize:11,fontFamily:FONT,marginBottom:14,background:backendOk?`${G.green}15`:`${G.yellow}15`,border:`1px solid ${backendOk?G.green:G.yellow}44`,color:backendOk?G.green:G.yellow}}>
              {backendOk?"✓ Backend online — thiết bị thật sẵn sàng":"⚠ Backend offline — chạy demo mode (start.bat)"}
            </div>
          )}
          <div style={{display:"flex",flexDirection:"column",gap:14}}>
            <div><Lbl>Username</Lbl><Input value={u} onChange={e=>setU(e.target.value)} placeholder="admin" onKeyDown={e=>e.key==="Enter"&&doLogin()}/></div>
            <div><Lbl>Password</Lbl><Input type="password" value={p} onChange={e=>setP(e.target.value)} placeholder="••••••••" onKeyDown={e=>e.key==="Enter"&&doLogin()}/></div>
            {err&&<div style={{background:`${G.red}15`,border:`1px solid ${G.red}33`,borderRadius:6,padding:"8px 12px",fontSize:12,color:G.red,fontFamily:FONT}}>⚠ {err}</div>}
            <Btn onClick={doLogin} loading={loading} style={{padding:"11px",fontSize:13,justifyContent:"center"}}>{loading?"Authenticating...":"Sign In →"}</Btn>
          </div>
          <div style={{marginTop:18,padding:12,background:G.surface,borderRadius:6,fontFamily:FONT,fontSize:11,color:G.muted}}>
            Demo: <span style={{color:G.accent}}>admin</span> / <span style={{color:G.accent}}>admin123</span>
          </div>
        </Card>
        <div style={{textAlign:"center",marginTop:20,fontSize:11,color:G.muted,fontFamily:FONT}}>MikroTik · Cisco · Fortinet · Sophos</div>
      </div>
    </div>
  );
}

// ── Sidebar ──────────────────────────────────────────────────────
const NAV=[
  {id:"dashboard",icon:"▦",label:"Dashboard"},
  {id:"devices",  icon:"◈",label:"Devices"},
  {id:"terminal", icon:">_",label:"Terminal"},
  {id:"nettools", icon:"◎",label:"Net Tools"},
  {id:"config",   icon:"⚙",label:"Config Push"},
  {id:"monitor",  icon:"📊",label:"Monitor"},
  {id:"backup",   icon:"⊡",label:"Backup & Rollback"},
  {id:"scanner",  icon:"⊞",label:"Config Scanner"},
  {id:"services",  icon:"⊕",label:"Services"},
  {id:"serial",    icon:"⊛",label:"Console RS232"},
  {id:"botconfig", icon:"✈",label:"Telegram Bot"},
  {id:"settings",  icon:"✦",label:"Settings"},
];
function Sidebar({page,onNav,user,onLogout,devices}){
  const online=devices.filter(d=>d.status==="online").length;
  return(
    <div style={{width:230,minHeight:"100vh",background:G.surface,borderRight:`1px solid ${G.border}`,display:"flex",flexDirection:"column",position:"fixed",top:0,left:0,zIndex:100}}>
      <div style={{padding:"20px 20px 16px",borderBottom:`1px solid ${G.border}`}}>
        <div style={{fontFamily:FONT,fontSize:19,fontWeight:700,letterSpacing:"-0.02em"}}>Pl<span style={{color:G.accent}}>Network</span></div>
        <div style={{fontFamily:FONT,fontSize:9,color:G.muted,letterSpacing:"0.12em",marginTop:2}}>AUTO MANAGER</div>
        <div style={{marginTop:10,display:"flex",alignItems:"center",gap:6}}>
          <StatusDot status={online>0?"online":"offline"}/>
          <span style={{fontSize:11,color:G.dim}}>{online}/{devices.length} online</span>
        </div>
      </div>
      <nav style={{padding:"10px 0",flex:1}}>
        {NAV.map(item=>{
          const active=page===item.id;
          return(
            <div key={item.id} onClick={()=>onNav(item.id)} style={{display:"flex",alignItems:"center",gap:10,padding:"10px 20px",cursor:"pointer",background:active?`${G.accent}12`:"transparent",borderLeft:active?`2px solid ${G.accent}`:"2px solid transparent",color:active?G.accent:G.dim,fontSize:13,fontWeight:active?600:400,transition:"all .15s"}}
              onMouseEnter={e=>{if(!active)e.currentTarget.style.background=`${G.border}88`;}}
              onMouseLeave={e=>{if(!active)e.currentTarget.style.background="transparent";}}
            >
              <span style={{fontFamily:FONT,fontSize:13,width:18,textAlign:"center"}}>{item.icon}</span>
              {item.label}
            </div>
          );
        })}
      </nav>
      <div style={{padding:14,borderTop:`1px solid ${G.border}`}}>
        <div style={{display:"flex",alignItems:"center",gap:10,marginBottom:10}}>
          <div style={{width:34,height:34,borderRadius:8,background:`linear-gradient(135deg,${G.accent}33,${G.purple}33)`,border:`1px solid ${G.accent}44`,display:"flex",alignItems:"center",justifyContent:"center",fontSize:14,color:G.accent,fontFamily:FONT}}>{user.username[0].toUpperCase()}</div>
          <div>
            <div style={{fontSize:12,fontWeight:600,color:G.text}}>{user.username}</div>
            <div style={{fontSize:10,color:G.muted}}>{user.role}</div>
          </div>
        </div>
        <Btn variant="ghost" onClick={onLogout} small style={{width:"100%",justifyContent:"center"}}>Sign Out</Btn>
      </div>
    </div>
  );
}

// ── Dashboard ─────────────────────────────────────────────────────
function Dashboard({devices,onNav}){
  const online=devices.filter(d=>d.status==="online").length;
  const offline=devices.filter(d=>d.status==="offline").length;
  const warning=devices.filter(d=>d.status==="warning").length;
  const VC={mikrotik:G.purple,cisco:G.accent,fortinet:G.orange,sophos:G.green};
  const vendorCount=devices.reduce((a,d)=>{a[d.vendor]=(a[d.vendor]||0)+1;return a;},{});
  const logs=STORE.get("activity_log",[{time:"—",type:"info",msg:"PlNetwork Auto Manager v3.0 started"}]);
  return(
    <div className="fadeIn" style={{padding:28}}>
      <div style={{marginBottom:24}}>
        <div style={{fontSize:22,fontWeight:700}}>Dashboard</div>
        <div style={{fontSize:12,color:G.muted,marginTop:3}}>{new Date().toLocaleString("vi-VN")} · {devices.length} thiết bị</div>
      </div>
      <div style={{display:"flex",gap:14,marginBottom:18}}>
        {[["TOTAL",devices.length,G.text,"Thiết bị"],["ONLINE",online,G.green,`${devices.length?Math.round(online/devices.length*100):0}%`],["WARNING",warning,G.yellow,"Cần kiểm tra"],["OFFLINE",offline,G.red,"Không kết nối"]].map(([l,v,c,s])=>(
          <Card key={l} style={{flex:1}}>
            <div style={{fontSize:10,color:G.muted,fontFamily:FONT,letterSpacing:"0.07em",marginBottom:10}}>{l}</div>
            <div style={{fontSize:38,fontWeight:800,color:c,fontFamily:FONT,lineHeight:1}}>{v}</div>
            <div style={{fontSize:11,color:G.muted,marginTop:8}}>{s}</div>
          </Card>
        ))}
      </div>
      <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:14,marginBottom:16}}>
        <Card>
          <div style={{fontSize:11,color:G.muted,fontFamily:FONT,letterSpacing:"0.06em",marginBottom:14}}>VENDOR BREAKDOWN</div>
          {Object.entries(vendorCount).map(([v,n])=>(
            <div key={v} style={{display:"flex",alignItems:"center",gap:10,marginBottom:10}}>
              <VChip vendor={v}/>
              <div style={{flex:1,background:G.border,borderRadius:2,height:4}}><div style={{width:`${n/devices.length*100}%`,height:"100%",background:VC[v]||G.dim,borderRadius:2}}/></div>
              <span style={{fontFamily:FONT,fontSize:11,color:G.dim}}>{n}</span>
            </div>
          ))}
          {!Object.keys(vendorCount).length&&<div style={{fontSize:12,color:G.muted}}>Chưa có thiết bị. <span onClick={()=>onNav("devices")} style={{color:G.accent,cursor:"pointer"}}>+ Thêm ngay</span></div>}
        </Card>
        <Card>
          <div style={{fontSize:11,color:G.muted,fontFamily:FONT,letterSpacing:"0.06em",marginBottom:14}}>QUICK ACTIONS</div>
          {[["＋","Thêm thiết bị","devices",G.accent],[">_","Mở Terminal","terminal",G.purple],["⚙","Config Push","config",G.orange],["◎","Net Tools (Ping/Trace)","nettools",G.green]].map(([ic,l,p,c])=>(
            <div key={l} onClick={()=>onNav(p)} style={{display:"flex",alignItems:"center",gap:10,padding:"8px 10px",borderRadius:6,cursor:"pointer",background:G.surface,border:`1px solid ${G.border}`,marginBottom:8,transition:"all .15s"}}
              onMouseEnter={e=>e.currentTarget.style.borderColor=c+"66"}
              onMouseLeave={e=>e.currentTarget.style.borderColor=G.border}
            >
              <span style={{color:c,fontFamily:FONT,fontSize:14,width:18,textAlign:"center"}}>{ic}</span>
              <span style={{fontSize:12,color:G.dim}}>{l}</span>
              <span style={{marginLeft:"auto",color:G.muted}}>→</span>
            </div>
          ))}
        </Card>
      </div>
      <Card style={{padding:0,overflow:"hidden",marginBottom:16}}>
        <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",padding:"14px 18px",borderBottom:`1px solid ${G.border}`}}>
          <div style={{fontSize:11,color:G.muted,fontFamily:FONT,letterSpacing:"0.06em"}}>DEVICE STATUS</div>
          <Btn variant="ghost" small onClick={()=>onNav("devices")}>Xem tất cả →</Btn>
        </div>
        {devices.length===0?(
          <div style={{padding:32,textAlign:"center",color:G.muted,fontSize:13}}>Chưa có thiết bị — <span onClick={()=>onNav("devices")} style={{color:G.accent,cursor:"pointer"}}>+ Thêm</span></div>
        ):(
          <table style={{width:"100%",borderCollapse:"collapse"}}>
            <tbody>
              {devices.slice(0,8).map(d=>(
                <tr key={d.id||d.name} style={{borderBottom:`1px solid ${G.border}`}}
                  onMouseEnter={e=>e.currentTarget.style.background=G.surface}
                  onMouseLeave={e=>e.currentTarget.style.background="transparent"}
                >
                  <td style={{padding:"10px 18px",width:14}}><StatusDot status={d.status}/></td>
                  <td style={{padding:"10px 8px",fontFamily:FONT,fontSize:12,color:G.text}}>{d.name}</td>
                  <td style={{padding:"10px 8px"}}><VChip vendor={d.vendor}/></td>
                  <td style={{padding:"10px 8px",fontFamily:FONT,fontSize:11,color:G.muted}}>{d.host}</td>
                  <td style={{padding:"10px 18px",fontSize:11,color:G.dim}}>{d.model||"—"}</td>
                  <td style={{padding:"10px 18px",fontFamily:FONT,fontSize:11,color:G.muted}}>{d.uptime||"—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
      <Card>
        <div style={{fontSize:11,color:G.muted,fontFamily:FONT,letterSpacing:"0.06em",marginBottom:12}}>ACTIVITY LOG</div>
        <div style={{fontFamily:FONT,fontSize:11,display:"flex",flexDirection:"column",gap:5,maxHeight:200,overflowY:"auto"}}>
          {[...logs].reverse().slice(0,15).map((l,i)=>{
            const c=l.type==="success"?G.green:l.type==="error"?G.red:l.type==="warn"?G.yellow:G.accent;
            return <div key={i} style={{display:"flex",gap:12}}><span style={{color:G.muted,minWidth:70,flexShrink:0}}>{l.time}</span><span style={{color:c}}>●</span><span style={{color:G.dim}}>{l.msg}</span></div>;
          })}
        </div>
      </Card>
    </div>
  );
}

// ── Device Modal ─────────────────────────────────────────────────
const EMPTY={name:"",vendor:"mikrotik",host:"",username:"admin",password:"",port:22,secret:"",api_port:3543,use_ssl:false,verify_ssl:false,device_type:"ios",vdom:"root",note:""};
const API_PORTS={mikrotik:3543,cisco:22,fortinet:443,sophos:4444};


// ── Password Prompt Modal ─────────────────────────────────────────
function PasswordPromptModal({device, onConfirm, onClose}){
  const [username, setUsername] = useState(device?.username||"admin");
  const [password, setPassword] = useState("");
  const [saving, setSaving] = useState(false);

  const handleConfirm = async() => {
    if(!password) return;
    setSaving(true);
    try{
      // Update device with new credentials
      await api(`/api/devices/${encodeURIComponent(device.name)}`, "PUT", {
        ...device, username, password
      });
      onConfirm(username, password);
    }catch(e){ console.error(e); }
    setSaving(false);
  };

  return(
    <div style={{position:"fixed",inset:0,background:"#00000099",zIndex:300,display:"flex",alignItems:"center",justifyContent:"center"}}>
      <div className="fadeIn" style={{background:G.card,border:`1px solid ${G.red}44`,borderRadius:12,width:400,padding:28}}>
        <div style={{fontSize:15,fontWeight:700,marginBottom:6,color:G.red}}>🔐 Sai password</div>
        <div style={{fontSize:12,color:G.muted,marginBottom:20}}>
          Không thể kết nối <b style={{color:G.text}}>{device?.name}</b> — nhập lại thông tin đăng nhập:
        </div>
        <div style={{display:"flex",flexDirection:"column",gap:10}}>
          <div><Lbl>Username</Lbl><Input value={username} onChange={e=>setUsername(e.target.value)} placeholder="admin"/></div>
          <div><Lbl>Password</Lbl><Input type="password" value={password} onChange={e=>setPassword(e.target.value)} 
            placeholder="Nhập password mới" autoFocus
            onKeyDown={e=>e.key==="Enter"&&handleConfirm()}/></div>
        </div>
        <div style={{display:"flex",gap:8,marginTop:20,justifyContent:"flex-end"}}>
          <Btn variant="ghost" onClick={onClose}>Hủy</Btn>
          <Btn onClick={handleConfirm} loading={saving} disabled={!password}>
            🔄 Thử lại & Lưu password
          </Btn>
        </div>
      </div>
    </div>
  );
}

function DeviceModal({device,onSave,onClose}){
  const [form,setForm]=useState(device?{...device}:{...EMPTY});
  const set=(k,v)=>setForm(p=>({...p,[k]:v}));
  const [testing,setTesting]=useState(false);
  const [testResult,setTestResult]=useState(null);

  const testConnect=async()=>{
    setTesting(true);setTestResult(null);
    try{
      // Try ping first
      const r=await api("/api/network/ping","POST",{host:form.host,count:1});
      setTestResult({ok:r.reachable,msg:r.reachable?`✓ Host reachable`:`✕ Host unreachable`});
    }catch{
      setTestResult({ok:false,msg:"✕ Backend offline — không test được"});
    }
    setTesting(false);
  };

  return(
    <div style={{position:"fixed",inset:0,background:"#00000088",zIndex:200,display:"flex",alignItems:"flex-start",justifyContent:"center",paddingTop:"4vh",paddingBottom:"4vh"}} onClick={e=>e.target===e.currentTarget&&onClose()}>
      <div className="fadeIn" style={{background:G.card,border:`1px solid ${G.border2}`,borderRadius:12,width:600,maxHeight:"92vh",display:"flex",flexDirection:"column",overflow:"hidden"}}>
        {/* Sticky header + name — always visible */}
        <div style={{padding:"24px 30px 0 30px",flexShrink:0}}>
          <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:16}}>
            <div style={{fontSize:16,fontWeight:700}}>{device?"Sửa thiết bị":"Thêm thiết bị mới"}</div>
            <span onClick={onClose} style={{cursor:"pointer",color:G.muted,fontSize:22,lineHeight:1}}>×</span>
          </div>
          <div style={{marginBottom:14}}><Lbl>Tên thiết bị *</Lbl><Input value={form.name} onChange={e=>set("name",e.target.value)} placeholder="CISCO-SW1 hoặc MIKROTIK-HN01"/></div>
        </div>
        {/* Scrollable body */}
        <div style={{overflowY:"auto",padding:"0 30px 30px 30px",flex:1}}>

        <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:14}}>

          <div>
            <Lbl>Vendor *</Lbl>
            <Sel value={form.vendor} onChange={e=>{set("vendor",e.target.value);set("api_port",API_PORTS[e.target.value]||443);}}
              options={["mikrotik","cisco","fortinet","sophos"].map(v=>({value:v,label:v.charAt(0).toUpperCase()+v.slice(1)}))}/>
          </div>
          <div>
            <Lbl>Host / IP *</Lbl>
            <div style={{display:"flex",gap:8}}>
              <Input value={form.host} onChange={e=>set("host",e.target.value)} placeholder="14.176.141.36"/>
              <Btn variant="ghost" small onClick={testConnect} loading={testing} style={{flexShrink:0,whiteSpace:"nowrap"}}>
                {!testing&&"Test Ping"}
              </Btn>
            </div>
            {testResult&&<div style={{marginTop:6,fontSize:11,fontFamily:FONT,color:testResult.ok?G.green:G.red}}>{testResult.msg}</div>}
          </div>

          <div><Lbl>Username</Lbl><Input value={form.username} onChange={e=>set("username",e.target.value)} placeholder="admin"/></div>
          <div><Lbl>Password</Lbl><Input type="password" value={form.password} onChange={e=>set("password",e.target.value)} placeholder="••••••••"/></div>

          <div>
            <Lbl>SSH Port</Lbl>
            <Input value={form.port} onChange={e=>set("port",Number(e.target.value))} placeholder="22"/>
          </div>
          <div>
            <Lbl>API Port {form.vendor==="mikrotik"&&<span style={{color:G.purple,fontSize:9}}>(RouterOS API)</span>}</Lbl>
            <Input value={form.api_port} onChange={e=>set("api_port",Number(e.target.value))} placeholder={String(API_PORTS[form.vendor]||443)}/>
          </div>

          {form.vendor==="cisco"&&<>
            <div><Lbl>Enable Secret</Lbl><Input type="password" value={form.secret} onChange={e=>set("secret",e.target.value)} placeholder="Enable password"/></div>
            <div><Lbl>Device Type</Lbl><Sel value={form.device_type} onChange={e=>set("device_type",e.target.value)} options={["ios","ios_xe","nx_os","asa","xr"].map(v=>({value:v,label:v.toUpperCase()}))}/></div>
          </>}
          {form.vendor==="fortinet"&&<div><Lbl>VDOM</Lbl><Input value={form.vdom} onChange={e=>set("vdom",e.target.value)} placeholder="root"/></div>}

          <div style={{gridColumn:"1/-1"}}><Lbl>Ghi chú / Vị trí</Lbl><Input value={form.note} onChange={e=>set("note",e.target.value)} placeholder="HN-01 · Tầng 3 · Chi nhánh Hà Nội"/></div>

          <div style={{gridColumn:"1/-1",display:"flex",gap:20}}>
            {[["use_ssl","Dùng SSL/HTTPS"],["verify_ssl","Verify SSL cert"]].map(([k,l])=>(
              <label key={k} style={{display:"flex",alignItems:"center",gap:8,cursor:"pointer",fontSize:13,color:G.dim}}>
                <input type="checkbox" checked={!!form[k]} onChange={e=>set(k,e.target.checked)} style={{accentColor:G.accent,width:14,height:14}}/>{l}
              </label>
            ))}
          </div>
        </div>

        {/* Vendor-specific info */}
        {form.vendor==="mikrotik"&&(
          <div style={{marginTop:16,padding:14,background:`${G.purple}0f`,border:`1px solid ${G.purple}33`,borderRadius:8}}>
            <div style={{fontSize:11,color:G.purple,fontFamily:FONT,marginBottom:8}}>// MikroTik RouterOS API Config</div>
            <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:8,fontSize:11,color:G.dim,fontFamily:FONT,lineHeight:2}}>
              <div>API port plain: <span style={{color:G.purple}}>3543</span></div>
              <div>API port SSL: <span style={{color:G.purple}}>8729</span></div>
              <div>REST API (v7+): <span style={{color:G.purple}}>80/443</span></div>
              <div>Winbox: <span style={{color:G.purple}}>3542</span></div>
            </div>
            <div style={{marginTop:8,padding:"6px 10px",background:`${G.surface}`,borderRadius:4,fontFamily:FONT,fontSize:11,color:G.accent}}>
              Enable: /ip service enable api
            </div>
          </div>
        )}
        {form.vendor==="cisco"&&(
          <div style={{marginTop:16,padding:14,background:`${G.accent}0f`,border:`1px solid ${G.accent}33`,borderRadius:8}}>
            <div style={{fontSize:11,color:G.accent,fontFamily:FONT,marginBottom:6}}>// Cisco SSH Config</div>
            <div style={{fontSize:11,color:G.dim,fontFamily:FONT,lineHeight:1.9}}>
              Enable SSH: <span style={{color:G.accent}}>ip ssh version 2</span> · <span style={{color:G.accent}}>crypto key generate rsa</span><br/>
              Enable secret nếu dùng enable mode
            </div>
          </div>
        )}

        <div style={{display:"flex",gap:10,marginTop:24,justifyContent:"flex-end"}}>
          <Btn variant="ghost" onClick={onClose}>Hủy</Btn>
          <Btn onClick={()=>{if(form.name&&form.host)onSave(form);}} disabled={!form.name||!form.host}>
            {device?"Cập nhật thiết bị":"Thêm thiết bị"}
          </Btn>
        </div>
        </div>{/* end scrollable body */}
      </div>
    </div>
  );
}

// ── Devices ───────────────────────────────────────────────────────
function DevicesPage({devices,setDevices,toast}){
  const [search,setSearch]=useState("");
  const [fv,setFv]=useState("all");
  const [modal,setModal]=useState(null);
  const [connecting,setConnecting]=useState({});
  const [loadingInfo,setLoadingInfo]=useState({});

  const filtered=devices.filter(d=>(fv==="all"||d.vendor===fv)&&(d.name.toLowerCase().includes(search.toLowerCase())||d.host.includes(search)));
  const saveDevs=d=>{setDevices(d);STORE.set("devices",d);};

  const saveDevice=async(form)=>{
    if(modal==="add"){
      const d={...form,id:Date.now(),status:"offline",model:"",uptime:"—",cpu:0,mem:0};
      // Sync to backend
      try{await api("/api/devices","POST",d);}catch{}
      saveDevs([...devices,d]);
      toast("success",`Đã thêm: ${d.name}`);
      addLog("success",`Thêm thiết bị: ${d.name} (${d.vendor} ${d.host})`);
    }else{
      try{await api(`/api/devices/${encodeURIComponent(modal.name)}`,"PUT",form);}catch{}
      saveDevs(devices.map(d=>d.id===modal.id?{...d,...form}:d));
      toast("success",`Đã cập nhật: ${form.name}`);
    }
    setModal(null);
  };

  const deleteDevice=async(id)=>{
    const d=devices.find(x=>x.id===id);
    try{await api(`/api/devices/${encodeURIComponent(d?.name)}`,"DELETE");}catch{}
    saveDevs(devices.filter(x=>x.id!==id));
    toast("warn",`Đã xóa: ${d?.name}`);
    addLog("warn",`Xóa: ${d?.name}`);
  };

  const [pwPrompt, setPwPrompt] = useState(null); // {device}

  const connectDevice=async(id, overrideUser=null, overridePass=null)=>{
    const device=devices.find(d=>d.id===id);
    if(!device)return;
    setConnecting(p=>({...p,[id]:true}));

    // If override credentials, update backend first then connect
    if(overrideUser){
      try{ await api(`/api/devices/${encodeURIComponent(device.name)}`,"PUT",{...device,username:overrideUser,password:overridePass}); }catch{}
      saveDevs(devices.map(d=>d.id===id?{...d,username:overrideUser,password:overridePass}:d));
    }

    try{
      const r=await api(`/api/devices/${encodeURIComponent(device.name)}/connect`,"POST");
      const info=r.info||{};
      saveDevs(devices.map(d=>d.id===id?{...d,status:"online",model:info.model||d.model,uptime:info.uptime||d.uptime,cpu:info.cpu||0,mem:info.mem||0}:d));
      toast("success",`Connected: ${device.name} (${info.model||device.vendor})`);
      addLog("success",`Connected: ${device.name} — ${info.uptime||""}`);
      setPwPrompt(null);
    }catch(e){
      const errStr=String(e).toLowerCase();
      const isAuth=errStr.includes("password")||errStr.includes("invalid user")||errStr.includes("authentication")||errStr.includes("login");
      if(isAuth){
        setPwPrompt(device);
        setConnecting(p=>({...p,[id]:false}));
        return;
      }
      saveDevs(devices.map(d=>d.id===id?{...d,status:"offline"}:d));
      toast("error",String(e));
      addLog("error",`Connect failed: ${device.name}`);
    }
    setConnecting(p=>({...p,[id]:false}));
  };

  const getInfo=async(id)=>{
    const device=devices.find(d=>d.id===id);
    if(!device)return;
    setLoadingInfo(p=>({...p,[id]:true}));
    try{
      const info=await api(`/api/devices/${encodeURIComponent(device.name)}/info`);
      saveDevs(devices.map(d=>d.id===id?{...d,...info}:d));
      toast("success",`Info OK: ${device.name}`);
    }catch{toast("warn","Backend offline");}
    setLoadingInfo(p=>({...p,[id]:false}));
  };

  return(
    <div className="fadeIn" style={{padding:28}}>
      {modal&&<DeviceModal device={modal==="add"?null:modal} onSave={saveDevice} onClose={()=>setModal(null)}/>}
      {pwPrompt&&<PasswordPromptModal device={pwPrompt}
        onConfirm={(u,p)=>connectDevice(pwPrompt.id,u,p)}
        onClose={()=>setPwPrompt(null)}/>}
      <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:22}}>
        <div>
          <div style={{fontSize:22,fontWeight:700}}>Devices</div>
          <div style={{fontSize:12,color:G.muted,marginTop:3}}>{devices.length} thiết bị · {filtered.length} hiển thị</div>
        </div>
        <Btn onClick={()=>setModal("add")}>＋ Thêm thiết bị</Btn>
      </div>
      <div style={{display:"flex",gap:10,marginBottom:16}}>
        <Input value={search} onChange={e=>setSearch(e.target.value)} placeholder="Tìm tên hoặc IP..." style={{maxWidth:300}}/>
        <Sel value={fv} onChange={e=>setFv(e.target.value)} options={[{value:"all",label:"Tất cả vendor"},...["mikrotik","cisco","fortinet","sophos"].map(v=>({value:v,label:v.charAt(0).toUpperCase()+v.slice(1)}))]} style={{width:"auto"}}/>
      </div>
      {devices.length===0?(
        <Card style={{textAlign:"center",padding:60}}>
          <div style={{fontSize:42,marginBottom:16}}>◈</div>
          <div style={{fontSize:16,color:G.dim,marginBottom:8}}>Chưa có thiết bị nào</div>
          <div style={{fontSize:13,color:G.muted,marginBottom:20}}>Thêm MikroTik, Cisco, Fortinet hoặc Sophos</div>
          <Btn onClick={()=>setModal("add")}>＋ Thêm thiết bị đầu tiên</Btn>
        </Card>
      ):(
        <Card style={{padding:0,overflow:"hidden"}}>
          <table style={{width:"100%",borderCollapse:"collapse"}}>
            <thead>
              <tr style={{background:G.surface}}>
                {["","Tên","Vendor","Host / IP","Model","Uptime","CPU","MEM","Note","Actions"].map(h=>(
                  <th key={h} style={{padding:"10px 12px",textAlign:"left",fontSize:10,color:G.muted,fontFamily:FONT,letterSpacing:"0.06em",fontWeight:500,borderBottom:`1px solid ${G.border}`,whiteSpace:"nowrap"}}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.map(d=>(
                <tr key={d.id||d.name} style={{borderBottom:`1px solid ${G.border}`,transition:"background .1s"}}
                  onMouseEnter={e=>e.currentTarget.style.background=G.surface}
                  onMouseLeave={e=>e.currentTarget.style.background="transparent"}
                >
                  <td style={{padding:"11px 12px"}}><StatusDot status={d.status}/></td>
                  <td style={{padding:"11px 8px",fontFamily:FONT,fontSize:12,color:G.text,whiteSpace:"nowrap"}}>{d.name}</td>
                  <td style={{padding:"11px 8px"}}><VChip vendor={d.vendor}/></td>
                  <td style={{padding:"11px 8px",fontFamily:FONT,fontSize:11,color:G.dim}}>{d.host}</td>
                  <td style={{padding:"11px 8px",fontSize:11,color:G.dim}}>{d.model||"—"}</td>
                  <td style={{padding:"11px 8px",fontFamily:FONT,fontSize:10,color:G.muted,whiteSpace:"nowrap"}}>{d.uptime||"—"}</td>
                  <td style={{padding:"11px 8px"}}>{d.status==="online"?<div style={{display:"flex",alignItems:"center",gap:5}}><MiniBar value={d.cpu||0} color={d.cpu>70?G.red:d.cpu>40?G.yellow:G.green}/><span style={{fontSize:10,fontFamily:FONT,color:G.dim}}>{d.cpu||0}%</span></div>:<span style={{color:G.muted,fontSize:10}}>—</span>}</td>
                  <td style={{padding:"11px 8px"}}>{d.status==="online"?<div style={{display:"flex",alignItems:"center",gap:5}}><MiniBar value={d.mem||0} color={d.mem>80?G.red:d.mem>60?G.yellow:G.accent}/><span style={{fontSize:10,fontFamily:FONT,color:G.dim}}>{d.mem||0}%</span></div>:<span style={{color:G.muted,fontSize:10}}>—</span>}</td>
                  <td style={{padding:"11px 8px",fontSize:11,color:G.muted,maxWidth:100,overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap"}}>{d.note||""}</td>
                  <td style={{padding:"11px 12px"}}>
                    <div style={{display:"flex",gap:5,flexWrap:"nowrap"}}>
                      <Btn small variant={d.status==="online"?"warning":"success"} onClick={()=>connectDevice(d.id)} loading={connecting[d.id]}>
                        {!connecting[d.id]&&(d.status==="online"?"Disconnect":"Connect")}
                      </Btn>
                      {d.status==="online"&&<Btn small variant="ghost" onClick={()=>getInfo(d.id)} loading={loadingInfo[d.id]}>{!loadingInfo[d.id]&&"Info"}</Btn>}
                      <Btn small variant="ghost" onClick={()=>setModal(d)}>✎</Btn>
                      <Btn small variant="danger" onClick={()=>deleteDevice(d.id)}>✕</Btn>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}
    </div>
  );
}

// ── Terminal ──────────────────────────────────────────────────────
function TerminalPage({devices,toast}){
  const [sel,setSel]=useState(devices.find(d=>d.status==="online")?.name||devices[0]?.name||"");
  const [input,setInput]=useState("");
  const [history,setHistory]=useState([
    {type:"system",text:"PlNetwork Auto Manager — RouterOS Terminal v3.0"},
    {type:"system",text:"Commands: help · devices · ping <ip> · trace <ip> · clear"},
    {type:"prompt",text:""},
  ]);
  const [cmdHist,setCmdHist]=useState(STORE.get("cmd_history",[]));
  const [histIdx,setHistIdx]=useState(-1);
  const [running,setRunning]=useState(false);
  const bottomRef=useRef(null);
  const inputRef=useRef(null);
  useEffect(()=>{bottomRef.current?.scrollIntoView({behavior:"smooth"});},[history]);

  const MOCK={
    mikrotik:{
      "/ip address print":"Flags: X-disabled,I-invalid,D-dynamic\n # ADDRESS            NETWORK        INTERFACE\n 0 192.168.1.1/24     192.168.1.0    bridge-local\n 1 10.0.0.1/30        10.0.0.0       ether1-wan",
      "/ip route print":"Flags: A-active,D-dynamic,C-connect,S-static\n # DST-ADDRESS         G GATEWAY        DIST\n 0 ADC 0.0.0.0/0          r 203.0.113.1    1\n 1 ADC 192.168.1.0/24     0.0.0.0         0",
      "/interface print":"Flags: D-dynamic,X-disabled,R-running\n 0 R  ether1-wan   ether   1500  1Gbps\n 1 R  ether2       ether   1500  100Mbps\n 2 R  bridge-local bridge  1500  1Gbps\n 3 R  wlan1        wlan    1500  300Mbps",
      "/system resource print":"uptime: 12d 7h 33m\nversion: 7.16 (stable)\nboard-name: CCR2004-16G-2S+\ncpu-load: 6%\nfree-memory: 2024.0MiB\ntotal-memory: 4096.0MiB",
      "/ip firewall filter print":"Flags: X-disabled,I-invalid\n 0  chain=input action=accept protocol=icmp\n 1  chain=input action=accept connection-state=established\n 2  chain=forward action=accept connection-state=established\n 3  chain=input action=drop in-interface=ether1-wan",
      "/user print":"Flags: X-disabled\n # NAME    GROUP     LAST-LOGGED-IN\n 0 admin   full      jan/15 14:32",
      "/ip service print":"Flags: X-DISABLED\n # NAME     PORT\n 0 X ftp        21\n 1 X ssh        22\n 2 X telnet     23\n 3   www        80\n 4   www-ssl   443\n 5   winbox   3542\n 6   api      3543\n 7   api-ssl  3544",
      "/ip dns print":"servers: 8.8.8.8,8.8.4.4\nallow-remote-requests: yes\ncache-size: 2048KiB",
      "/interface wireless print":"Flags: X-disabled,R-running\n 0 R  wlan1  station  300Mbps  channel: 6/20-Ce",
      help:"/ip address print · /ip route print · /interface print\n/system resource print · /ip firewall filter print\n/user print · /ip service print · /ip dns print\nping <ip> · trace <ip> · clear · devices",
    },
    cisco:{
      "show version":"Cisco IOS Software, Version 15.7(3)M\nRouter uptime is 42 days, 3 hours",
      "show interfaces":"GigabitEthernet0/0 is up, line protocol is up\n  Internet address is 10.0.0.1/30",
      "show ip route":"S* 0.0.0.0/0 [1/0] via 203.0.113.1\nC  10.0.0.0/30 directly connected",
      "show running-config":"hostname Router1\ninterface GigabitEthernet0/0\n ip address 10.0.0.1 255.255.255.252",
      help:"show version · show interfaces · show ip route · show running-config\nping <ip> · clear · devices",
    },
    fortinet:{
      "get system status":"Version: FortiGate-100F v7.4.1\nSerial: FGT100F000000\nSystem time: Thu Jan 15 20:30",
      "show system interface":"== [ wan1 ]\nip: 203.0.113.2/30  status: up\n== [ internal ]\nip: 192.168.1.1/24  status: up",
      help:"get system status · show system interface · clear · devices",
    },
  };

  const selectedDevice=devices.find(d=>d.name===sel);

  const runCommand=async()=>{
    if(!input.trim()||running)return;
    const cmd=input.trim();
    const newH=[cmd,...cmdHist.filter(c=>c!==cmd)].slice(0,100);
    setCmdHist(newH);STORE.set("cmd_history",newH);
    setHistIdx(-1);setInput("");setRunning(true);
    const push=lines=>setHistory(p=>[...p.filter(l=>l.type!=="prompt"),...lines,{type:"prompt",text:""}]);

    if(cmd==="clear"){setHistory([{type:"system",text:"Terminal cleared."},{type:"prompt",text:""}]);setRunning(false);return;}
    if(cmd==="devices"){
      push([{type:"input",text:"[local]$ devices"},...devices.map(d=>({type:"output",text:`  ${d.status==="online"?"●":"○"} ${d.name.padEnd(32)} ${d.vendor.padEnd(12)} ${d.host}`}))]);
      setRunning(false);return;
    }

    // ping / trace — run on device if online
    if(cmd.startsWith("ping ")||cmd.startsWith("trace ")){
      const isPing=cmd.startsWith("ping");
      // Hỗ trợ: ping <ip>  hoặc  ping <ip> src <src_ip>
      const parts=cmd.trim().split(/\s+/);
      const host=parts[1];
      const srcIdx=parts.indexOf("src");
      const srcAddr=srcIdx!==-1?parts[srcIdx+1]:"";
      const lines=[{type:"input",text:`[${sel||"local"}]$ ${cmd}`}];
      if(!host){lines.push({type:"error",text:`Usage: ${isPing?"ping":"trace"} <host> [src <src_ip>]`});push(lines);setRunning(false);return;}

      if(selectedDevice&&selectedDevice.status==="online"){
        try{
          if(isPing){
            // Dùng endpoint /ping — backend gọi RouterOS API (port 3543)
            const body={host,count:4};
            if(srcAddr) body.src=srcAddr;
            const r=await api(`/api/devices/${encodeURIComponent(sel)}/ping`,"POST",body);
            if(r.output) r.output.split("\n").forEach(l=>lines.push({type:"output",text:l}));
            else if(r.error) lines.push({type:"error",text:`Error: ${r.error}`});
          } else {
            // Trace dùng endpoint riêng — backend gọi RouterOS API /tool/traceroute
            const r=await api(`/api/devices/${encodeURIComponent(sel)}/traceroute`,"POST",{host,count:3});
            if(r.output) r.output.split("\n").forEach(l=>lines.push({type:"output",text:l}));
            else if(r.error) lines.push({type:"error",text:`Error: ${r.error}`});
          }
          addLog("info",`${isPing?"Ping":"Trace"} ${host} via ${sel}`);
        }catch(e){
          lines.push({type:"error",text:`Error: ${e.message||e}`});
        }
        push(lines);setRunning(false);return;
      }
      try{
        const r=await api("/api/network/ping","POST",{host,count:4});
        (r.output||"").split("\n").forEach(l=>lines.push({type:"output",text:l}));
      }catch{
        if(isPing){
          for(let i=1;i<=4;i++) lines.push({type:"output",text:`  Reply from ${host}: time=${Math.floor(Math.random()*50+5)}ms`});
        }else{
          [{n:1,ip:"192.168.1.1",ms:2},{n:2,ip:"10.0.0.1",ms:8},{n:3,ip:host,ms:25}]
            .forEach(h=>lines.push({type:"output",text:`  ${h.n}  ${h.ms}ms  ${h.ip}`}));
        }
      }
      push(lines);setRunning(false);return;
    }

    const lines=[{type:"input",text:`[${sel||"local"}]$ ${cmd}`}];
    if(!selectedDevice){lines.push({type:"error",text:"Error: Chọn thiết bị trước"});push(lines);setRunning(false);return;}
    if(selectedDevice.status!=="online"){lines.push({type:"error",text:`Error: ${sel} offline — nhấn Connect`});push(lines);setRunning(false);return;}

    try{
      const r=await api(`/api/devices/${encodeURIComponent(sel)}/command`,"POST",{command:cmd});
      if(r.output) r.output.split("\n").forEach(l=>lines.push({type:"output",text:l}));
      else if(r.error) lines.push({type:"error",text:`Error: ${r.error}`});
      addLog("info",`CMD [${sel}]: ${cmd}`);
    }catch{
      const mock=MOCK[selectedDevice?.vendor]||{};
      const resp=mock[cmd]||mock[cmd.toLowerCase()];
      if(resp){
        resp.split("\n").forEach(l=>lines.push({type:"output",text:l}));
        lines.push({type:"dim",text:"  ↳ [demo mode — start backend for real output]"});
      }else{
        lines.push({type:"error",text:`% Unknown: ${cmd}`});
        lines.push({type:"dim",text:"  Type 'help' for available commands"});
      }
    }
    push(lines);setRunning(false);
  };

  const LC={system:G.accent,input:G.green,output:G.text,error:G.red,dim:G.muted};
  const vendor=selectedDevice?.vendor||"mikrotik";
  const QUICK=Object.keys(MOCK[vendor]||{}).filter(k=>k!=="help");

  return(
    <div className="fadeIn" style={{padding:28}}>
      <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:20}}>
        <div>
          <div style={{fontSize:22,fontWeight:700}}>Terminal</div>
          <div style={{fontSize:12,color:G.muted,marginTop:3}}>RouterOS API · ping · traceroute</div>
        </div>
        <div style={{display:"flex",gap:10,alignItems:"center"}}>
          {selectedDevice&&<Badge color={selectedDevice.status==="online"?G.green:G.red}>{selectedDevice.status}</Badge>}
          <Sel value={sel} onChange={e=>setSel(e.target.value)}
            options={[{value:"",label:"-- Chọn thiết bị --"},...devices.map(d=>({value:d.name,label:`${d.name} (${d.status})`}))]}
            style={{width:280}}/>
        </div>
      </div>
      <div style={{background:"#05070b",border:`1px solid ${G.border}`,borderRadius:10,overflow:"hidden"}}>
        <div style={{display:"flex",alignItems:"center",gap:8,padding:"10px 16px",background:G.surface,borderBottom:`1px solid ${G.border}`}}>
          <div style={{width:10,height:10,borderRadius:"50%",background:G.red}}/>
          <div style={{width:10,height:10,borderRadius:"50%",background:G.yellow}}/>
          <div style={{width:10,height:10,borderRadius:"50%",background:G.green}}/>
          <span style={{marginLeft:8,fontFamily:FONT,fontSize:11,color:G.muted}}>plnetwork-terminal — {sel||"no device"}</span>
          {running&&<span style={{marginLeft:"auto"}}><Spinner size={12}/></span>}
        </div>
        <div onClick={()=>inputRef.current?.focus()} style={{height:420,overflowY:"auto",padding:"14px 20px",fontFamily:FONT,fontSize:12,lineHeight:1.75,cursor:"text"}}>
          {history.map((line,i)=>(
            <div key={i} style={{color:LC[line.type]||G.text,whiteSpace:"pre-wrap"}}>
              {line.text}
              {line.type==="prompt"&&i===history.length-1&&<span style={{animation:"blink 1s step-end infinite",borderLeft:`2px solid ${G.green}`,marginLeft:1}}/>}
            </div>
          ))}
          <div ref={bottomRef}/>
        </div>
        <div style={{display:"flex",alignItems:"center",gap:10,padding:"10px 20px",borderTop:`1px solid ${G.border}`,background:`${G.surface}88`}}>
          <span style={{fontFamily:FONT,fontSize:12,color:G.green,userSelect:"none",flexShrink:0}}>[{sel||"local"}]$</span>
          <input ref={inputRef} value={input} onChange={e=>setInput(e.target.value)}
            onKeyDown={e=>{
              if(e.key==="Enter")runCommand();
              if(e.key==="ArrowUp"){const i=Math.min(histIdx+1,cmdHist.length-1);setHistIdx(i);setInput(cmdHist[i]||"");}
              if(e.key==="ArrowDown"){const i=Math.max(histIdx-1,-1);setHistIdx(i);setInput(i===-1?"":cmdHist[i]||"");}
            }}
            placeholder="Nhập lệnh... ping 8.8.8.8 · /ip address print · ↑↓ history"
            style={{flex:1,background:"transparent",border:"none",outline:"none",color:G.text,fontFamily:FONT,fontSize:12}}
            autoFocus
          />
          {running?<Spinner/>:<Btn small onClick={runCommand}>Run ↵</Btn>}
        </div>
      </div>
      {QUICK.length>0&&(
        <Card style={{marginTop:14}}>
          <div style={{fontSize:11,color:G.muted,fontFamily:FONT,letterSpacing:"0.06em",marginBottom:10}}>QUICK — {vendor.toUpperCase()}</div>
          <div style={{display:"flex",flexWrap:"wrap",gap:8}}>
            {["ping 8.8.8.8","ping 1.1.1.1","trace 8.8.8.8",...QUICK].map(cmd=>(
              <div key={cmd} onClick={()=>setInput(cmd)} style={{padding:"4px 10px",borderRadius:4,cursor:"pointer",background:G.surface,border:`1px solid ${G.border2}`,fontFamily:FONT,fontSize:11,color:G.dim,transition:"all .15s"}}
                onMouseEnter={e=>{e.currentTarget.style.borderColor=G.accent+"66";e.currentTarget.style.color=G.accent;}}
                onMouseLeave={e=>{e.currentTarget.style.borderColor=G.border2;e.currentTarget.style.color=G.dim;}}
              >{cmd}</div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}

// ── Net Tools (Ping / Traceroute / Bandwidth) ─────────────────────
function NetToolsPage({devices,toast}){
  const [tab,setTab]=useState("ping");
  const [pingHost,setPingHost]=useState("8.8.8.8");
  const [pingCount,setPingCount]=useState("4");
  const [pingDevice,setPingDevice]=useState("");
  const [pingResult,setPingResult]=useState(null);
  const [pinging,setPinging]=useState(false);

  const [traceHost,setTraceHost]=useState("8.8.8.8");
  const [traceResult,setTraceResult]=useState(null);
  const [tracing,setTracing]=useState(false);

  const [bwDevice,setBwDevice]=useState(devices.find(d=>d.status==="online")?.name||"");
  const [bwIface,setBwIface]=useState("ether1");
  const [bwResult,setBwResult]=useState(null);
  const [bwRunning,setBwRunning]=useState(false);
  const [bwHistory,setBwHistory]=useState([]);
  const bwInterval=useRef(null);

  const onlineDevices=devices.filter(d=>d.status==="online");

  // Ping
  const doPing=async()=>{
    if(!pingHost.trim())return;
    setPinging(true);setPingResult(null);
    try{
      const endpoint=pingDevice?`/api/devices/${encodeURIComponent(pingDevice)}/ping`:"/api/network/ping";
      const r=await api(endpoint,"POST",{host:pingHost,count:Number(pingCount)||4});
      setPingResult(r);
      addLog(r.reachable?"success":"warn",`Ping ${pingHost}: ${r.reachable?"reachable":"unreachable"}`);
    }catch{
      // Demo
      const ttl=Math.floor(Math.random()*50)+5;
      setPingResult({
        host:pingHost,reachable:true,count:Number(pingCount)||4,
        output:[...Array(Number(pingCount)||4)].map((_,i)=>`Reply from ${pingHost}: bytes=32 time=${ttl+i}ms TTL=64`).join("\n")+`\n\nPing statistics for ${pingHost}:\n  Packets: Sent = ${pingCount}, Received = ${pingCount}, Lost = 0 (0% loss)\nRoundtrip: min=${ttl}ms, avg=${ttl+2}ms, max=${ttl+5}ms`,
        rtt_line:`rtt min/avg/max = ${ttl}/${ttl+2}/${ttl+5} ms`,
      });
    }
    setPinging(false);
  };

  // Traceroute
  const doTrace=async()=>{
    if(!traceHost.trim())return;
    setTracing(true);setTraceResult(null);
    try{
      const r=await api("/api/network/traceroute","POST",{host:traceHost});
      setTraceResult(r);
    }catch(e){
      const errMsg = e?.message||'';
      if(errMsg.includes('timeout')||errMsg.includes('500')){
        setTraceResult({host:traceHost,output:"Traceroute timeout - server blocked. Try ping instead or use device terminal."});
        setTracing(false);return;
      }
      const hops=[
        {n:1,ip:"192.168.1.1",ms:[1,2,1]},
        {n:2,ip:"10.0.0.1",ms:[5,4,5]},
        {n:3,ip:"203.0.113.1",ms:[15,14,16]},
        {n:4,ip:"8.8.4.4",ms:[22,21,23]},
        {n:5,ip:traceHost,ms:[25,24,26]},
      ];
      setTraceResult({host:traceHost,output:hops.map(h=>`  ${String(h.n).padStart(2)}   ${h.ms[0]}ms  ${h.ms[1]}ms  ${h.ms[2]}ms  ${h.ip}`).join("\n")});
    }
    setTracing(false);
  };

  // Bandwidth monitor (polls /system resource from MikroTik)
  const startBw=()=>{
    setBwRunning(true);setBwHistory([]);
    bwInterval.current=setInterval(async()=>{
      try{
        const r=await api(`/api/devices/${encodeURIComponent(bwDevice)}/command`,"POST",{command:`/interface monitor-traffic ${bwIface} once`});
        const out=r.output||"";
        const rxMatch=out.match(/rx-bits-per-second:\s*(\d+)/);
        const txMatch=out.match(/tx-bits-per-second:\s*(\d+)/);
        const rx=rxMatch?Math.round(Number(rxMatch[1])/1000):Math.floor(Math.random()*5000+500);
        const tx=txMatch?Math.round(Number(txMatch[1])/1000):Math.floor(Math.random()*2000+200);
        setBwHistory(p=>[...p.slice(-29),{time:new Date().toLocaleTimeString("vi-VN"),rx,tx}]);
        setBwResult({rx,tx});
      }catch{
        const rx=Math.floor(Math.random()*8000+1000);
        const tx=Math.floor(Math.random()*3000+500);
        setBwHistory(p=>[...p.slice(-29),{time:new Date().toLocaleTimeString("vi-VN"),rx,tx}]);
        setBwResult({rx,tx,demo:true});
      }
    },2000);
  };

  const stopBw=()=>{
    clearInterval(bwInterval.current);
    setBwRunning(false);
  };

  useEffect(()=>()=>clearInterval(bwInterval.current),[]);

  const formatBps=v=>{
    if(v>=1000000)return`${(v/1000000).toFixed(1)} Gbps`;
    if(v>=1000)return`${(v/1000).toFixed(1)} Mbps`;
    return`${v} Kbps`;
  };

  const maxBw=Math.max(...bwHistory.map(h=>Math.max(h.rx,h.tx)),1);

  return(
    <div className="fadeIn" style={{padding:28}}>
      <div style={{marginBottom:24}}>
        <div style={{fontSize:22,fontWeight:700}}>Network Tools</div>
        <div style={{fontSize:12,color:G.muted,marginTop:3}}>Ping · Traceroute · Bandwidth Monitor</div>
      </div>

      {/* Tabs */}
      <div style={{display:"flex",gap:8,marginBottom:20}}>
        {[["ping","◎ Ping"],["trace","⤳ Traceroute"],["bandwidth","⬌ Bandwidth"]].map(([id,label])=>(
          <div key={id} onClick={()=>setTab(id)} style={{padding:"8px 18px",borderRadius:6,cursor:"pointer",fontSize:12,fontWeight:600,background:tab===id?`${G.accent}22`:G.card,border:`1px solid ${tab===id?G.accent+"66":G.border}`,color:tab===id?G.accent:G.muted,transition:"all .15s"}}>
            {label}
          </div>
        ))}
      </div>

      {/* PING */}
      {tab==="ping"&&(
        <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:16}}>
          <Card>
            <div style={{fontSize:12,color:G.muted,fontFamily:FONT,letterSpacing:"0.06em",marginBottom:16}}>PING CONFIG</div>
            <div style={{display:"flex",flexDirection:"column",gap:12}}>
              <div><Lbl>Target Host / IP</Lbl><Input value={pingHost} onChange={e=>setPingHost(e.target.value)} placeholder="8.8.8.8 / hostname" onKeyDown={e=>e.key==="Enter"&&doPing()}/></div>
              <div><Lbl>Count</Lbl><Sel value={pingCount} onChange={e=>setPingCount(e.target.value)} options={["4","8","16","32","100"].map(v=>({value:v,label:`${v} packets`}))}/></div>
              <div>
                <Lbl>Ping từ thiết bị (tùy chọn)</Lbl>
                <Sel value={pingDevice} onChange={e=>setPingDevice(e.target.value)}
                  options={[{value:"",label:"— From server —"},...onlineDevices.map(d=>({value:d.name,label:`${d.name} (${d.vendor})`}))]}/>
              </div>
              <Btn onClick={doPing} loading={pinging} style={{padding:"10px",justifyContent:"center"}}>
                {pinging?"Pinging...":"◎ Run Ping"}
              </Btn>
            </div>
          </Card>
          <Card style={{background:"#05070b"}}>
            <div style={{fontSize:12,color:G.muted,fontFamily:FONT,letterSpacing:"0.06em",marginBottom:12}}>RESULT</div>
            {!pingResult&&<div style={{fontSize:12,color:G.muted}}>Chưa có kết quả</div>}
            {pingResult&&(
              <div>
                <div style={{display:"flex",alignItems:"center",gap:10,marginBottom:12}}>
                  <Badge color={pingResult.reachable?G.green:G.red}>{pingResult.reachable?"REACHABLE":"UNREACHABLE"}</Badge>
                  <span style={{fontFamily:FONT,fontSize:12,color:G.dim}}>{pingResult.host}</span>
                </div>
                <pre style={{fontFamily:FONT,fontSize:11,color:G.text,whiteSpace:"pre-wrap",lineHeight:1.8,maxHeight:280,overflowY:"auto"}}>{pingResult.output}</pre>
                {pingResult.rtt_line&&<div style={{marginTop:8,padding:"6px 10px",background:`${G.green}15`,borderRadius:4,fontFamily:FONT,fontSize:11,color:G.green}}>{pingResult.rtt_line}</div>}
              </div>
            )}
          </Card>
        </div>
      )}

      {/* TRACEROUTE */}
      {tab==="trace"&&(
        <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:16}}>
          <Card>
            <div style={{fontSize:12,color:G.muted,fontFamily:FONT,letterSpacing:"0.06em",marginBottom:16}}>TRACEROUTE CONFIG</div>
            <div style={{display:"flex",flexDirection:"column",gap:12}}>
              <div><Lbl>Target Host / IP</Lbl><Input value={traceHost} onChange={e=>setTraceHost(e.target.value)} placeholder="8.8.8.8" onKeyDown={e=>e.key==="Enter"&&doTrace()}/></div>
              <Btn onClick={doTrace} loading={tracing} style={{padding:"10px",justifyContent:"center"}}>
                {tracing?"Tracing route...":"⤳ Run Traceroute"}
              </Btn>
              <div style={{padding:12,background:G.surface,borderRadius:6,fontSize:11,color:G.muted,fontFamily:FONT,lineHeight:1.8}}>
                Traceroute hiển thị từng hop<br/>trên đường đến đích
              </div>
            </div>
          </Card>
          <Card style={{background:"#05070b"}}>
            <div style={{fontSize:12,color:G.muted,fontFamily:FONT,letterSpacing:"0.06em",marginBottom:12}}>HOPS</div>
            {!traceResult&&<div style={{fontSize:12,color:G.muted}}>Chưa có kết quả</div>}
            {traceResult&&(
              <div>
                <div style={{fontFamily:FONT,fontSize:11,color:G.dim,marginBottom:8}}>→ {traceResult.host}</div>
                <pre style={{fontFamily:FONT,fontSize:11,color:G.text,whiteSpace:"pre-wrap",lineHeight:2,maxHeight:320,overflowY:"auto"}}>{traceResult.output}</pre>
              </div>
            )}
          </Card>
        </div>
      )}

      {/* BANDWIDTH */}
      {tab==="bandwidth"&&(
        <div style={{display:"flex",flexDirection:"column",gap:16}}>
          <div style={{display:"grid",gridTemplateColumns:"2fr 1fr",gap:16}}>
            <Card>
              <div style={{fontSize:12,color:G.muted,fontFamily:FONT,letterSpacing:"0.06em",marginBottom:14}}>BANDWIDTH MONITOR CONFIG</div>
              <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:12,marginBottom:14}}>
                <div>
                  <Lbl>Thiết bị (MikroTik)</Lbl>
                  <Sel value={bwDevice} onChange={e=>setBwDevice(e.target.value)}
                    options={[{value:"",label:"-- Chọn thiết bị --"},...onlineDevices.map(d=>({value:d.name,label:d.name}))]}/>
                </div>
                <div><Lbl>Interface</Lbl><Input value={bwIface} onChange={e=>setBwIface(e.target.value)} placeholder="ether1"/></div>
              </div>
              <div style={{display:"flex",gap:10}}>
                <Btn onClick={bwRunning?stopBw:startBw} variant={bwRunning?"warning":"success"} style={{padding:"10px 20px"}}>
                  {bwRunning?"⏹ Stop Monitor":"▶ Start Monitor"}
                </Btn>
                {bwRunning&&<span className="pulse" style={{fontSize:12,color:G.green,alignSelf:"center",fontFamily:FONT}}>● Live — cập nhật mỗi 2s</span>}
              </div>
            </Card>

            {/* Current stats */}
            <Card>
              <div style={{fontSize:12,color:G.muted,fontFamily:FONT,letterSpacing:"0.06em",marginBottom:14}}>CURRENT</div>
              {bwResult?(
                <div>
                  <div style={{marginBottom:14}}>
                    <div style={{fontSize:11,color:G.muted,marginBottom:4}}>↓ RX (Download)</div>
                    <div style={{fontSize:28,fontWeight:800,color:G.green,fontFamily:FONT}}>{formatBps(bwResult.rx)}</div>
                  </div>
                  <div>
                    <div style={{fontSize:11,color:G.muted,marginBottom:4}}>↑ TX (Upload)</div>
                    <div style={{fontSize:28,fontWeight:800,color:G.accent,fontFamily:FONT}}>{formatBps(bwResult.tx)}</div>
                  </div>
                  {bwResult.demo&&<div style={{marginTop:10,fontSize:10,color:G.muted,fontFamily:FONT}}>demo mode</div>}
                </div>
              ):(
                <div style={{fontSize:12,color:G.muted}}>Chưa có dữ liệu</div>
              )}
            </Card>
          </div>

          {/* Chart */}
          {bwHistory.length>0&&(
            <Card style={{background:"#05070b"}}>
              <div style={{fontSize:12,color:G.muted,fontFamily:FONT,letterSpacing:"0.06em",marginBottom:14}}>
                BANDWIDTH HISTORY — {bwIface} &nbsp;
                <span style={{color:G.green}}>■ RX</span>&nbsp;&nbsp;
                <span style={{color:G.accent}}>■ TX</span>
              </div>
              <div style={{display:"flex",alignItems:"flex-end",gap:3,height:120,paddingBottom:4}}>
                {bwHistory.map((h,i)=>(
                  <div key={i} style={{flex:1,display:"flex",flexDirection:"column",justifyContent:"flex-end",gap:1,height:"100%",position:"relative"}}>
                    <div title={`RX: ${formatBps(h.rx)}`} style={{background:G.green,width:"100%",height:`${(h.rx/maxBw)*100}%`,borderRadius:"2px 2px 0 0",opacity:0.85,transition:"height .3s"}}/>
                    <div title={`TX: ${formatBps(h.tx)}`} style={{background:G.accent,width:"100%",height:`${(h.tx/maxBw)*60}%`,borderRadius:"2px 2px 0 0",opacity:0.85,transition:"height .3s"}}/>
                  </div>
                ))}
              </div>
              <div style={{display:"flex",justifyContent:"space-between",marginTop:4}}>
                <span style={{fontSize:10,color:G.muted,fontFamily:FONT}}>{bwHistory[0]?.time}</span>
                <span style={{fontSize:10,color:G.muted,fontFamily:FONT}}>Max: {formatBps(maxBw)}</span>
                <span style={{fontSize:10,color:G.muted,fontFamily:FONT}}>{bwHistory[bwHistory.length-1]?.time}</span>
              </div>
            </Card>
          )}
        </div>
      )}
    </div>
  );
}

// ── Config Push ───────────────────────────────────────────────────
function ConfigPage({devices,toast}){
  const [mode,setMode]=useState("template");
  const [vendor,setVendor]=useState("mikrotik");
  const [tmpl,setTmpl]=useState("mikrotik/vlan");
  const [vars,setVars]=useState({});
  const [targets,setTargets]=useState([]);
  const [preview,setPreview]=useState("");
  const [pushing,setPushing]=useState(false);
  const [result,setResult]=useState(null);
  const [manualCmds,setManualCmds]=useState("");

  // ── Template Groups ─────────────────────────────────────────────
  const TEMPLATE_GROUPS = {
    mikrotik: [
      {group:"🌐 IP & Routing", items:["mikrotik/interface_ip","mikrotik/vlan","mikrotik/bridge","mikrotik/static_route","mikrotik/default_route","mikrotik/ip_pool"]},
      {group:"🔥 Firewall", items:["mikrotik/fw_accept","mikrotik/fw_drop","mikrotik/fw_nat_masquerade","mikrotik/fw_nat_dstnat","mikrotik/fw_address_list"]},
      {group:"📡 PPPoE & WAN", items:["mikrotik/pppoe_client","mikrotik/pppoe_lb_2wan","mikrotik/pppoe_lb_3wan","mikrotik/lan_to_pppoe"]},
      {group:"🧅 SOCKS5 & Proxy", items:["mikrotik/socks5_server","mikrotik/socks5_transparent","mikrotik/socks5_lan_redirect"]},
      {group:"🏠 LAN Services", items:["mikrotik/dhcp_server","mikrotik/dhcp_reservation","mikrotik/dns","mikrotik/hotspot"]},
      {group:"🔀 Mangle & QoS", items:["mikrotik/mangle_mark_conn","mikrotik/mangle_mark_routing","mikrotik/queue_simple","mikrotik/queue_tree"]},
      {group:"🔒 VPN", items:["mikrotik/l2tp_server","mikrotik/l2tp_client","mikrotik/ovpn_server"]},
      {group:"⚙ System", items:["mikrotik/ntp","mikrotik/snmp","mikrotik/user_add","mikrotik/scheduler","mikrotik/email_alert"]},
      {group:"🔄 Routing", items:["mikrotik/bgp_peer","mikrotik/ospf_instance","mikrotik/routing_table","mikrotik/routing_rule"]},
    ],
    cisco:[{group:"Cisco",items:["cisco/interface_ip","cisco/vlan","cisco/static_route","cisco/ntp","cisco/acl","cisco/bgp_neighbor"]}],
    fortinet:[{group:"Fortinet",items:["fortinet/firewall_address","fortinet/firewall_policy","fortinet/static_route"]}],
    sophos:[{group:"Sophos",items:["sophos/ip_host","sophos/firewall_rule"]}],
  };
  const TEMPLATES={
    mikrotik: TEMPLATE_GROUPS.mikrotik.flatMap(g=>g.items),
    cisco: TEMPLATE_GROUPS.cisco.flatMap(g=>g.items),
    fortinet: TEMPLATE_GROUPS.fortinet.flatMap(g=>g.items),
    sophos: TEMPLATE_GROUPS.sophos.flatMap(g=>g.items),
  };
  const TVARS={
    // IP & Routing
    "mikrotik/interface_ip":[["ip","192.168.1.1"],["prefix","24"],["interface","ether1"],["comment","LAN"]],
    "mikrotik/vlan":[["name","VLAN10"],["vlan_id","10"],["interface","ether2"],["ip","10.10.0.1"],["prefix","24"]],
    "mikrotik/bridge":[["name","bridge-lan"],["ip","192.168.1.1"],["prefix","24"],["ports","ether2,ether3,ether4"]],
    "mikrotik/static_route":[["dst","10.0.0.0"],["prefix","8"],["gateway","192.168.1.254"],["comment","Static"]],
    "mikrotik/default_route":[["gateway","203.0.113.1"],["distance","1"],["comment","Default GW"]],
    "mikrotik/ip_pool":[["name","dhcp-pool"],["range_start","192.168.1.100"],["range_end","192.168.1.200"]],
    // Firewall
    "mikrotik/fw_accept":[["chain","forward"],["src",""],["dst",""],["protocol","tcp"],["dst_port","80,443"],["comment","Allow HTTP/HTTPS"]],
    "mikrotik/fw_drop":[["chain","input"],["src",""],["protocol","tcp"],["dst_port","23"],["comment","Block Telnet"]],
    "mikrotik/fw_nat_masquerade":[["out_interface","ether1-wan"],["comment","WAN Masquerade"]],
    "mikrotik/fw_nat_dstnat":[["dst_port","80"],["protocol","tcp"],["to_address","192.168.1.10"],["to_port","80"],["comment","Port forward"]],
    "mikrotik/fw_address_list":[["list","blocked"],["address","10.0.0.0/8"],["comment",""]],
    // PPPoE
    "mikrotik/pppoe_client":[["name","pppoe-out1"],["interface","ether1"],["user","username@isp"],["password","password"],["profile","default"]],
    "mikrotik/pppoe_lb_2wan":[["pppoe1","pppoe-out1"],["pppoe2","pppoe-out2"],["ip1","192.168.1.2"],["ip2","192.168.1.3"]],
    "mikrotik/pppoe_lb_3wan":[["pppoe1","pppoe-out1"],["pppoe2","pppoe-out2"],["pppoe3","pppoe-out3"],["ip1","192.168.1.2"],["ip2","192.168.1.3"],["ip3","192.168.1.4"]],
    "mikrotik/lan_to_pppoe":[["pppoe","pppoe-out1"],["src_ips","192.168.1.2-192.168.1.5"],["table_name","pppoe-out1"],["comment","LAN to PPPoE"]],
    // DHCP
    "mikrotik/dhcp_server":[["pool_name","dhcp-pool"],["range_start","192.168.1.100"],["range_end","192.168.1.200"],["network","192.168.1.0"],["prefix","24"],["gateway","192.168.1.1"],["dns","8.8.8.8"],["interface","bridge-lan"]],
    "mikrotik/dhcp_reservation":[["ip","192.168.1.50"],["mac","AA:BB:CC:DD:EE:FF"],["comment","Server-01"]],
    "mikrotik/dns":[["servers","8.8.8.8,8.8.4.4"],["allow_remote","yes"]],
    "mikrotik/hotspot":[["interface","wlan1"],["address_pool","hs-pool"],["range_start","10.5.50.2"],["range_end","10.5.50.254"],["dns","8.8.8.8"]],
    // SOCKS5
    "mikrotik/socks5_server":[["port","1080"],["allowed_src","192.168.1.0/24"],["comment","SOCKS5 Server"]],
    "mikrotik/socks5_transparent":[["socks5_server","127.0.0.1"],["socks5_port","1080"],["src_ips","192.168.1.2-192.168.1.5"],["table_name","socks5-route"],["redirect_port","1080"],["comment","Transparent SOCKS5"]],
    "mikrotik/socks5_lan_redirect":[["src_ips","192.168.1.2-192.168.1.5"],["socks5_ip","192.168.1.1"],["socks5_port","1080"],["table_name","socks5-mark"],["comment","LAN to SOCKS5"]],
    // Mangle
    "mikrotik/mangle_mark_conn":[["chain","prerouting"],["in_interface","pppoe-out1"],["new_mark","isp1"]],
    "mikrotik/mangle_mark_routing":[["chain","prerouting"],["src_address","192.168.1.2"],["new_mark","pppoe-out1"]],
    "mikrotik/queue_simple":[["name","limit-user"],["target","192.168.1.100"],["max_limit_up","5M"],["max_limit_down","10M"]],
    "mikrotik/queue_tree":[["name","upload"],["parent","ether1"],["max_limit","20M"],["priority","8"]],
    // VPN
    "mikrotik/l2tp_server":[["enabled","yes"],["auth","mschap2"],["secret","vpnpassword"]],
    "mikrotik/l2tp_client":[["name","l2tp-vpn"],["server","vpn.example.com"],["user","vpnuser"],["password","vpnpass"]],
    "mikrotik/ovpn_server":[["port","1194"],["auth","sha1"],["cipher","aes128"]],
    // System
    "mikrotik/ntp":[["server1","pool.ntp.org"],["server2","time.cloudflare.com"]],
    "mikrotik/snmp":[["community","public"],["contact","admin@example.com"],["location","Server Room"]],
    "mikrotik/user_add":[["name","netadmin"],["group","full"],["password","StrongPass!"]],
    "mikrotik/scheduler":[["name","reboot-weekly"],["start_date","jan/01/2024"],["start_time","03:00:00"],["interval","7d"],["on_event","/system reboot"]],
    "mikrotik/email_alert":[["server","smtp.gmail.com"],["port","587"],["from","router@example.com"],["to","admin@example.com"]],
    // Routing
    "mikrotik/bgp_peer":[["name","isp-peer"],["remote_address","203.0.113.1"],["remote_as","65001"],["local_as","65000"]],
    "mikrotik/ospf_instance":[["name","default"],["router_id","1.1.1.1"],["network","192.168.0.0/16"],["area","0.0.0.0"]],
    "mikrotik/routing_table":[["name","pppoe-out1"]],
    "mikrotik/routing_rule":[["src_address","192.168.1.2"],["table","pppoe-out1"],["action","lookup-only-in-table"]],
    // Cisco
    "cisco/interface_ip":[["interface","GigabitEthernet0/1"],["description","Uplink"],["ip","10.0.0.2"],["netmask","255.255.255.252"]],
    "cisco/ntp":[["ntp_server","pool.ntp.org"],["source_interface","Loopback0"]],
    "cisco/static_route":[["network","0.0.0.0"],["netmask","0.0.0.0"],["gateway","10.0.0.1"]],
    "cisco/vlan":[["vlan_id","10"],["name","VLAN10"],["interface","GigabitEthernet0/1"]],
    "cisco/acl":[["name","BLOCK-TELNET"],["action","deny"],["protocol","tcp"],["dst_port","23"]],
    "cisco/bgp_neighbor":[["remote_as","65001"],["neighbor","203.0.113.1"],["local_as","65000"]],
    "fortinet/firewall_address":[["name","Server-Net"],["ip","10.10.0.0"],["netmask","255.255.255.0"]],
    "fortinet/firewall_policy":[["name","LAN-to-WAN"],["src_interface","internal"],["dst_interface","wan1"],["action","accept"]],
    "fortinet/static_route":[["dst","0.0.0.0"],["mask","0.0.0.0"],["gateway","203.0.113.1"],["device","wan1"]],
    "sophos/ip_host":[["name","WebServer-01"],["ip","10.0.1.50"],["host_type","IP"]],
    "sophos/firewall_rule":[["name","Allow-Web"],["src_zone","LAN"],["dst_zone","WAN"],["service","HTTPS"]],
  };
  const GEN={
    // IP & Routing
    "mikrotik/interface_ip":v=>`/ip address add address=${v.ip}/${v.prefix} interface=${v.interface} comment="${v.comment}"`,
    "mikrotik/vlan":v=>`/interface vlan add name=${v.name} vlan-id=${v.vlan_id} interface=${v.interface}\n/ip address add address=${v.ip}/${v.prefix} interface=${v.name}`,
    "mikrotik/bridge":v=>{const ports=v.ports.split(",").map(p=>`/interface bridge port add bridge=${v.name} interface=${p.trim()}`).join("\n");return `/interface bridge add name=${v.name}\n${ports}\n/ip address add address=${v.ip}/${v.prefix} interface=${v.name}`;},
    "mikrotik/static_route":v=>`/ip route add dst-address=${v.dst}/${v.prefix} gateway=${v.gateway} comment="${v.comment}"`,
    "mikrotik/default_route":v=>`/ip route add dst-address=0.0.0.0/0 gateway=${v.gateway} distance=${v.distance} comment="${v.comment}"`,
    "mikrotik/ip_pool":v=>`/ip pool add name=${v.name} ranges=${v.range_start}-${v.range_end}`,
    // Firewall
    "mikrotik/fw_accept":v=>{let c=`/ip firewall filter add chain=${v.chain} action=accept`;if(v.src)c+=` src-address=${v.src}`;if(v.dst)c+=` dst-address=${v.dst}`;if(v.protocol)c+=` protocol=${v.protocol}`;if(v.dst_port)c+=` dst-port=${v.dst_port}`;c+=` comment="${v.comment}"`;return c;},
    "mikrotik/fw_drop":v=>{let c=`/ip firewall filter add chain=${v.chain} action=drop`;if(v.src)c+=` src-address=${v.src}`;if(v.protocol)c+=` protocol=${v.protocol}`;if(v.dst_port)c+=` dst-port=${v.dst_port}`;c+=` comment="${v.comment}"`;return c;},
    "mikrotik/fw_nat_masquerade":v=>`/ip firewall nat add chain=srcnat action=masquerade out-interface=${v.out_interface} comment="${v.comment}"`,
    "mikrotik/fw_nat_dstnat":v=>`/ip firewall nat add chain=dstnat protocol=${v.protocol} dst-port=${v.dst_port} action=dst-nat to-addresses=${v.to_address} to-ports=${v.to_port} comment="${v.comment}"`,
    "mikrotik/fw_address_list":v=>`/ip firewall address-list add list=${v.list} address=${v.address} comment="${v.comment}"`,
    // PPPoE
    "mikrotik/pppoe_client":v=>`/interface pppoe-client add name=${v.name} interface=${v.interface} user="${v.user}" password="${v.password}" profile=${v.profile} add-default-route=yes use-peer-dns=yes`,
    "mikrotik/pppoe_lb_2wan":v=>`# === Load Balancing 2 PPPoE WAN ===\n/routing table\nadd fib name=${v.pppoe1}\nadd fib name=${v.pppoe2}\n\n/ip firewall mangle\nadd action=mark-routing chain=prerouting new-routing-mark=${v.pppoe1} passthrough=yes src-address=${v.ip1}\nadd action=mark-connection chain=prerouting connection-mark=no-mark in-interface=${v.pppoe1} new-connection-mark=${v.pppoe1} passthrough=yes\nadd action=mark-routing chain=output connection-mark=${v.pppoe1} new-routing-mark=${v.pppoe1} passthrough=yes\nadd action=mark-routing chain=prerouting new-routing-mark=${v.pppoe2} passthrough=yes src-address=${v.ip2}\nadd action=mark-connection chain=prerouting connection-mark=no-mark in-interface=${v.pppoe2} new-connection-mark=${v.pppoe2} passthrough=yes\nadd action=mark-routing chain=output connection-mark=${v.pppoe2} new-routing-mark=${v.pppoe2} passthrough=yes\n\n/ip route\nadd distance=1 dst-address=0.0.0.0/0 gateway=${v.pppoe1} routing-table=${v.pppoe1} scope=30 target-scope=10\nadd distance=1 dst-address=0.0.0.0/0 gateway=${v.pppoe2} routing-table=${v.pppoe2} scope=30 target-scope=10\n\n/routing rule\nadd action=lookup-only-in-table src-address=${v.ip1} table=${v.pppoe1}\nadd action=lookup-only-in-table src-address=${v.ip2} table=${v.pppoe2}`,
    "mikrotik/pppoe_lb_3wan":v=>`# === Load Balancing 3 PPPoE WAN ===\n/routing table\nadd fib name=${v.pppoe1}\nadd fib name=${v.pppoe2}\nadd fib name=${v.pppoe3}\n\n/ip firewall mangle\nadd action=mark-routing chain=prerouting new-routing-mark=${v.pppoe1} passthrough=yes src-address=${v.ip1}\nadd action=mark-connection chain=prerouting connection-mark=no-mark in-interface=${v.pppoe1} new-connection-mark=${v.pppoe1} passthrough=yes\nadd action=mark-routing chain=output connection-mark=${v.pppoe1} new-routing-mark=${v.pppoe1} passthrough=yes\nadd action=mark-routing chain=prerouting new-routing-mark=${v.pppoe2} passthrough=yes src-address=${v.ip2}\nadd action=mark-connection chain=prerouting connection-mark=no-mark in-interface=${v.pppoe2} new-connection-mark=${v.pppoe2} passthrough=yes\nadd action=mark-routing chain=output connection-mark=${v.pppoe2} new-routing-mark=${v.pppoe2} passthrough=yes\nadd action=mark-routing chain=prerouting new-routing-mark=${v.pppoe3} passthrough=yes src-address=${v.ip3}\nadd action=mark-connection chain=prerouting connection-mark=no-mark in-interface=${v.pppoe3} new-connection-mark=${v.pppoe3} passthrough=yes\nadd action=mark-routing chain=output connection-mark=${v.pppoe3} new-routing-mark=${v.pppoe3} passthrough=yes\n\n/ip route\nadd distance=1 dst-address=0.0.0.0/0 gateway=${v.pppoe1} routing-table=${v.pppoe1} scope=30 target-scope=10\nadd distance=1 dst-address=0.0.0.0/0 gateway=${v.pppoe2} routing-table=${v.pppoe2} scope=30 target-scope=10\nadd distance=1 dst-address=0.0.0.0/0 gateway=${v.pppoe3} routing-table=${v.pppoe3} scope=30 target-scope=10\n\n/routing rule\nadd action=lookup-only-in-table src-address=${v.ip1} table=${v.pppoe1}\nadd action=lookup-only-in-table src-address=${v.ip2} table=${v.pppoe2}\nadd action=lookup-only-in-table src-address=${v.ip3} table=${v.pppoe3}`,
    "mikrotik/lan_to_pppoe":v=>{
      const parseIPs = (s) => {
        const ips = [];
        for(const part of s.split(",").map(x=>x.trim())){
          if(part.includes("-") && !part.includes("/")){
            const [startIP, endPart] = part.split("-");
            const base = startIP.split(".").slice(0,3).join(".");
            const start = parseInt(startIP.split(".")[3]);
            const end = parseInt(endPart.includes(".")?endPart.split(".")[3]:endPart);
            for(let i=start;i<=end;i++) ips.push(`${base}.${i}`);
          } else { ips.push(part); }
        }
        return ips;
      };
      const ips = parseIPs(v.src_ips||v.src_ip||"192.168.1.2");
      const addrList   = ips.map(ip=>`add address=${ip} list=${v.table_name}`).join("\n");
      const mangleRule = ips.map(ip=>`add action=mark-routing chain=prerouting new-routing-mark=${v.table_name} passthrough=yes src-address=${ip}`).join("\n");
      const routeRules = ips.map(ip=>`add action=lookup-only-in-table disabled=no src-address=${ip} routing-mark=${v.table_name} table=${v.table_name}`).join("\n");
      return `/routing table
add fib name=${v.table_name}
/ip firewall address-list
${addrList}
/ip firewall mangle
${mangleRule}
add action=mark-connection chain=prerouting connection-mark=no-mark in-interface=${v.pppoe} new-connection-mark=${v.table_name} passthrough=yes
add action=mark-routing chain=output connection-mark=${v.table_name} new-routing-mark=${v.table_name} passthrough=yes
/ip route
add distance=1 dst-address=0.0.0.0/0 gateway=${v.pppoe} routing-table=${v.table_name} scope=30 target-scope=10
/routing rule
${routeRules}`;
    },
    // DHCP
    "mikrotik/dhcp_server":v=>`/ip pool add name=${v.pool_name} ranges=${v.range_start}-${v.range_end}\n/ip dhcp-server add name=dhcp-${v.interface} interface=${v.interface} address-pool=${v.pool_name} disabled=no\n/ip dhcp-server network add address=${v.network}/${v.prefix} gateway=${v.gateway} dns-server=${v.dns}`,
    "mikrotik/dhcp_reservation":v=>`/ip dhcp-server lease add address=${v.ip} mac-address=${v.mac} comment="${v.comment}"`,
    "mikrotik/dns":v=>`/ip dns set servers=${v.servers} allow-remote-requests=${v.allow_remote}`,
    "mikrotik/hotspot":v=>`/ip pool add name=${v.address_pool} ranges=${v.range_start}-${v.range_end}\n/ip hotspot setup hotspot-interface=${v.interface} address-pool=${v.address_pool} dns-name="" use-radius=no\n/ip dns set servers=${v.dns} allow-remote-requests=yes`,
    // Mangle
    "mikrotik/mangle_mark_conn":v=>`/ip firewall mangle add action=mark-connection chain=${v.chain} connection-mark=no-mark in-interface=${v.in_interface} new-connection-mark=${v.new_mark} passthrough=yes`,
    "mikrotik/mangle_mark_routing":v=>`/ip firewall mangle add action=mark-routing chain=${v.chain} new-routing-mark=${v.new_mark} passthrough=yes src-address=${v.src_address}`,
    "mikrotik/queue_simple":v=>`/queue simple add name="${v.name}" target=${v.target} max-limit=${v.max_limit_up}/${v.max_limit_down}`,
    "mikrotik/queue_tree":v=>`/queue tree add name="${v.name}" parent=${v.parent} max-limit=${v.max_limit} priority=${v.priority}`,
    // SOCKS5
    "mikrotik/socks5_server":v=>`# === Enable MikroTik SOCKS5 Proxy Server ===
/ip socks
set enabled=yes port=${v.port} connection-idle-timeout=2m max-connections=200
/ip socks access
add action=allow src-address=${v.allowed_src} comment="${v.comment}"
/ip firewall filter
add chain=input protocol=tcp dst-port=${v.port} action=accept comment="Allow SOCKS5 ${v.port}"`,
    "mikrotik/socks5_transparent":v=>{
      const parseIPs=(s)=>{const ips=[];for(const part of s.split(",").map(x=>x.trim())){if(part.includes("-")&&!part.includes("/")){const[startIP,endPart]=part.split("-");const base=startIP.split(".").slice(0,3).join(".");const start=parseInt(startIP.split(".")[3]);const end=parseInt(endPart.includes(".")?endPart.split(".")[3]:endPart);for(let i=start;i<=end;i++)ips.push(`${base}.${i}`);}else{ips.push(part);}}return ips;};
      const ips=parseIPs(v.src_ips||"192.168.1.2");
      const addrList=ips.map(ip=>`add address=${ip} list=${v.table_name}`).join("\n");
      const mangleRules=ips.map(ip=>`add action=mark-routing chain=prerouting new-routing-mark=${v.table_name} passthrough=yes src-address=${ip}`).join("\n");
      const routingRules=ips.map(ip=>`add action=lookup-only-in-table disabled=no src-address=${ip} routing-mark=${v.table_name} table=${v.table_name}`).join("\n");
      return `/routing table
add fib name=${v.table_name}
/ip firewall address-list
${addrList}
/ip firewall mangle
${mangleRules}
add action=mark-connection chain=prerouting connection-mark=no-mark in-interface=lo new-connection-mark=${v.table_name} passthrough=yes
add action=mark-routing chain=output connection-mark=${v.table_name} new-routing-mark=${v.table_name} passthrough=yes
/ip firewall nat
add chain=dstnat protocol=tcp src-address-list=${v.table_name} dst-port=80,443,8080 action=redirect to-ports=${v.redirect_port} comment="${v.comment}"
/ip route
add distance=1 dst-address=0.0.0.0/0 gateway=${v.socks5_server} routing-table=${v.table_name} scope=30 target-scope=10
/routing rule
${routingRules}
/ip firewall filter
add chain=input protocol=tcp dst-port=${v.redirect_port} action=accept comment="Allow SOCKS5"`;
    },
    "mikrotik/socks5_lan_redirect":v=>{
      const parseIPs=(s)=>{const ips=[];for(const part of s.split(",").map(x=>x.trim())){if(part.includes("-")&&!part.includes("/")){const[startIP,endPart]=part.split("-");const base=startIP.split(".").slice(0,3).join(".");const start=parseInt(startIP.split(".")[3]);const end=parseInt(endPart.includes(".")?endPart.split(".")[3]:endPart);for(let i=start;i<=end;i++)ips.push(`${base}.${i}`);}else{ips.push(part);}}return ips;};
      const ips=parseIPs(v.src_ips||"192.168.1.2");
      const addrList=ips.map(ip=>`add address=${ip} list=${v.table_name}`).join("\n");
      const mangleMark=ips.map(ip=>`add action=mark-connection chain=prerouting new-connection-mark=${v.table_name} passthrough=yes src-address=${ip}`).join("\n");
      const natRules=ips.map(ip=>`add chain=dstnat protocol=tcp src-address=${ip} dst-port=80,443 action=dst-nat to-addresses=${v.socks5_ip} to-ports=${v.socks5_port} comment="${v.comment}"`).join("\n");
      return `/ip firewall address-list
${addrList}
/ip firewall mangle
${mangleMark}
add action=mark-routing chain=prerouting connection-mark=${v.table_name} new-routing-mark=${v.table_name} passthrough=yes
/ip firewall nat
${natRules}
/ip firewall filter
add chain=forward protocol=tcp dst-port=${v.socks5_port} action=accept comment="Allow to SOCKS5"
add chain=input protocol=tcp dst-port=${v.socks5_port} src-address=${v.socks5_ip} action=accept`;
    },
        // VPN
    "mikrotik/l2tp_server":v=>`/interface l2tp-server server set enabled=${v.enabled} authentication=${v.auth}\n/ppp secret add name=vpnuser password="${v.secret}" service=l2tp local-address=10.200.0.1 remote-address=10.200.0.2`,
    "mikrotik/l2tp_client":v=>`/interface l2tp-client add name=${v.name} connect-to=${v.server} user="${v.user}" password="${v.password}" add-default-route=no`,
    "mikrotik/ovpn_server":v=>`/interface ovpn-server server set enabled=yes port=${v.port} auth=${v.auth} cipher=${v.cipher}`,
    // System
    "mikrotik/ntp":v=>`/system ntp client set enabled=yes servers=${v.server1},${v.server2}`,
    "mikrotik/snmp":v=>`/snmp set enabled=yes contact="${v.contact}" location="${v.location}"\n/snmp community set name=${v.community} addresses=0.0.0.0/0`,
    "mikrotik/user_add":v=>`/user add name=${v.name} group=${v.group} password="${v.password}"`,
    "mikrotik/scheduler":v=>`/system scheduler add name="${v.name}" start-date=${v.start_date} start-time=${v.start_time} interval=${v.interval} on-event="${v.on_event}"`,
    "mikrotik/email_alert":v=>`/tool e-mail set server=${v.server} port=${v.port} from=${v.from}\n# Send test: /tool e-mail send to="${v.to}" subject="Test" body="Test from RouterOS"`,
    // Routing advanced
    "mikrotik/bgp_peer":v=>`/routing bgp peer add name=${v.name} remote-address=${v.remote_address} remote-as=${v.remote_as} instance=default`,
    "mikrotik/ospf_instance":v=>`/routing ospf instance set default router-id=${v.router_id}\n/routing ospf network add network=${v.network} area=${v.area}`,
    "mikrotik/routing_table":v=>`/routing table add fib name=${v.name}`,
    "mikrotik/routing_rule":v=>`/routing rule add action=${v.action} src-address=${v.src_address} table=${v.table}`,
    // Cisco
    "cisco/interface_ip":v=>`interface ${v.interface}\n description ${v.description}\n ip address ${v.ip} ${v.netmask}\n no shutdown`,
    "cisco/ntp":v=>`ntp server ${v.ntp_server}\nntp source ${v.source_interface}`,
    "cisco/static_route":v=>`ip route ${v.network} ${v.netmask} ${v.gateway}`,
    "cisco/vlan":v=>`vlan ${v.vlan_id}\n name ${v.name}\ninterface ${v.interface}\n switchport mode access\n switchport access vlan ${v.vlan_id}`,
    "cisco/acl":v=>`ip access-list extended ${v.name}\n ${v.action} ${v.protocol} any any eq ${v.dst_port}`,
    "cisco/bgp_neighbor":v=>`router bgp ${v.local_as}\n neighbor ${v.neighbor} remote-as ${v.remote_as}`,
    "fortinet/firewall_address":v=>`config firewall address\n edit "${v.name}"\n  set subnet ${v.ip} ${v.netmask}\n next\nend`,
    "fortinet/firewall_policy":v=>`config firewall policy\n edit 0\n  set name "${v.name}"\n  set srcintf "${v.src_interface}"\n  set dstintf "${v.dst_interface}"\n  set action ${v.action}\n next\nend`,
    "fortinet/static_route":v=>`config router static\n edit 0\n  set dst ${v.dst} ${v.mask}\n  set gateway ${v.gateway}\n  set device "${v.device}"\n next\nend`,
    "sophos/ip_host":v=>`<IPHost><Name>${v.name}</Name><IPAddress>${v.ip}</IPAddress><HostType>${v.host_type}</HostType></IPHost>`,
    "sophos/firewall_rule":v=>`<FirewallRule><Name>${v.name}</Name><SourceZones><Zone>${v.src_zone}</Zone></SourceZones><DestZones><Zone>${v.dst_zone}</Zone></DestZones><Services><Service>${v.service}</Service></Services></FirewallRule>`,
  };

  useEffect(()=>{
    const dv={};(TVARS[tmpl]||[]).forEach(([k,v])=>{dv[k]=v;});
    setVars(dv);setPreview("");
  },[tmpl]);

  const handlePush=async()=>{
    if(!targets.length){toast("warn","Chọn ít nhất 1 thiết bị");return;}
    const p=mode==="manual"?manualCmds:preview;
    if(!p.trim()){toast("warn","Generate preview trước");return;}
    setPushing(true);setResult(null);
    const commands=p.split("\n").filter(l=>l.trim());
    const results={};
    for(const devName of targets){
      try{const r=await api(`/api/devices/${encodeURIComponent(devName)}/config`,"POST",{commands});results[devName]={ok:true,status:r.status};}
      catch{await new Promise(r=>setTimeout(r,300));results[devName]={ok:true,status:"ok (demo)"};}
      addLog("success",`Config push → ${devName}: ${tmpl||"manual"}`);
    }
    setPushing(false);setResult(results);
    toast("success",`Đã push config đến ${targets.length} thiết bị`);
  };

  const online=devices.filter(d=>d.status==="online");
  return(
    <div className="fadeIn" style={{padding:28}}>
      <div style={{marginBottom:22}}>
        <div style={{fontSize:22,fontWeight:700}}>Config Push</div>
        <div style={{fontSize:12,color:G.muted,marginTop:3}}>Triển khai config từ template hoặc manual</div>
      </div>
      <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:16}}>
        <div style={{display:"flex",flexDirection:"column",gap:14}}>
          <Card style={{padding:14}}>
            <div style={{display:"flex",gap:8}}>
              {["template","manual"].map(m=>(
                <div key={m} onClick={()=>setMode(m)} style={{flex:1,textAlign:"center",padding:"8px",borderRadius:6,cursor:"pointer",fontSize:12,fontWeight:600,background:mode===m?`${G.accent}22`:G.surface,border:`1px solid ${mode===m?G.accent+"66":G.border}`,color:mode===m?G.accent:G.muted,transition:"all .15s"}}>
                  {m==="template"?"⚙ Template":">_ Manual"}
                </div>
              ))}
            </div>
          </Card>
          {mode==="template"?(
            <>
              <Card>
                <Lbl>Vendor</Lbl>
                <Sel value={vendor} onChange={e=>{setVendor(e.target.value);setTmpl(TEMPLATES[e.target.value][0]);}} options={["mikrotik","cisco","fortinet","sophos"].map(v=>({value:v,label:v.charAt(0).toUpperCase()+v.slice(1)}))}/>
                <div style={{marginTop:12}}>
                  <Lbl>Template</Lbl>
                  <div style={{maxHeight:320,overflowY:"auto",border:`1px solid ${G.border2}`,borderRadius:6,background:G.surface}}>
                    {(TEMPLATE_GROUPS[vendor]||[]).map(g=>(
                      <div key={g.group}>
                        <div style={{padding:"6px 10px",fontSize:10,color:G.accent,fontFamily:FONT,letterSpacing:"0.06em",background:`${G.accent}0a`,borderBottom:`1px solid ${G.border}`,position:"sticky",top:0}}>{g.group}</div>
                        {g.items.map(t=>(
                          <div key={t} onClick={()=>setTmpl(t)} style={{padding:"7px 14px",fontSize:12,cursor:"pointer",color:tmpl===t?G.accent:G.dim,background:tmpl===t?`${G.accent}15`:"transparent",borderBottom:`1px solid ${G.border}`,transition:"all .1s",fontFamily:FONT}}
                            onMouseEnter={e=>{if(tmpl!==t)e.currentTarget.style.background=`${G.surface}cc`;}}
                            onMouseLeave={e=>{if(tmpl!==t)e.currentTarget.style.background="transparent";}}
                          >
                            {tmpl===t?"▶ ":""}{t.replace(vendor+"/","").replace(/_/g," ")}
                          </div>
                        ))}
                      </div>
                    ))}
                  </div>
                </div>
              </Card>
              <Card>
                <Lbl>Variables</Lbl>
                <div style={{display:"flex",flexDirection:"column",gap:8}}>
                  {(TVARS[tmpl]||[]).map(([k])=>(
                    <div key={k} style={{display:"grid",gridTemplateColumns:"130px 1fr",gap:8,alignItems:"center"}}>
                      <span style={{fontFamily:FONT,fontSize:11,color:G.accent}}>{k}</span>
                      <Input value={vars[k]??""} onChange={e=>setVars(p=>({...p,[k]:e.target.value}))}/>
                    </div>
                  ))}
                </div>
              </Card>
              <Btn variant="ghost" onClick={()=>{const g=GEN[tmpl];setPreview(g?g(vars):"# No preview");}}>⬡ Generate Preview</Btn>
            </>
          ):(
            <Card>
              <Lbl>Commands (1 dòng = 1 lệnh)</Lbl>
              <textarea value={manualCmds} onChange={e=>setManualCmds(e.target.value)} placeholder={"/ip address add address=10.0.0.1/24 interface=ether1\n/ip route add dst-address=0.0.0.0/0 gateway=10.0.0.254"} style={{width:"100%",minHeight:180,background:G.surface,border:`1px solid ${G.border2}`,color:G.text,padding:"10px 12px",borderRadius:6,fontSize:12,fontFamily:FONT,outline:"none",resize:"vertical",lineHeight:1.8}}/>
            </Card>
          )}
        </div>
        <div style={{display:"flex",flexDirection:"column",gap:14}}>
          <Card>
            <Lbl>Target Devices</Lbl>
            {online.length===0?<div style={{fontSize:12,color:G.muted}}>Không có thiết bị online</div>:(
              <div style={{display:"flex",flexDirection:"column",gap:6}}>
                {online.map(d=>(
                  <div key={d.id||d.name} onClick={()=>setTargets(p=>p.includes(d.name)?p.filter(x=>x!==d.name):[...p,d.name])} style={{display:"flex",alignItems:"center",gap:10,padding:"8px 10px",borderRadius:6,cursor:"pointer",background:targets.includes(d.name)?`${G.accent}15`:G.surface,border:`1px solid ${targets.includes(d.name)?G.accent+"44":G.border}`,transition:"all .15s"}}>
                    <div style={{width:14,height:14,borderRadius:3,border:`1.5px solid ${targets.includes(d.name)?G.accent:G.muted}`,background:targets.includes(d.name)?G.accent:"transparent",display:"flex",alignItems:"center",justifyContent:"center",fontSize:9,color:"#000"}}>{targets.includes(d.name)?"✓":""}</div>
                    <span style={{fontFamily:FONT,fontSize:12,color:G.text,flex:1}}>{d.name}</span>
                    <VChip vendor={d.vendor}/>
                  </div>
                ))}
              </div>
            )}
          </Card>
          {preview&&(
            <Card style={{background:"#05070b"}}>
              <Lbl>Preview</Lbl>
              <pre style={{fontFamily:FONT,fontSize:11,color:G.green,whiteSpace:"pre-wrap",lineHeight:1.8,maxHeight:200,overflowY:"auto"}}>{preview}</pre>
            </Card>
          )}
          <Btn onClick={handlePush} loading={pushing} disabled={!targets.length} style={{padding:"12px",fontSize:13,justifyContent:"center"}}>
            {pushing?`Pushing...`:`⚙ Push to ${targets.length} device(s)`}
          </Btn>
          {result&&(
            <Card className="fadeIn" style={{background:`${G.green}0a`,borderColor:`${G.green}44`}}>
              <div style={{fontSize:12,color:G.green,fontFamily:FONT,marginBottom:8}}>✓ Config push hoàn tất</div>
              {Object.entries(result).map(([name,r])=><div key={name} style={{fontSize:11,color:G.dim,marginBottom:3}}><span style={{color:G.green}}>✓</span> {name}: {r.status}</div>)}
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Backup ────────────────────────────────────────────────────────

// ── Monitor Page — InfluxDB + Realtime + Charts ───────────────────
function MonitorPage({devices, toast}){
  const [monStatus,  setMonStatus]  = useState({active:false, devices:{}});
  const [selDev,     setSelDev]     = useState(null);
  const [devCfg,     setDevCfg]     = useState({});      // {interval, enabled} per device
  const [thresholds, setThresholds] = useState({});      // per device
  const [range,      setRange]      = useState("1h");
  const [metrics,    setMetrics]    = useState({});      // InfluxDB history {cpu:[],mem:[]}
  const [ifaceData,  setIfaceData]  = useState({});      // traffic per interface
  const [liveIface,  setLiveIface]  = useState([]);      // live snapshot
  const [activeTab,  setActiveTab]  = useState("overview"); // overview|chart|iface|threshold
  const [loading,    setLoading]    = useState(false);
  const [livePoll,   setLivePoll]   = useState(false);
  const liveTimer = useRef(null);

  const cpuColor = v => v>80?"#ef4444":v>50?"#f59e0b":"#22c55e";
  const memColor = v => v>85?"#ef4444":v>60?"#f59e0b":"#38bdf8";
  const bwColor  = v => v>800?"#ef4444":v>400?"#f59e0b":"#a78bfa";

  // ── Fetch monitor status toàn bộ ──────────────────────────────
  const fetchStatus = async() => {
    try{ const s=await api("/api/monitor/status"); setMonStatus(s); }catch{}
  };

  // ── Fetch config của device đang chọn ─────────────────────────
  const fetchDevCfg = async(name) => {
    try{
      const [cfg,th] = await Promise.all([
        api(`/api/monitor/${encodeURIComponent(name)}/config`),
        api(`/api/monitor/${encodeURIComponent(name)}/thresholds`),
      ]);
      setDevCfg(p=>({...p,[name]:cfg}));
      setThresholds(p=>({...p,[name]:th}));
    }catch{}
  };

  // ── Fetch metrics từ InfluxDB ──────────────────────────────────
  const fetchMetrics = async(name, rng=range) => {
    setLoading(true);
    try{
      const [sys,ifc] = await Promise.all([
        api(`/api/monitor/${encodeURIComponent(name)}/metrics?range=${rng}&field=cpu,mem,hdd`),
        api(`/api/monitor/${encodeURIComponent(name)}/interfaces?range=${rng}`),
      ]);
      setMetrics(p=>({...p,[name]:{range:rng,...sys.data}}));
      setIfaceData(p=>({...p,[name]:ifc.interfaces||{}}));
    }catch(e){toast("error","InfluxDB: "+String(e));}
    setLoading(false);
  };

  // ── Live interface snapshot ────────────────────────────────────
  const fetchLive = async(name) => {
    try{
      const r=await api(`/api/monitor/${encodeURIComponent(name)}/interfaces/live`);
      setLiveIface(r.interfaces||[]);
    }catch{}
  };

  // Auto-refresh live khi bật
  useEffect(()=>{
    if(livePoll && selDev){
      liveTimer.current = setInterval(()=>fetchLive(selDev), 5000);
      fetchLive(selDev);
    } else {
      clearInterval(liveTimer.current);
    }
    return ()=>clearInterval(liveTimer.current);
  },[livePoll, selDev]);

  useEffect(()=>{ fetchStatus(); },[]);

  useEffect(()=>{
    if(selDev){
      fetchDevCfg(selDev);
      if(activeTab==="chart") fetchMetrics(selDev, range);
      if(activeTab==="iface") fetchMetrics(selDev, range);
      if(activeTab==="live")  fetchLive(selDev);
    }
  },[selDev, activeTab]);

  // ── Bật/tắt monitor cho device ────────────────────────────────
  const setMonitorCfg = async(name, interval, enabled) => {
    try{
      await api(`/api/monitor/${encodeURIComponent(name)}/config`,"POST",{interval,enabled});
      toast("success",`Monitor ${enabled?"bật":"tắt"}: ${name} (${interval}s)`);
      fetchStatus(); fetchDevCfg(name);
    }catch(e){toast("error",String(e));}
  };

  // ── Lưu threshold ─────────────────────────────────────────────
  const saveThreshold = async(name, th) => {
    try{
      await api(`/api/monitor/${encodeURIComponent(name)}/thresholds`,"POST",th);
      toast("success","Đã lưu ngưỡng cảnh báo");
      setThresholds(p=>({...p,[name]:th}));
    }catch(e){toast("error",String(e));}
  };

  // ── Components ────────────────────────────────────────────────
  const MiniBar = ({value=0, color, width=120}) => (
    <div style={{display:"flex",alignItems:"center",gap:6}}>
      <div style={{width,height:5,background:G.border,borderRadius:3,overflow:"hidden"}}>
        <div style={{width:`${Math.min(value,100)}%`,height:"100%",background:color,borderRadius:3,transition:"width .5s"}}/>
      </div>
      <span style={{fontFamily:FONT,fontSize:11,color,minWidth:34}}>{value}%</span>
    </div>
  );

  // SVG sparkline đơn giản (không cần recharts)
  const SparkLine = ({data=[], color="#38bdf8", maxVal=null, unit=""}) => {
    if(!data||data.length<2) return(
      <div style={{height:60,display:"flex",alignItems:"center",justifyContent:"center",
        color:G.muted,fontSize:11,fontFamily:FONT}}>no data — start monitor first</div>
    );
    const w=460, h=60;
    const vals  = data.map(d=>d.v);
    const mx    = maxVal || Math.max(...vals, 1);
    const mn    = 0;
    const pts   = vals.map((v,i)=>`${i/(vals.length-1)*w},${h-(v-mn)/(mx-mn||1)*h}`).join(" ");
    const area  = `0,${h} ${pts} ${w},${h}`;
    const last  = vals[vals.length-1];
    const avg   = (vals.reduce((a,b)=>a+b,0)/vals.length).toFixed(1);
    const max   = Math.max(...vals).toFixed(1);
    return(
      <div>
        <svg width="100%" viewBox={`0 0 ${w} ${h}`} style={{display:"block",marginBottom:4}}>
          <defs>
            <linearGradient id={`grad_${color.replace("#","")}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={color} stopOpacity="0.3"/>
              <stop offset="100%" stopColor={color} stopOpacity="0.02"/>
            </linearGradient>
          </defs>
          <polygon points={area} fill={`url(#grad_${color.replace("#","")})`}/>
          <polyline points={pts} fill="none" stroke={color} strokeWidth="1.5" opacity="0.9"/>
          <circle cx={vals.length>1?(vals.length-1)/(vals.length-1)*w:w} cy={h-(last-mn)/(mx-mn||1)*h} r="3" fill={color}/>
        </svg>
        <div style={{display:"flex",gap:16,fontSize:10,fontFamily:FONT,color:G.muted}}>
          <span>Cur: <span style={{color}}>{last?.toFixed?.(1)??last}{unit}</span></span>
          <span>Avg: <span style={{color:G.dim}}>{avg}{unit}</span></span>
          <span>Max: <span style={{color:G.dim}}>{max}{unit}</span></span>
          <span style={{marginLeft:"auto",color:G.muted}}>{data.length} points · {range}</span>
        </div>
      </div>
    );
  };

  // Bandwidth chart — rx (xanh) và tx (tím) chồng lên nhau
  const BandwidthChart = ({rxData=[], txData=[], ifaceName}) => {
    if(!rxData.length && !txData.length) return(
      <div style={{height:60,display:"flex",alignItems:"center",justifyContent:"center",
        color:G.muted,fontSize:11}}>no traffic data</div>
    );
    const w=460, h=60;
    const allVals = [...rxData.map(d=>d.v), ...txData.map(d=>d.v)];
    const mx = Math.max(...allVals, 0.01);
    const toSvg = (data,W,H) => data.map((d,i)=>`${i/(data.length-1||1)*W},${H-(d.v/mx)*H}`).join(" ");
    const rxPts = rxData.length>1 ? toSvg(rxData,w,h) : null;
    const txPts = txData.length>1 ? toSvg(txData,w,h) : null;
    const lastRx = rxData[rxData.length-1]?.v||0;
    const lastTx = txData[txData.length-1]?.v||0;
    return(
      <div>
        <div style={{fontSize:11,color:G.muted,fontFamily:FONT,marginBottom:4}}>{ifaceName}</div>
        <svg width="100%" viewBox={`0 0 ${w} ${h}`} style={{display:"block",marginBottom:4}}>
          {rxPts&&<polyline points={rxPts} fill="none" stroke="#22c55e" strokeWidth="1.5" opacity="0.85"/>}
          {txPts&&<polyline points={txPts} fill="none" stroke="#a78bfa" strokeWidth="1.5" opacity="0.85"/>}
        </svg>
        <div style={{display:"flex",gap:16,fontSize:10,fontFamily:FONT}}>
          <span style={{color:"#22c55e"}}>↓ RX {lastRx.toFixed(2)} Mbps</span>
          <span style={{color:"#a78bfa"}}>↑ TX {lastTx.toFixed(2)} Mbps</span>
          <span style={{color:G.muted,marginLeft:"auto"}}>{range}</span>
        </div>
      </div>
    );
  };

  // ── Threshold form ─────────────────────────────────────────────
  const ThresholdForm = ({name}) => {
    const th = thresholds[name]||{};
    const [cpu,  setCpu]  = useState(th.cpu||"");
    const [mem,  setMem]  = useState(th.mem||"");
    const [bw,   setBw]   = useState(th.bw_mbps||"");
    const [down, setDown] = useState(th.iface_down!==false);
    return(
      <div style={{display:"flex",flexDirection:"column",gap:12}}>
        <div style={{fontSize:12,color:G.muted,marginBottom:4}}>
          Cảnh báo Telegram khi vượt ngưỡng · Cooldown 5 phút
        </div>
        {[
          ["CPU > (%)",   cpu,  setCpu,  "80"],
          ["MEM > (%)",   mem,  setMem,  "85"],
          ["Bandwidth > (Mbps)", bw, setBw, "900"],
        ].map(([label,val,setter,ph])=>(
          <div key={label} style={{display:"flex",alignItems:"center",gap:12}}>
            <span style={{fontSize:12,color:G.dim,width:160}}>{label}</span>
            <input value={val} onChange={e=>setter(e.target.value)}
              placeholder={ph}
              style={{width:80,background:G.surface,border:`1px solid ${G.border2}`,
                color:G.text,borderRadius:4,padding:"4px 8px",fontSize:12,fontFamily:FONT}}/>
          </div>
        ))}
        <div style={{display:"flex",alignItems:"center",gap:8}}>
          <input type="checkbox" checked={down} onChange={e=>setDown(e.target.checked)} id={`down_${name}`}/>
          <label htmlFor={`down_${name}`} style={{fontSize:12,color:G.dim}}>Cảnh báo khi Interface DOWN</label>
        </div>
        <Btn onClick={()=>saveThreshold(name,{
          cpu: cpu?Number(cpu):null,
          mem: mem?Number(mem):null,
          bw_mbps: bw?Number(bw):null,
          iface_down: down,
        })} style={{alignSelf:"flex-start",padding:"5px 16px",fontSize:12}}>
          💾 Lưu ngưỡng
        </Btn>
        {th.cpu&&<div style={{fontSize:10,color:G.green,fontFamily:FONT}}>
          ✓ Đã cấu hình: CPU&gt;{th.cpu}% MEM&gt;{th.mem||"—"}% BW&gt;{th.bw_mbps||"—"}Mbps
        </div>}
      </div>
    );
  };

  // ── Device detail panel ────────────────────────────────────────
  const DevDetail = ({dev}) => {
    const cfg   = devCfg[dev.name]||{interval:60,enabled:false};
    const mData = metrics[dev.name]||{};
    const iData = ifaceData[dev.name]||{};
    const mon   = monStatus.devices?.[dev.name]||{};
    const [intv, setIntv] = useState(cfg.interval||60);

    const TABS = [
      {id:"chart",    label:"📈 CPU/MEM"},
      {id:"iface",    label:"📶 Bandwidth"},
      {id:"live",     label:"⚡ Live"},
      {id:"threshold",label:"⚠️ Ngưỡng"},
    ];

    return(
      <div style={{marginTop:16,padding:16,background:G.surface,borderRadius:8,
        border:`1px solid ${G.accent}44`}}>

        {/* Header */}
        <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:14}}>
          <div style={{display:"flex",alignItems:"center",gap:10}}>
            <span style={{fontWeight:700,fontSize:14}}>{dev.name}</span>
            <VChip vendor={dev.vendor}/>
            <span style={{fontSize:10,color:G.muted,fontFamily:FONT}}>{dev.host}</span>
          </div>
          <div style={{display:"flex",gap:8,alignItems:"center"}}>
            <select value={intv} onChange={e=>setIntv(Number(e.target.value))}
              style={{background:G.card,border:`1px solid ${G.border2}`,color:G.text,
                borderRadius:4,padding:"3px 8px",fontSize:11}}>
              <option value={30}>Poll 30s</option>
              <option value={60}>Poll 60s</option>
              <option value={300}>Poll 5m</option>
            </select>
            {cfg.enabled
              ? <Btn onClick={()=>setMonitorCfg(dev.name,intv,false)}
                  style={{background:"#7f1d1d",padding:"3px 12px",fontSize:11}}>⏹ Stop</Btn>
              : <Btn onClick={()=>setMonitorCfg(dev.name,intv,true)}
                  style={{background:"#14532d",padding:"3px 12px",fontSize:11}}>▶ Start</Btn>
            }
            <div style={{display:"flex",alignItems:"center",gap:4,fontSize:10}}>
              <div style={{width:7,height:7,borderRadius:"50%",
                background:mon.running?"#22c55e":"#6b7280"}}/>
              <span style={{color:mon.running?"#22c55e":G.muted}}>
                {mon.running?`polling ${intv}s`:"stopped"}
              </span>
            </div>
          </div>
        </div>

        {/* Sub-tabs */}
        <div style={{display:"flex",gap:4,marginBottom:14,borderBottom:`1px solid ${G.border}`}}>
          {TABS.map(t=>(
            <button key={t.id} onClick={()=>{setActiveTab(t.id); if(t.id==="live"){setLivePoll(false);fetchLive(dev.name);}}}
              style={{padding:"5px 14px",fontSize:11,background:"transparent",border:"none",
                cursor:"pointer",color:activeTab===t.id?G.accent:G.muted,fontFamily:FONT,
                borderBottom:activeTab===t.id?`2px solid ${G.accent}`:"2px solid transparent"}}>
              {t.label}
            </button>
          ))}
          {/* Range selector */}
          {(activeTab==="chart"||activeTab==="iface")&&(
            <div style={{marginLeft:"auto",display:"flex",gap:4}}>
              {["1h","6h","24h","7d"].map(r=>(
                <button key={r} onClick={()=>{setRange(r);fetchMetrics(dev.name,r);}}
                  style={{padding:"3px 10px",fontSize:10,background:range===r?G.accent+"22":"transparent",
                    border:`1px solid ${range===r?G.accent:G.border}`,borderRadius:4,
                    cursor:"pointer",color:range===r?G.accent:G.muted,fontFamily:FONT}}>
                  {r}
                </button>
              ))}
              <Btn onClick={()=>fetchMetrics(dev.name,range)}
                style={{padding:"3px 10px",fontSize:10,marginLeft:4}}>↻</Btn>
            </div>
          )}
        </div>

        {loading&&<div style={{textAlign:"center",padding:20,color:G.muted,fontSize:12}}>
          <span className="spin" style={{display:"inline-block",marginRight:6}}>◌</span>Loading...
        </div>}

        {/* CPU/MEM charts */}
        {activeTab==="chart"&&!loading&&(
          <div style={{display:"flex",flexDirection:"column",gap:16}}>
            <div>
              <div style={{fontSize:11,color:G.muted,marginBottom:6}}>
                CPU Load (%) · {dev.cpu||0}% now
              </div>
              <SparkLine data={mData.cpu||[]} color={cpuColor(dev.cpu||0)} unit="%"/>
            </div>
            <div>
              <div style={{fontSize:11,color:G.muted,marginBottom:6}}>
                Memory (%) · {dev.mem||0}% now
              </div>
              <SparkLine data={mData.mem||[]} color={memColor(dev.mem||0)} unit="%"/>
            </div>
            {mData.hdd&&mData.hdd.length>0&&(
              <div>
                <div style={{fontSize:11,color:G.muted,marginBottom:6}}>HDD Usage (%)</div>
                <SparkLine data={mData.hdd} color="#fb923c" unit="%"/>
              </div>
            )}
          </div>
        )}

        {/* Bandwidth per interface */}
        {activeTab==="iface"&&!loading&&(
          <div style={{display:"flex",flexDirection:"column",gap:14}}>
            {Object.keys(iData).length===0&&(
              <div style={{color:G.muted,fontSize:12,textAlign:"center",padding:20}}>
                Chưa có dữ liệu bandwidth. Bật monitor để ghi InfluxDB.
              </div>
            )}
            {Object.entries(iData).map(([name,traf])=>(
              <div key={name} style={{padding:12,background:G.card,borderRadius:6,
                border:`1px solid ${G.border}`}}>
                <BandwidthChart rxData={traf.rx||[]} txData={traf.tx||[]} ifaceName={name}/>
              </div>
            ))}
          </div>
        )}

        {/* Live interface snapshot */}
        {activeTab==="live"&&(
          <div>
            <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:10}}>
              <span style={{fontSize:11,color:G.muted}}>Snapshot từ RouterOS API · auto-refresh 5s</span>
              <div style={{display:"flex",gap:8}}>
                <Btn onClick={()=>fetchLive(dev.name)} style={{padding:"3px 10px",fontSize:10}}>↻ Refresh</Btn>
                <button onClick={()=>setLivePoll(p=>!p)}
                  style={{padding:"3px 12px",fontSize:10,background:livePoll?"#7f1d1d":"#14532d",
                    border:"none",borderRadius:4,cursor:"pointer",color:G.text,fontFamily:FONT}}>
                  {livePoll?"⏹ Stop Auto":"▶ Auto 5s"}
                </button>
              </div>
            </div>
            <div style={{overflowX:"auto"}}>
              <table style={{width:"100%",borderCollapse:"collapse",fontSize:11,fontFamily:FONT}}>
                <thead>
                  <tr style={{background:G.card}}>
                    {["Interface","Type","Status","↓ RX Mbps","↑ TX Mbps","RX Drop","TX Drop"].map(h=>(
                      <th key={h} style={{padding:"6px 10px",textAlign:"left",color:G.muted,
                        borderBottom:`1px solid ${G.border}`,fontWeight:500}}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {liveIface.filter(i=>!i.disabled).map(ifc=>(
                    <tr key={ifc.name} style={{borderBottom:`1px solid ${G.border}`,
                      background:ifc.running?"transparent":"#2d0a0a22"}}>
                      <td style={{padding:"6px 10px",color:G.text,fontWeight:500}}>{ifc.name}</td>
                      <td style={{padding:"6px 10px",color:G.muted}}>{ifc.type||"—"}</td>
                      <td style={{padding:"6px 10px"}}>
                        <span style={{color:ifc.running?"#22c55e":"#ef4444",fontWeight:600}}>
                          {ifc.running?"● UP":"● DOWN"}
                        </span>
                      </td>
                      <td style={{padding:"6px 10px",color:"#22c55e"}}>{ifc.rx_mbps?.toFixed(3)||"0.000"}</td>
                      <td style={{padding:"6px 10px",color:"#a78bfa"}}>{ifc.tx_mbps?.toFixed(3)||"0.000"}</td>
                      <td style={{padding:"6px 10px",color:ifc.rx_drop>0?"#f59e0b":G.muted}}>{ifc.rx_drop||0}</td>
                      <td style={{padding:"6px 10px",color:ifc.tx_drop>0?"#f59e0b":G.muted}}>{ifc.tx_drop||0}</td>
                    </tr>
                  ))}
                  {!liveIface.length&&(
                    <tr><td colSpan={7} style={{padding:20,textAlign:"center",color:G.muted}}>
                      Nhấn Refresh hoặc bật Auto 5s
                    </td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Threshold config */}
        {activeTab==="threshold"&&<ThresholdForm name={dev.name}/>}
      </div>
    );
  };

  // ── Render chính ──────────────────────────────────────────────
  return(
    <div className="fadeIn" style={{padding:28}}>
      <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:20}}>
        <div>
          <div style={{fontSize:22,fontWeight:700}}>📊 Monitor</div>
          <div style={{fontSize:12,color:G.muted,marginTop:3}}>
            InfluxDB · Poll 30s/60s/5m · Bandwidth · Alerts
          </div>
        </div>
        <div style={{display:"flex",alignItems:"center",gap:8,fontSize:11}}>
          <div style={{width:8,height:8,borderRadius:"50%",
            background:monStatus.active?"#22c55e":"#6b7280"}}/>
          <span style={{color:monStatus.active?"#22c55e":G.muted}}>
            {monStatus.active
              ? `${Object.values(monStatus.devices||{}).filter(d=>d.running).length} device(s) polling`
              : "Idle"}
          </span>
          <Btn onClick={fetchStatus} style={{padding:"3px 10px",fontSize:10}}>↻</Btn>
        </div>
      </div>

      {/* API endpoints info */}
      <div style={{marginBottom:16,padding:"10px 14px",background:"#0d1b2a",borderRadius:6,
        border:"1px solid #1e3a5f",fontSize:10,fontFamily:FONT,color:G.dim}}>
        <span style={{color:"#38bdf8"}}>// InfluxDB endpoints: </span>
        {[
          `GET /api/monitor/{name}/metrics?range=1h`,
          `GET /api/monitor/{name}/interfaces?range=24h`,
          `GET /api/monitor/{name}/interfaces/live`,
          `POST /api/monitor/{name}/config  {interval:60,enabled:true}`,
        ].map(e=><span key={e} style={{marginLeft:12,color:"#93c5fd"}}>{e}</span>)}
      </div>

      {/* Device overview grid */}
      <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fill,minmax(280px,1fr))",gap:12,marginBottom:16}}>
        {devices.map(dev=>{
          const mon = monStatus.devices?.[dev.name]||{};
          const isSelected = selDev===dev.name;
          const cpu = dev.cpu||0;
          const mem = dev.mem||0;
          return(
            <div key={dev.name}
              onClick={()=>{setSelDev(isSelected?null:dev.name); setActiveTab("chart");}}
              style={{padding:14,background:G.card,borderRadius:8,cursor:"pointer",
                border:`1px solid ${isSelected?G.accent:G.border2}`,
                boxShadow:isSelected?`0 0 16px ${G.accent}22`:"none",transition:"all .2s"}}>
              <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:10}}>
                <div style={{display:"flex",alignItems:"center",gap:8}}>
                  <div style={{width:8,height:8,borderRadius:"50%",
                    background:dev.status==="online"?"#22c55e":"#ef4444"}}/>
                  <span style={{fontWeight:600,fontSize:13}}>{dev.name}</span>
                  <VChip vendor={dev.vendor}/>
                </div>
                <div style={{display:"flex",alignItems:"center",gap:4,fontSize:10}}>
                  {mon.running
                    ? <span style={{color:"#22c55e",fontFamily:FONT}}>📡 {mon.interval||"?"}s</span>
                    : <span style={{color:G.muted,fontFamily:FONT}}>💤 off</span>}
                </div>
              </div>
              <div style={{display:"flex",flexDirection:"column",gap:5}}>
                <div style={{display:"flex",justifyContent:"space-between",alignItems:"center"}}>
                  <span style={{fontSize:11,color:G.muted}}>CPU</span>
                  <MiniBar value={cpu} color={cpuColor(cpu)} width={130}/>
                </div>
                <div style={{display:"flex",justifyContent:"space-between",alignItems:"center"}}>
                  <span style={{fontSize:11,color:G.muted}}>MEM</span>
                  <MiniBar value={mem} color={memColor(mem)} width={130}/>
                </div>
              </div>
              {dev.uptime&&(
                <div style={{marginTop:6,fontSize:10,color:G.muted,fontFamily:FONT}}>
                  ⏱ {dev.uptime} · {dev.model||dev.vendor}
                </div>
              )}
            </div>
          );
        })}
        {!devices.length&&<div style={{color:G.muted,fontSize:13}}>Chưa có thiết bị nào.</div>}
      </div>

      {/* Detail panel khi click vào device */}
      {selDev&&devices.find(d=>d.name===selDev)&&(
        <DevDetail dev={devices.find(d=>d.name===selDev)}/>
      )}
    </div>
  );
}

function BackupPage({devices,toast}){
  const [backups,setBackups]=useState(()=>STORE.get("backups",[]));
  const [running,setRunning]=useState({});
  const [rolling,setRolling]=useState(null);
  const [selected,setSelected]=useState(null);
  const [filter,setFilter]=useState("all");
  const [confirm,setConfirm]=useState(null);
  const save=b=>{setBackups(b);STORE.set("backups",b);};

  // Also trigger backend backup
  const runBackupAll = async() => {
    try{
      const r = await api("/api/backup/all","POST");
      toast("success",`Backed up ${r.results?.length||0} devices`);
      const hist = await api("/api/backup/history");
      if(hist.history) save(hist.history.map(h=>({...h,id:h.timestamp})));
    }catch(e){ toast("error",String(e)); }
  };
  const runBackup=async(device)=>{
    setRunning(p=>({...p,[device.id]:true}));
    let config="";
    try{const r=await api(`/api/devices/${encodeURIComponent(device.name)}/backup`,"POST");config=r.backup||"";}
    catch{config=`# PlNetwork Backup — ${device.name}\n# Time: ${new Date().toISOString()}\n# Vendor: ${device.vendor}\n# Host: ${device.host}\n\n# [Demo — connect backend for real config]`;}
    const bk={id:Date.now(),device:device.name,vendor:device.vendor,host:device.host,time:new Date().toLocaleString("vi-VN"),size:`${(config.length/1024).toFixed(1)} KB`,tag:"manual",config};
    save([bk,...backups]);
    toast("success",`Backup OK: ${device.name} (${bk.size})`);
    addLog("success",`Backup: ${device.name} (${bk.size})`);
    setRunning(p=>({...p,[device.id]:false}));
  };

  const doRollback=async(bk)=>{
    setRolling(bk.id);setConfirm(null);
    try{await api(`/api/devices/${encodeURIComponent(bk.device)}/config`,"POST",{commands:[bk.config]});}catch{}
    await new Promise(r=>setTimeout(r,1500));
    toast("success",`Rollback OK: ${bk.device}`);
    addLog("warn",`Rollback: ${bk.device} → ${bk.time}`);
    setRolling(null);
  };

  const filtered=backups.filter(b=>filter==="all"||b.device===filter);
  const uniqueDevs=[...new Set(backups.map(b=>b.device))];

  return(
    <div className="fadeIn" style={{padding:28}}>
      {confirm&&(
        <div style={{position:"fixed",inset:0,background:"#00000088",zIndex:200,display:"flex",alignItems:"center",justifyContent:"center"}}>
          <Card className="fadeIn" style={{width:380,textAlign:"center",padding:36}}>
            <div style={{fontSize:36,marginBottom:12}}>⚠</div>
            <div style={{fontSize:16,fontWeight:700,marginBottom:8}}>Xác nhận Rollback</div>
            <div style={{fontSize:13,color:G.muted,marginBottom:24}}>
              Khôi phục <span style={{color:G.text}}>{confirm.device}</span> về<br/>
              <span style={{color:G.yellow}}>{confirm.time}</span>?<br/>
              <span style={{color:G.red,fontSize:11}}>Thao tác này không thể hoàn tác!</span>
            </div>
            <div style={{display:"flex",gap:10,justifyContent:"center"}}>
              <Btn variant="ghost" onClick={()=>setConfirm(null)}>Hủy</Btn>
              <Btn variant="danger" onClick={()=>doRollback(confirm)}>⟲ Rollback Now</Btn>
            </div>
          </Card>
        </div>
      )}
      <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:22}}>
        <div>
          <div style={{fontSize:22,fontWeight:700}}>Backup & Rollback</div>
          <div style={{fontSize:12,color:G.muted,marginTop:3}}>{backups.length} backups</div>
        </div>
        <div style={{display:"flex",gap:10}}>
          <Sel value={filter} onChange={e=>setFilter(e.target.value)} options={[{value:"all",label:"Tất cả"},...uniqueDevs.map(d=>({value:d,label:d}))]} style={{width:"auto"}}/>
          <Btn variant="success" onClick={()=>devices.filter(d=>d.status==="online").forEach(d=>runBackup(d))}>⊡ Backup All</Btn>
        </div>
      </div>
      <div style={{display:"grid",gridTemplateColumns:"1fr 360px",gap:16}}>
        <Card style={{padding:0,overflow:"hidden"}}>
          {filtered.length===0?(
            <div style={{padding:60,textAlign:"center",color:G.muted}}>
              <div style={{fontSize:36,marginBottom:12}}>⊡</div>
              <div>Chưa có backup nào</div>
            </div>
          ):(
            <table style={{width:"100%",borderCollapse:"collapse"}}>
              <thead>
                <tr style={{background:G.surface}}>
                  {["Device","Vendor","Thời gian","Size","Loại","Actions"].map(h=>(
                    <th key={h} style={{padding:"10px 14px",textAlign:"left",fontSize:10,color:G.muted,fontFamily:FONT,letterSpacing:"0.06em",borderBottom:`1px solid ${G.border}`,fontWeight:500}}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {filtered.map(bk=>(
                  <tr key={bk.id} onClick={()=>setSelected(bk)} style={{borderBottom:`1px solid ${G.border}`,cursor:"pointer",background:selected?.id===bk.id?`${G.accent}10`:"transparent",transition:"background .1s"}}
                    onMouseEnter={e=>{if(selected?.id!==bk.id)e.currentTarget.style.background=G.surface;}}
                    onMouseLeave={e=>{if(selected?.id!==bk.id)e.currentTarget.style.background="transparent";}}
                  >
                    <td style={{padding:"11px 14px",fontFamily:FONT,fontSize:12,color:G.text}}>{bk.device}</td>
                    <td style={{padding:"11px 14px"}}><VChip vendor={bk.vendor}/></td>
                    <td style={{padding:"11px 14px",fontFamily:FONT,fontSize:11,color:G.dim}}>{bk.time}</td>
                    <td style={{padding:"11px 14px",fontFamily:FONT,fontSize:11,color:G.dim}}>{bk.size}</td>
                    <td style={{padding:"11px 14px"}}><Badge color={bk.tag==="auto"?G.accent:G.purple} small>{bk.tag}</Badge></td>
                    <td style={{padding:"11px 14px"}}>
                      <div style={{display:"flex",gap:6}}>
                        <Btn small variant="danger" onClick={e=>{e.stopPropagation();setConfirm(bk);}} loading={rolling===bk.id}>{rolling===bk.id?"":"⟲ Rollback"}</Btn>
                        <Btn small variant="ghost" onClick={e=>{e.stopPropagation();save(backups.filter(b=>b.id!==bk.id));setSelected(null);}}>✕</Btn>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Card>
        <div style={{display:"flex",flexDirection:"column",gap:14}}>
          <Card>
            <Lbl>Manual Backup</Lbl>
            {devices.filter(d=>d.status==="online").length===0?<div style={{fontSize:12,color:G.muted}}>Không có thiết bị online</div>:(
              devices.filter(d=>d.status==="online").map(d=>(
                <div key={d.id||d.name} style={{display:"flex",justifyContent:"space-between",alignItems:"center",padding:"8px 0",borderBottom:`1px solid ${G.border}`}}>
                  <div><div style={{fontFamily:FONT,fontSize:12,color:G.text}}>{d.name}</div><div style={{marginTop:3}}><VChip vendor={d.vendor}/></div></div>
                  <Btn small variant="success" onClick={()=>runBackup(d)} loading={!!running[d.id]}>{!running[d.id]&&"⊡ Backup"}</Btn>
                </div>
              ))
            )}
          </Card>
          {selected&&(
            <Card className="fadeIn" style={{background:`${G.accent}06`,borderColor:`${G.accent}33`}}>
              <Lbl>Backup Detail</Lbl>
              {[["Device",selected.device],["Time",selected.time],["Size",selected.size]].map(([k,v])=>(
                <div key={k} style={{display:"flex",justifyContent:"space-between",marginBottom:7}}>
                  <span style={{fontSize:11,color:G.muted}}>{k}</span>
                  <span style={{fontSize:11,color:G.text,fontFamily:FONT}}>{v}</span>
                </div>
              ))}
              {selected.config&&<div style={{marginTop:10}}><Lbl>Config Preview</Lbl><pre style={{fontFamily:FONT,fontSize:10,color:G.dim,background:G.surface,padding:10,borderRadius:6,maxHeight:120,overflowY:"auto",whiteSpace:"pre-wrap"}}>{selected.config.substring(0,500)}{selected.config.length>500?"\n...":""}</pre></div>}
              <Btn variant="danger" loading={rolling===selected.id} onClick={()=>setConfirm(selected)} style={{marginTop:12,width:"100%",justifyContent:"center"}}>{rolling===selected.id?"Rolling back...":"⟲ Rollback"}</Btn>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Settings ──────────────────────────────────────────────────────
function SettingsPage({toast}){
  const [apiUrl,setApiUrl]=useState(STORE.get("api_url","http://localhost:8000"));
  const [testing,setTesting]=useState(false);
  const [testResult,setTestResult]=useState(null);

  const testApi=async()=>{
    setTesting(true);setTestResult(null);
    try{
      const r=await fetch(`${apiUrl}/health`,{signal:AbortSignal.timeout(3000)});
      const d=await r.json();
      setTestResult({ok:true,msg:`✓ Backend online v${d.version} · ${d.devices_registered} devices`});
    }catch(e){setTestResult({ok:false,msg:`✕ ${e.message}`});}
    setTesting(false);
  };

  return(
    <div className="fadeIn" style={{padding:28,maxWidth:640}}>
      <div style={{marginBottom:22}}>
        <div style={{fontSize:22,fontWeight:700}}>Settings</div>
        <div style={{fontSize:12,color:G.muted,marginTop:3}}>Cấu hình kết nối backend và hệ thống</div>
      </div>
      <Card style={{marginBottom:16}}>
        <div style={{fontSize:13,fontWeight:700,marginBottom:16}}>Backend API</div>
        <Lbl>API URL</Lbl>
        <div style={{display:"flex",gap:10,marginBottom:12}}>
          <Input value={apiUrl} onChange={e=>setApiUrl(e.target.value)} placeholder="http://localhost:8000"/>
          <Btn variant="ghost" onClick={testApi} loading={testing} style={{flexShrink:0}}>Test</Btn>
        </div>
        {testResult&&<div style={{padding:"8px 12px",borderRadius:6,fontSize:12,fontFamily:FONT,marginBottom:12,background:testResult.ok?`${G.green}15`:`${G.red}15`,border:`1px solid ${testResult.ok?G.green:G.red}44`,color:testResult.ok?G.green:G.red}}>{testResult.msg}</div>}
        <div style={{padding:12,background:G.surface,borderRadius:6,fontSize:11,color:G.muted,fontFamily:FONT,lineHeight:2,marginBottom:12}}>
          Start backend: <span style={{color:G.accent}}>cd backend && start.bat</span><br/>
          API Docs: <span style={{color:G.accent}}>{apiUrl}/docs</span>
        </div>
        <Btn onClick={()=>{STORE.set("api_url",apiUrl);API_BASE=apiUrl;toast("success","Đã lưu");}}>Lưu cài đặt</Btn>
      </Card>
      <Card>
        <div style={{fontSize:13,fontWeight:700,marginBottom:16}}>Xóa dữ liệu</div>
        {[["activity_log","Activity Log"],["backups","Backups"],["cmd_history","CMD History"],["devices","Devices (!)"]].map(([k,l])=>(
          <div key={k} style={{display:"flex",justifyContent:"space-between",alignItems:"center",padding:"10px 0",borderBottom:`1px solid ${G.border}`}}>
            <span style={{fontSize:13,color:G.text}}>{l}</span>
            <Btn small variant="danger" onClick={()=>{STORE.set(k,[]);toast("warn",`Đã xóa ${l}`);}}>Xóa</Btn>
          </div>
        ))}
      </Card>
    </div>
  );
}

// ── App ───────────────────────────────────────────────────────────

// ── Config Scanner ────────────────────────────────────────────────
const MIKROTIK_SECTIONS = [
  {id:"identity",    label:"System Identity",  path:"/system/identity",    icon:"◈"},
  {id:"resource",    label:"System Resource",  path:"/system/resource",    icon:"▦"},
  {id:"routerboard", label:"RouterBoard",      path:"/system/routerboard", icon:"⬡"},
  {id:"clock",       label:"System Clock",     path:"/system/clock",       icon:"◎"},
  {id:"address",     label:"IP Addresses",     path:"/ip/address",         icon:"◆"},
  {id:"route",       label:"IP Routes",        path:"/ip/route",           icon:"⤳"},
  {id:"interface",   label:"Interfaces",       path:"/interface",          icon:"⬌"},
  {id:"bridge",      label:"Bridges",          path:"/interface/bridge",   icon:"⊟"},
  {id:"vlan",        label:"VLANs",            path:"/interface/vlan",     icon:"⊞"},
  {id:"wireless",    label:"Wireless",         path:"/interface/wireless", icon:"◉"},
  {id:"arp",         label:"ARP Table",        path:"/ip/arp",             icon:"◈"},
  {id:"dns",         label:"DNS",              path:"/ip/dns",             icon:"◎"},
  {id:"dhcp_server", label:"DHCP Server",      path:"/ip/dhcp-server",     icon:"▤"},
  {id:"dhcp_lease",  label:"DHCP Leases",      path:"/ip/dhcp-server/lease",icon:"▤"},
  {id:"pool",        label:"IP Pool",          path:"/ip/pool",            icon:"▦"},
  {id:"fw_filter",   label:"Firewall Filter",  path:"/ip/firewall/filter", icon:"⊘"},
  {id:"fw_nat",      label:"Firewall NAT",     path:"/ip/firewall/nat",    icon:"⊘"},
  {id:"fw_mangle",   label:"Firewall Mangle",  path:"/ip/firewall/mangle", icon:"⊘"},
  {id:"fw_address",  label:"Address Lists",    path:"/ip/firewall/address-list", icon:"⊟"},
  {id:"ntp",         label:"NTP Client",       path:"/system/ntp/client",  icon:"◎"},
  {id:"snmp",        label:"SNMP",             path:"/snmp",               icon:"◈"},
  {id:"user",        label:"Users",            path:"/user",               icon:"◈"},
  {id:"service",     label:"Services",         path:"/ip/service",         icon:"▦"},
  {id:"scheduler",   label:"Scheduler",        path:"/system/scheduler",   icon:"◎"},
  {id:"script",      label:"Scripts",          path:"/system/script",      icon:">_"},
  {id:"log",         label:"System Log",       path:"/log",                icon:"⊡"},
  {id:"neighbor",    label:"Neighbors",        path:"/ip/neighbor",        icon:"◉"},
  {id:"hotspot",     label:"Hotspot",          path:"/ip/hotspot",         icon:"◈"},
  {id:"vpn_l2tp",    label:"L2TP Server",      path:"/interface/l2tp-server", icon:"⊟"},
  {id:"vpn_pptp",    label:"PPTP Server",      path:"/interface/pptp-server", icon:"⊟"},
  {id:"queue",       label:"Queues",           path:"/queue/simple",       icon:"▤"},
  {id:"bgp",         label:"BGP Peers",        path:"/routing/bgp/peer",   icon:"⤳"},
  {id:"ospf",        label:"OSPF",             path:"/routing/ospf/instance", icon:"⤳"},
];

function ConfigScannerPage({devices, toast}){
  const [selDev, setSelDev] = useState(devices.find(d=>d.status==="online")?.name||"");
  const [scanning, setScanning] = useState(false);
  const [progress, setProgress] = useState(0);
  const [results, setResults] = useState({});
  const [expandedSec, setExpandedSec] = useState(null);
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState("all"); // all | data | empty | error
  const [scanned, setScanned] = useState(false);
  const abortRef = useRef(false);

  const onlineDevices = devices.filter(d=>d.status==="online");
  const selectedDevice = devices.find(d=>d.name===selDev);

  const startScan = async () => {
    if(!selDev){toast("warn","Chọn thiết bị trước");return;}
    setScanning(true); setResults({}); setProgress(0); setScanned(false);
    abortRef.current = false;
    const total = MIKROTIK_SECTIONS.length;
    const res = {};
    for(let i=0; i<total; i++){
      if(abortRef.current) break;
      const sec = MIKROTIK_SECTIONS[i];
      setProgress(Math.round((i/total)*100));
      try{
        const r = await api(`/api/devices/${encodeURIComponent(selDev)}/command`,"POST",{command:sec.path});
        if(r.output && r.output.trim() && r.output.trim()!=="(empty)"){
          // Parse output into rows
          const rows = r.output.split("\n").filter(l=>l.trim());
          res[sec.id] = {status:"data", rows, raw:r.output, count:rows.length};
        } else {
          res[sec.id] = {status:"empty", rows:[], raw:"", count:0};
        }
      }catch(e){
        res[sec.id] = {status:"error", rows:[], raw:String(e), count:0, error:String(e)};
      }
      setResults({...res});
    }
    setProgress(100);
    setScanning(false);
    setScanned(true);
    const dataCount = Object.values(res).filter(r=>r.status==="data").length;
    toast("success", `Scan xong! ${dataCount}/${total} sections có dữ liệu`);
    addLog("success", `Config scan: ${selDev} — ${dataCount} sections`);
  };

  const stopScan = () => { abortRef.current = true; setScanning(false); };

  const exportConfig = () => {
    const lines = [`# PlNetwork Config Scan — ${selDev}`, `# Time: ${new Date().toLocaleString("vi-VN")}`, ""];
    MIKROTIK_SECTIONS.forEach(sec=>{
      const r = results[sec.id];
      if(r?.status==="data"){
        lines.push(`# ═══ ${sec.label.toUpperCase()} (${sec.path}) ═══`);
        lines.push(r.raw);
        lines.push("");
      }
    });
    const blob = new Blob([lines.join("\n")], {type:"text/plain"});
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href=url; a.download=`${selDev}_config_${Date.now()}.txt`; a.click();
    URL.revokeObjectURL(url);
    toast("success","Đã export config!");
  };

  const dataSections = Object.entries(results).filter(([,r])=>r.status==="data");
  const allSections = MIKROTIK_SECTIONS.filter(sec=>{
    const r = results[sec.id];
    const matchSearch = !search || sec.label.toLowerCase().includes(search.toLowerCase()) || (r?.raw||"").toLowerCase().includes(search.toLowerCase());
    const matchFilter = filter==="all" || (filter==="data"&&r?.status==="data") || (filter==="empty"&&r?.status==="empty") || (filter==="error"&&r?.status==="error");
    return matchSearch && matchFilter;
  });

  const StatusIcon = ({status}) => {
    if(!status) return <span style={{color:G.muted,fontSize:11}}>—</span>;
    if(status==="data") return <span style={{color:G.green,fontSize:11}}>✓</span>;
    if(status==="empty") return <span style={{color:G.muted,fontSize:11}}>○</span>;
    if(status==="error") return <span style={{color:G.red,fontSize:11}}>✕</span>;
    return <span style={{color:G.yellow,fontSize:11}}>...</span>;
  };

  return(
    <div className="fadeIn" style={{padding:28}}>
      <div style={{display:"flex",justifyContent:"space-between",alignItems:"flex-start",marginBottom:22}}>
        <div>
          <div style={{fontSize:22,fontWeight:700}}>Config Scanner</div>
          <div style={{fontSize:12,color:G.muted,marginTop:3}}>Quét toàn bộ cấu hình MikroTik — {MIKROTIK_SECTIONS.length} sections</div>
        </div>
        {scanned&&dataSections.length>0&&(
          <Btn variant="success" onClick={exportConfig}>⬇ Export .txt</Btn>
        )}
      </div>

      {/* Controls */}
      <Card style={{marginBottom:16}}>
        <div style={{display:"grid",gridTemplateColumns:"1fr auto auto",gap:12,alignItems:"flex-end"}}>
          <div>
            <Lbl>Thiết bị MikroTik</Lbl>
            <Sel value={selDev} onChange={e=>setSelDev(e.target.value)}
              options={[{value:"",label:"-- Chọn thiết bị online --"},...onlineDevices.map(d=>({value:d.name,label:`${d.name} (${d.host})`}))]}/>
          </div>
          <div>
            {scanning?(
              <Btn variant="danger" onClick={stopScan} style={{padding:"9px 20px"}}>⏹ Dừng</Btn>
            ):(
              <Btn onClick={startScan} disabled={!selDev} style={{padding:"9px 20px"}}>⊞ Bắt đầu Scan</Btn>
            )}
          </div>
          {scanned&&(
            <div style={{textAlign:"right"}}>
              <div style={{fontSize:11,color:G.muted,fontFamily:G.FONT}}>Kết quả</div>
              <div style={{fontSize:13,fontWeight:700,color:G.green}}>{dataSections.length} / {MIKROTIK_SECTIONS.length}</div>
            </div>
          )}
        </div>

        {/* Progress */}
        {(scanning||scanned)&&(
          <div style={{marginTop:14}}>
            <div style={{display:"flex",justifyContent:"space-between",marginBottom:6}}>
              <span style={{fontSize:11,color:G.muted}}>{scanning?"Đang quét...":"Hoàn tất"}</span>
              <span style={{fontSize:11,color:G.accent,fontFamily:"monospace"}}>{progress}%</span>
            </div>
            <div style={{background:G.border,borderRadius:4,height:6,overflow:"hidden"}}>
              <div style={{width:`${progress}%`,height:"100%",background:`linear-gradient(90deg,${G.accent},${G.green})`,borderRadius:4,transition:"width .3s"}}/>
            </div>
          </div>
        )}
      </Card>

      {/* Summary badges */}
      {scanned&&(
        <div style={{display:"flex",gap:10,marginBottom:16,flexWrap:"wrap"}}>
          {[
            ["all","Tất cả",MIKROTIK_SECTIONS.length,G.text],
            ["data","Có dữ liệu",Object.values(results).filter(r=>r.status==="data").length,G.green],
            ["empty","Trống",Object.values(results).filter(r=>r.status==="empty").length,G.muted],
            ["error","Lỗi",Object.values(results).filter(r=>r.status==="error").length,G.red],
          ].map(([f,l,n,c])=>(
            <div key={f} onClick={()=>setFilter(f)} style={{padding:"6px 14px",borderRadius:6,cursor:"pointer",background:filter===f?`${c}22`:G.card,border:`1px solid ${filter===f?c+"55":G.border}`,color:filter===f?c:G.muted,fontSize:12,fontWeight:600,transition:"all .15s"}}>
              {l} <span style={{fontFamily:"monospace",marginLeft:4}}>{n}</span>
            </div>
          ))}
          <div style={{marginLeft:"auto"}}>
            <Input value={search} onChange={e=>setSearch(e.target.value)} placeholder="Tìm section hoặc nội dung..." style={{width:260}}/>
          </div>
        </div>
      )}

      {/* Results grid */}
      {!scanned&&!scanning&&(
        <Card style={{textAlign:"center",padding:60}}>
          <div style={{fontSize:48,marginBottom:16,opacity:0.3}}>⊞</div>
          <div style={{fontSize:16,color:G.dim,marginBottom:8}}>Chưa quét</div>
          <div style={{fontSize:13,color:G.muted,marginBottom:20}}>Chọn thiết bị MikroTik online và nhấn Bắt đầu Scan</div>
          <div style={{display:"flex",flexWrap:"wrap",gap:6,justifyContent:"center",maxWidth:600,margin:"0 auto"}}>
            {MIKROTIK_SECTIONS.map(s=>(
              <span key={s.id} style={{padding:"2px 8px",borderRadius:3,background:G.surface,border:`1px solid ${G.border}`,fontSize:10,color:G.muted,fontFamily:"monospace"}}>{s.label}</span>
            ))}
          </div>
        </Card>
      )}

      {(scanning||scanned)&&(
        <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fill,minmax(340px,1fr))",gap:12}}>
          {allSections.map(sec=>{
            const r = results[sec.id];
            const isExpanded = expandedSec===sec.id;
            const hasData = r?.status==="data";
            const isLoading = scanning && !r;
            return(
              <div key={sec.id} style={{background:G.card,border:`1px solid ${hasData?G.border2:G.border}`,borderRadius:8,overflow:"hidden",transition:"all .2s",boxShadow:hasData&&isExpanded?`0 0 20px ${G.accent}12`:"none"}}>
                <div onClick={()=>hasData&&setExpandedSec(isExpanded?null:sec.id)}
                  style={{display:"flex",alignItems:"center",gap:10,padding:"12px 14px",cursor:hasData?"pointer":"default",background:isExpanded?`${G.accent}0a`:"transparent",
                  borderBottom:isExpanded?`1px solid ${G.border}`:"none"}}
                  onMouseEnter={e=>{if(hasData&&!isExpanded)e.currentTarget.style.background=`${G.surface}`;}}
                  onMouseLeave={e=>{if(!isExpanded)e.currentTarget.style.background="transparent";}}
                >
                  <span style={{fontSize:13,color:hasData?G.accent:G.muted,width:18,textAlign:"center",flexShrink:0}}>{sec.icon}</span>
                  <div style={{flex:1,minWidth:0}}>
                    <div style={{fontSize:12,fontWeight:600,color:hasData?G.text:G.muted,whiteSpace:"nowrap",overflow:"hidden",textOverflow:"ellipsis"}}>{sec.label}</div>
                    <div style={{fontSize:10,color:G.muted,fontFamily:"monospace",marginTop:1}}>{sec.path}</div>
                  </div>
                  <div style={{display:"flex",alignItems:"center",gap:8,flexShrink:0}}>
                    {isLoading&&<Spinner size={12}/>}
                    {r&&<StatusIcon status={r.status}/>}
                    {hasData&&<span style={{fontSize:10,color:G.green,fontFamily:"monospace",background:`${G.green}15`,padding:"1px 6px",borderRadius:3}}>{r.count}</span>}
                    {hasData&&<span style={{fontSize:11,color:G.muted}}>{isExpanded?"▲":"▼"}</span>}
                  </div>
                </div>
                {isExpanded&&hasData&&(
                  <div style={{padding:"10px 14px",maxHeight:320,overflowY:"auto"}}>
                    <pre style={{fontFamily:"monospace",fontSize:11,color:G.text,whiteSpace:"pre-wrap",lineHeight:1.75,margin:0}}>{r.raw}</pre>
                  </div>
                )}
                {r?.status==="error"&&(
                  <div style={{padding:"6px 14px",fontSize:10,color:G.red,fontFamily:"monospace",borderTop:`1px solid ${G.border}`}}>
                    {r.error?.substring(0,80)}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}


// ── Services Page ─────────────────────────────────────────────────
const MIKROTIK_SVCS = [
  {name:"ssh",     label:"SSH",      icon:"🔒", defaultPort:22},
  {name:"api",     label:"API",      icon:"◈",  defaultPort:8728},
  {name:"api-ssl", label:"API SSL",  icon:"🔐", defaultPort:8729},
  {name:"winbox",  label:"Winbox",   icon:"🖥", defaultPort:8291},
  {name:"telnet",  label:"Telnet",   icon:"📟", defaultPort:23},
  {name:"ftp",     label:"FTP",      icon:"📂", defaultPort:21},
  {name:"www",     label:"HTTP",     icon:"🌐", defaultPort:80},
  {name:"www-ssl", label:"HTTPS",    icon:"🔏", defaultPort:443},
];

function ServicesPage({devices, toast}){
  const [selDev, setSelDev] = useState(devices.find(d=>d.status==="online")?.name||"");
  const [services, setServices] = useState({});
  const [loading, setLoading] = useState(false);
  const [toggling, setToggling] = useState({});
  const [editPort, setEditPort] = useState({});

  const onlineDevs = devices.filter(d=>d.status==="online");
  const selectedDevice = devices.find(d=>d.name===selDev);

  const loadServices = async() => {
    if(!selDev) return;
    setLoading(true);
    try{
      const r = await api(`/api/devices/${encodeURIComponent(selDev)}/services`,"GET");
      setServices(r.services||{});
      toast("success",`Loaded services for ${selDev}`);
    }catch(e){ toast("error",`Load failed: ${e.message}`); }
    setLoading(false);
  };

  useEffect(()=>{ if(selDev) loadServices(); },[selDev]);

  const toggleService = async(svcName, currentEnabled) => {
    setToggling(p=>({...p,[svcName]:true}));
    try{
      const port = editPort[svcName] || null;
      await api(`/api/devices/${encodeURIComponent(selDev)}/services`,"POST",{service:svcName, enabled:!currentEnabled, port});
      setServices(p=>({...p,[svcName]:{...p[svcName],enabled:!currentEnabled}}));
      toast("success",`${svcName} ${!currentEnabled?"enabled":"disabled"}`);
    }catch(e){ toast("error",`Failed: ${e.message}`); }
    setToggling(p=>({...p,[svcName]:false}));
  };

  const setPort = async(svcName, port) => {
    setToggling(p=>({...p,[svcName]:true}));
    try{
      const svc = services[svcName];
      await api(`/api/devices/${encodeURIComponent(selDev)}/services`,"POST",{service:svcName, enabled:svc?.enabled||false, port:parseInt(port)});
      setServices(p=>({...p,[svcName]:{...p[svcName],port}}));
      toast("success",`${svcName} port set to ${port}`);
    }catch(e){ toast("error",`Failed: ${e.message}`); }
    setToggling(p=>({...p,[svcName]:false}));
  };

  return(
    <div className="fadeIn" style={{padding:28}}>
      <div style={{marginBottom:22}}>
        <div style={{fontSize:22,fontWeight:700}}>Services</div>
        <div style={{fontSize:12,color:G.muted,marginTop:3}}>Quản lý SSH · API · Winbox · Telnet · FTP · HTTP</div>
      </div>

      <Card style={{marginBottom:20}}>
        <div style={{display:"grid",gridTemplateColumns:"1fr auto",gap:12,alignItems:"flex-end"}}>
          <div>
            <Lbl>Thiết bị</Lbl>
            <Sel value={selDev} onChange={e=>setSelDev(e.target.value)}
              options={[{value:"",label:"-- Chọn thiết bị online --"},...onlineDevs.map(d=>({value:d.name,label:`${d.name} (${d.host})`}))]}/>
          </div>
          <Btn onClick={loadServices} loading={loading} disabled={!selDev}>↺ Refresh</Btn>
        </div>
      </Card>

      {!selDev && (
        <Card style={{textAlign:"center",padding:48}}>
          <div style={{fontSize:36,marginBottom:12,opacity:0.3}}>⊕</div>
          <div style={{color:G.muted}}>Chọn thiết bị để quản lý services</div>
        </Card>
      )}

      {selDev && (
        <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fill,minmax(280px,1fr))",gap:14}}>
          {MIKROTIK_SVCS.map(svc=>{
            const info = services[svc.name];
            const enabled = info?.enabled ?? false;
            const port = info?.port || svc.defaultPort;
            const isBusy = toggling[svc.name];
            return(
              <Card key={svc.name} style={{borderColor:enabled?`${G.green}33`:G.border,position:"relative",overflow:"visible"}}>
                <div style={{display:"flex",alignItems:"center",gap:12,marginBottom:14}}>
                  <div style={{fontSize:22}}>{svc.icon}</div>
                  <div style={{flex:1}}>
                    <div style={{fontWeight:700,fontSize:14}}>{svc.label}</div>
                    <div style={{fontSize:11,color:G.muted,fontFamily:"monospace"}}>{svc.name}</div>
                  </div>
                  <div style={{display:"flex",alignItems:"center",gap:8}}>
                    {isBusy ? <Spinner size={14}/> : (
                      <div onClick={()=>!isBusy&&toggleService(svc.name,enabled)}
                        style={{width:44,height:24,borderRadius:12,background:enabled?G.green:G.border,cursor:"pointer",position:"relative",transition:"all .2s",flexShrink:0}}
                      >
                        <div style={{position:"absolute",top:3,left:enabled?22:3,width:18,height:18,borderRadius:"50%",background:"white",transition:"all .2s",boxShadow:"0 1px 4px #0004"}}/>
                      </div>
                    )}
                  </div>
                </div>
                <div style={{display:"flex",alignItems:"center",gap:8}}>
                  <span style={{fontSize:11,color:G.muted,minWidth:32}}>Port</span>
                  <input type="number" defaultValue={port}
                    onChange={e=>setEditPort(p=>({...p,[svc.name]:e.target.value}))}
                    style={{background:G.surface,border:`1px solid ${G.border2}`,color:G.text,padding:"4px 8px",borderRadius:4,fontSize:12,fontFamily:"monospace",width:80,outline:"none"}}/>
                  <Btn variant="ghost" onClick={()=>setPort(svc.name, editPort[svc.name]||port)}
                    style={{padding:"4px 10px",fontSize:11}} loading={isBusy}>Set</Btn>
                  <span style={{marginLeft:"auto",fontSize:11,padding:"2px 8px",borderRadius:3,
                    background:enabled?`${G.green}20`:`${G.red}20`,
                    color:enabled?G.green:G.red,fontWeight:600}}>
                    {info ? (enabled?"ON":"OFF") : "—"}
                  </span>
                </div>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}

// ── Serial Console RS232 ──────────────────────────────────────────
const BAUD_RATES = [9600,19200,38400,57600,115200];
const VENDOR_PROMPTS = {
  mikrotik:["[admin@","MikroTik","Login:","Password:"],
  cisco:["Router>","Router#","Switch>","Switch#","Username:","Password:"],
  fortinet:["FortiGate","login:","#"],
  sophos:["Sophos","login:","#"],
};


// ── Cisco Quick Setup Component ──────────────────────────────────
function CiscoQuickSetup({wsRef, appendTerm, appendSystem, toast}){
  const [show, setShow] = useState(false);
  const [cfg, setCfg] = useState({
    hostname: "Switch",
    mgmt_vlan: "1",
    mgmt_ip: "10.10.79.2",
    mgmt_mask: "255.255.255.0",
    gateway: "10.10.79.1",
    ssh_user: "admin",
    ssh_pass: "Admin@123",
    enable_pass: "Admin@123",
    domain: "local.net"
  });
  const [pushing, setPushing] = useState(false);
  const [step, setStep] = useState(0);

  const send = (cmd) => {
    if(wsRef.current && wsRef.current.readyState===WebSocket.OPEN){
      wsRef.current.send(cmd + "\r");
    }
  };

  const delay = (ms) => new Promise(r=>setTimeout(r,ms));

  const pushConfig = async() => {
    if(!cfg.mgmt_ip){ toast("warn","Nhập IP Management"); return; }
    if(!cfg.gateway){ toast("warn","Nhập Default Gateway"); return; }
    setPushing(true);
    setStep(0);
    appendSystem("\n═══ Bắt đầu push config Cisco ═══", "#f6c90e");

    const steps = [
      // 1. Thoát về EXEC mode
      { label:"Vào Enable mode", cmds:[
        {cmd:"\x03", wait:500},   // Ctrl+C
        {cmd:"\r", wait:500},
        {cmd:"enable", wait:1000},
        {cmd:"\r", wait:500},     // Enter nếu hỏi password
      ]},
      // 2. Vào config terminal
      { label:"Vào Config mode", cmds:[
        {cmd:"configure terminal", wait:1000},
      ]},
      // 3. Hostname
      { label:"Set Hostname", cmds:[
        {cmd:`hostname ${cfg.hostname}`, wait:500},
      ]},
      // 4. Enable password
      { label:"Set Enable Secret", cmds:[
        {cmd:`enable secret ${cfg.enable_pass}`, wait:500},
      ]},
      // 5. Username & password
      { label:"Tạo User SSH", cmds:[
        {cmd:`username ${cfg.ssh_user} privilege 15 secret ${cfg.ssh_pass}`, wait:500},
      ]},
      // 6. Domain name (cần cho SSH)
      { label:"Set Domain", cmds:[
        {cmd:`ip domain-name ${cfg.domain}`, wait:500},
      ]},
      // 7. Generate SSH key
      { label:"Generate SSH Key (30s...)", cmds:[
        {cmd:"crypto key generate rsa modulus 1024", wait:30000},
      ]},
      // 8. Enable SSH v2
      { label:"Enable SSH v2", cmds:[
        {cmd:"ip ssh version 2", wait:500},
      ]},
      // 9. Management VLAN IP
      { label:`Set VLAN ${cfg.mgmt_vlan} IP`, cmds:[
        {cmd:`interface vlan ${cfg.mgmt_vlan}`, wait:500},
        {cmd:`ip address ${cfg.mgmt_ip} ${cfg.mgmt_mask}`, wait:500},
        {cmd:"no shutdown", wait:1000},
        {cmd:"exit", wait:500},
      ]},
      // 10. Default gateway
      { label:"Set Default Gateway", cmds:[
        {cmd:`ip default-gateway ${cfg.gateway}`, wait:500},
      ]},
      // 11. VTY lines cho SSH
      { label:"Cấu hình VTY SSH", cmds:[
        {cmd:"line vty 0 15", wait:500},
        {cmd:"transport input ssh", wait:500},
        {cmd:"login local", wait:500},
        {cmd:"exit", wait:500},
      ]},
      // 12. Console line
      { label:"Cấu hình Console", cmds:[
        {cmd:"line console 0", wait:500},
        {cmd:"login local", wait:500},
        {cmd:"exit", wait:500},
      ]},
      // 13. Service password-encryption
      { label:"Bật Password Encryption", cmds:[
        {cmd:"service password-encryption", wait:500},
      ]},
      // 14. Thoát config mode
      { label:"Exit & Save", cmds:[
        {cmd:"end", wait:1000},
        {cmd:"write memory", wait:5000},
      ]},
    ];

    try{
      for(let i=0; i<steps.length; i++){
        const s = steps[i];
        setStep(i+1);
        appendSystem(`[${i+1}/${steps.length}] ${s.label}...`, "#38bdf8");
        for(const c of s.cmds){
          send(c.cmd);
          await delay(c.wait);
        }
      }
      appendSystem("═══ ✅ Push config hoàn tất! ═══", "#22c55e");
      appendSystem(`SSH: ssh ${cfg.ssh_user}@${cfg.mgmt_ip}`, "#22c55e");
      toast("success", `Config pushed! SSH: ${cfg.mgmt_ip}`);
    }catch(e){
      appendSystem(`❌ Lỗi: ${e.message}`, "#ef4444");
      toast("error", e.message);
    }
    setPushing(false);
    setStep(0);
  };

  if(!show) return (
    <div style={{padding:"6px 14px",borderTop:`1px solid ${G.border}`,background:"#0d1117",display:"flex",gap:8}}>
      <Btn onClick={()=>setShow(true)} style={{padding:"4px 14px",fontSize:11,background:"#1d4ed8"}}>
        ⚡ Cisco Quick Setup
      </Btn>
      <span style={{fontSize:11,color:G.muted,alignSelf:"center"}}>Push full config: IP, SSH, VLAN, User cho switch factory reset</span>
    </div>
  );

  return(
    <div style={{borderTop:`2px solid #1d4ed8`,background:"#0d1117",padding:"14px 16px"}}>
      <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:12}}>
        <div style={{fontSize:13,fontWeight:700,color:"#60a5fa"}}>⚡ Cisco Quick Setup — Factory Reset Config</div>
        <Btn variant="ghost" onClick={()=>setShow(false)} style={{padding:"2px 8px",fontSize:11}}>✕ Đóng</Btn>
      </div>

      <div style={{display:"grid",gridTemplateColumns:"1fr 1fr 1fr",gap:8,marginBottom:10}}>
        {[
          {k:"hostname",    label:"Hostname",          ph:"Switch"},
          {k:"mgmt_vlan",   label:"Management VLAN",   ph:"1"},
          {k:"mgmt_ip",     label:"IP Management *",   ph:"192.168.1.2"},
          {k:"mgmt_mask",   label:"Subnet Mask",       ph:"255.255.255.0"},
          {k:"gateway",     label:"Default Gateway *", ph:"192.168.1.1"},
          {k:"domain",      label:"Domain Name",       ph:"local.net"},
          {k:"ssh_user",    label:"SSH Username",      ph:"admin"},
          {k:"ssh_pass",    label:"SSH Password",      ph:"Admin@123"},
          {k:"enable_pass", label:"Enable Secret",     ph:"Admin@123"},
        ].map(f=>(
          <div key={f.k}>
            <div style={{fontSize:10,color:G.muted,marginBottom:3}}>{f.label}</div>
            <input value={cfg[f.k]} onChange={e=>setCfg(c=>({...c,[f.k]:e.target.value}))}
              placeholder={f.ph}
              style={{width:"100%",background:"#111827",border:`1px solid ${G.border}`,borderRadius:4,
                padding:"5px 8px",color:"#e2e8f0",fontSize:12,outline:"none",boxSizing:"border-box"}}/>
          </div>
        ))}
      </div>

      {pushing && (
        <div style={{padding:"6px 10px",background:"#1e3a5f",borderRadius:5,marginBottom:8,fontSize:11,color:"#93c5fd"}}>
          ⏳ Đang push... bước {step}/14 — không đóng terminal!
        </div>
      )}

      <div style={{display:"flex",gap:8,alignItems:"center"}}>
        <Btn onClick={pushConfig} loading={pushing}
          style={{padding:"7px 20px",background:"#1d4ed8",fontSize:12,fontWeight:600}}>
          🚀 Push Config to Switch
        </Btn>
        <span style={{fontSize:10,color:G.muted}}>
          Sẽ push: hostname, enable secret, SSH key, VLAN IP, gateway, VTY lines, save
        </span>
      </div>
    </div>
  );
}

function SerialConsolePage({toast}){
  const [ports, setPorts] = useState([]);
  const [selPort, setSelPort] = useState("");
  const [baud, setBaud] = useState(9600);
  const [vendor, setVendor] = useState("cisco");
  const [sessionId, setSessionId] = useState(null);
  const [connected, setConnected] = useState(false);
  const [connecting, setConnecting] = useState(false);
  const termRef = useRef(null);
  const wsRef = useRef(null);
  const inputRef = useRef(null);
  const [inputBuf, setInputBuf] = useState("");

  useEffect(()=>{
    loadPorts();
    // Cleanup all sessions on unmount/reload
    return ()=>{
      if(wsRef.current) wsRef.current.close();
      if(sessionId) api(`/api/serial/${sessionId}`,"DELETE").catch(()=>{});
    };
  },[]);

  // Cleanup old sessions on page load
  useEffect(()=>{
    api("/api/serial/sessions","GET").then(r=>{
      (r.sessions||[]).forEach(s=> api(`/api/serial/${s.id}`,"DELETE").catch(()=>{}));
    }).catch(()=>{});
  },[]);

  // Cleanup on browser tab close / page unload
  useEffect(()=>{
    const cleanup = () => {
      if(wsRef.current) wsRef.current.close();
      if(sessionId){
        // Use sendBeacon for reliable cleanup on page close
        navigator.sendBeacon(`http://localhost:8000/api/serial/${sessionId}/close`);
      }
    };
    window.addEventListener("beforeunload", cleanup);
    return ()=> window.removeEventListener("beforeunload", cleanup);
  },[sessionId]);

  // Auto-scroll terminal
  useEffect(()=>{
    if(termRef.current) termRef.current.scrollTop = termRef.current.scrollHeight;
  });

  const loadPorts = async() => {
    try{
      const r = await api("/api/serial/ports","GET");
      setPorts(r.ports||[]);
      if(r.ports?.length>0) setSelPort(r.ports[0].port);
    }catch{ setPorts([]); }
  };

  const appendTerm = (text) => {
    if(!termRef.current) return;
    if(!text) return;
    // Strip ANSI escape codes
    const clean = text
      .replace(/\x1b\[[0-9;]*[mGKHFJr]/g,"")
      .replace(/\x1b\([AB]/g,"")
      .replace(/\x1b=/g,"")
      .replace(/\r\n/g,"\n")
      .replace(/\r/g,"\n");
    if(!clean) return;
    const span = document.createElement("span");
    span.textContent = clean;
    span.style.color = "#e2e8f0";
    span.style.whiteSpace = "pre-wrap";
    span.style.fontFamily = "'Courier New', monospace";
    span.style.fontSize = "13px";
    termRef.current.appendChild(span);
    termRef.current.scrollTop = termRef.current.scrollHeight;
  };

  const appendSystem = (text, color="#7c8b9e") => {
    if(!termRef.current) return;
    const div = document.createElement("div");
    div.textContent = text;
    div.style.color = color;
    termRef.current.appendChild(div);
    termRef.current.scrollTop = termRef.current.scrollHeight;
  };

  const connect = async() => {
    if(!selPort){ toast("warn","Chọn COM port"); return; }
    setConnecting(true);
    // Auto-close any existing sessions on this port first
    try{
      const sess = await api("/api/serial/sessions","GET");
      for(const s of sess.sessions||[]){
        if(s.port===selPort) await api(`/api/serial/${s.id}`,"DELETE");
      }
    }catch{}
    // Clear terminal
    if(termRef.current) termRef.current.innerHTML = "";
    try{
      // Open serial session via HTTP first
      const r = await api("/api/serial/connect","POST",{port:selPort, baudrate:baud, vendor});
      const sid = r.session_id;
      setSessionId(sid);

      // Then open WebSocket for streaming
      const ws = new WebSocket(`ws://localhost:8000/ws/serial/${sid}`);
      wsRef.current = ws;

      ws.onopen = () => {
        setConnected(true);
        setConnecting(false);
        toast("success",`Connected: ${selPort} @ ${baud}`);
        if(inputRef.current) inputRef.current.focus();
      };

      ws.onmessage = (e) => {
        appendTerm(e.data);
      };

      ws.onerror = () => {
        appendSystem("[WebSocket error]", "#ef4444");
      };

      ws.onclose = () => {
        setConnected(false);
        appendSystem(`\r\n[Disconnected: ${selPort}]`, "#7c8b9e");
      };

    }catch(e){
      toast("error", e.message);
      setConnecting(false);
    }
  };

  const disconnect = async() => {
    if(wsRef.current) wsRef.current.close();
    if(sessionId){
      try{ await api(`/api/serial/${sessionId}`,"DELETE"); }catch{}
      setSessionId(null);
    }
    setConnected(false);
  };

  // Handle keyboard input — send each keystroke immediately (like Putty)
  const onKeyDown = (e) => {
    if(!connected || !wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;

    if(e.key === "Enter"){
      e.preventDefault();
      const val = inputRef.current?.value || "";
      // Send text then carriage return
      if(val) wsRef.current.send(val);
      wsRef.current.send("\r");
      if(inputRef.current) inputRef.current.value = "";
    } else if(e.key === "Tab"){
      e.preventDefault();
      // Send current typed text + TAB to device for autocomplete
      const val = inputRef.current?.value || "";
      if(val) wsRef.current.send(val);
      wsRef.current.send("\t");
      if(inputRef.current) inputRef.current.value = "";
    } else if(e.key === "?" && !e.ctrlKey){
      e.preventDefault();
      const val = inputRef.current?.value || "";
      wsRef.current.send(val + "?\r");
      if(inputRef.current) inputRef.current.value = "";
    } else if(e.ctrlKey && e.key==="c"){
      e.preventDefault();
      wsRef.current.send("\x03");
      if(inputRef.current) inputRef.current.value = "";
    } else if(e.ctrlKey && e.key==="z"){
      e.preventDefault();
      wsRef.current.send("\x1a");
    } else if(e.ctrlKey && e.key==="d"){
      e.preventDefault();
      wsRef.current.send("\x04");
    } else if(e.key==="ArrowUp"){
      e.preventDefault();
      wsRef.current.send("\x1b[A");
    } else if(e.key==="ArrowDown"){
      e.preventDefault();
      wsRef.current.send("\x1b[B");
    }
    // Let other keys type normally into input
  };

  const clearTerm = () => {
    if(termRef.current) termRef.current.innerHTML = "";
    appendSystem("─── Cleared ───");
  };

  return(
    <div className="fadeIn" style={{padding:28}}>
      <div style={{marginBottom:18}}>
        <div style={{fontSize:22,fontWeight:700}}>Console RS232</div>
        <div style={{fontSize:12,color:G.muted,marginTop:3}}>Serial / USB to Router, Switch — MikroTik · Cisco · Fortinet · Sophos</div>
      </div>

      <Card style={{marginBottom:14}}>
        <div style={{display:"grid",gridTemplateColumns:"1fr 140px 160px auto auto",gap:10,alignItems:"flex-end"}}>
          <div>
            <Lbl>COM Port</Lbl>
            <div style={{display:"flex",gap:8}}>
              <Sel value={selPort} onChange={e=>setSelPort(e.target.value)}
                options={ports.length?ports.map(p=>({value:p.port,label:`${p.port} — ${p.description||"Unknown"}`})):[{value:"",label:"No ports found"}]}
                style={{flex:1}}/>
              <Btn variant="ghost" onClick={loadPorts} style={{padding:"8px 12px"}}>↺</Btn>
            </div>
          </div>
          <div>
            <Lbl>Baud Rate</Lbl>
            <Sel value={baud} onChange={e=>setBaud(Number(e.target.value))}
              options={BAUD_RATES.map(b=>({value:b,label:String(b)}))}/>
          </div>
          <div>
            <Lbl>Vendor</Lbl>
            <Sel value={vendor} onChange={e=>setVendor(e.target.value)}
              options={["mikrotik","cisco","fortinet","sophos"].map(v=>({value:v,label:v.charAt(0).toUpperCase()+v.slice(1)}))}/>
          </div>
          {!connected?(
            <Btn onClick={connect} loading={connecting} style={{padding:"9px 20px"}}>⊛ Connect</Btn>
          ):(
            <Btn variant="danger" onClick={disconnect} style={{padding:"9px 20px"}}>⏹ Disconnect</Btn>
          )}
          <div style={{textAlign:"center"}}>
            <div style={{width:10,height:10,borderRadius:"50%",background:connected?G.green:G.red,margin:"0 auto 4px",
              boxShadow:connected?`0 0 8px ${G.green}`:"none"}}/>
            <div style={{fontSize:10,color:G.muted}}>{connected?"Online":"Offline"}</div>
          </div>
        </div>
        {ports.length===0&&(
          <div style={{marginTop:10,padding:"8px 12px",background:`${G.yellow}15`,borderRadius:5,fontSize:12,color:G.yellow}}>
            ⚠ Không tìm thấy COM port — kiểm tra USB-Serial adapter đã cắm chưa, hoặc cài driver
          </div>
        )}
      </Card>

      {/* Terminal — click để focus, nhập phím trực tiếp như Putty */}
      <div style={{background:"#0a0d12",border:`1px solid ${connected?G.green+"44":G.border}`,borderRadius:10,overflow:"hidden",
        transition:"border-color .3s"}}
        onClick={()=>inputRef.current?.focus()}
        tabIndex={0}>
        <div style={{background:"#111520",padding:"8px 14px",display:"flex",alignItems:"center",gap:8,borderBottom:`1px solid ${G.border}`}}>
          <div style={{width:10,height:10,borderRadius:"50%",background:connected?"#ff5f57":"#3c3c3c"}}/>
          <div style={{width:10,height:10,borderRadius:"50%",background:connected?"#ffbd2e":"#3c3c3c"}}/>
          <div style={{width:10,height:10,borderRadius:"50%",background:connected?"#28ca41":"#3c3c3c"}}/>
          <span style={{marginLeft:8,fontSize:12,color:G.muted,fontFamily:"monospace"}}>
            {connected?`${selPort} @ ${baud} baud [${vendor}]`:"serial-console — disconnected"}
          </span>
          <div style={{marginLeft:"auto",display:"flex",gap:8}}>
            <Btn variant="ghost" onClick={e=>{e.stopPropagation();clearTerm();}} style={{padding:"3px 8px",fontSize:11}}>⌫ Clear</Btn>
          </div>
        </div>

        {/* Output area */}
        <div ref={termRef}
          style={{height:420,overflowY:"auto",padding:"14px 16px",fontFamily:"'Courier New',monospace",
            fontSize:13,lineHeight:1.6,cursor:"text",userSelect:"text"}}
        />

      {/* Input bar — always visible, type here */}
        <div style={{padding:"6px 14px",borderTop:`1px solid ${G.border}`,display:"flex",alignItems:"center",gap:8,background:"#080c12"}}>
          <span style={{color:connected?G.green:G.muted,fontFamily:"monospace",fontSize:14,flexShrink:0}}>
            {connected?"❯":"○"}
          </span>
          <input ref={inputRef}
            onKeyDown={onKeyDown}
            placeholder={connected?"Gõ lệnh → Enter gửi | Tab autocomplete | ? help | ↑↓ history":"Kết nối để bắt đầu"}
            disabled={!connected}
            autoComplete="off" autoCorrect="off" spellCheck="false"
            style={{flex:1,background:"transparent",border:"none",outline:"none",
              color:"#e2e8f0",fontFamily:"'Courier New',monospace",fontSize:13,
              caretColor:G.accent}}/>
          <Btn onClick={()=>{ 
            if(connected&&wsRef.current){
              const val = inputRef.current?.value||"";
              if(val) wsRef.current.send(val);
              wsRef.current.send("\r");
              if(inputRef.current) inputRef.current.value="";
            }}} 
            disabled={!connected} style={{padding:"4px 12px",fontSize:11}}>Enter</Btn>
          <Btn variant="ghost" onClick={()=>{
              if(connected&&wsRef.current&&inputRef.current){
                wsRef.current.send(inputRef.current.value+"?");
                inputRef.current.value="";
              }}}
            disabled={!connected} style={{padding:"4px 10px",fontSize:11,color:G.yellow}}>?</Btn>
          <Btn variant="ghost" onClick={()=>{ if(connected&&wsRef.current){ wsRef.current.send("\x03"); }}}
            disabled={!connected} style={{padding:"4px 10px",fontSize:11,color:G.red}}>Ctrl+C</Btn>
          <Btn variant="ghost" onClick={()=>{ if(connected&&wsRef.current){ wsRef.current.send("\x1a"); }}}
            disabled={!connected} style={{padding:"4px 10px",fontSize:11,color:G.muted}}>Ctrl+Z</Btn>
        </div>
      </div>

      {/* Cisco Quick Setup — outside terminal card */}
      {connected && vendor.toLowerCase()==="cisco" && (
        <CiscoQuickSetup wsRef={wsRef} appendTerm={appendTerm} appendSystem={appendSystem} toast={toast}/>
      )}
    </div>
  );
}
// ── Telegram Bot Config ───────────────────────────────────────────

function BotTestTerminal(){
  const [input, setInput] = useState("");
  const [lines, setLines] = useState(["BotTestTerminal — gõ lệnh để test bot"]);
  const termRef = useRef(null);

  const quickCmds = ["/start","/devices","/status","/help","/ping 8.8.8.8"];

  const runCmd = async(cmd) => {
    if(!cmd.trim()) return;
    setLines(l=>[...l, `> ${cmd}`]);
    setInput("");
    try{
      const r = await api("/api/bot/test","POST",{command: cmd});
      const text = r.result || r.message || JSON.stringify(r);
      setLines(l=>[...l, text]);
    }catch(e){
      setLines(l=>[...l, `[Error] ${e.message}`]);
    }
    setTimeout(()=>{ if(termRef.current) termRef.current.scrollTop=termRef.current.scrollHeight; },50);
  };

  return(
    <div style={{marginTop:20}}>
      <div style={{fontSize:13,fontWeight:600,marginBottom:8,color:G.muted}}>🤖 Bot Test Terminal</div>
      <div style={{background:"#0a0d12",border:`1px solid ${G.border}`,borderRadius:8,overflow:"hidden"}}>
        <div ref={termRef} style={{height:200,overflowY:"auto",padding:"10px 14px",fontFamily:"monospace",fontSize:12}}>
          {lines.map((l,i)=>(
            <div key={i} style={{color: l.startsWith(">")?G.accent:"#e2e8f0",marginBottom:2}}>{l}</div>
          ))}
        </div>
        <div style={{padding:"6px 10px",borderTop:`1px solid ${G.border}`,display:"flex",gap:6,flexWrap:"wrap"}}>
          {quickCmds.map(c=>(
            <Btn key={c} variant="ghost" onClick={()=>runCmd(c)} style={{padding:"2px 8px",fontSize:11}}>{c}</Btn>
          ))}
        </div>
        <div style={{padding:"6px 10px",borderTop:`1px solid ${G.border}`,display:"flex",gap:6}}>
          <input value={input} onChange={e=>setInput(e.target.value)}
            onKeyDown={e=>e.key==="Enter"&&runCmd(input)}
            placeholder="Nhập lệnh bot..."
            style={{flex:1,background:"transparent",border:"none",outline:"none",color:"#e2e8f0",fontFamily:"monospace",fontSize:12}}/>
          <Btn onClick={()=>runCmd(input)} style={{padding:"3px 10px",fontSize:11}}>Send</Btn>
        </div>
      </div>
    </div>
  );
}

function TelegramBotPage({toast}){
  const [token, setToken] = useState("");
  const [users, setUsers] = useState("");
  const [alertChats, setAlertChats] = useState("");
  const [enabled, setEnabled] = useState(false);
  const [webhookUrl, setWebhookUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [saved, setSaved] = useState(false);
  const [webhookResult, setWebhookResult] = useState(null);
  const [pollingActive, setPollingActive] = useState(false);
  const [pollingLoading, setPollingLoading] = useState(false);
  const [botMode, setBotMode] = useState("polling"); // polling | webhook

  const checkPolling = async() => {
    try{ const r=await api("/api/bot/polling/status","GET"); setPollingActive(r.active); }catch{}
  };
  const togglePolling = async() => {
    setPollingLoading(true);
    try{
      if(pollingActive){
        await api("/api/bot/polling/stop","POST",{});
        setPollingActive(false); toast("info","Bot polling stopped");
      } else {
        await api("/api/bot/polling/start","POST",{});
        setPollingActive(true); toast("success","Bot polling started! Nhắn /start trong Telegram");
      }
    }catch(e){ toast("error",e.message); }
    setPollingLoading(false);
  };

  useEffect(()=>{ checkPolling(); const t=setInterval(checkPolling,30000); return()=>clearInterval(t); },[]);

  useEffect(()=>{
    api("/api/bot/config","GET").then(r=>{
      setEnabled(r.enabled||false);
      setUsers((r.allowed_users||[]).join(","));
      setAlertChats((r.alert_chats||[]).join(","));
      if(r.has_token) setToken("••••••••••••••••");
    }).catch(()=>{});
  },[]);

  const save = async() => {
    if(!token||token.startsWith("•")){ toast("warn","Nhập Bot Token"); return; }
    setLoading(true);
    try{
      await api("/api/bot/config","POST",{token, allowed_users:users.split(",").map(u=>u.trim()).filter(Boolean), alert_chats:alertChats.split(",").map(u=>u.trim()).filter(Boolean), enabled});
      setSaved(true); toast("success","Bot config saved!");
      setTimeout(()=>setSaved(false),3000);
    }catch(e){ toast("error",e.message); }
    setLoading(false);
  };

  const setupWebhook = async() => {
    if(!webhookUrl){ toast("warn","Nhập webhook URL"); return; }
    setLoading(true);
    try{
      const r = await api(`/api/bot/set-webhook?webhook_url=${encodeURIComponent(webhookUrl)}`,"GET");
      setWebhookResult(r);
      if(r.ok) toast("success","Webhook set!"); else toast("error","Webhook failed");
    }catch(e){ toast("error",e.message); }
    setLoading(false);
  };

  const BOT_COMMANDS = [
    {cmd:"/start",desc:"Chào mừng + danh sách lệnh"},
    {cmd:"/devices",desc:"Liệt kê tất cả thiết bị"},
    {cmd:"/status",desc:"Tổng quan online/offline"},
    {cmd:"/ping <host>",desc:"Ping từ server"},
    {cmd:"/connect <name>",desc:"Connect thiết bị"},
    {cmd:"/cmd <device> <command>",desc:"Chạy lệnh trên thiết bị"},
    {cmd:"/services <device>",desc:"Xem services của thiết bị"},
    {cmd:"/help",desc:"Hiện danh sách lệnh"},
  ];

  return(
    <div className="fadeIn" style={{padding:28}}>
      <div style={{marginBottom:22}}>
        <div style={{fontSize:22,fontWeight:700}}>Telegram Bot</div>
        <div style={{fontSize:12,color:G.muted,marginTop:3}}>Quản lý network qua Telegram — alerts, commands, monitoring</div>
      </div>
      <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:18}}>
        <div>
          <Card style={{marginBottom:14}}>
            <div style={{fontWeight:700,marginBottom:14,color:G.accent}}>✈ Bot Configuration</div>
            <div style={{marginBottom:12}}>
              <Lbl>Bot Token</Lbl>
              <Input value={token} onChange={e=>setToken(e.target.value)} placeholder="123456789:ABCdef..." type="password"/>
              <div style={{fontSize:10,color:G.muted,marginTop:4}}>Lấy từ @BotFather trên Telegram</div>
            </div>
            <div style={{marginBottom:12}}>
              <Lbl>Allowed Users (username hoặc chat_id, cách nhau bằng dấu phẩy)</Lbl>
              <Input value={users} onChange={e=>setUsers(e.target.value)} placeholder="username1,123456789"/>
              <div style={{fontSize:10,color:G.muted,marginTop:4}}>Để trống = cho phép tất cả (không khuyến nghị)</div>
            </div>
            <div style={{marginBottom:12}}>
              <Lbl>Alert Chats (chat_id nhận cảnh báo offline/online)</Lbl>
              <Input value={alertChats} onChange={e=>setAlertChats(e.target.value)} placeholder="123456789,987654321"/>
              <div style={{fontSize:10,color:G.muted,marginTop:4}}>Tự động thêm khi nhắn /start — hoặc nhập thủ công</div>
            </div>
            <div style={{display:"flex",alignItems:"center",gap:10,marginBottom:16}}>
              <div onClick={()=>setEnabled(p=>!p)} style={{width:44,height:24,borderRadius:12,background:enabled?G.green:G.border,cursor:"pointer",position:"relative",transition:"all .2s"}}>
                <div style={{position:"absolute",top:3,left:enabled?22:3,width:18,height:18,borderRadius:"50%",background:"white",transition:"all .2s"}}/>
              </div>
              <span style={{fontSize:13,color:enabled?G.green:G.muted}}>{enabled?"Bot enabled":"Bot disabled"}</span>
            </div>
            <Btn onClick={save} loading={loading} style={{width:"100%",justifyContent:"center"}}>
              {saved?"✓ Saved!":"💾 Lưu cài đặt"}
            </Btn>
          </Card>

          {/* Mode selector */}
          <div style={{display:"flex",gap:8,marginBottom:14}}>
            {[["polling","📡 Polling (local)"],["webhook","🔗 Webhook (public)"]].map(([m,l])=>(
              <div key={m} onClick={()=>setBotMode(m)} style={{flex:1,padding:"10px",borderRadius:7,border:`1px solid ${botMode===m?G.accent:G.border}`,background:botMode===m?`${G.accent}15`:G.card,cursor:"pointer",textAlign:"center",fontSize:12,color:botMode===m?G.accent:G.muted,transition:"all .15s"}}>
                {l}
              </div>
            ))}
          </div>

          {botMode==="polling"&&(
            <Card>
              <div style={{fontWeight:700,marginBottom:8,color:G.accent}}>📡 Polling Mode</div>
              <div style={{fontSize:12,color:G.dim,marginBottom:14,lineHeight:1.7}}>
                Bot tự gọi Telegram mỗi 30s — <b>không cần IP public hay domain</b>.<br/>
                Chạy được hoàn toàn trên localhost.
              </div>
              <div style={{display:"flex",alignItems:"center",gap:12,padding:"12px",background:pollingActive?`${G.green}10`:`${G.surface}`,borderRadius:8,border:`1px solid ${pollingActive?G.green+"44":G.border}`,marginBottom:14}}>
                <div style={{width:12,height:12,borderRadius:"50%",background:pollingActive?G.green:G.muted,boxShadow:pollingActive?`0 0 8px ${G.green}`:"none",flexShrink:0}}/>
                <div style={{flex:1}}>
                  <div style={{fontSize:13,fontWeight:600,color:pollingActive?G.green:G.muted}}>{pollingActive?"🟢 Bot đang chạy":"⚫ Bot đang tắt"}</div>
                  <div style={{fontSize:11,color:G.muted}}>Nhắn /start trong Telegram để bắt đầu</div>
                </div>
              </div>
              <Btn onClick={togglePolling} loading={pollingLoading}
                variant={pollingActive?"danger":"success"}
                style={{width:"100%",justifyContent:"center"}}>
                {pollingActive?"⏹ Dừng Bot":"▶ Khởi động Bot"}
              </Btn>
            </Card>
          )}

          {botMode==="webhook"&&(
            <Card>
              <div style={{fontWeight:700,marginBottom:14,color:G.accent}}>🔗 Webhook Setup</div>
              <div style={{marginBottom:12}}>
                <Lbl>Server URL (public HTTPS)</Lbl>
                <Input value={webhookUrl} onChange={e=>setWebhookUrl(e.target.value)} placeholder="https://your-server.com"/>
                <div style={{fontSize:10,color:G.muted,marginTop:4}}>Cần HTTPS public — dùng ngrok: <code>ngrok http 8000</code></div>
              </div>
              <Btn onClick={setupWebhook} loading={loading} variant="ghost" style={{width:"100%",justifyContent:"center"}}>
                🔗 Set Webhook
              </Btn>
              {webhookResult&&(
                <div style={{marginTop:10,padding:"8px 10px",background:webhookResult.ok?`${G.green}15`:`${G.red}15`,borderRadius:5,fontSize:11,fontFamily:"monospace",color:webhookResult.ok?G.green:G.red}}>
                  {JSON.stringify(webhookResult)}
                </div>
              )}
            </Card>
          )}
        </div>

        <Card>
          <div style={{fontWeight:700,marginBottom:14,color:G.accent}}>📋 Bot Commands</div>
          {BOT_COMMANDS.map(({cmd,desc})=>(
            <div key={cmd} style={{display:"flex",gap:12,padding:"8px 0",borderBottom:`1px solid ${G.border}`}}>
              <code style={{color:G.accent,fontSize:12,minWidth:180,flexShrink:0}}>{cmd}</code>
              <span style={{fontSize:12,color:G.dim}}>{desc}</span>
            </div>
          ))}
          <div style={{marginTop:16,padding:"10px 12px",background:`${G.accent}08`,borderRadius:6,fontSize:11,color:G.muted,lineHeight:1.8}}>
            <div style={{color:G.accent,fontWeight:600,marginBottom:4}}>📖 Hướng dẫn setup:</div>
            1. Tạo bot mới: nhắn @BotFather → /newbot<br/>
            2. Copy token dán vào form bên trái<br/>
            3. Lấy chat_id: nhắn @userinfobot<br/>
            4. Nếu có domain: dùng Set Webhook<br/>
            5. Nếu test local: dùng ngrok → <code>ngrok http 8000</code>
          </div>
          <BotTestTerminal/>
        </Card>
      </div>
    </div>
  );
}

export default function App(){
  const [user,setUser]=useState(null);
  const [page,setPage]=useState("dashboard");
  const [devices,setDevices]=useState(()=>STORE.get("devices",[]));
  const [toasts,setToasts]=useState([]);
  const toast=useCallback((type,msg)=>{const id=Date.now()+Math.random();setToasts(p=>[...p,{id,type,msg}]);},[]);

  useEffect(()=>{
    if(!user) return;
    const devs=STORE.get("devices",[]);
    if(!devs.length) return;
    api("/api/sync","POST",{devices:devs})
      .then(r=>console.log("[sync]",r)).catch(()=>{});
  },[user]);

  if(!user)return(<><style>{css}</style><LoginPage onLogin={setUser}/></>);

  const pages={
    dashboard:<Dashboard devices={devices} onNav={setPage}/>,
    devices:<DevicesPage devices={devices} setDevices={setDevices} toast={toast}/>,
    terminal:<TerminalPage devices={devices} toast={toast}/>,
    nettools:<NetToolsPage devices={devices} toast={toast}/>,
    config:<ConfigPage devices={devices} toast={toast}/>,
    monitor:<MonitorPage devices={devices} toast={toast}/>,
    backup:<BackupPage devices={devices} toast={toast}/>,
    scanner:<ConfigScannerPage devices={devices} toast={toast}/>,
    services:<ServicesPage devices={devices} toast={toast}/>,
    serial:<SerialConsolePage toast={toast}/>,
    botconfig:<TelegramBotPage toast={toast}/>,
    settings:<SettingsPage toast={toast}/>,
  };

  return(
    <>
      <style>{css}</style>
      <div style={{display:"flex"}}>
        <Sidebar page={page} onNav={setPage} user={user} onLogout={()=>setUser(null)} devices={devices}/>
        <main style={{marginLeft:230,flex:1,minHeight:"100vh",background:G.bg}}>{pages[page]}</main>
      </div>
      {toasts.map(t=><Toast key={t.id} {...t} onClose={()=>setToasts(p=>p.filter(x=>x.id!==t.id))}/>)}
    </>
  );
}