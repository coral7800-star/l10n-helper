"""중국어 게임 텍스트의 한국어 번역 및 용어 검수 작업 공간."""
import hashlib
import io
import re
from collections import Counter

import pandas as pd
import streamlit as st


PLACEHOLDER = re.compile(r"\{[^{}]+\}|%(?:\d+\$)?[sdif]|</?[^>]+>")


def review(source: str, target: str, glossary: pd.DataFrame) -> list[str]:
    issues = []
    if not target.strip():
        issues.append("번역 누락")
    for _, term in glossary.iterrows():
        zh, ko = str(term["zh"]).strip(), str(term["ko"]).strip()
        if zh and ko and zh in source and ko not in target:
            issues.append(f"용어 확인: {zh} → {ko}")
    if Counter(PLACEHOLDER.findall(source)) != Counter(PLACEHOLDER.findall(target)):
        issues.append("플레이스홀더/태그 불일치")
    if re.search(r"[\u4e00-\u9fff]", target):
        issues.append("번역에 한자 포함: 확인 필요")
    return issues


def load_csv(data, columns):
    frame = pd.read_csv(data, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    missing = set(columns) - set(frame.columns)
    if missing:
        raise ValueError(f"필수 열 누락: {', '.join(sorted(missing))}")
    return frame


def csv_bytes(frame):
    # Spreadsheet formula injection protection for exported user text.
    safe = frame.map(lambda v: "'" + v if isinstance(v, str) and v.lstrip().startswith(("=", "+", "-", "@")) else v)
    return safe.to_csv(index=False).encode("utf-8-sig")


def main():
    st.set_page_config(page_title="L10n Helper", page_icon="🎮", layout="wide")
    st.title("🎮 L10n Helper")
    st.caption("중국어 → 한국어 게임 번역 · 용어 검수")
    st.info("직접 번역을 편집하고 용어와 형식을 검사합니다. 자동 번역 API 연결은 포함되어 있지 않습니다.")
    with st.sidebar:
        st.header("CSV 가져오기")
        text_file = st.file_uploader("번역 파일 (id, zh, ko)", type="csv")
        term_file = st.file_uploader("용어집 (zh, ko)", type="csv")
        st.caption("UTF-8 CSV를 사용하세요. 업로드 데이터는 외부 번역 서비스로 전송하지 않습니다.")
    texts = pd.DataFrame([
        {"id": "quest_001", "zh": "勇士，欢迎来到王国！", "ko": "용사여, 왕국에 오신 것을 환영합니다!"},
        {"id": "item_001", "zh": "获得{count}个钻石", "ko": "{count}개의 다이아몬드 획득"},
    ])
    terms = pd.DataFrame([{"zh": "勇士", "ko": "용사"}, {"zh": "钻石", "ko": "다이아몬드"}])
    try:
        if text_file is not None:
            texts = load_csv(io.BytesIO(text_file.getvalue()), ["id", "zh", "ko"])
        if term_file is not None:
            terms = load_csv(io.BytesIO(term_file.getvalue()), ["zh", "ko"])
    except (ValueError, UnicodeError, pd.errors.ParserError) as exc:
        st.error(f"CSV를 읽을 수 없습니다: {exc}")
        st.stop()
    # Changing either uploaded file resets the associated editor state.
    text_key = hashlib.sha256(texts.to_csv(index=False).encode()).hexdigest()
    term_key = hashlib.sha256(terms.to_csv(index=False).encode()).hexdigest()
    st.subheader("용어집")
    glossary = st.data_editor(terms, num_rows="dynamic", hide_index=True, key=f"terms_{term_key}").fillna("")
    st.subheader("번역 편집")
    edited = st.data_editor(texts, disabled=[c for c in texts.columns if c != "ko"], hide_index=True, key=f"texts_{text_key}").fillna("")
    result = edited.copy()
    result["검수 결과"] = [" / ".join(review(str(row["zh"]), str(row["ko"]), glossary)) or "통과" for _, row in edited.iterrows()]
    st.subheader("검수 결과")
    st.metric("확인 필요", int((result["검수 결과"] != "통과").sum()))
    only_issues = st.checkbox("확인 필요한 항목만 표시")
    st.dataframe(result[result["검수 결과"] != "통과"] if only_issues else result, hide_index=True)
    st.caption("용어 검사는 부분 문자열 일치 방식이며, 한자와 태그 경고는 사람이 최종 확인해야 합니다.")
    st.download_button("번역·검수 CSV 다운로드", csv_bytes(result), "l10n_review.csv", "text/csv")
    st.download_button("용어집 CSV 다운로드", csv_bytes(glossary), "glossary.csv", "text/csv")


if __name__ == "__main__":
    main()
