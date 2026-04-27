<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Timetable Solver</title>
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700&family=DM+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<script src="https://unpkg.com/react@18/umd/react.development.js"></script>
<script src="https://unpkg.com/react-dom@18/umd/react-dom.development.js"></script>
<script src="https://unpkg.com/@babel/standalone/babel.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/fullcalendar@6.1.20/index.global.min.js"></script>
<style>
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: 'DM Mono', monospace; background: #f0f4f8; color: #1a1a1a; }
input, select, button, textarea { font-family: inherit; }

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
.editor-body { padding: 32px 36px; display: flex; flex-direction: column; gap: 24px; }

.editor-toolbar { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
.editor-toolbar input  { background: #1e293b; border: 1px solid #334155; border-radius: 5px;
                          padding: 7px 12px; font-size: 12px; color: #e2e8f0; width: 200px; }
.editor-toolbar input::placeholder { color: #475569; }
.editor-toolbar input:focus { outline: none; border-color: #3b82f6; }
.editor-toolbar select { background: #1e293b; border: 1px solid #334155; border-radius: 5px;
                          padding: 7px 10px; font-size: 12px; color: #e2e8f0; }
.status-msg  { font-size: 11px; color: #22c55e; }
.status-msg.err { color: #f87171; }

.editor-cols { display: grid; grid-template-columns: 1fr 1fr 1fr 1fr; gap: 20px; }
.editor-cols-wide { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
.editor-cols-3 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 20px; }
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
.add-row     { display: flex; gap: 6px; align-items: center; }
.add-row input, .add-row select {
               flex: 1; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 4px;
               padding: 5px 8px; font-size: 11px; color: #1e293b; }
.add-row input:focus, .add-row select:focus { outline: none; border-color: #3b82f6; }
.add-row button { background: #3b82f6; color: #fff; border: none; border-radius: 4px;
                  padding: 5px 12px; cursor: pointer; font-size: 12px; flex-shrink: 0; }
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
table.grid td.blocked { background: #fee2e2; }
table.grid td.blocked input[type=checkbox] { accent-color: #ef4444; }

/* ── result page ── */
.result-body { padding: 20px 36px; }
.tabs        { display: flex; gap: 6px; flex-wrap: wrap; }
.tab         { padding: 6px 14px; font-size: 12px; border: none; border-radius: 4px;
               cursor: pointer; transition: all .15s; letter-spacing: .02em; }
.tab.active  { background: #1e293b; color: #fff; font-weight: 700; }
.tab.inactive{ background: #f1f5f9; color: #475569; }

.soft-warn   { background: #fefce8; border: 1px solid #fde047; border-radius: 6px;
               padding: 10px 16px; font-size: 11px; color: #713f12; margin-bottom: 16px; }

.fc-toolbar-title { font-family: 'Playfair Display', serif !important; font-size: 16px !important; }
.fc { font-family: 'DM Mono', monospace !important; font-size: 11px !important; }
.fc .fc-col-header-cell { background: #f8fafc; }
.fc .fc-timegrid-slot-label { font-size: 10px; color: #64748b; }
.fc-event { border-radius: 4px !important; font-size: 10px !important; cursor: pointer; }
.fc-event-main { padding: 2px 4px !important; }

.solving-msg { display: flex; align-items: center; justify-content: center;
               min-height: 40vh; color: #64748b; font-size: 14px; letter-spacing: .04em; }
.error-box   { background: #fdf0ef; border: 1px solid #f0b9b5; color: #c0392b;
               border-radius: 6px; padding: 12px 16px; font-size: 13px; }

@media print {
  .page-header, .editor-body, .result-toolbar, .fc-toolbar { display: none !important; }
  .result-body { padding: 0; }
}
</style>
</head>
<body>
<div id="root"></div>
<script type="text/babel">
const { useState, useEffect, useRef, useCallback } = React;

const API       = "http://localhost:8765";
const DAYS      = ["Monday","Tuesday","Wednesday","Thursday","Friday"];
const MAX_SLOTS = 8;
const ROOM_TYPES = ["standard","lab","gym","art","other"];

// Period 1 = 08:00, period N = 08:00 + (N-1) hours
const SLOT_START = 8; // 08:00
function slotToTime(slot) {
  const h = SLOT_START + slot - 1;
  return `${String(h).padStart(2,"0")}:00:00`;
}
function slotToTimeEnd(slot) {
  const h = SLOT_START + slot;
  return `${String(h).padStart(2,"0")}:00:00`;
}

function computeSoftScore(schedule, softConstraints) {
  const w = softConstraints || {};
  const wHole    = w.weight_class_holes          || 1;
  const wFirst   = w.weight_avoid_first_slot     || 2;
  const wLast    = w.weight_avoid_last_slot      || 1;
  const wSpread  = w.weight_teacher_spread       || 1;
  const wSubjSpr = w.weight_subject_daily_spread || 2;

  const classDay  = {};   // (class,day)    -> [slots]
  const teachDay  = {};   // (teacher,day)  -> [slots]
  const classSubj = {};   // (class,subject)-> Set of days
  for (const e of schedule) {
    const ck = `${e.class}\0${e.day}`;
    (classDay[ck] = classDay[ck] || []).push(e.slot);
    const tk = `${e.teacher}\0${e.day}`;
    (teachDay[tk] = teachDay[tk] || []).push(e.slot);
    const sk = `${e.class}\0${e.subject}`;
    if (!classSubj[sk]) classSubj[sk] = { days: new Set(), count: 0 };
    classSubj[sk].days.add(e.day);
    classSubj[sk].count++;
  }

  let holes = 0, first = 0, last = 0, spread = 0, subjSpread = 0;
  for (const slots of Object.values(classDay)) {
    slots.sort((a,b)=>a-b);
    const mn = slots[0], mx = slots[slots.length-1];
    if (mn === 1) first++;
    if (mx === MAX_SLOTS) last++;
    holes += (mx - mn + 1) - slots.length;
  }
  for (const slots of Object.values(teachDay)) {
    if (slots.length <= 1) continue;
    slots.sort((a,b)=>a-b);
    spread += (slots[slots.length-1] - slots[0] + 1) - slots.length;
  }
  for (const { days, count } of Object.values(classSubj)) {
    subjSpread += count - days.size;
  }

  const total = holes*wHole + first*wFirst + last*wLast + spread*wSpread + subjSpread*wSubjSpr;
  return { total, class_holes: holes, avoid_first_slot: first, avoid_last_slot: last,
           teacher_spread: spread, subject_daily_spread: subjSpread };
}

// Map day name → a fixed Monday in a reference week (2024-01-01 is Monday)
const DAY_DATE = {
  Monday:"2024-01-01", Tuesday:"2024-01-02", Wednesday:"2024-01-03",
  Thursday:"2024-01-04", Friday:"2024-01-05"
};

const PALETTE = [
  "#3b82f6","#22c55e","#eab308","#ec4899","#8b5cf6",
  "#f97316","#06b6d4","#d946ef","#ef4444","#10b981",
  "#f59e0b","#6366f1","#84cc16","#0ea5e9","#e11d48",
];
function subjColor(subjects, name) {
  const i = subjects.indexOf(name);
  return i >= 0 ? PALETTE[i % PALETTE.length] : "#94a3b8";
}
function hexToRgba(hex, alpha) {
  const r = parseInt(hex.slice(1,3),16);
  const g = parseInt(hex.slice(3,5),16);
  const b = parseInt(hex.slice(5,7),16);
  return `rgba(${r},${g},${b},${alpha})`;
}

// ---------------------------------------------------------------------------
// FullCalendar result view — one resource at a time, days as columns
// ---------------------------------------------------------------------------
function TimetableCalendar({ schedule, subjects, viewMode, selection, onEventDrop }) {
  const calRef = useRef(null);
  const calObj = useRef(null);

  const filterKey = viewMode === "By Class" ? "class"
                  : viewMode === "By Teacher" ? "teacher" : "room";

  const events = schedule
    .filter(e => e[filterKey] === selection)
    .map((e, idx) => {
      const color = subjColor(subjects, e.subject);
      const lines = viewMode === "By Class"   ? [e.subject, e.teacher, e.room]
                  : viewMode === "By Teacher" ? [e.subject, e.class,   e.room]
                  :                             [e.subject, e.class,   e.teacher];
      return {
        id:              String(idx),
        title:           e.subject,
        start:           `${DAY_DATE[e.day]}T${slotToTime(e.slot)}`,
        end:             `${DAY_DATE[e.day]}T${slotToTimeEnd(e.slot)}`,
        backgroundColor: hexToRgba(color, 0.18),
        borderColor:     color,
        textColor:       color,
        extendedProps:   { ...e, _lines: lines },
      };
    });

  useEffect(() => {
    if (!calRef.current) return;
    if (calObj.current) { calObj.current.destroy(); calObj.current = null; }

    calObj.current = new FullCalendar.Calendar(calRef.current, {
      initialView:       "timeGridWeek",
      initialDate:       "2024-01-01",
      headerToolbar:     false,
      weekends:          false,
      allDaySlot:        false,
      slotMinTime:       slotToTime(1),
      slotMaxTime:       slotToTimeEnd(MAX_SLOTS),
      slotDuration:      "01:00:00",
      slotLabelInterval: "01:00:00",
      expandRows:        true,
      height:            MAX_SLOTS * 72 + 44,
      editable:          true,
      events,
      slotLabelContent(arg) {
        const slot = arg.date.getHours() - SLOT_START + 1;
        return { html: `<span style="font-size:11px;color:#64748b;font-weight:600">P${slot}</span>` };
      },
      dayHeaderContent(arg) {
        return { html: `<span style="font-size:13px;font-weight:700;font-family:'Playfair Display',serif">${
          DAYS[arg.date.getDay() - 1]}</span>` };
      },
      eventContent(arg) {
        const lines = arg.event.extendedProps._lines;
        return {
          html: `<div style="padding:6px 8px;line-height:1.5;height:100%">
            <div style="font-family:'Playfair Display',serif;font-weight:700;font-size:13px">${lines[0]}</div>
            <div style="font-size:11px;opacity:.85">${lines[1]}</div>
            <div style="font-size:10px;opacity:.65">${lines[2]}</div>
          </div>`
        };
      },
      eventDrop(info) {
        const p       = info.event.extendedProps;
        const newDay  = DAYS[info.event.start.getDay() - 1];
        const newSlot = info.event.start.getHours() - SLOT_START + 1;
        if (!newDay || newSlot < 1 || newSlot > MAX_SLOTS) { info.revert(); return; }
        if (onEventDrop) onEventDrop(p, newDay, newSlot, selection, viewMode, info.revert);
      },
    });
    calObj.current.render();
    return () => { if (calObj.current) { calObj.current.destroy(); calObj.current = null; } };
  }, [events, selection, viewMode]);

  return (
    <div style={{background:"#fff", borderRadius:10, padding:"16px 20px",
                 boxShadow:"0 1px 3px rgba(0,0,0,.08), 0 4px 16px rgba(0,0,0,.04)"}}>
      <div ref={calRef} />
      <div style={{display:"flex",gap:16,marginTop:14,flexWrap:"wrap"}}>
        {subjects.map(s => {
          const c = subjColor(subjects, s);
          return (
            <div key={s} style={{display:"flex",alignItems:"center",gap:6,fontSize:11,color:"#64748b"}}>
              <div style={{width:10,height:10,borderRadius:"50%",background:c,flexShrink:0}} />
              {s}
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Editor components
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

function AddRow({ placeholders, types, options, onAdd }) {
  const [vals, setVals] = useState(placeholders.map((_, i) =>
    options?.[i] ? options[i][0] : ""));
  function commit() {
    if (!vals[0].trim && vals[0] === "") return;
    if (typeof vals[0] === "string" && !vals[0].trim()) return;
    onAdd(vals);
    setVals(placeholders.map((_, i) => options?.[i] ? options[i][0] : ""));
  }
  return (
    <div className="add-row">
      {placeholders.map((ph, i) =>
        options?.[i] ? (
          <select key={i} value={vals[i]}
                  onChange={e => setVals(v => v.map((x,j) => j===i ? e.target.value : x))}>
            {options[i].map(o => <option key={o} value={o}>{o}</option>)}
          </select>
        ) : (
          <input key={i} type={types?.[i]||"text"} placeholder={ph} value={vals[i]}
                 onChange={e => setVals(v => v.map((x,j) => j===i ? e.target.value : x))}
                 onKeyDown={e => e.key==="Enter" && commit()} />
        )
      )}
      <button onClick={commit}>+</button>
    </div>
  );
}

function TabBar({ label, options, active, onChange }) {
  return (
    <div>
      {label && <div style={{fontSize:10,color:"#94a3b8",textTransform:"uppercase",
                   letterSpacing:".08em",marginBottom:8}}>{label}</div>}
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
// App
// ---------------------------------------------------------------------------
function App() {
  const [page,         setPage]         = useState("editor");
  const [classes,      setClasses]      = useState([]);
  const [subjects,     setSubjects]     = useState([]);
  const [teachers,     setTeachers]     = useState([]);
  const [rooms,        setRooms]        = useState([]);
  const [requirements, setRequirements] = useState({});
  const [canTeach,     setCanTeach]     = useState({});

  // New constraint state
  const [subjectRoomType,   setSubjectRoomType]   = useState({});  // {subj: type}
  const [teacherUnavail,    setTeacherUnavail]     = useState({});  // {teacher: {day: {slot: bool}}}
  const [hardConstraints,   setHardConstraints]    = useState({
    max_consecutive_same_subj: 2, max_teacher_periods_day: 4 });
  const [softConstraints,   setSoftConstraints]    = useState({
    weight_class_holes: 1, weight_avoid_first_slot: 2,
    weight_avoid_last_slot: 1, weight_teacher_spread: 1, weight_subject_daily_spread: 2 });

  const [probName,    setProbName]    = useState("");
  const [savedNames,  setSavedNames]  = useState([]);
  const [statusMsg,   setStatusMsg]   = useState(null);
  const [result,      setResult]      = useState(null);
  const [schedule,    setSchedule]    = useState([]);  // mutable after drag-drop
  const [viewMode,    setViewMode]    = useState("By Class");
  const [selection,   setSelection]   = useState(null);
  const [unavailTeacher, setUnavailTeacher] = useState(null);

  useEffect(() => { refreshList().then(() => loadProblem("DEFAULT")); }, []);

  async function refreshList() {
    try { setSavedNames((await (await fetch(`${API}/list`)).json()).names || []); } catch(_) {}
  }

  function buildPayload() {
    return {
      classes, subjects, teachers,
      rooms: rooms.map(r => ({ ...r, room_type: r.room_type || "standard" })),
      days: DAYS, slots: MAX_SLOTS,
      requirements,
      can_teach: Object.fromEntries(
        teachers.map(t => [t, subjects.filter(s => (canTeach[t]||{})[s])])
      ),
      subject_room_type: subjectRoomType,
      teacher_unavailability: Object.entries(teacherUnavail).flatMap(
        ([teacher, days]) => Object.entries(days).flatMap(
          ([day, slots]) => Object.entries(slots)
            .filter(([_, blocked]) => blocked)
            .map(([slot]) => ({ teacher, day, slot: parseInt(slot) }))
        )
      ),
      hard_constraints: hardConstraints,
      soft_constraints: softConstraints,
    };
  }

  async function saveProblem() {
    if (!probName.trim()) { setStatusMsg({text:"Enter a name first.",ok:false}); return; }
    try {
      const d = await (await fetch(`${API}/save`, {
        method:"POST", headers:{"Content-Type":"application/json"},
        body: JSON.stringify({ name: probName.trim(), data: buildPayload() }),
      })).json();
      setStatusMsg(d.ok ? {text:`Saved "${probName.trim()}"`,ok:true}
                        : {text:`Save failed: ${d.error}`,ok:false});
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
      setSubjectRoomType(p.subject_room_type||{});
      // Deserialise flat unavailability list → nested {teacher:{day:{slot:bool}}}
      const ua = {};
      for (const { teacher, day, slot } of (p.teacher_unavailability||[])) {
        if (!ua[teacher]) ua[teacher] = {};
        if (!ua[teacher][day]) ua[teacher][day] = {};
        ua[teacher][day][slot] = true;
      }
      setTeacherUnavail(ua);
      setHardConstraints(p.hard_constraints || { max_consecutive_same_subj:2, max_teacher_periods_day:4 });
      setSoftConstraints(p.soft_constraints || { weight_class_holes:1, weight_avoid_first_slot:2, weight_avoid_last_slot:1, weight_teacher_spread:1, weight_subject_daily_spread:2 });
      setProbName(name); setResult(null); setSchedule([]); setStatusMsg(null); setPage("editor");
      setUnavailTeacher((p.teachers||[])[0] || null);
    } catch(e) { setStatusMsg({text:"Load failed: "+e.message,ok:false}); }
  }

  function newProblem() {
    if (!confirm("Clear current problem and start fresh?")) return;
    setClasses([]); setSubjects([]); setTeachers([]); setRooms([]);
    setRequirements({}); setCanTeach({});
    setSubjectRoomType({}); setTeacherUnavail({});
    setHardConstraints({ max_consecutive_same_subj:2, max_teacher_periods_day:4 });
    setSoftConstraints({ weight_class_holes:1, weight_avoid_first_slot:2, weight_avoid_last_slot:1, weight_teacher_spread:1 });
    setProbName(""); setResult(null); setSchedule([]); setStatusMsg(null);
  }

  async function deleteProblem() {
    if (!probName || probName === "DEFAULT") return;
    if (!confirm(`Delete "${probName}"?`)) return;
    try {
      const d = await (await fetch(`${API}/delete`, {
        method:"POST", headers:{"Content-Type":"application/json"},
        body: JSON.stringify({name: probName}),
      })).json();
      setStatusMsg(d.ok ? {text:`Deleted "${probName}"`,ok:true}
                        : {text:`Delete failed: ${d.error}`,ok:false});
      if (d.ok) { refreshList(); setProbName(""); }
    } catch(e) { setStatusMsg({text:`Delete failed: ${e.message}`,ok:false}); }
  }

  // ── entity CRUD ───────────────────────────────────────────────────────────
  const addClass     = ([n,s])    => { if(!n||classes.find(c=>c.name===n))return; setClasses(p=>[...p,{name:n,size:parseInt(s)||25}]); setRequirements(p=>({...p,[n]:p[n]||{}})); };
  const removeClass  = n          => { setClasses(p=>p.filter(c=>c.name!==n)); setRequirements(p=>{const x={...p};delete x[n];return x;}); };
  const addSubject   = ([n])      => { if(!n||subjects.includes(n))return; setSubjects(p=>[...p,n]); };
  const removeSubject= n          => {
    setSubjects(p=>p.filter(s=>s!==n));
    setRequirements(p=>Object.fromEntries(Object.entries(p).map(([c,sv])=>{const x={...sv};delete x[n];return[c,x];})));
    setCanTeach(p=>Object.fromEntries(Object.entries(p).map(([t,sv])=>{const x={...sv};delete x[n];return[t,x];})));
    setSubjectRoomType(p=>{const x={...p};delete x[n];return x;});
  };
  const addTeacher   = ([n])      => { if(!n||teachers.includes(n))return; setTeachers(p=>[...p,n]); setCanTeach(p=>({...p,[n]:{}})); setUnavailTeacher(t=>t||n); };
  const removeTeacher= n          => { setTeachers(p=>p.filter(t=>t!==n)); setCanTeach(p=>{const x={...p};delete x[n];return x;}); setTeacherUnavail(p=>{const x={...p};delete x[n];return x;}); };
  const addRoom      = ([n,c,rt]) => { if(!n||rooms.find(r=>r.name===n))return; setRooms(p=>[...p,{name:n,capacity:parseInt(c)||30,room_type:rt||"standard"}]); };
  const removeRoom   = n          => setRooms(p=>p.filter(r=>r.name!==n));
  const setReq       = (c,s,v)   => setRequirements(p=>({...p,[c]:{...(p[c]||{}),[s]:parseInt(v)||0}}));
  const setTeach     = (t,s,v)   => setCanTeach(p=>({...p,[t]:{...(p[t]||{}),[s]:v}}));
  const setUnavail   = (t,d,sl,v)=> setTeacherUnavail(p=>({...p,[t]:{...(p[t]||{}),[d]:{...((p[t]||{})[d]||{}),[sl]:v}}}));
  const setSRT       = (s,v)     => setSubjectRoomType(p=> v==="any" ? (({[s]:_,...r})=>r)(p) : {...p,[s]:v});

  // ── solve ─────────────────────────────────────────────────────────────────
  async function solve() {
    setPage("solving");
    try {
      const payload = buildPayload();
      const r = await (await fetch(`${API}/solve`, {
        method:"POST", headers:{"Content-Type":"application/json"},
        body: JSON.stringify(payload),
      })).json();
      if (r.ok) {
        // Check for unresolved hard violations the solver couldn't fix
        const vr = await (await fetch(`${API}/validate`, {
          method:"POST", headers:{"Content-Type":"application/json"},
          body: JSON.stringify({ schedule: r.schedule, original: [], data: payload }),
        })).json();
        r.hard_violations = vr.ok ? [] : vr.violations;
      }
      setResult(r);
      setSchedule(r.ok ? r.schedule : []);
      setPage(r.ok ? "result" : "editor");
      if (!r.ok) setStatusMsg({text: r.error, ok: false});
    } catch(e) {
      setResult({ok:false,error:e.message});
      setPage("editor");
      setStatusMsg({text:e.message,ok:false});
    }
  }

  // ── drag-drop override ────────────────────────────────────────────────────
  async function handleEventDrop(origEntry, newDay, newSlot, newRes, viewMode, revert) {
    const idx = schedule.findIndex(e =>
      e.class === origEntry.class && e.subject === origEntry.subject &&
      e.occ === origEntry.occ);
    if (idx < 0) { revert(); return; }

    const updated = [...schedule];
    const entry   = { ...updated[idx], day: newDay, slot: newSlot };
    if (viewMode === "By Class")   entry.class   = newRes || entry.class;
    if (viewMode === "By Teacher") entry.teacher = newRes || entry.teacher;
    if (viewMode === "By Room")    entry.room    = newRes || entry.room;
    updated[idx] = entry;

    try {
      const r = await fetch(`${API}/validate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ schedule: updated, original: schedule, data: buildPayload() }),
      });
      const resp = await r.json();
      if (resp.ok) {
        setSchedule(updated);
      } else {
        revert();
        alert("Move violates hard constraints:\n" + resp.violations.join("\n"));
      }
    } catch (e) {
      revert();
    }
  }

  // ── solving spinner ───────────────────────────────────────────────────────
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

  // ── result page ───────────────────────────────────────────────────────────
  if (page === "result" && result?.ok) {
    const softScore = computeSoftScore(schedule, softConstraints);
    const pen       = softScore.total;
    const sd        = softScore;
    const hardViols = result.hard_violations || [];
    return (
      <div>
        <div className="page-header">
          <div>
            <div className="page-title">School Timetable</div>
            <div className="page-sub">
              {`SOLVED IN ${result.stats.elapsed_ms} MS`}
              {hardViols.length > 0 ? ` · ✗ ${hardViols.length} HARD VIOLATION${hardViols.length>1?"S":""}` :
               pen > 0 ? ` · ⚠ SOFT PENALTY ${pen}` : ` · ✓ ALL CONSTRAINTS SATISFIED`}
            </div>
          </div>
          <div className="header-btns">
            <button className="btn btn-ghost" onClick={() => window.print()}>Print</button>
            <button className="btn btn-ghost" onClick={() => setPage("editor")}>← Edit</button>
            <button className="btn btn-primary" onClick={solve}>Re-solve</button>
          </div>
        </div>

        <div className="result-body">
          {hardViols.length > 0 && (
            <div className="soft-warn" style={{background:"#fee2e2",borderColor:"#fca5a5",color:"#991b1b"}}>
              ✗ {hardViols.length} hard constraint{hardViols.length>1?"s":""} could not be satisfied —{" "}
              <details style={{display:"inline"}}>
                <summary style={{display:"inline",cursor:"pointer"}}>show details</summary>
                <ul style={{margin:"4px 0 0 16px",padding:0}}>{hardViols.map((v,i)=><li key={i}>{v}</li>)}</ul>
              </details>
            </div>
          )}
          {pen > 0 && (
            <div className="soft-warn">
              ⚠ Soft score: {pen} —{" "}
              {[
                sd.class_holes      && `${sd.class_holes} class holes`,
                sd.avoid_first_slot && `${sd.avoid_first_slot} early starts`,
                sd.avoid_last_slot  && `${sd.avoid_last_slot} late finishes`,
                sd.teacher_spread         && `${sd.teacher_spread} teacher idle gaps`,
                sd.subject_daily_spread   && `${sd.subject_daily_spread} subject clustering`,
              ].filter(Boolean).join(", ")}
            </div>
          )}
          {(() => {
            const filterKey = viewMode === "By Class" ? "class"
                            : viewMode === "By Teacher" ? "teacher" : "room";
            const options = [...new Set(schedule.map(e => e[filterKey]))].sort();
            const safeSelection = options.includes(selection) ? selection : (options[0] || null);
            return (
              <>
                <div className="result-toolbar" style={{display:"flex",gap:24,marginBottom:16,alignItems:"flex-end",flexWrap:"wrap"}}>
                  <TabBar label="View by" options={["By Class","By Teacher","By Room"]}
                          active={viewMode} onChange={v => { setViewMode(v); setSelection(null); }} />
                  {options.length > 0 && (
                    <TabBar label={viewMode.replace("By ","")} options={options}
                            active={safeSelection} onChange={setSelection} />
                  )}
                </div>
                <TimetableCalendar
                  schedule={schedule}
                  subjects={subjects}
                  viewMode={viewMode}
                  selection={safeSelection}
                  onEventDrop={handleEventDrop}
                />
              </>
            );
          })()}
        </div>
      </div>
    );
  }

  // ── editor page ───────────────────────────────────────────────────────────
  const activeUnavailTeacher = unavailTeacher || teachers[0] || null;

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

        {/* Toolbar */}
        <div style={{display:"flex",flexDirection:"column",gap:8}}>
          <div className="editor-toolbar">
            <input value={probName} onChange={e=>setProbName(e.target.value)}
                   placeholder="Problem name" maxLength={64}
                   onKeyDown={e=>e.key==="Enter"&&saveProblem()} />
            <button className="btn btn-dark" onClick={saveProblem}>Save</button>
            <button className="btn btn-danger" onClick={deleteProblem}
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
        <div className="editor-cols">
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
            <TagList items={rooms} label={r=>`${r.name} (${r.capacity}, ${r.room_type||"standard"})`} onRemove={removeRoom} />
            <AddRow placeholders={["Room","Cap",""]} types={["text","number",null]}
                    options={[null,null,ROOM_TYPES]} onAdd={addRoom} />
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
                    <th></th>{subjects.map(s=><th key={s}>{s}</th>)}
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
                    <th></th>{subjects.map(s=><th key={s}>{s}</th>)}
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

        {/* Row 3: Subject room type · Soft constraints */}
        <div className="editor-cols-3">
          <div className="card">
            <div className="card-title">Subject room type requirement</div>
            {subjects.length ? (
              <div style={{overflowX:"auto"}}>
                <table className="grid">
                  <thead><tr><th style={{textAlign:"left"}}>Subject</th><th>Required room type</th></tr></thead>
                  <tbody>
                    {subjects.map(s=>(
                      <tr key={s}>
                        <td className="row-hd">{s}</td>
                        <td>
                          <select value={subjectRoomType[s]||"any"}
                                  onChange={e=>setSRT(s,e.target.value)}
                                  style={{fontSize:11,background:"#f8fafc",border:"1px solid #e2e8f0",
                                          borderRadius:3,padding:"2px 4px"}}>
                            <option value="any">any</option>
                            {ROOM_TYPES.map(rt=><option key={rt} value={rt}>{rt}</option>)}
                          </select>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : <span className="placeholder">Add subjects first.</span>}
          </div>

          <div className="card">
            <div className="card-title">Hard constraints</div>
            <div style={{display:"flex",flexDirection:"column",gap:14}}>
              {[
                ["Max consecutive same subject", "max_consecutive_same_subj", 2],
                ["Max periods per day per teacher", "max_teacher_periods_day", 4],
              ].map(([label, key, def]) => (
                <div key={key}>
                  <div style={{fontSize:11,color:"#64748b",marginBottom:4}}>{label}</div>
                  <input type="number" min={1} max={8}
                         value={hardConstraints[key] ?? def}
                         onChange={e=>setHardConstraints(p=>({...p,[key]:parseInt(e.target.value)||def}))}
                         style={{width:60,background:"#f8fafc",border:"1px solid #e2e8f0",
                                 borderRadius:4,padding:"4px 8px",fontSize:12}} />
                </div>
              ))}
            </div>
          </div>

          <div className="card">
            <div className="card-title">Soft constraints (weights)</div>
            <div style={{display:"flex",flexDirection:"column",gap:14}}>
              {[
                ["Class free-period holes", "weight_class_holes", 1],
                ["Avoid slot 1 (early start)", "weight_avoid_first_slot", 2],
                ["Avoid last slot (late finish)", "weight_avoid_last_slot", 1],
                ["Teacher idle gaps (free periods between lessons)", "weight_teacher_spread", 1],
                ["Subject clustering (same subject on same day)", "weight_subject_daily_spread", 2],
              ].map(([label, key, def]) => (
                <div key={key}>
                  <div style={{fontSize:11,color:"#64748b",marginBottom:4}}>{label}</div>
                  <input type="number" min={0} max={10}
                         value={softConstraints[key] ?? def}
                         onChange={e=>setSoftConstraints(p=>({...p,[key]:parseInt(e.target.value)??def}))}
                         style={{width:60,background:"#f8fafc",border:"1px solid #e2e8f0",
                                 borderRadius:4,padding:"4px 8px",fontSize:12}} />
                </div>
              ))}
            </div>
          </div>

          <div className="card">
            <div className="card-title">Schedule info</div>
            <div style={{fontSize:11,color:"#64748b",lineHeight:1.8}}>
              <div>Days: Monday – Friday</div>
              <div>Periods: {MAX_SLOTS} per day</div>
              <div>Total slots: {5 * MAX_SLOTS}</div>
              {subjects.length > 0 && classes.length > 0 && (() => {
                const total = classes.reduce((acc,cl)=>
                  acc + subjects.reduce((a,s)=>a+(requirements[cl.name]?.[s]||0),0),0);
                return <div>Lessons to schedule: {total}</div>;
              })()}
            </div>
          </div>
        </div>

        {/* Row 4: Teacher unavailability */}
        <div className="card">
          <div className="card-title">Teacher unavailability — block day/period combinations</div>
          {teachers.length ? (
            <div>
              <div style={{marginBottom:12}}>
                <TabBar options={teachers} active={activeUnavailTeacher}
                        onChange={setUnavailTeacher} />
              </div>
              {activeUnavailTeacher && (
                <div style={{overflowX:"auto"}}>
                  <table className="grid">
                    <thead><tr>
                      <th>Period</th>
                      {DAYS.map(d=><th key={d}>{d.slice(0,3)}</th>)}
                    </tr></thead>
                    <tbody>
                      {Array.from({length:MAX_SLOTS},(_,i)=>i+1).map(sl=>(
                        <tr key={sl}>
                          <td className="row-hd">P{sl}</td>
                          {DAYS.map(d=>{
                            const blocked = !!((teacherUnavail[activeUnavailTeacher]||{})[d]||{})[sl];
                            return (
                              <td key={d} className={blocked?"blocked":""}>
                                <input type="checkbox" checked={blocked}
                                       onChange={e=>setUnavail(activeUnavailTeacher,d,sl,e.target.checked)} />
                              </td>
                            );
                          })}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          ) : <span className="placeholder">Add teachers first.</span>}
        </div>

      </div>
    </div>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<App />);
</script>
</body>
</html>
