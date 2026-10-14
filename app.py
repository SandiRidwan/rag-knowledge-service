"""
Streamlit UI: ask your own documents questions, see citations, or a refusal.

    streamlit run app.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from rag import config  # noqa: E402
from rag.service import KnowledgeBase  # noqa: E402

st.set_page_config(page_title="RAG Knowledge Service", page_icon="🔎", layout="wide")
st.title("🔎 Ask your documents")
st.caption(
    "Local RAG that runs with **no API key**: it retrieves from your files and "
    "**cites** each answer, or **refuses** when the corpus does not cover the "
    "question. Add an LLM key for synthesised answers.")


@st.cache_resource
def get_kb():
    return KnowledgeBase()


try:
    kb = get_kb()
except SystemExit as e:
    st.error(str(e))
    st.code("python -m rag.ingest.cli")
    st.stop()

with st.sidebar:
    st.markdown("### Corpus")
    srcs = sorted({c.source for c in kb.chunks})
    st.write(f"{len(srcs)} files · {len(kb.chunks)} chunks")
    st.write(f"LLM: {config.active_llm() or 'none (extractive mode)'}")
    st.write(f"Refuse below coverage: {config.REFUSE_BELOW}")
    with st.expander("Files"):
        for s in srcs:
            st.write(f"- {s}")

question = st.text_input("Your question", placeholder="e.g. How do I mock a request?")
col1, col2 = st.columns([1, 3])
ask = col1.button("Ask", type="primary")
extractive = col2.toggle("Extractive only (no LLM)", value=(config.active_llm() is None))

if ask and question.strip():
    with st.spinner("Retrieving..."):
        ans = kb.ask(question, use_llm=not extractive)
    if ans.refused:
        st.warning(ans.answer)
    else:
        st.markdown("#### Answer")
        st.markdown(ans.answer)
        st.caption(f"mode: {ans.mode}")
    if ans.citations:
        st.markdown("#### Citations")
        for c in ans.citations:
            st.markdown(
                f"**[{c.score}] {c.source} › {c.title}**  \n"
                f"<span style='color:#888'>{c.excerpt}</span>",
                unsafe_allow_html=True)
