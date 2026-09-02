/* Local conversation history — ChatGPT-style list + thread. */
"use strict";
const AVHistory = (() => {
  const GREEN = "#3ddc84";
  const PINK = "#a01650";

  function esc(s) {
    return String(s || "").replace(/&/g, "&amp;").replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  function when(iso) {
    if (!iso) return "";
    const d = new Date(iso);
    if (isNaN(d.getTime())) return iso;
    return d.toLocaleString(undefined, {
      month: "short", day: "numeric", hour: "numeric", minute: "2-digit"
    });
  }

  function accent(agent) {
    return String(agent || "").toLowerCase().indexOf("friday") >= 0
      ? PINK : GREEN;
  }

  function css() {
    return `
#av-hist-btn{position:fixed;top:18px;right:18px;z-index:90;cursor:pointer;
  font:700 11px 'SF Mono',Menlo,Consolas,monospace;letter-spacing:.28em;
  color:#3ddc84;border:1px solid #3ddc84;background:rgba(0,0,0,.72);
  padding:8px 12px;border-radius:2px;user-select:none;
  -webkit-app-region:no-drag;pointer-events:auto}
#av-hist-modal{position:fixed;inset:0;z-index:120;background:rgba(0,0,0,.82);
  display:flex;align-items:center;justify-content:center;
  font-family:'SF Mono',Menlo,Consolas,monospace;color:#c8ffd4;
  -webkit-app-region:no-drag}
#av-hist-box{width:min(980px,96vw);height:min(84vh,720px);background:#050805;
  border:1px solid #3ddc84;display:flex;overflow:hidden}
body[data-agent='friday'] #av-hist-box{border-color:#a01650;color:#ffd0e4}
#av-hist-side{width:280px;min-width:220px;border-right:1px solid rgba(61,220,132,.28);
  overflow:auto;background:#030503}
#av-hist-main{flex:1;display:flex;flex-direction:column;min-width:0}
#av-hist-head{display:flex;align-items:center;justify-content:space-between;
  gap:12px;padding:12px 16px;border-bottom:1px solid rgba(61,220,132,.28);
  letter-spacing:.22em;font-size:11px;font-weight:700}
#av-hist-head button{cursor:pointer;background:transparent;color:inherit;
  border:1px solid currentColor;padding:4px 10px;letter-spacing:.2em;
  font:700 10px inherit}
.av-hist-item{display:block;width:100%;text-align:left;cursor:pointer;
  background:transparent;border:0;border-bottom:1px solid rgba(255,255,255,.05);
  color:inherit;padding:12px 14px;font:500 12px/1.35 inherit}
.av-hist-item:hover,.av-hist-item.on{background:rgba(61,220,132,.12)}
.av-hist-item .who{letter-spacing:.16em;font-size:10px;font-weight:700;
  margin-bottom:4px;opacity:.85}
.av-hist-item .preview{opacity:.8;display:-webkit-box;-webkit-line-clamp:2;
  -webkit-box-orient:vertical;overflow:hidden}
#av-hist-thread{flex:1;overflow:auto;padding:16px 18px 28px}
.av-hist-empty{padding:28px 18px;opacity:.6}
.av-hist-bubble{max-width:78%;margin:10px 0;padding:10px 12px;border-radius:4px;
  white-space:pre-wrap;word-break:break-word;line-height:1.45;font-size:13px}
.av-hist-bubble.you{margin-left:auto;background:rgba(53,224,255,.14);
  border:1px solid rgba(53,224,255,.35)}
.av-hist-bubble.agent{margin-right:auto;background:rgba(61,220,132,.1);
  border:1px solid rgba(61,220,132,.3)}
.av-hist-bubble .who{letter-spacing:.16em;font-size:10px;font-weight:700;
  margin-bottom:6px;opacity:.7}
.av-hist-page{min-height:100vh;background:#000;margin:0;color:#c8ffd4;
  font-family:'SF Mono',Menlo,Consolas,monospace}
.av-hist-page #av-hist-modal{background:#000}
.av-hist-page #av-hist-box{width:min(1100px,98vw);height:94vh;margin:3vh auto}
`;
  }

  function ensureCss() {
    if (document.getElementById("av-hist-css")) return;
    const s = document.createElement("style");
    s.id = "av-hist-css";
    s.textContent = css();
    document.head.appendChild(s);
  }

  async function fetchList() {
    const r = await fetch("/api/history", { cache: "no-store" });
    return r.json();
  }

  async function fetchOne(id) {
    const r = await fetch("/api/history/" + encodeURIComponent(id),
                          { cache: "no-store" });
    return r.json();
  }

  function renderList(box, items, selected, onOpen) {
    const side = box.querySelector("#av-hist-side");
    if (!items.length) {
      side.innerHTML = '<div class="av-hist-empty">No chats yet.</div>';
      return;
    }
    side.innerHTML = items.map(it => {
      const col = accent(it.agent);
      const title = it.title || it.preview || "New chat";
      const on = it.id === selected ? " on" : "";
      return `<button class="av-hist-item${on}" data-id="${esc(it.id)}">
        <div class="who" style="color:${col}">${esc((it.agent || "?").toUpperCase())}
          · ${esc(when(it.started))}</div>
        <div class="preview">${esc(title)}</div>
      </button>`;
    }).join("");
    side.querySelectorAll(".av-hist-item").forEach(btn => {
      btn.onclick = () => onOpen(btn.getAttribute("data-id"));
    });
  }

  function renderThread(box, doc) {
    const head = box.querySelector("#av-hist-head span");
    if (head) {
      head.textContent = (doc.title || doc.preview || "CHAT").toUpperCase();
    }
    const pane = box.querySelector("#av-hist-thread");
    const turns = doc.turns || [];
    if (!turns.length) {
      pane.innerHTML = '<div class="av-hist-empty">Empty chat.</div>';
      return;
    }
    pane.innerHTML = turns.map(t => {
      const you = String(t.role || "").toLowerCase() === "you";
      const col = you ? "#35e0ff" : accent(t.role);
      return `<div class="av-hist-bubble ${you ? "you" : "agent"}">
        <div class="who" style="color:${col}">${esc((t.role || "?").toUpperCase())}
          · ${esc(when(t.ts))}</div>
        ${esc(t.text)}
      </div>`;
    }).join("");
    pane.scrollTop = 0;
  }

  function makeBox() {
    const box = document.createElement("div");
    box.id = "av-hist-box";
    box.innerHTML =
      '<aside id="av-hist-side"></aside>' +
      '<section id="av-hist-main">' +
      '<div id="av-hist-head"><span>CHATS</span>' +
      '<button type="button" data-close>CLOSE</button></div>' +
      '<div id="av-hist-thread"><div class="av-hist-empty">Select a chat.</div></div>' +
      "</section>";
    return box;
  }

  function wire(box, closeFn) {
    const close = box.querySelector("[data-close]");
    if (close && closeFn) close.onclick = closeFn;
    let selected = "";
    function showList() {
      fetchList().then(items => {
        renderList(box, items, selected, showOne);
        if (!selected && items[0]) showOne(items[0].id);
      }).catch(() => renderList(box, [], "", showOne));
    }
    function showOne(id) {
      selected = id;
      fetchList().then(items => renderList(box, items, selected, showOne));
      fetchOne(id).then(doc => renderThread(box, doc))
        .catch(() => showList());
    }
    showList();
  }

  function openModal() {
    ensureCss();
    closeModal();
    const modal = document.createElement("div");
    modal.id = "av-hist-modal";
    const box = makeBox();
    modal.appendChild(box);
    document.body.appendChild(modal);
    const close = () => closeModal();
    modal.addEventListener("click", e => { if (e.target === modal) close(); });
    wire(box, close);
  }

  function closeModal() {
    const m = document.getElementById("av-hist-modal");
    if (m) m.remove();
  }

  function openHistory() {
    if (document.body.classList.contains("av-overlay")) {
      fetch("/api/open-history", { cache: "no-store" }).catch(() => {});
      return;
    }
    openModal();
  }

  function attachButton(opts) {
    opts = opts || {};
    ensureCss();
    if (document.getElementById("av-hist-btn")) return;
    const btn = document.createElement("button");
    btn.id = "av-hist-btn";
    btn.type = "button";
    btn.textContent = "HISTORY";
    btn.onclick = e => { e.preventDefault(); e.stopPropagation(); openHistory(); };
    document.body.appendChild(btn);
    if (!opts.always) {
      btn.style.opacity = "0";
      let hideT = null;
      addEventListener("mousemove", () => {
        btn.style.opacity = "1";
        clearTimeout(hideT);
        hideT = setTimeout(() => { btn.style.opacity = "0"; }, 3000);
      });
    }
  }

  function mountPage(root) {
    ensureCss();
    document.body.classList.add("av-hist-page");
    const modal = document.createElement("div");
    modal.id = "av-hist-modal";
    const box = makeBox();
    const close = box.querySelector("[data-close]");
    if (close) close.style.display = "none";
    modal.appendChild(box);
    (root || document.body).appendChild(modal);
    wire(box, null);
  }

  return { openModal, openHistory, attachButton, mountPage, closeModal };
})();
