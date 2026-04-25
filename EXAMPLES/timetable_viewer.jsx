<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Timetable Solver</title>
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700&family=DM+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<script src="https://unpkg.com/react@18/umd/react.development.js"></script>
<script src="https://unpkg.com/react-dom@18/umd/react-dom.development.js"></script>
<script src="https://unpkg.com/@babel/standalone/babel.min.js"></script>
<style>
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: 'DM Mono', monospace; background: #f0f4f8; color: #1a1a1a; }
input, select, button { font-family: inherit; }

/* ── shared header ── */
.page-header { background: #1e293b; padding: 20px 36px; display: flex;
               align-items: center; justify-content: space-between;
               border-bottom: 1px solid #0f172a; }
.page-title  { font-family: 'Playfair Display', serif; font-size: 22px;
               font-weight: 700; color: #f8fafc; letter-spacing: .01em; }
.page-sub    { font-size: 10px; color: #64748b; letter-spacing: .04em; margin-top: 2px; }
.header-btns { display: flex; gap: 8px; align-items: center; }

/* ── buttons ── */
.btn         { border: none; border-radius: 5px; cursor: pointer; font-size: 12px;
               padding: 7px 16px; letter-spacing: .02em; transition: background .15s; }
.btn-primary { background: #22c55e; color: #fff; font-weight: 600; }
.btn-primary:hover { background: #16a34a; }
.btn-primary:disabled { background: #334155; color: #64748b; cursor: default; }
.btn-dark    { background: #334155; color: #e2e8f0; }
.btn-dark:hover { background: #475569; }
.btn-danger  { background: #7f1d1d; color: #fca5a5; }
.btn-danger:hover { background: #991b1b; }
.btn-ghost   { background: #1e293b; color: #94a3b8; border: 1px solid #334155; }
.btn-ghost:hover { color: #e2e8f0; border-color: #475569; }

/* ── editor page ── */
.editor-body { padding: 32px 36px; display: flex; flex-direction: column; gap: 32px; }

.editor-toolbar { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
.editor-toolbar input  { background: #1e293b; border: 1px solid #334155; border-radius: 5px;
                          padding: 7px 12px; font-size: 12px; color: #e2e8f0; width: 200px; }
.editor-toolbar input::placeholder { color: #475569; }
.editor-toolbar input:focus { outline: none; border-color: #3b82f6; }
.editor-toolbar select { background: #1e293b; border: 1px solid #334155; border-radius: 5px;
                          padding: 7px 10px; font-size: 12px; color: #e2e8f0; }
.status-msg  { font-size: 11px; color: #22c55e; }
.status-msg.err { color: #f87171; }

.editor-cols { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 24px; }
.editor-cols-wide { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }
.card        { background: #fff; border-radius: 10px; padding: 20px 24px;
               box-shadow: 0 1px 3px rgba(0,0,0,.07), 0 2px 8px rgba(0,0,0,.04); }
.card-title  { font-size: 10px; color: #94a3b8; text-transform: uppercase;
               letter-spacing: .08em; margin-bottom: 12px; }

.tag-row     { display: flex; flex-wrap: wrap; gap: 6px; min-height: 28px; margin-bottom: 10px; }
.tag         { display: inline-flex; align-items: center; gap: 3px; background: #f1f5f9;
               border: 1px solid #e2e8f0; border-radius: 4px; padding: 3px 10px;
               font-size: 11px; color: #475569; }
.tag button  { background: none; border: none; cursor: pointer; color: #94a3b8;
               font-size: 14px; line-height: 1; padding: 0 2px; }
.tag button:hover { color: #ef4444; }
.add-row     { display: flex; gap: 6px; }
.add-row input { flex: 1; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 4px;
                 padding: 5px 8px; font-size: 11px; color: #1e293b; }
.add-row input:focus { outline: none; border-color: #3b82f6; }
.add-row button { background: #3b82f6; color: #fff; border: none; border-radius: 4px;
                  padding: 5px 12px; cursor: pointer; font-size: 12px; }
.add-row button:hover { background: #2563eb; }
.placeholder { color: #94a3b8; font-size: 11px; font-style: italic; }
.info-line   { font-size: 11px; color: #94a3b8; }

table.grid   { border-collapse: collapse; width: 100%; font-size: 11px; }
table.grid th { background: #f8fafc; padding: 5px 8px; text-align: center; color: #64748b;
                border: 1px solid #e2e8f0; font-size: 10px; letter-spacing: .04em; }
table.grid td { border: 1px solid #e2e8f0; padding: 3px 5px; text-align: center; }
table.grid td.row-hd { color: #64748b; text-align: left; padding-left: 8px; font-size: 11px;
                        white-space: nowrap; }
table.grid td input[type=number]   { width: 38px; text-align: center; background: #f8fafc;
  border: 1px solid #e2e8f0; border-radius: 3px; padding: 3px; font-size: 11px; color: #1e293b; }
table.grid td input[type=checkbox] { width: 14px; height: 14px; cursor: pointer; accent-color: #3b82f6; }

/* ── result page ── */
.result-body { padding: 28px 36px; }
.tabs        { display: flex; gap: 6px; flex-wrap: wrap; }
.tab         { padding: 6px 14px; font-size: 12px; border: none; border-radius: 4px;
               cursor: pointer; transition: all .15s; letter-spacing: .02em; }
.tab.active  { background: #1e293b; color: #fff; font-weight: 700; }
.tab.inactive{ background: #f1f5f9; color: #475569; }
.stats-grid  { display: grid; gap: 10px; margin-bottom: 24px; }
.stat-card   { border-radius: 6px; padding: 12px 14px; }
.stat-num    { font-size: 22px; font-weight: 700; line-height: 1; }
.stat-lbl    { font-size: 10px; opacity: .7; margin-top: 4px; text-transform: uppercase;
               letter-spacing: .05em; }
.tt-wrap     { background: #fff; border-radius: 10px; overflow: hidden;
               box-shadow: 0 1px 3px rgba(0,0,0,.08), 0 4px 16px rgba(0,0,0,.04); }
table.tt     { border-collapse: collapse; width: 100%; table-layout: fixed; }
table.tt th  { padding: 10px 12px; font-size: 13px; font-weight: 700; text-align: left;
               border-bottom: 2px solid #e2e8f0; background: #f8fafc;
               font-family: 'Playfair Display', serif; color: #1e293b; letter-spacing: .02em; }
table.tt th.period-col { width: 72px; font-family: 'DM Mono', monospace; font-size: 11px;
                          font-weight: 500; color: #64748b; }
table.tt td.period-cell { padding: 0 12px; font-size: 11px; font-weight: 600; color: #94a3b8;
                           background: #f8fafc; border-right: 2px solid #e2e8f0;
                           vertical-align: middle; height: 68px; }
table.tt td.lesson-cell { padding: 0; height: 68px; border: 1px solid #e2e8f0;
                           vertical-align: top; cursor: pointer; }
table.tt td.empty-cell  { padding: 0; height: 68px; border: 1px solid #e2e8f0; }
.cell-inner  { height: 100%; padding: 8px 10px; transition: background .15s; display: flex;
               flex-direction: column; justify-content: center; gap: 3px; }
.cell-subj   { font-family: 'Playfair Display', serif; font-size: 12px; font-weight: 700;
               letter-spacing: .01em; }
.cell-info   { font-size: 10px; opacity: .8; }
.legend      { display: flex; gap: 16px; margin-top: 14px; flex-wrap: wrap; }
.legend-item { display: flex; align-items: center; gap: 6px; font-size: 11px; color: #64748b; }
.legend-dot  { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }
.hint        { margin-top: 10px; font-size: 10px; color: #94a3b8; letter-spacing: .03em; }
.error-box   { background: #fdf0ef; border: 1px solid #f0b9b5; color: #c0392b;
               border-radius: 6px; padding: 12px 16px; font-size: 13px; }
.solving-msg { display: flex; align-items: center; justify-content: center;
               min-height: 40vh; color: #64748b; font-size: 14px; letter-spacing: .04em; }
</style>
</head>
<body>
<div id="root"></div>
<script type="text/babel">
const { useState, useEffect } = React;

const API       = "http://localhost:8765";
const DAYS      = ["Monday","Tuesday","Wednesday","Thursday","Friday"];
const MAX_SLOTS = 8;

const PALETTE = [
  { bg:"#dbeafe", border:"#3b82f6", text:"#1e3a8a", dot:"#3b82f6" },
  { bg:"#dcfce7", border:"#22c55e", text:"#14532d", dot:"#22c55e" },
  { bg:"#fef9c3", border:"#eab308", text:"#713f12", dot:"#eab308" },
  { bg:"#fce7f3", border:"#ec4899", text:"#831843", dot:"#ec4899" },
  { bg:"#ede9fe", border:"#8b5cf6", text:"#3b0764", dot:"#8b5cf6" },
  { bg:"#ffedd5", border:"#f97316", text:"#7c2d12", dot:"#f97316" },
  { bg:"#cffafe", border:"#06b6d4", text:"#164e63", dot:"#06b6d4" },
  { bg:"#fae8ff", border:"#d946ef", text:"#701a75", dot:"#d946ef" },
];
const EMPTY_COLOR = { bg:"#f8fafc", border:"#e2e8f0", text:"#94a3b8" };

function subjColor(subjects, name) {
  const i = subjects.indexOf(name);
  return i >= 0 ? PALETTE[i % PALETTE.length] : EMPTY_COLOR;
}

// ---------------------------------------------------------------------------
// Result page components
// ---------------------------------------------------------------------------
function Cell({ lesson, isSelected, onClick, subjects }) {
  const c = lesson ? subjColor(subjects, lesson.subject) : EMPTY_COLOR;
  return lesson ? (
    <td className="lesson-cell" onClick={onClick}>
      <div className="cell-inner" style={{
        background: isSelected ? c.border : c.bg,
        borderLeft: `3px solid ${c.border}`,
      }}>
        <div className="cell-subj" style={{color: isSelected ? "#fff" : c.text}}>
          {lesson.subject}
        </div>
        <div className="cell-info" style={{color: isSelected ? "rgba(255,255,255,.85)" : c.text}}>
          {lesson.teacher} · {lesson.room}
        </div>
      </div>
    </td>
  ) : (
    <td className="empty-cell">
      <div className="cell-inner" style={{background: EMPTY_COLOR.bg,
            borderLeft:"3px solid transparent", opacity:.35, alignItems:"center"}}>
        <span style={{fontSize:11,color:"#cbd5e1"}}>—</span>
      </div>
    </td>
  );
}

function TimetableGrid({ schedule, days, slots, filterKey, filterVal, subjects }) {
  const [selected, setSelected] = useState(null);
  function getLesson(day, slot) {
    return schedule.find(e =>
      e.day === day && e.slot === slot &&
      (filterKey === "class" ? e.class : filterKey === "teacher" ? e.teacher : e.room) === filterVal
    ) || null;
  }
  return (
    <div>
      <div className="tt-wrap">
        <table className="tt" style={{tableLayout:"fixed"}}>
          <thead><tr>
            <th className="period-col">PERIOD</th>
            {days.map(d => <th key={d} style={{minWidth:100}}>{d}</th>)}
          </tr></thead>
          <tbody>
            {slots.map(sl => (
              <tr key={sl}>
                <td className="period-cell">P{sl}</td>
                {days.map(d => {
                  const lesson = getLesson(d, sl);
                  const key = `${d}-${sl}`;
                  return (
                    <Cell key={d} lesson={lesson} subjects={subjects}
                          isSelected={selected === key}
                          onClick={() => setSelected(selected === key ? null : key)} />
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="legend">
        {subjects.map(s => {
          const c = subjColor(subjects, s);
          return (
            <div className="legend-item" key={s}>
              <div className="legend-dot" style={{background: c.dot}} />
              {s}
            </div>
          );
        })}
      </div>
      <div className="hint">Click any cell to highlight it.</div>
    </div>
  );
}

function StatsBar({ schedule, filterKey, filterVal, subjects }) {
  const filtered = schedule.filter(e =>
    (filterKey === "class" ? e.class : filterKey === "teacher" ? e.teacher : e.room) === filterVal
  );
  const counts = Object.fromEntries(subjects.map(s => [s, 0]));
  filtered.forEach(e => { if (counts[e.subject] !== undefined) counts[e.subject]++; });
  const cols = Math.min(subjects.length, 4);
  return (
    <div className="stats-grid" style={{gridTemplateColumns:`repeat(${cols},1fr)`, marginBottom:24}}>
      {subjects.map(s => {
        const c = subjColor(subjects, s);
        return (
          <div className="stat-card" key={s}
               style={{background: c.bg, borderLeft: `3px solid ${c.border}`}}>
            <div className="stat-num" style={{color: c.text}}>{counts[s]}</div>
            <div className="stat-lbl" style={{color: c.text}}>{s}</div>
          </div>
        );
      })}
    </div>
  );
}

function TabBar({ label, options, active, onChange }) {
  return (
    <div>
      <div style={{fontSize:10,color:"#94a3b8",textTransform:"uppercase",
                   letterSpacing:".08em",marginBottom:8}}>{label}</div>
      <div className="tabs">
        {options.map(o => (
          <button key={o} className={`tab ${active===o?"active":"inactive"}`}
                  onClick={() => onChange(o)}>{o}</button>
        ))}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Editor page components
// ---------------------------------------------------------------------------
function TagList({ items, label, onRemove }) {
  if (!items.length) return <span className="placeholder">None yet.</span>;
  return (
    <div className="tag-row">
      {items.map(item => {
        const key = typeof item === "object" ? item.name : item;
        return (
          <span className="tag" key={key}>
            {label(item)}
            <button onClick={() => onRemove(key)}>×</button>
          </span>
        );
      })}
    </div>
  );
}

function AddRow({ placeholders, types, onAdd }) {
  const [vals, setVals] = useState(placeholders.map(() => ""));
  function commit() {
    if (!vals[0].trim()) return;
    onAdd(vals);
    setVals(placeholders.map(() => ""));
  }
  return (
    <div className="add-row">
      {placeholders.map((ph, i) => (
        <input key={i} type={types?.[i]||"text"} placeholder={ph} value={vals[i]}
               onChange={e => setVals(v => v.map((x,j) => j===i ? e.target.value : x))}
               onKeyDown={e => e.key==="Enter" && commit()} />
      ))}
      <button onClick={commit}>+</button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// App
// ---------------------------------------------------------------------------
function App() {
  const [page,         setPage]         = useState("editor"); // "editor" | "solving" | "result"
  const [classes,      setClasses]      = useState([]);
  const [subjects,     setSubjects]     = useState([]);
  const [teachers,     setTeachers]     = useState([]);
  const [rooms,        setRooms]        = useState([]);
  const [requirements, setRequirements] = useState({});
  const [canTeach,     setCanTeach]     = useState({});

  const [probName,   setProbName]   = useState("");
  const [savedNames, setSavedNames] = useState([]);
  const [statusMsg,  setStatusMsg]  = useState(null);
  const [result,     setResult]     = useState(null);
  const [viewMode,   setViewMode]   = useState("By Class");
  const [selection,  setSelection]  = useState(null);

  useEffect(() => { refreshList().then(() => loadProblem("DEFAULT")); }, []);

  useEffect(() => {
    if (!result?.ok) return;
    const opts = viewMode === "By Class" ? result.classes
               : viewMode === "By Teacher" ? [...new Set(result.schedule.map(e=>e.teacher))].sort()
               : [...new Set(result.schedule.map(e=>e.room))].sort();
    setSelection(opts[0] || null);
  }, [viewMode, result]);

  async function refreshList() {
    try { setSavedNames((await (await fetch(`${API}/list`)).json()).names || []); } catch(_) {}
  }

  function buildPayload() {
    return {
      classes, subjects, teachers, rooms,
      days: DAYS, slots: MAX_SLOTS,
      requirements,
      can_teach: Object.fromEntries(
        teachers.map(t => [t, subjects.filter(s => (canTeach[t]||{})[s])])
      ),
    };
  }

  async function saveProblem() {
    if (!probName.trim()) { setStatusMsg({text:"Enter a name first.",ok:false}); return; }
    try {
      const d = await (await fetch(`${API}/save`, {
        method:"POST", headers:{"Content-Type":"application/json"},
        body: JSON.stringify({name:probName.trim(), data:buildPayload()}),
      })).json();
      setStatusMsg(d.ok ? {text:`Saved "${probName.trim()}"`,ok:true} : {text:`Save failed: ${d.error}`,ok:false});
      if (d.ok) refreshList();
    } catch(e) { setStatusMsg({text:`Save failed: ${e.message}`,ok:false}); }
  }

  async function loadProblem(name) {
    if (!name) return;
    try {
      const d = await (await fetch(`${API}/load?name=${encodeURIComponent(name)}`)).json();
      if (!d.ok) { setStatusMsg({text:"Load failed: "+d.error,ok:false}); return; }
      const p = d.data;
      setClasses(p.classes||[]); setSubjects(p.subjects||[]);
      setTeachers(p.teachers||[]); setRooms(p.rooms||[]);
      setRequirements(p.requirements||{});
      const ct = {};
      for (const [t,ss] of Object.entries(p.can_teach||{}))
        ct[t] = Object.fromEntries((ss||[]).map(s=>[s,true]));
      setCanTeach(ct);
      setProbName(name); setResult(null); setStatusMsg(null); setPage("editor");
    } catch(e) { setStatusMsg({text:"Load failed: "+e.message,ok:false}); }
  }

  function newProblem() {
    if (!confirm("Clear current problem and start fresh?")) return;
    setClasses([]); setSubjects([]); setTeachers([]); setRooms([]);
    setRequirements({}); setCanTeach({});
    setProbName(""); setResult(null); setStatusMsg(null);
  }

  async function deleteProblem() {
    if (!probName || probName === "DEFAULT") return;
    if (!confirm(`Delete "${probName}"?`)) return;
    try {
      const d = await (await fetch(`${API}/delete`, {
        method:"POST", headers:{"Content-Type":"application/json"},
        body: JSON.stringify({name: probName}),
      })).json();
      setStatusMsg(d.ok ? {text:`Deleted "${probName}"`,ok:true} : {text:`Delete failed: ${d.error}`,ok:false});
      if (d.ok) { refreshList(); setProbName(""); }
    } catch(e) { setStatusMsg({text:`Delete failed: ${e.message}`,ok:false}); }
  }

  const addClass     = ([n,s]) => { if(!n||classes.find(c=>c.name===n))return; setClasses(p=>[...p,{name:n,size:parseInt(s)||25}]); setRequirements(p=>({...p,[n]:p[n]||{}})); };
  const removeClass  = n       => { setClasses(p=>p.filter(c=>c.name!==n)); setRequirements(p=>{const x={...p};delete x[n];return x;}); };
  const addSubject   = ([n])   => { if(!n||subjects.includes(n))return; setSubjects(p=>[...p,n]); };
  const removeSubject= n       => { setSubjects(p=>p.filter(s=>s!==n)); setRequirements(p=>Object.fromEntries(Object.entries(p).map(([c,sv])=>{const x={...sv};delete x[n];return[c,x];}))); setCanTeach(p=>Object.fromEntries(Object.entries(p).map(([t,sv])=>{const x={...sv};delete x[n];return[t,x];}))); };
  const addTeacher   = ([n])   => { if(!n||teachers.includes(n))return; setTeachers(p=>[...p,n]); setCanTeach(p=>({...p,[n]:{}})); };
  const removeTeacher= n       => { setTeachers(p=>p.filter(t=>t!==n)); setCanTeach(p=>{const x={...p};delete x[n];return x;}); };
  const addRoom      = ([n,c]) => { if(!n||rooms.find(r=>r.name===n))return; setRooms(p=>[...p,{name:n,capacity:parseInt(c)||30}]); };
  const removeRoom   = n       => setRooms(p=>p.filter(r=>r.name!==n));
  const setReq       = (c,s,v)=> setRequirements(p=>({...p,[c]:{...(p[c]||{}),[s]:parseInt(v)||0}}));
  const setTeach     = (t,s,v)=> setCanTeach(p=>({...p,[t]:{...(p[t]||{}),[s]:v}}));

  async function solve() {
    setPage("solving");
    try {
      const r = await (await fetch(`${API}/solve`,{
        method:"POST", headers:{"Content-Type":"application/json"},
        body:JSON.stringify(buildPayload()),
      })).json();
      setResult(r);
      setPage(r.ok ? "result" : "editor");
      if (!r.ok) setStatusMsg({text: r.error, ok: false});
    } catch(e) {
      setResult({ok:false,error:e.message});
      setPage("editor");
      setStatusMsg({text:e.message,ok:false});
    }
  }

  // result view state
  const viewOptions = ["By Class","By Teacher","By Room"];
  let filterKey = "class", filterOptions = [];
  if (result?.ok) {
    if (viewMode==="By Class")   { filterKey="class";   filterOptions=result.classes; }
    if (viewMode==="By Teacher") { filterKey="teacher"; filterOptions=[...new Set(result.schedule.map(e=>e.teacher))].sort(); }
    if (viewMode==="By Room")    { filterKey="room";    filterOptions=[...new Set(result.schedule.map(e=>e.room))].sort(); }
  }
  const safeSelection = filterOptions.includes(selection) ? selection : filterOptions[0];

  // ── solving spinner ──────────────────────────────────────────────────────
  if (page === "solving") return (
    <div>
      <div className="page-header">
        <div>
          <div className="page-title">School Timetable</div>
          <div className="page-sub">{probName || "UNSAVED"}</div>
        </div>
      </div>
      <div className="solving-msg">Solving… please wait</div>
    </div>
  );

  // ── result page ──────────────────────────────────────────────────────────
  if (page === "result") return (
    <div>
      <div className="page-header">
        <div>
          <div className="page-title">School Timetable</div>
          <div className="page-sub">
            {`SOLVED IN ${result.stats.elapsed_ms} MS · ${result.stats.calls} CALLS · ${result.stats.backtracks} BACKTRACKS`}
          </div>
        </div>
        <div className="header-btns">
          <button className="btn btn-ghost" onClick={() => setPage("editor")}>← Edit</button>
          <button className="btn btn-primary" onClick={solve}>Re-solve</button>
        </div>
      </div>

      <div className="result-body">
        <div style={{display:"flex",gap:32,marginBottom:28,flexWrap:"wrap",alignItems:"flex-end"}}>
          <TabBar label="View by" options={viewOptions} active={viewMode}
                  onChange={m => setViewMode(m)} />
          <TabBar label={viewMode==="By Class"?"Class":viewMode==="By Teacher"?"Teacher":"Room"}
                  options={filterOptions} active={safeSelection} onChange={setSelection} />
        </div>
        <StatsBar schedule={result.schedule} filterKey={filterKey}
                  filterVal={safeSelection} subjects={subjects} />
        <TimetableGrid schedule={result.schedule} days={result.days} slots={result.slots}
                       filterKey={filterKey} filterVal={safeSelection} subjects={subjects} />
      </div>
    </div>
  );

  // ── editor page ──────────────────────────────────────────────────────────
  return (
    <div>
      <div className="page-header">
        <div>
          <div className="page-title">School Timetable</div>
          <div className="page-sub">CONFIGURE PROBLEM · PRESS SOLVE</div>
        </div>
        <div className="header-btns">
          {result?.ok && <button className="btn btn-ghost" onClick={() => setPage("result")}>View last result →</button>}
          <button className="btn btn-primary" onClick={solve}>Solve</button>
        </div>
      </div>

      <div className="editor-body">

        {/* Toolbar: problem save/load */}
        <div style={{display:"flex",flexDirection:"column",gap:8}}>
          <div className="editor-toolbar">
            <input value={probName} onChange={e=>setProbName(e.target.value)}
                   placeholder="Problem name" maxLength={64}
                   onKeyDown={e=>e.key==="Enter"&&saveProblem()} />
            <button className="btn btn-dark" onClick={saveProblem}>Save</button>
            <button className="btn btn-danger"
                    onClick={deleteProblem}
                    disabled={!probName||probName==="DEFAULT"}>Delete</button>
            <select value="" onChange={e=>loadProblem(e.target.value)}>
              <option value="">— load saved problem —</option>
              {savedNames.map(n=><option key={n} value={n}>{n}</option>)}
            </select>
            <button className="btn btn-dark" onClick={newProblem}>New</button>
          </div>
          {statusMsg && <div className={`status-msg${statusMsg.ok?"":" err"}`}>{statusMsg.text}</div>}
        </div>

        {/* Row 1: Classes · Subjects · Teachers · Rooms */}
        <div className="editor-cols" style={{gridTemplateColumns:"1fr 1fr 1fr 1fr"}}>
          <div className="card">
            <div className="card-title">Classes</div>
            <TagList items={classes} label={c=>`${c.name} (${c.size})`} onRemove={removeClass} />
            <AddRow placeholders={["Name","Size"]} types={["text","number"]} onAdd={addClass} />
          </div>
          <div className="card">
            <div className="card-title">Subjects</div>
            <TagList items={subjects} label={s=>s} onRemove={removeSubject} />
            <AddRow placeholders={["Subject"]} onAdd={addSubject} />
          </div>
          <div className="card">
            <div className="card-title">Teachers</div>
            <TagList items={teachers} label={t=>t} onRemove={removeTeacher} />
            <AddRow placeholders={["Teacher"]} onAdd={addTeacher} />
          </div>
          <div className="card">
            <div className="card-title">Rooms</div>
            <TagList items={rooms} label={r=>`${r.name} (${r.capacity})`} onRemove={removeRoom} />
            <AddRow placeholders={["Room","Cap"]} types={["text","number"]} onAdd={addRoom} />
          </div>
        </div>

        {/* Row 2: Requirements · Can-teach */}
        <div className="editor-cols-wide">
          <div className="card">
            <div className="card-title">Lessons per class per subject (periods/week)</div>
            {classes.length && subjects.length ? (
              <div style={{overflowX:"auto"}}>
                <table className="grid">
                  <thead><tr>
                    <th></th>
                    {subjects.map(s=><th key={s}>{s}</th>)}
                  </tr></thead>
                  <tbody>
                    {classes.map(cl=>(
                      <tr key={cl.name}>
                        <td className="row-hd">{cl.name}</td>
                        {subjects.map(s=>(
                          <td key={s}>
                            <input type="number" min={0} max={MAX_SLOTS}
                                   value={(requirements[cl.name]||{})[s]||0}
                                   onChange={e=>setReq(cl.name,s,e.target.value)} />
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : <span className="placeholder">Add classes and subjects first.</span>}
          </div>

          <div className="card">
            <div className="card-title">Teacher — subject qualification</div>
            {teachers.length && subjects.length ? (
              <div style={{overflowX:"auto"}}>
                <table className="grid">
                  <thead><tr>
                    <th></th>
                    {subjects.map(s=><th key={s}>{s}</th>)}
                  </tr></thead>
                  <tbody>
                    {teachers.map(t=>(
                      <tr key={t}>
                        <td className="row-hd">{t}</td>
                        {subjects.map(s=>(
                          <td key={s}>
                            <input type="checkbox"
                                   checked={!!((canTeach[t]||{})[s])}
                                   onChange={e=>setTeach(t,s,e.target.checked)} />
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : <span className="placeholder">Add teachers and subjects first.</span>}
          </div>
        </div>

        {/* Schedule info */}
        <div className="info-line">
          Schedule: Monday – Friday · {MAX_SLOTS} periods per day
        </div>

      </div>
    </div>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<App />);
</script>
</body>
</html>
