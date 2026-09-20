"""Application-controlled Issue Triage workflow shared by CLI and Streamlit demos."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Literal

from openai import OpenAI
from pydantic import BaseModel, ConfigDict, Field


# =====================================================================
# 1. CONTRACT: Schema Pydantic cho IssueTriage (Slide 36 & 68)
# =====================================================================
class IssueTriage(BaseModel):
    """The machine-readable contract between application and model."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["classified", "insufficient_data", "out_of_scope"] = Field(
        description="Trạng thái phân loại: classified, insufficient_data, out_of_scope"
    )
    severity: Literal["P0", "P1", "P2", "P3"] | None = Field(
        default=None,
        description="Mức độ nghiêm trọng từ P0 đến P3. Null nếu không xác định được."
    )
    component: str | None = Field(
        default=None,
        description="Phân hệ bị lỗi (payment, identity, search...)."
    )
    needs_urgent_response: bool = Field(
        default=False,
        description="Có cần đội ngũ trực ban on-call xử lý khẩn cấp không."
    )
    reason: str = Field(
        description="Lý do ngắn gọn dựa trên dữ liệu issue."
    )


# =====================================================================
# 2. PROMPT TEMPLATE: Tách biệt Instruction và Input (Slide 22)
# =====================================================================
SYSTEM_PROMPT = (
    "Bạn là kỹ sư phụ trách phân loại sự cố phần mềm (Issue Triage). "
    "Khi xác định được component bị lỗi, hãy gọi tool get_component_owner để tra cứu team chịu trách nhiệm. "
    "Component hợp lệ chỉ gồm: payment, identity hoặc search. "
    "Tuyệt đối không tự thực thi tool."
)

USER_PROMPT_TEMPLATE = """<task>
Hãy phân tích và phân loại sự cố phần mềm sau đây:
1. Nếu phát hiện component liên quan (payment, identity, search), hãy gọi tool get_component_owner để tra cứu team phụ trách.
2. Đánh giá mức độ nghiêm trọng: P0 (sập toàn bộ/ảnh hưởng thanh toán), P1 (nghiêm trọng), P2 (vừa), P3 (nhẹ/giao diện).
3. Nếu dữ liệu mơ hồ hoặc không đủ, chọn status=insufficient_data. Nếu không phải sự cố phần mềm, chọn status=out_of_scope.
</task>

<input>
{issue_text}
</input>"""


# =====================================================================
# 3. TOOLS: Định nghĩa công cụ (Slide 45)
# =====================================================================
COMPONENT_OWNERS = {
    "payment": "checkout-platform",
    "identity": "identity-platform",
    "search": "search-platform",
}

FUNCTION_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_component_owner",
            "description": (
                "Trả team chịu trách nhiệm cho một software component. "
                "Chỉ dùng component trong danh sách schema."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "component": {
                        "type": "string",
                        "enum": list(COMPONENT_OWNERS),
                    }
                },
                "required": ["component"],
                "additionalProperties": False,
            },
            "strict": True,
        },
    }
]


# =====================================================================
# 4. TRACE & RESULT DATACLASSES
# =====================================================================
@dataclass(frozen=True)
class ToolTrace:
    """One validated tool request and the application result returned to the model."""

    call_id: str
    name: str
    arguments: dict[str, Any]
    result: dict[str, str]


@dataclass(frozen=True)
class TriageResult:
    """Consumer-facing result of a complete Issue Triage run with Pydantic output."""

    tool_traces: tuple[ToolTrace, ...]
    final_response: IssueTriage


# =====================================================================
# 5. APPLICATION EXECUTION & VALIDATION (Slide 41 & 51)
# =====================================================================
def get_component_owner(component: str) -> str:
    """Return the owner only for application-approved components."""
    return COMPONENT_OWNERS[component]


def execute_tool_call(name: str, raw_arguments: str) -> dict[str, str]:
    """Validate a requested tool and its semantics before application execution."""
    if name != "get_component_owner":
        raise ValueError(f"Tool is not allowed: {name}")

    arguments = json.loads(raw_arguments)
    if not isinstance(arguments, dict):
        raise ValueError("Tool arguments must be a JSON object.")
    if set(arguments) != {"component"} or not isinstance(arguments["component"], str):
        raise ValueError("Tool arguments must contain exactly one string: component.")

    component = arguments["component"]
    if component not in COMPONENT_OWNERS:
        raise ValueError(f"Unknown component: {component}")

    return {"component": component, "owner": get_component_owner(component)}


def validate_application_rules(triage: IssueTriage, tool_traces: tuple[ToolTrace, ...]) -> None:
    """Validate domain and business logic rules at the application layer."""
    # Luật 1: Sự cố P0 bắt buộc phải yêu cầu phản hồi khẩn cấp
    if triage.severity == "P0" and not triage.needs_urgent_response:
        raise ValueError(
            "Application validation failed: Sự cố P0 bắt buộc phải có needs_urgent_response=True!"
        )

    # Luật 2: Đã phân loại thành công thì phải có severity và component
    if triage.status == "classified":
        if not triage.severity:
            raise ValueError(
                "Application validation failed: Status 'classified' yêu cầu phải có severity!"
            )
        if not triage.component:
            raise ValueError(
                "Application validation failed: Status 'classified' yêu cầu phải có component!"
            )

    # Luật 3: Tính nhất quán giữa tool đã tra cứu và kết quả component của model
    for trace in tool_traces:
        queried_comp = trace.result.get("component")
        if queried_comp and triage.component and queried_comp.lower() != triage.component.lower():
            raise ValueError(
                f"Application validation failed: Tool đã tra cứu '{queried_comp}' nhưng model trả về '{triage.component}'!"
            )


# =====================================================================
# 6. MAIN WORKFLOW
# =====================================================================
def triage_issue(client: OpenAI, model: str, issue: str) -> TriageResult:
    """Triage one issue, execute validated owner lookups, and return structured IssueTriage."""
    formatted_user_prompt = USER_PROMPT_TEMPLATE.format(issue_text=issue)

    messages: list[Any] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": formatted_user_prompt},
    ]

    first_response = client.chat.completions.create(
        model=model,
        messages=messages,
        tools=FUNCTION_TOOLS,
        tool_choice="auto",
    )
    assistant_message = first_response.choices[0].message
    tool_calls = assistant_message.tool_calls or []

    messages.append(assistant_message)
    traces: list[ToolTrace] = []

    for tool_call in tool_calls:
        arguments = json.loads(tool_call.function.arguments)
        result = execute_tool_call(tool_call.function.name, tool_call.function.arguments)
        traces.append(
            ToolTrace(
                call_id=tool_call.id,
                name=tool_call.function.name,
                arguments=arguments,
                result=result,
            )
        )
        messages.append(
            {
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(result, ensure_ascii=False),
            }
        )

    # Lần gọi 2: Ép kiểu cấu trúc trả về IssueTriage qua Pydantic
    constrained_response = client.beta.chat.completions.parse(
        model=model,
        messages=messages,
        response_format=IssueTriage,
    )
    parsed_triage = constrained_response.choices[0].message.parsed
    if parsed_triage is None:
        raise RuntimeError("Model không trả về được cấu trúc IssueTriage hợp lệ.")

    # Application Validation ở tầng ứng dụng
    validate_application_rules(parsed_triage, tuple(traces))

    return TriageResult(
        tool_traces=tuple(traces),
        final_response=parsed_triage,
    )
