#!/usr/bin/env python3
"""Demo C: application-controlled tool execution after a model tool request."""

from __future__ import annotations

import argparse
import json
import sys

# Đảm bảo in tiếng Việt không bị lỗi charmap trên Windows terminal
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

from demo_common import model_name, openai_client
from triage_workflow import triage_issue

DEFAULT_ISSUE = (
    "Nút thanh toán trả HTTP 500 với mọi thẻ Visa từ 14:30. "
    "Hãy triage issue và cho biết team nào cần xử lý."
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--issue", default=DEFAULT_ISSUE, help="Nội dung issue cần triage.")
    args = parser.parse_args()

    result = triage_issue(openai_client(), model_name(), args.issue)
    for trace in result.tool_traces:
        print("=== 1. Model đề xuất tool call ===")
        print(
            json.dumps(
                {
                    "id": trace.call_id,
                    "name": trace.name,
                    "arguments": trace.arguments,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        print("\n=== 2. Application thực thi ===")
        print(
            f"get_component_owner({trace.result['component']!r}) "
            f"-> {trace.result['owner']!r}"
        )
        print("\n=== 3. Tool result quay lại model ===")
        print(json.dumps(trace.result, ensure_ascii=False, indent=2))

    print("\n=== 4. Final response (Structured IssueTriage) ===")
    print(result.final_response.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
