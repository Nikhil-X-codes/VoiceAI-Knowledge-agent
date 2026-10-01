from __future__ import annotations

import json

from kb.retrieval import prepare_retrieval, search_kb


if __name__ == "__main__":
    prepare_retrieval()
    search_kb("late fee due date", category="policy")
    print("kb_index_ready_and_warm")
