#!/usr/bin/env python3
"""Demo 04: Streamlit UI for Issue Triage with application-controlled function calling."""

from __future__ import annotations

import os

import streamlit as st

from demo_common import load_environment, model_name, openai_client
from triage_workflow import TriageResult, triage_issue

DEFAULT_ISSUE = """Nút thanh toán trả HTTP 500 với mọi thẻ Visa từ 14:30.
Hãy triage issue và cho biết team nào cần xử lý."""

st.set_page_config(
    page_title="Issue Triage — Function Calling",
    page_icon="IT",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.markdown(
    """
    <style>
    [data-testid="stFormSubmitButton"] > button {
        background-color: #15803d;
        color: #ffffff;
    }
    [data-testid="stFormSubmitButton"] > button:hover {
        background-color: #166534;
        color: #ffffff;
    }
    </style>
    """,
    unsafe_allow_html=True,
)



def render_result(result: TriageResult) -> None:
    """Render the machine-visible tool trace before the model's final response."""
    triage = result.final_response

    # Metrics hiển thị tóm tắt
    col1, col2, col3 = st.columns(3)
    col1.metric("Mức độ nghiêm trọng", triage.severity or "N/A")
    col2.metric("Trạng thái", triage.status)
    col3.metric("Khẩn cấp (On-call)?", "CÓ (Khẩn cấp)" if triage.needs_urgent_response else "Không")

    if result.tool_traces:
        first_trace = result.tool_traces[0]
        col_comp, col_owner = st.columns(2)
        col_comp.metric("Component đã xác thực", first_trace.result.get("component", "N/A"))
        col_owner.metric("Team phụ trách", first_trace.result.get("owner", "N/A"))

    with st.expander("Trace function calling (4 bước)", expanded=True):
        for index, trace in enumerate(result.tool_traces, start=1):
            st.markdown(f"**{index}. Model yêu cầu tool** `{trace.name}`")
            st.json({"id": trace.call_id, "arguments": trace.arguments})
            st.markdown("**Application validate và thực thi**")
            st.json(trace.result)

    st.subheader("Kết quả phân loại (Structured IssueTriage)")
    st.json(triage.model_dump())
    st.info(f"**Lý do phân loại:** {triage.reason}")


def main() -> None:
    load_environment()

    with st.sidebar:
        st.header("Runtime")
        st.write("OpenAI-compatible API")
        st.code(os.getenv("OPENAI_BASE_URL") or "Chưa cấu hình URL", language=None)
        st.write("Model")
        st.code(os.getenv("OPENAI_MODEL") or "Chưa cấu hình model", language=None)
        st.divider()
        st.write(
            "Application chỉ thực thi get_component_owner cho payment, identity và search."
        )

    st.title("Issue Triage")
    st.write("Demo 04 — model đề xuất tool call; application kiểm tra rồi mới thực thi.")

    with st.form("issue-triage-form"):
        issue = st.text_area(
            "Mô tả issue",
            value=DEFAULT_ISSUE,
            height=220,
            help="Nêu symptom, phạm vi ảnh hưởng và thời điểm bắt đầu nếu có.",
        )
        submitted = st.form_submit_button("Phân loại issue", type="primary", use_container_width=True)

    if not submitted:
        return
    if not issue.strip():
        st.error("Nhập mô tả issue trước khi chạy triage.")
        return

    try:
        with st.spinner("Đang gọi model và xử lý tool request…"):
            result = triage_issue(openai_client(), model_name(), issue.strip())
    except Exception as error:
        st.error(f"Triage không hoàn tất: {error}")
        st.info("Kiểm tra OPENAI_BASE_URL, OPENAI_MODEL và quyền truy cập model trong .env.")
        return

    st.success("Application đã hoàn tất function-calling flow.")
    render_result(result)


if __name__ == "__main__":
    main()
