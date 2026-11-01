"""Local page for hand-labelling the verifier sheet (python -m research.labelling serve <sheet>).

Asks one plain question per claim (worded for its type), shows the rewritten
line, the most similar lines of the original (by word overlap, computed in the
page) and the full original with matches highlighted. Press S (supported) or
U (unsupported); the label is written to sheet.csv at once,
so labelling can stop and resume at any point. The verifier's own verdict is
never sent to the page, so it cannot bias the labeller.
"""
from __future__ import annotations

import csv
import json
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HIDDEN = {"verifier", "verifier_reason", "weight"}   # never shown while labelling
EDITABLE = {"label_a", "label_b", "label_final", "notes"}

PAGE = r"""<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Claim checking</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
:root{--ink:#17201a;--muted:#5a6658;--line:#d6dbcc;--bg:#eef1e6;--card:#fbfcf8;--yes:#2f7a3d;--no:#c1272d;--hl:#ffe680;--soft:#fff7cf}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.55 system-ui,Segoe UI,sans-serif}
header{display:flex;gap:14px;align-items:center;padding:10px 20px;border-bottom:1px solid var(--line);background:var(--card);position:sticky;top:0;z-index:2;flex-wrap:wrap}
header b{font-size:17px}#count{color:var(--muted);font-size:14px;white-space:nowrap}
.bar{flex:1;min-width:120px;height:10px;background:var(--line);border-radius:5px;overflow:hidden}.bar i{display:block;height:100%;background:var(--yes);transition:width .2s}
main{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:16px;padding:16px 20px;max-width:1400px;margin:auto}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:18px 20px}
.k{font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);margin:16px 0 6px}
.k:first-child{margin-top:0}
#question{font-size:21px;line-height:1.35;font-weight:650;margin:0}
#question b{background:var(--hl);padding:0 4px;border-radius:4px}
#hint{color:var(--muted);font-size:14.5px;margin:6px 0 0}
.line{background:#fff;border:1px solid var(--line);border-radius:10px;padding:10px 12px}
.rew{font-size:17px;border-left:4px solid var(--ink)}
#search{display:inline-block;margin-top:8px;font-size:14px;padding:3px 10px;border-radius:99px}
.found{background:#e3f1e4;color:var(--yes)}.notfound{background:#fbe5e5;color:var(--no)}
.match{cursor:pointer;margin-bottom:6px;font-size:15px}.match:hover{border-color:var(--ink)}
.match small{color:var(--muted)}
mark{background:var(--hl);padding:0 1px;border-radius:2px}
.btns{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:18px}
button{font:inherit;padding:10px 16px;border-radius:10px;border:1px solid var(--line);background:#fff;color:var(--ink);cursor:pointer}
.big{padding:14px 12px;font-size:17px;font-weight:650;color:#fff;text-align:left}
.big span{display:block;font-size:13px;font-weight:400;opacity:.9}
.yes{background:var(--yes);border-color:var(--yes)}.no{background:var(--no);border-color:var(--no)}
.chosen{outline:4px solid var(--ink);outline-offset:2px}
.nav{display:flex;gap:8px;margin-top:10px;flex-wrap:wrap}.nav button{font-size:14px;padding:7px 12px}
#answer{font-size:14px;color:var(--muted);margin-top:10px}
input[type=text]{width:100%;padding:8px 10px;border:1px solid var(--line);border-radius:8px;font:inherit;font-size:14px}
#full{white-space:pre-wrap;font-size:14.5px;line-height:1.6;max-height:calc(100vh - 150px);overflow:auto;margin:0}
.flash{animation:fl 1.2s}@keyframes fl{from{background:var(--hl)}to{background:transparent}}
select{font:inherit;font-size:14px;padding:3px}label.small{font-size:14px;color:var(--muted)}
#guide{position:fixed;inset:0;background:rgba(20,25,20,.45);display:none;align-items:flex-start;justify-content:center;z-index:5;overflow:auto;padding:30px 12px}
#guide .card{max-width:820px;width:100%}
#guide h2{margin:0 0 6px;font-size:22px}#guide table{border-collapse:collapse;width:100%;font-size:14.5px;margin:10px 0}
#guide td,#guide th{border:1px solid var(--line);padding:7px 9px;vertical-align:top;text-align:left}#guide th{background:#eef1e6}
#guide ol{padding-left:22px;margin:8px 0}#guide li{margin:4px 0}
#done{display:none;max-width:700px;margin:40px auto}
code{background:#eef1e6;padding:1px 5px;border-radius:4px;font-size:13.5px}
@media(max-width:900px){main{grid-template-columns:1fr}#full{max-height:60vh}}
</style></head><body>
<header><b>Claim checking</b><span id="count"></span><div class="bar"><i id="prog"></i></div>
<button id="gbtn">How to decide</button>
<label class="small">I am labeller <select id="who"><option value="label_a">A (main)</option><option value="label_b">B (second person)</option><option value="label_final">Final (settle disagreements)</option></select></label></header>

<main id="work"><section class="card">
<div class="k">Question <span id="num"></span></div>
<p id="question"></p><p id="hint"></p>
<div class="k">What the AI wrote</div>
<div class="line rew" id="rew"></div><span id="search"></span>
<div class="k">Most similar lines in the original resume <small style="text-transform:none;letter-spacing:0;font-weight:400">(click to find it on the right)</small></div>
<div id="matches"></div>
<div class="btns">
<button class="big yes" id="bS">✓ Yes: the original backs it up<span>supported · key S</span></button>
<button class="big no" id="bU">✗ No: it's new or inflated<span>unsupported · key U</span></button></div>
<div class="nav"><button id="bPrev">← Previous</button><button id="bNext">Not sure, skip for now →</button><button id="next0">Jump to next unanswered</button></div>
<div id="answer"></div>
<div class="k">Note (optional, e.g. why you were unsure)</div><input type="text" id="notes">
</section>
<section class="card"><div class="k">The original resume (what the person really wrote)</div><div id="full"></div></section></main>

<section class="card" id="done"><h2>All questions answered</h2>
<p>Every claim has an answer from this labeller. Your answers are already saved in <code>sheet.csv</code>, so you can close this tab.</p>
<p>Next, stop the page with Ctrl+C in the terminal, then score the checker:</p>
<p><code>.venv\Scripts\python -m research.labelling evaluate research/labels/sheet.csv</code></p>
<p><button id="review">Go back and review answers</button></p></section>

<div id="guide"><div class="card">
<h2>How to decide</h2>
<p>An AI rewrote real resumes to fit a job ad. Some lines it wrote are honest rewordings; some add things the person never claimed. A checker program tried to tell them apart. <b>Your answers are the ground truth that tells us how accurate that checker is.</b></p>
<p>For each question, ask one thing: <b>reading only the original resume (right side), would I believe this line is true of this person?</b></p>
<ol><li>Read the question and the AI's line on the left.</li>
<li>Look at the most similar original lines, or search the full resume on the right. The yellow highlights are the matching words.</li>
<li>Press <b>S</b> if the original backs it up and <b>U</b> if it doesn't. If you can't decide, skip it and come back later.</li></ol>
<table><tr><th>Type</th><th>✓ Yes (S) when…</th><th>✗ No (U) when…</th></tr>
<tr><td>Skill</td><td>The skill or an obvious synonym is in the original (JS = JavaScript)</td><td>It only comes from the job ad. Example: original has no "Kubernetes", rewrite lists it</td></tr>
<tr><td>Number</td><td>The same number is in the original, for the same thing</td><td>New number ("improved efficiency by 35%"), or a real number moved to a different achievement</td></tr>
<tr><td>Role level</td><td>The original shows the same level: they really led or managed it</td><td>"Assisted / helped / part of" became "led / managed / drove", or a senior title was added</td></tr>
<tr><td>Qualification</td><td>The degree, certificate or licence is in the original</td><td>New, or upgraded (B.Sc → M.Sc, diploma → degree)</td></tr>
<tr><td>Sentence</td><td>Every fact in it is in the original, even if the wording is completely different</td><td>It adds a duty, result, tool, audience or setting the original never mentions</td></tr></table>
<p><b>Tips.</b> Ignore pure style words ("effectively", "successfully", "with attention to detail"); judge the facts. The "most similar lines" are the computer's guess and can be wrong, so if they don't match, check the full resume. Don't overthink it: 20–30 seconds per question is normal. Every answer saves immediately, so you can stop and come back any time.</p>
<p><button id="gclose" class="big yes" style="text-align:center">Got it, start</button></p>
</div></div>

<script>
let rows=[],i=0;const $=id=>document.getElementById(id);
const esc=s=>(s||"").replace(/[&<>]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;"}[c]));
const STOP=new Set("the and with for from that this into their within across over under also using used such through while was were has have had are its our your they them all any per via who".split(" "));
const words=t=>[...new Set((t||"").toLowerCase().match(/[a-z0-9+#%]+/g)||[])].filter(w=>w.length>2&&!STOP.has(w));
const rx=w=>new RegExp("(?<![A-Za-z0-9])("+w.replace(/[.*+?^${}()|[\]\\]/g,"\\$&")+")(?![A-Za-z0-9])","gi");
function mark(text,terms){let h=esc(text);for(const w of terms){h=h.replace(rx(esc(w)),"<mark>$1</mark>")}return h}
const LABEL={skill:"Skill",metric:"Number",role_scope:"Role level",credential:"Qualification",content:"Sentence"};
function ask(r){const c=esc(r.claim);switch(r.type){
case"skill":return[`Does the original resume show this person has the skill <b>${c}</b>?`,"Yes if the skill or an obvious synonym appears. No if it only appears in the job ad."];
case"metric":return[`Does the number <b>${c}</b> come from the original resume, for the same thing?`,"No if the number is new, or a real number is attached to a different achievement."];
case"role_scope":return[`The AI says <b>${c}</b>. Does the original show the person really had that level of role?`,"No if the original only says helped / assisted / supported / part of, or never mentions it."];
case"credential":return[`Does the original resume list the qualification <b>${c}</b>?`,"No if it is new or upgraded (B.Sc → M.Sc)."];
default:return["Does the original resume say what this line says (in any words)?","Judge the facts, not the style. No if the line adds a duty, result, tool or setting the original never mentions."]}}
const HEAD=/^(professional |work |career )?(summary|experience|education( and training)?|skills|accomplishments|highlights|certifications?|qualifications|overview|profile|objective|training|interests|languages|additional information|affiliations|awards|projects)$/i;
function tidy(t){const out=[];let buf=[];const flush=()=>{if(buf.length){out.push(buf.join(" ").replace(/\s+,/g,",").replace(/\s+:/g,":"));buf=[]}};
for(let l of (t||"").split("\n")){l=l.replace(/[－–]/g,"—").trim();if(!l)continue;
if(HEAD.test(l)){flush();out.push("");out.push(l.toUpperCase());continue}
if(l.length<40&&!/[.;]$/.test(l))buf.push(l);else{flush();out.push(...l.split(/(?<=[.;])\s+(?=[A-Z])/))}}
flush();return out.join("\n").replace(/^\n+/,"")}
function sentences(t){return (t||"").split(/\n|(?<=[.;])\s+/).map(s=>s.trim()).filter(s=>s.length>3)}
function similar(r){const q=words(r.rewritten_line);if(!q.length)return[];
return sentences(r.original).map(s=>{const w=new Set(words(s));const hit=q.filter(x=>w.has(x));return{s,hit,score:hit.length/q.length}})
.filter(x=>x.score>=0.2&&x.hit.length>=2).sort((a,b)=>b.score-a.score).slice(0,3)}
function lab(r){return (r[$("who").value]||"").trim().toUpperCase().slice(0,1)}
function show(){const r=rows[i];if(!r)return;const done=rows.filter(lab).length;
$("count").textContent=`${done} of ${rows.length} answered`;$("prog").style.width=(100*done/rows.length)+"%";
$("num").textContent=`${i+1} of ${rows.length} · ${LABEL[r.type]||r.type}`;
const [q,h]=ask(r);$("question").innerHTML=q;$("hint").textContent=h;
const isTerm=r.type!=="content";const terms=isTerm?[r.claim]:words(r.rewritten_line);
$("rew").innerHTML=isTerm?mark(r.rewritten_line,[r.claim]):esc(r.rewritten_line);
const s=$("search");if(isTerm){const n=((r.original||"").match(rx(r.claim))||[]).length;
s.style.display="";s.className=n?"found":"notfound";s.textContent=n?`"${r.claim}" appears ${n}× in the original`:`"${r.claim}" does not appear word-for-word in the original. Check for synonyms.`}else s.style.display="none";
const m=similar(r);$("matches").innerHTML=m.length?m.map((x,k)=>`<div class="line match" data-k="${k}">${mark(x.s,x.hit)} <small>· ${Math.round(100*x.score)}% of words shared</small></div>`).join(""):'<div class="line"><small>No original line shares many words with it. That often means it is new, but skim the resume on the right to be sure.</small></div>';
document.querySelectorAll(".match").forEach(el=>el.onclick=()=>jump(m[+el.dataset.k].s));
const full=$("full");full.innerHTML=isTerm?mark(r.original,[r.claim]):(m[0]?esc(r.original).replace(esc(m[0].s),`<mark id="best">${esc(m[0].s)}</mark>`):esc(r.original));
full.scrollTop=0;scrollTo(full.querySelector("mark"));
const l=lab(r);$("bS").classList.toggle("chosen",l==="S");$("bU").classList.toggle("chosen",l==="U");
$("answer").textContent=l?`Your answer: ${l==="S"?"Yes (supported)":"No (unsupported)"}. Press the other button to change it.`:"";
$("notes").value=r.notes||"";$("done").style.display="none";$("work").style.display=""}
function jump(sent){const full=$("full");full.innerHTML=esc(rows[i].original).replace(esc(sent),`<mark id="j" class="flash">${esc(sent)}</mark>`);
scrollTo($("j"))}
function scrollTo(el){const full=$("full");if(el)full.scrollTop+=el.getBoundingClientRect().top-full.getBoundingClientRect().top-60}
async function save(field,value){const r=rows[i];r[field]=value;await fetch("/api/label",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({row_id:r.row_id,field,value})})}
function nextOpen(){for(let k=1;k<=rows.length;k++){const j=(i+k)%rows.length;if(!lab(rows[j]))return j}return -1}
async function answer(v){await save($("who").value,v);const j=nextOpen();if(j<0){finish();return}i=j;show()}
function finish(){$("count").textContent=`${rows.length} of ${rows.length} answered`;$("prog").style.width="100%";$("work").style.display="none";$("done").style.display="block"}
function guide(on){$("guide").style.display=on?"flex":"none";if(!on)try{localStorage.setItem("seenGuide","1")}catch(e){}}
$("bS").onclick=()=>answer("S");$("bU").onclick=()=>answer("U");
$("bPrev").onclick=()=>{if(i>0)i--;show()};$("bNext").onclick=()=>{if(i<rows.length-1)i++;show()};
$("next0").onclick=()=>{const j=nextOpen();if(j>=0){i=j;show()}else finish()};$("review").onclick=()=>{i=0;show()};
$("who").onchange=()=>{const k=rows.findIndex(r=>!lab(r));i=k>=0?k:0;show()};$("notes").onchange=e=>save("notes",e.target.value);
$("gbtn").onclick=()=>guide(true);$("gclose").onclick=()=>guide(false);
document.onkeydown=e=>{if(e.target.tagName==="INPUT"||e.target.tagName==="SELECT")return;if($("guide").style.display==="flex"){if(e.key==="Escape"||e.key==="Enter")guide(false);return}
const k=e.key.toLowerCase();if(k==="s")answer("S");else if(k==="u")answer("U");else if(e.key==="ArrowLeft")$("bPrev").click();else if(e.key==="ArrowRight")$("bNext").click()};
let seen=false;try{seen=!!localStorage.getItem("seenGuide")}catch(e){}if(!seen&&!location.hash.includes("noguide"))guide(true);
fetch("/api/rows").then(r=>r.json()).then(d=>{rows=d;rows.forEach(r=>r.original=tidy(r.original));const k=rows.findIndex(r=>!lab(r));i=k>=0?k:0;show()});
</script></body></html>"""


