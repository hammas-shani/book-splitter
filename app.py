"""
PDF Chapter Splitter - Universal Edition (Deep Hierarchy Update)
================================================================
Understands nested chapters inside parts (Level 1, 2, and 3 TOC).
0% Data Loss Guaranteed in Splitting.
Requires: pip install streamlit pymupdf
"""

import io
import re
import zipfile
import statistics
from collections import Counter

import fitz  # PyMuPDF
import streamlit as st

# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG & UI STYLES
# ─────────────────────────────────────────────────────────────────────────────

st.set_page_config(page_title="Universal PDF Splitter", page_icon="📚", layout="centered")

STYLES = """
<style>
[data-testid="stAppViewContainer"] { background: linear-gradient(160deg, #0d0d1a 0%, #1a1033 50%, #0d1a2a 100%); min-height: 100vh; }
.pro-title { text-align: center; font-size: clamp(2rem, 5vw, 3.2rem); font-weight: 900; background: linear-gradient(90deg, #a78bfa 0%, #60a5fa 50%, #34d399 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 0.3rem; }
.pro-subtitle { text-align: center; color: #64748b; font-size: 1rem; margin-bottom: 2.5rem; }
.step-pill { display: inline-flex; align-items: center; gap: 10px; background: linear-gradient(135deg, #1e1b4b88, #312e8188); border: 1px solid #4338ca55; border-radius: 50px; padding: 8px 20px 8px 10px; font-weight: 700; color: #a5b4fc; margin: 1.5rem 0 0.75rem 0; }
.step-num { background: linear-gradient(135deg, #6366f1, #8b5cf6); color: white; border-radius: 50%; width: 28px; height: 28px; display: inline-flex; align-items: center; justify-content: center; font-weight: 900; }
.card { background: linear-gradient(135deg, #0f172a, #1e1b4b55); border: 1px solid #4338ca44; border-radius: 16px; padding: 22px 24px; margin: 12px 0; }
.metrics-row { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-bottom: 20px; }
.metric-box { background: #0f172a; border: 1px solid #4338ca44; border-radius: 12px; padding: 16px 12px; text-align: center; }
.metric-val { font-size: 2rem; font-weight: 900; line-height: 1.1; }
.metric-lbl { font-size: 0.7rem; color: #64748b; margin-top: 5px; text-transform: uppercase; }
.ch-item { display: flex; justify-content: space-between; align-items: center; background: #0f172a; border-left: 3px solid #6366f1; border-radius: 0 8px 8px 0; padding: 9px 14px; margin: 5px 0; font-size: 0.875rem; color: #cbd5e1; }
.ch-badge { background: #1e1b4b; color: #818cf8; border-radius: 20px; padding: 3px 10px; font-size: 0.72rem; font-weight: 600; margin-left: 10px; }
.success-card { background: linear-gradient(135deg, #052e16, #064e3b); border: 1px solid #10b98155; border-radius: 16px; padding: 28px 24px; text-align: center; margin: 16px 0; }
.success-title { font-size: 1.3rem; font-weight: 800; color: #34d399; margin: 10px 0 4px; }
div[data-testid="stFileUploader"] { border: 2px dashed #4338ca66 !important; border-radius: 14px !important; background: #0f172a88 !important; padding: 8px !important; }
button[kind="primary"] { width: 100% !important; background: linear-gradient(135deg, #6366f1, #8b5cf6) !important; color: white !important; border: none !important; border-radius: 10px !important; font-weight: 700 !important; }
button[kind="secondary"] { width: 100% !important; background: #1e1b4b !important; color: #f87171 !important; border: 1px solid #4338ca55 !important; border-radius: 8px !important; font-weight: bold !important; transition: all 0.2s; height: 38px;}
button[kind="secondary"]:hover { background: #ef4444 !important; color: white !important; }
.ch-item:hover { background: #1e293b; border-left-color: #8b5cf6; cursor: default; }
</style>
"""
st.markdown(STYLES, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# UNIVERSAL PATTERNS
# ─────────────────────────────────────────────────────────────────────────────

UNIVERSAL_PATTERNS = [
    # Pattern A: Explicit Chapter/Part (e.g., "Chapter 1:", "Part II")
    re.compile(r"^(chapter|chap\.?|part|book|volume|unit|module|section|lesson)\s+([0-9ivxlcdm]+|[a-z]+)", re.IGNORECASE),
    
    # Pattern B: Numbered Headings (e.g., "1. Introduction", "IV. Conclusion")
    re.compile(r"^([0-9]{1,2}|[ivxlcdm]{1,5})[\.\-\:\u2013\u2014]\s*[A-Z]", re.IGNORECASE),
    
    # Pattern C: Standard Book Sections
    re.compile(r"^(introduction|prologue|preface|foreword|epilogue|conclusion|appendix|acknowledgments?|bibliography)\b", re.IGNORECASE)
]


# ─────────────────────────────────────────────────────────────────────────────
# UNIVERSAL PDF ANALYZER (WITH DEEP HIERARCHY)
# ─────────────────────────────────────────────────────────────────────────────

class UniversalAnalyzer:
    def __init__(self, doc: fitz.Document):
        self.doc = doc
        self.pages = len(doc)
        self.body_size = self._calculate_body_font()
        # Smarter dynamic gap for books with small chapters
        self.min_gap = max(2, self.pages // 100) 

    def _calculate_body_font(self) -> float:
        sizes = []
        step = max(1, self.pages // 40)
        for i in range(0, self.pages, step):
            for block in self.doc[i].get_text("dict").get("blocks", []):
                if block.get("type") != 0: continue
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        sz = span.get("size", 0.0)
                        if sz > 5 and span.get("text", "").strip():
                            sizes.append(round(sz, 1))
        if sizes:
            return Counter(sizes).most_common(1)[0][0]
        return 12.0

    def analyze(self) -> dict:
        candidates = []

        # ── TIER 1: Deep Native TOC (Parts + Chapters) ──
        toc = self.doc.get_toc()
        if toc:
            valid_items = []
            for item in toc:
                lvl, title, page_num = item[0], item[1].strip(), item[2]
                title_lower = title.lower()

                # Rule 1: Always include Level 1 (Usually Parts or Main Sections)
                if lvl == 1:
                    valid_items.append(item)
                # Rule 2: Include Level 2 and Level 3 ONLY IF they look like Chapters/Sections
                elif lvl in [2, 3]:
                    if (re.search(r"\b(chapter|chap|section|unit|lesson)\b", title_lower) or 
                        re.match(r"^(\d+|[ivxlcdm]+)[\.\-\:\s]", title_lower)):
                        valid_items.append(item)

            if 3 <= len(valid_items) <= 150:
                seen_pages = set()
                for item in valid_items:
                    # PyMuPDF pages are 0-indexed, TOC is 1-indexed
                    page_idx = item[2] - 1
                    
                    # If a Part and Chapter start on the exact same page, we only need to split there once
                    if page_idx not in seen_pages and page_idx >= 0:
                        candidates.append({
                            "page": page_idx, 
                            "display_page": page_idx + 1, 
                            "title": item[1].strip(), 
                            "score": 1.0
                        })
                        seen_pages.add(page_idx)
                
                return self._pack_result(candidates, "Deep TOC Extraction (Parts + Nested Chapters)", 99.9)

        # ── TIER 2: Visual & Textual Scanning (If TOC is missing) ──
        raw_candidates = []
        
        for pg_idx in range(self.pages):
            page = self.doc[pg_idx]
            blocks = page.get_text("dict").get("blocks", [])
            text_blocks = [b for b in blocks if b.get("type") == 0]

            best_score = 0.0
            best_text = ""

            for block in text_blocks[:8]:
                spans = []
                text_parts = []
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        spans.append(span)
                        text_parts.append(span.get("text", ""))
                
                full_text = re.sub(r"\s+", " ", " ".join(text_parts)).strip()
                if not full_text or len(full_text) > 100: continue
                if re.search(r"^\d+\.\d+", full_text): continue 

                avg_sz = statistics.mean(s.get("size", self.body_size) for s in spans)
                bbox = block.get("bbox", [0, 0, 0, 0])
                y0 = bbox[1]

                if y0 > page.rect.height * 0.40:
                    continue

                score = 0.0
                
                if any(pat.match(full_text) for pat in UNIVERSAL_PATTERNS):
                    # Give slightly higher score to explicitly named "Chapters" vs "Parts"
                    if "chapter" in full_text.lower():
                        score += 0.65
                    else:
                        score += 0.55
                
                if avg_sz >= self.body_size * 1.35:
                    score += 0.50
                elif avg_sz >= self.body_size * 1.15:
                    score += 0.20
                    
                if any(s.get("flags", 0) & (1 << 4) for s in spans):
                    score += 0.15

                if score > best_score:
                    best_score = score
                    best_text = full_text

            if best_score >= 0.55:
                raw_candidates.append({
                    "page": pg_idx, "display_page": pg_idx + 1,
                    "title": best_text, "score": min(1.0, best_score)
                })

        candidates = self._deduplicate(raw_candidates, self.min_gap)
        method = "Text & Typography Scanning" if candidates else "Fallback: Equal Split"
        conf = 85.0 if candidates else 0.0
        
        return self._pack_result(candidates, method, conf)

    def _pack_result(self, candidates, method, conf):
        return {
            "total_pages": self.pages,
            "candidates": candidates,
            "candidate_count": len(candidates),
            "confidence": conf,
            "method": method
        }

    @staticmethod
    def _deduplicate(candidates: list[dict], min_gap: int) -> list[dict]:
        if not candidates: return []
        result, i = [], 0
        while i < len(candidates):
            cluster = [candidates[i]]
            j = i + 1
            while j < len(candidates) and candidates[j]["page"] - candidates[i]["page"] < min_gap:
                cluster.append(candidates[j])
                j += 1
            result.append(max(cluster, key=lambda x: x["score"]))
            i = j
        return result


# ─────────────────────────────────────────────────────────────────────────────
# 0% DATA LOSS SPLITTING ENGINE (Bulletproof Slicing)
# ─────────────────────────────────────────────────────────────────────────────

def sanitize_filename(name: str) -> str:
    if not name:
        return "Section"
    # Remove invalid characters for Windows/Linux/Mac filenames
    clean_name = re.sub(r'[\\/*?:"<>|]', "", name)
    # Remove leading/trailing spaces and dots
    clean_name = clean_name.strip(". ")
    # Limit length
    clean_name = clean_name[:100]
    return clean_name if clean_name else "Section"

def get_safe_split_points(candidates: list[dict], max_chapters: int, auto: bool, total_pages: int) -> list[dict]:
    if not candidates or max_chapters <= 1:
        step = max(1, total_pages // max(max_chapters, 1))
        return [{"page": p, "title": f"Part_{i+1:02d}"} for i, p in enumerate(range(0, total_pages, step))]
        
    unique_candidates = []
    seen_pages = set()
    for c in candidates:
        if c["page"] not in seen_pages:
            unique_candidates.append(c)
            seen_pages.add(c["page"])
            
    unique_candidates.sort(key=lambda x: x["page"])
    
    if not auto and len(unique_candidates) > max_chapters:
        step = len(unique_candidates) / max_chapters
        unique_candidates = [unique_candidates[int(i * step)] for i in range(max_chapters)]
        
    return unique_candidates

def split_pdf_safely(doc: fitz.Document, split_points: list[dict]) -> list[tuple[str, bytes]]:
    total_pages = len(doc)
    points = sorted(split_points, key=lambda x: max(0, x["page"]))
    
    if not points or points[0]["page"] != 0:
        points.insert(0, {"page": 0, "title": points[0]["title"] if points else "Start"})
        
    results = []
    
    for i in range(len(points)):
        start = points[i]["page"]
        end = points[i+1]["page"] - 1 if i + 1 < len(points) else total_pages - 1
        
        if start > end: continue 
        
        new_doc = fitz.open()
        new_doc.insert_pdf(doc, from_page=start, to_page=end)
        
        safe_title = sanitize_filename(points[i].get("title", f"Section_{i + 1:02d}"))
        fname = f"{i + 1:02d} - {safe_title}.pdf"
        
        pdf_bytes = new_doc.tobytes(garbage=4, deflate=True)
        new_doc.close()
        
        results.append((fname, pdf_bytes))
        
    return results

def build_zip(chapters: list[tuple[str, bytes]]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for fname, data in chapters: zf.writestr(fname, data)
    return buf.getvalue()

def _fmt_size(n_bytes: int) -> str:
    return f"{n_bytes / 1_048_576:.1f} MB" if n_bytes >= 1_048_576 else f"{n_bytes / 1024:.1f} KB"


# ─────────────────────────────────────────────────────────────────────────────
# APP UI
# ─────────────────────────────────────────────────────────────────────────────

for _key in ("pdf_bytes", "pdf_name", "analysis", "split_result"):
    if _key not in st.session_state: st.session_state[_key] = None

st.markdown('<div class="pro-title">Universal PDF Splitter</div>', unsafe_allow_html=True)
st.markdown('<div class="pro-subtitle">0% Data Loss · Extracts Parts & Nested Chapters</div>', unsafe_allow_html=True)

st.markdown("""<div class="step-pill"><span class="step-num">1</span>📂 Upload your PDF</div>""", unsafe_allow_html=True)
uploaded = st.file_uploader("Drag & drop a PDF here", type=["pdf"], label_visibility="collapsed")

if uploaded:
    raw = uploaded.read()
    if raw != st.session_state.pdf_bytes:
        st.session_state.update({"pdf_bytes": raw, "pdf_name": uploaded.name, "analysis": None, "split_result": None})
    st.success(f"✅ **{st.session_state.pdf_name}** — {_fmt_size(len(raw))}")

if st.session_state.pdf_bytes:
    st.markdown("""<div class="step-pill"><span class="step-num">2</span>🔍 Analyze Book Pattern</div>""", unsafe_allow_html=True)

    if st.button("🔍 Find Parts & Chapters", use_container_width=True, type="primary"):
        with st.spinner("Scanning Deep Hierarchy..."):
            doc = fitz.open(stream=st.session_state.pdf_bytes, filetype="pdf")
            analysis_result = UniversalAnalyzer(doc).analyze()
            for i, c in enumerate(analysis_result.get("candidates", [])):
                c["_id"] = i
            st.session_state.analysis = analysis_result
            doc.close()
            st.session_state.split_result = None
            st.session_state.pop("chapter_editor", None)  # Reset data editor state on new analysis

if st.session_state.analysis:
    a = st.session_state.analysis
    conf = a["confidence"]
    col = "#10b981" if conf > 80 else ("#f59e0b" if conf > 50 else "#ef4444")
    
    st.markdown(f"""
        <div class="card">
          <div class="card-title">📊 Analysis Report</div>
          <div class="metrics-row">
            <div class="metric-box"><div class="metric-val" style="color:#60a5fa;">{a['total_pages']}</div><div class="metric-lbl">Total Pages</div></div>
            <div class="metric-box"><div class="metric-val" style="color:#a78bfa;">{a['candidate_count']}</div><div class="metric-lbl">Sections Found</div></div>
            <div class="metric-box"><div class="metric-val" style="color:{col};">{conf}%</div><div class="metric-lbl">Confidence</div></div>
          </div>
          <div style="color:#475569;font-size:0.78rem;margin-top:14px; text-align:center;">
            Pattern Engine Used: <b style="color:#94a3b8;">{a.get('method', 'Unknown')}</b>
          </div>
        </div>
    """, unsafe_allow_html=True)

    candidates = a.get("candidates", [])
    if candidates:
        st.markdown('<div class="card" style="margin-bottom:0px;"><div class="card-title" style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;"><span style="font-weight:700;">📑 Selected Sections</span><span style="font-size:0.75rem;color:#64748b;">(Click ❌ to remove)</span></div>', unsafe_allow_html=True)
        
        if "deleted_ids" not in st.session_state:
            st.session_state.deleted_ids = set()
            
        selected_candidates = []
        for i, c in enumerate(candidates):
            c_id = c.get("_id", i)
            if c_id in st.session_state.deleted_ids:
                continue
                
            selected_candidates.append(c)
            
            cols = st.columns([10, 1.5])
            with cols[0]:
                st.markdown(f'<div class="ch-item" style="margin: 0 0 8px 0;"><span class="ch-title">{c["title"][:60]}</span><span class="ch-badge">p.{c["display_page"]}</span></div>', unsafe_allow_html=True)
            with cols[1]:
                if st.button("❌", key=f"del_{c_id}", help="Remove section"):
                    st.session_state.deleted_ids.add(c_id)
                    st.rerun()
                    
        st.session_state.selected_candidates = selected_candidates
        st.markdown('</div>', unsafe_allow_html=True)
        
        if st.session_state.deleted_ids:
            if st.button("↺ Restore Removed Sections", key="restore_all", type="secondary"):
                st.session_state.deleted_ids = set()
                st.rerun()
    else:
        st.warning("⚠️ No standard chapters found. The PDF will be split evenly.")
        st.session_state.selected_candidates = []

if st.session_state.analysis:
    st.markdown("""<div class="step-pill"><span class="step-num">3</span>✂️ Configure Split</div>""", unsafe_allow_html=True)
    a = st.session_state.analysis
    
    sel_count = len(st.session_state.get("selected_candidates", []))
    
    col_l, col_r = st.columns([1, 1], gap="medium")
    with col_l:
        mode = st.radio("Split Mode:", [f"🤖 Use Selected ({sel_count} sections)", "✏️ Manual Splits (Even)"], index=0, disabled=(sel_count==0))
    with col_r:
        manual_n = st.number_input("Total Output Files (Manual):", min_value=2, max_value=200, value=max(2, sel_count), disabled=mode.startswith("🤖"))

    if st.button("✂️ Slice & Generate PDFs", use_container_width=True, type="primary"):
        with st.spinner("Slicing PDF without data loss..."):
            cands_to_use = st.session_state.selected_candidates if mode.startswith("🤖") else []
            pts = get_safe_split_points(cands_to_use, int(manual_n), mode.startswith("🤖"), a["total_pages"])
            doc = fitz.open(stream=st.session_state.pdf_bytes, filetype="pdf")
            chaps = split_pdf_safely(doc, pts)
            doc.close()
            st.session_state.split_result = {"chapters": chaps, "zip_bytes": build_zip(chaps), "count": len(chaps)}

if st.session_state.split_result:
    r = st.session_state.split_result
    st.markdown("""<div class="step-pill"><span class="step-num">4</span>⬇️ Download</div>""", unsafe_allow_html=True)
    st.markdown(f"""
        <div class="success-card">
          <div class="success-title">✅ Success! Generated {r['count']} PDF Files</div>
          <div class="success-sub">Total size: {_fmt_size(sum(len(d) for _, d in r["chapters"]))}</div>
        </div>
    """, unsafe_allow_html=True)
    st.download_button(f"⬇️ Download All {r['count']} Files (ZIP)", data=r["zip_bytes"], file_name="split_sections.zip", mime="application/zip", use_container_width=True)