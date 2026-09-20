#!/usr/bin/env python3
"""Demo 0: send one issue to an LLM and print its free-form triage."""

from __future__ import annotations

import argparse

from demo_common import model_name, openai_client

DEFAULT_ISSUE = "Nút thanh toán trả HTTP 500 với mọi thẻ Visa từ 14:30."


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--issue", default=DEFAULT_ISSUE, help="Nội dung issue cần phân loại.")
    args = parser.parse_args()

    response = openai_client().chat.completions.create(
        model=model_name(),
        messages=[
            {"role": "system", "content": "Bạn hỗ trợ phân loại issue phần mềm."},
            {"role": "user", "content": args.issue},
        ],
    )

    print(response.choices[0].message.content)


if __name__ == "__main__":
    main()