def serve(sheet: str, port: int = 8765, open_browser: bool = True) -> None:
    path = Path(sheet)
    originals = path.parent / "originals"
    lock = threading.Lock()

    def read():
        with open(path, encoding="utf-8", newline="") as f:
            return list(csv.DictReader(f))

    def write(rows):
        fields = list(rows[0].keys())
        tmp = path.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            w.writerows(rows)
        tmp.replace(path)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *a):  # quiet
            pass

        def _send(self, code, body, ctype):
            data = body.encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            if self.path == "/":
                return self._send(200, PAGE, "text/html; charset=utf-8")
            if self.path == "/api/rows":
                with lock:
                    rows = read()
                out = []
                for r in rows:
                    o = originals / f"{r['row_id']}.txt"
                    out.append({k: v for k, v in r.items() if k not in HIDDEN}
                               | {"original": o.read_text(encoding="utf-8") if o.exists() else ""})
                return self._send(200, json.dumps(out), "application/json")
            self._send(404, "not found", "text/plain")

        def do_POST(self):
            if self.path != "/api/label":
                return self._send(404, "not found", "text/plain")
            msg = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
            if msg.get("field") not in EDITABLE:
                return self._send(400, "bad field", "text/plain")
            with lock:
                rows = read()
                for r in rows:
                    if r["row_id"] == msg.get("row_id"):
                        r[msg["field"]] = str(msg.get("value", ""))[:500]
                write(rows)
            self._send(200, "{}", "application/json")

    url = f"http://127.0.0.1:{port}/"
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"labelling page: {url}  (labels save to {path}; Ctrl+C to stop)")
    if open_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
