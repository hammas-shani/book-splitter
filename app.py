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
.stButton > button { width: 100% !important; background: linear-gradient(135deg, #6366f1, #8b5cf6) !important; color: white !important; border: none !important; border-radius: 10px !important; font-weight: 700 !important; }
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

def get_safe_split_points(candidates: list[dict], max_chapters: int, auto: bool, total_pages: int) -> list[int]:
    if not candidates or max_chapters <= 1:
        step = max(1, total_pages // max(max_chapters, 1))
        return list(range(0, total_pages, step))
        
    pages = sorted(list(set(c["page"] for c in candidates)))
    
    if not auto and len(pages) > max_chapters:
        step = len(pages) / max_chapters
        pages = [pages[int(i * step)] for i in range(max_chapters)]
        
    return pages

def split_pdf_safely(doc: fitz.Document, split_points: list[int]) -> list[tuple[str, bytes]]:
    total_pages = len(doc)
    points = sorted(list(set(max(0, p) for p in split_points)))
    
    if not points or points[0] != 0:
        points.insert(0, 0)
        
    points.append(total_pages)
    results = []
    
    for i in range(len(points) - 1):
        start = points[i]
        end = points[i+1] - 1  
        
        if start > end: continue 
        
        new_doc = fitz.open()
        new_doc.insert_pdf(doc, from_page=start, to_page=end)
        
        fname = f"Section_{i + 1:02d}.pdf"
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

st.markdown('<div class="pro-title">📚 Universal PDF Splitter</div>', unsafe_allow_html=True)
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

    if st.button("🔍 Find Parts & Chapters", use_container_width=True):
        with st.spinner("Scanning Deep Hierarchy..."):
            doc = fitz.open(stream=st.session_state.pdf_bytes, filetype="pdf")
            st.session_state.analysis = UniversalAnalyzer(doc).analyze()
            doc.close()
            st.session_state.split_result = None

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
        items_html = "".join([f'<div class="ch-item"><span class="ch-title">{c["title"][:60]}</span><span class="ch-badge">p.{c["display_page"]}</span></div>' for c in candidates[:15]])
        more = f'<div style="color:#475569;font-size:0.78rem;margin-top:8px;">+ {len(candidates)-15} more sections</div>' if len(candidates) > 15 else ""
        st.markdown(f'<div class="card"><div class="card-title">📑 Detected Boundaries (Preview)</div>{items_html}{more}</div>', unsafe_allow_html=True)
    else:
        st.warning("⚠️ No standard chapters found. The PDF will be split evenly.")

if st.session_state.analysis:
    st.markdown("""<div class="step-pill"><span class="step-num">3</span>✂️ Configure Split</div>""", unsafe_allow_html=True)
    a = st.session_state.analysis
    
    col_l, col_r = st.columns([1, 1], gap="medium")
    with col_l:
        mode = st.radio("Split Mode:", [f"🤖 Auto ({a['candidate_count']} files)", "✏️ Manual Splits"], index=0, disabled=(a['candidate_count']==0))
    with col_r:
        manual_n = st.number_input("Total Output Files:", min_value=2, max_value=200, value=max(2, a['candidate_count']), disabled=mode.startswith("🤖"))

    if st.button("✂️ Slice & Generate PDFs", use_container_width=True):
        with st.spinner("Slicing PDF without data loss..."):
            pts = get_safe_split_points(a.get("candidates", []), int(manual_n), mode.startswith("🤖"), a["total_pages"])
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