# =========================================================
# STREAMLIT PDF CHAPTER SPLITTER UI
# =========================================================
# INSTALL:
#
# pip install streamlit pymupdf regex
#
# RUN:
#
# streamlit run app.py
#
# =========================================================

import streamlit as st
import fitz
import re
import os
import tempfile
import zipfile
from pathlib import Path

# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="PDF Chapter Splitter",
    page_icon="📚",
    layout="centered"
)

# =========================================================
# STYLING
# =========================================================

st.markdown("""
<style>

.main {
    background-color: #0f1117;
}

.title {
    text-align: center;
    font-size: 42px;
    font-weight: bold;
    color: white;
    margin-bottom: 10px;
}

.subtitle {
    text-align: center;
    font-size: 18px;
    color: #b0b0b0;
    margin-bottom: 40px;
}

.upload-box {
    border: 2px dashed #4CAF50;
    border-radius: 15px;
    padding: 30px;
    background-color: #161a23;
}

.success-box {
    padding: 15px;
    border-radius: 10px;
    background: #1b4332;
    color: white;
    font-weight: bold;
}

</style>
""", unsafe_allow_html=True)

# =========================================================
# HEADER
# =========================================================

st.markdown(
    '<div class="title">📚 PDF Chapter Splitter</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitle">Upload your PDF and split it into smart chapter PDFs automatically</div>',
    unsafe_allow_html=True
)

# =========================================================
# CONFIG
# =========================================================

MAX_CHAPTERS = 10

PATTERNS = [

    r'^\s*chapter\s+\d+',
    r'^\s*CHAPTER\s+\d+',
    r'^\s*chapter\s+[a-zA-Z]+',
    r'^\s*part\s+\d+',
    r'^\s*PART\s+\d+',
    r'^\s*[IVXLCDM]+\s*$',
    r'^\s*\d+\s*$',

]

compiled_patterns = [
    re.compile(p, re.IGNORECASE)
    for p in PATTERNS
]

# =========================================================
# HELPERS
# =========================================================

def is_chapter_heading(text):

    text = text.strip()

    if len(text) > 80:
        return False

    for pattern in compiled_patterns:
        if pattern.match(text):
            return True

    return False

# =========================================================
# FIND CHAPTERS
# =========================================================

def find_chapter_pages(doc):

    chapter_pages = []

    for page_num in range(len(doc)):

        page = doc[page_num]

        blocks = page.get_text("blocks")

        found = False

        for block in blocks:

            text = block[4].strip()

            lines = text.split("\n")

            for line in lines[:8]:

                if is_chapter_heading(line):

                    chapter_pages.append(page_num)

                    found = True
                    break

            if found:
                break

    chapter_pages = sorted(list(set(chapter_pages)))

    return chapter_pages

# =========================================================
# LIMIT CHAPTERS
# =========================================================

def reduce_chapters(chapter_pages):

    if len(chapter_pages) <= MAX_CHAPTERS:
        return chapter_pages

    selected = []

    step = len(chapter_pages) / MAX_CHAPTERS

    for i in range(MAX_CHAPTERS):
        idx = int(i * step)
        selected.append(chapter_pages[idx])

    return sorted(list(set(selected)))

# =========================================================
# SPLIT PDF
# =========================================================

def split_pdf(input_pdf_path):

    doc = fitz.open(input_pdf_path)

    chapter_pages = find_chapter_pages(doc)

    if not chapter_pages:
        chapter_pages = [0]

    chapter_pages = reduce_chapters(chapter_pages)

    temp_dir = tempfile.mkdtemp()

    output_files = []

    total_pages = len(doc)

    for i in range(len(chapter_pages)):

        start_page = chapter_pages[i]

        if i < len(chapter_pages) - 1:
            end_page = chapter_pages[i + 1] - 1
        else:
            end_page = total_pages - 1

        new_pdf = fitz.open()

        new_pdf.insert_pdf(
            doc,
            from_page=start_page,
            to_page=end_page
        )

        output_path = os.path.join(
            temp_dir,
            f"chapter_{i+1}.pdf"
        )

        new_pdf.save(output_path)

        new_pdf.close()

        output_files.append(output_path)

    return output_files

# =========================================================
# CREATE ZIP
# =========================================================

def create_zip(files):

    zip_path = tempfile.mktemp(suffix=".zip")

    with zipfile.ZipFile(zip_path, "w") as zipf:

        for file in files:

            zipf.write(
                file,
                arcname=Path(file).name
            )

    return zip_path

# =========================================================
# UI
# =========================================================

uploaded_file = st.file_uploader(
    "Upload PDF",
    type=["pdf"]
)

# =========================================================
# PROCESS
# =========================================================

if uploaded_file:

    st.success("PDF Uploaded Successfully")

    with tempfile.NamedTemporaryFile(
        delete=False,
        suffix=".pdf"
    ) as tmp_file:

        tmp_file.write(uploaded_file.read())

        temp_pdf_path = tmp_file.name

    if st.button("🚀 Split PDF"):

        with st.spinner("Processing PDF..."):

            try:

                split_files = split_pdf(temp_pdf_path)

                zip_path = create_zip(split_files)

                st.markdown(
                    """
                    <div class="success-box">
                    ✅ PDF Split Successfully
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                with open(zip_path, "rb") as f:

                    st.download_button(
                        label="⬇ Download ZIP",
                        data=f,
                        file_name="split_chapters.zip",
                        mime="application/zip"
                    )

            except Exception as e:

                st.error(f"Error: {str(e)}")