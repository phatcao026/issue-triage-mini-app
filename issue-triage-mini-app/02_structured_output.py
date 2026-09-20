#!/usr/bin/env python3
"""Demo B: contrast prompt-only JSON with provider-constrained structured output."""

from __future__ import annotations

import argparse
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from demo_common import model_name, openai_client

DEFAULT_ISSUE = "Nút thanh toán trả HTTP 500 với mọi thẻ Visa từ 14:30."


class IssueTriage(BaseModel):
    """The machine-readable contract between this demo and the model."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["classified", "insufficient_data", "out_of_scope"]
    severity: Literal["P0", "P1", "P2", "P3"] | None = None
    component: str | None = None
    needs_urgent_response: bool = False
    reason: str = Field(description="Lý do ngắn gọn dựa trên dữ liệu issue")


SYSTEM_PROMPT = """Bạn là kỹ sư phụ trách phân loại sự cố phần mềm.
Phân loại severity theo P0/P1/P2/P3 dựa trên dữ liệu issue. Nếu dữ liệu không
đủ để phân loại, dùng status=insufficient_data thay vì đoán. Chỉ dùng
status=out_of_scope khi nội dung không phải issue phần mềm."""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--issue", default=DEFAULT_ISSUE, help="Nội dung issue cần phân loại.")
    args = parser.parse_args()

    client = openai_client()
    model = model_name()
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"{args.issue}\n\nChỉ trả về một JSON object đúng schema.",
        },
    ]

    prompt_only = client.chat.completions.create(model=model, messages=messages)
    print("=== Prompt-only response ===")
    print(prompt_only.choices[0].message.content)

    constrained = client.beta.chat.completions.parse(
        model=model,
        messages=messages,
        response_format=IssueTriage,
    )
    parsed = constrained.choices[0].message.parsed
    if parsed is None:
        raise RuntimeError("Model did not return a structured IssueTriage response.")

    print("\n=== Constrained structured response ===")
    print(parsed.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
