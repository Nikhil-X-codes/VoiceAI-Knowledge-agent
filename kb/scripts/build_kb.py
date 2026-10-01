from __future__ import annotations

import csv
import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from dotenv import load_dotenv

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

try:
    import trafilatura
except Exception:  # pragma: no cover
    trafilatura = None

try:
    from bs4 import BeautifulSoup
except Exception:  # pragma: no cover
    BeautifulSoup = None

try:
    import pdfplumber
except Exception:  # pragma: no cover
    pdfplumber = None

try:
    import fitz
except Exception:  # pragma: no cover
    fitz = None

try:
    from presidio_analyzer import AnalyzerEngine, NlpEngineProvider
    from presidio_anonymizer import AnonymizerEngine
except Exception:  # pragma: no cover
    AnalyzerEngine = None
    NlpEngineProvider = None
    AnonymizerEngine = None

ROOT = Path(__file__).resolve().parents[2]
KB_DIR = ROOT / "kb"
DATA_DIR = KB_DIR / "data"
RAW_DIR = KB_DIR / "raw"
SOURCES_CSV = DATA_DIR / "sources.csv"
ERRORS_CSV = DATA_DIR / "extraction_errors.csv"
DUPLICATES_CSV = DATA_DIR / "duplicates_log.csv"
RECORDS_JSONL = DATA_DIR / "records.jsonl"

load_dotenv(ROOT / ".env")

CATEGORY_TAXONOMY = {
    "product": "product",
    "policy": "policy",
    "qualification": "qualification",
    "faq": "faq",
    "objection": "objection",
    "script_rule": "script_rule",
}

SEED_SOURCES = [
    {
        "source_id": "src_001",
        "type": "web",
        "ref": "https://example.com/loan_terms",
        "method": "trafilatura",
        "status": "ok",
        "label": "Loan terms and late fees",
    },
    {
        "source_id": "src_002",
        "type": "pdf",
        "ref": "loan_fee_schedule.pdf",
        "method": "pdfplumber",
        "status": "ok",
        "label": "Fee schedule",
    },
    {
        "source_id": "src_003",
        "type": "web",
        "ref": "https://example.com/faq",
        "method": "beautifulsoup",
        "status": "ok",
        "label": "Frequently asked questions",
    },
]

SAMPLE_RECORDS = [
    {
        "record_id": "kb_policy_001",
        "title": "Late Payment Fee Rules",
        "content": "A late fee applies when an installment is unpaid after the due date. The overdue amount is calculated from the unpaid principal plus any applicable penalty fee. Customers may request an extension or a new payment date if they provide a valid reason.",
        "category": "policy",
        "subcategory": "late_fees",
        "source": {"type": "pdf", "ref": "loan_fee_schedule.pdf", "page": 3, "url": None},
        "language": "en",
        "market": "global",
        "version": "1.0",
        "status": "active",
        "effective_date": "2026-01-01",
        "pii": False,
        "tags": ["fees", "overdue"],
    },
    {
        "record_id": "kb_product_001",
        "title": "Installment Loan Product Summary",
        "content": "The installment loan is a consumer finance product with scheduled monthly repayments. Customers can pay by bank transfer, e-wallet, or in-person payment channels depending on the market and the selected repayment method.",
        "category": "product",
        "subcategory": "loan_summary",
        "source": {"type": "web", "ref": "https://example.com/loan_terms", "page": None, "url": "https://example.com/loan_terms"},
        "language": "en",
        "market": "global",
        "version": "1.0",
        "status": "active",
        "effective_date": "2026-01-01",
        "pii": False,
        "tags": ["product", "installment"],
    },
    {
        "record_id": "kb_qualification_001",
        "title": "Eligibility and reminder window",
        "content": "Reminders are sent three days before the due date as a standard courtesy. Customers may be asked to confirm the payment date, amount, and their preferred resolution when they have difficulty paying on time.",
        "category": "qualification",
        "subcategory": "reminder_window",
        "source": {"type": "web", "ref": "https://example.com/faq", "page": None, "url": "https://example.com/faq"},
        "language": "en",
        "market": "global",
        "version": "1.0",
        "status": "active",
        "effective_date": "2026-01-01",
        "pii": False,
        "tags": ["reminder", "eligibility"],
    },
    {
        "record_id": "kb_objection_001",
        "title": "Handling fee objections",
        "content": "If the customer says fees are too high, explain the fee schedule from the official policy, offer a repayment plan, and provide an option for a callback or human escalation if the concern continues.",
        "category": "objection",
        "subcategory": "fees_too_high",
        "source": {"type": "web", "ref": "https://example.com/faq", "page": None, "url": "https://example.com/faq"},
        "language": "en",
        "market": "global",
        "version": "1.0",
        "status": "active",
        "effective_date": "2026-01-01",
        "pii": False,
        "tags": ["objection", "fees"],
    },
]


def normalize_whitespace(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n +", "\n", text)
    text = re.sub(r" +\n", "\n", text)
    return text.strip()


def normalize_dates(text: str) -> str:
    patterns = [
        (r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b", r"\3-\2-\1"),
        (r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b", r"\1-\2-\3"),
    ]
    for pattern, repl in patterns:
        text = re.sub(pattern, repl, text)
    return text


def canonicalize_terms(text: str) -> str:
    term_map = {
        "EMI": "installment",
        "monthly payment": "installment",
        "monthly repayment": "installment",
    }
    for old, new in term_map.items():
        pattern = rf"\b{re.escape(old)}\b"
        text = re.sub(pattern, new, text, flags=re.IGNORECASE)
    return text


def remove_repeat_boilerplate(lines: Iterable[str]) -> list[str]:
    cleaned = [line.strip() for line in lines if line.strip()]
    if not cleaned:
        return []

    line_counts: dict[str, int] = {}
    for line in cleaned:
        line_counts[line] = line_counts.get(line, 0) + 1

    repeated = {line for line, count in line_counts.items() if count > 1 and len(line) > 20}
    return [line for line in cleaned if line not in repeated]


def mask_pii_text(text: str) -> tuple[str, bool]:
    if AnalyzerEngine is None or AnonymizerEngine is None:
        regex_replacements = [
            (r"\b\+?[0-9][0-9\s().-]{7,}\d\b", "[PHONE]"),
            (r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", "[EMAIL]"),
            (r"\b(?:[A-Z][a-z]+\s+[A-Z][a-z]+)\b", "[NAME]"),
        ]
        masked = text
        for pattern, replacement in regex_replacements:
            masked = re.sub(pattern, replacement, masked)
        return masked, bool(re.search(r"\[(PHONE|EMAIL|NAME)\]", masked))

    nlp_configuration = {
        "nlp_engine_name": "spacy",
        "models": [{"lang_code": "en", "model_name": "en_core_web_sm"}],
    }
    provider = NlpEngineProvider(nlp_configuration=nlp_configuration)
    analyzer = AnalyzerEngine(nlp_engine=provider.create_engine(), supported_languages=["en"])
    anonymizer = AnonymizerEngine()
    findings = analyzer.analyze(text=text, entities=["PERSON", "EMAIL_ADDRESS", "PHONE_NUMBER", "LOCATION"], language="en")
    if not findings:
        return text, False
    anonymized = anonymizer.anonymize(text=text, analyzer_results=findings)
    return anonymized.text, True


def sanitize_record(record: dict[str, Any]) -> dict[str, Any]:
    content = normalize_whitespace(record["content"])
    content = normalize_dates(content)
    content = canonicalize_terms(content)
    content = "\n".join(remove_repeat_boilerplate(content.splitlines()))
    masked_content, pii_found = mask_pii_text(content)

    sanitized = dict(record)
    sanitized["content"] = masked_content
    sanitized["pii"] = bool(record.get("pii") or pii_found)
    sanitized["category"] = CATEGORY_TAXONOMY.get(record["category"], record["category"])
    sanitized["source"] = record.get("source", {})
    return sanitized


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def deduplicate_records(records: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Keep canonical records and log exact or cosine near-duplicates above 0.85."""
    kept: list[dict[str, Any]] = []
    duplicate_rows: list[dict[str, Any]] = []
    seen_hashes: dict[str, str] = {}
    for record in records:
        normalized = normalize_whitespace(record.get("content", "")).lower()
        digest = str(hash(normalized))
        if digest in seen_hashes:
            duplicate_rows.append({
                "duplicate_record_id": record.get("record_id"),
                "canonical_record_id": seen_hashes[digest],
                "method": "exact",
                "similarity": 1.0,
            })
            continue
        duplicate_of = None
        similarity = 0.0
        if kept and normalized:
            matrix = TfidfVectorizer().fit_transform([item["content"] for item in kept] + [normalized])
            similarities = cosine_similarity(matrix[-1], matrix[:-1])[0]
            best_index = int(similarities.argmax())
            similarity = float(similarities[best_index])
            if similarity >= 0.85:
                duplicate_of = kept[best_index]["record_id"]
        if duplicate_of:
            duplicate_rows.append({
                "duplicate_record_id": record.get("record_id"),
                "canonical_record_id": duplicate_of,
                "method": "tfidf_cosine",
                "similarity": round(similarity, 4),
            })
            continue
        seen_hashes[digest] = record.get("record_id", "")
        kept.append(record)
    return kept, duplicate_rows


def load_source_manifest(path: Path) -> list[dict[str, Any]]:
    return json.loads(path.read_text(encoding="utf-8"))


def extract_manifest_records(path: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    records: list[dict[str, Any]] = []
    source_rows: list[dict[str, Any]] = []
    error_rows: list[dict[str, Any]] = []
    for index, source in enumerate(load_source_manifest(path), start=1):
        ref = source["ref"]
        source_type = source["type"]
        text = ""
        if source_type == "web":
            text = extract_url_text(ref)
        elif source_type == "pdf":
            pdf_path = Path(ref)
            if not pdf_path.is_absolute():
                pdf_path = path.parent / pdf_path
            text = extract_pdf_text(str(pdf_path)) if pdf_path.exists() else ""
        else:
            error_rows.append({"source_id": source.get("source_id", f"src_{index:03d}"), "ref": ref, "error_type": "unsupported_type", "message": source_type, "status": "failed"})
            continue
        status = "ok" if text else "failed"
        source_rows.append({
            "source_id": source.get("source_id", f"src_{index:03d}"),
            "ref": ref,
            "type": source_type,
            "date_fetched": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "method": "trafilatura" if source_type == "web" else "pdfplumber",
            "status": status,
            "label": source.get("title", ref),
        })
        if not text:
            error_rows.append({"source_id": source.get("source_id", f"src_{index:03d}"), "ref": ref, "error_type": "empty_or_failed_extraction", "message": "No text extracted from source.", "status": "failed"})
            continue
        records.append({
            "record_id": source.get("record_id", f"kb_{source.get('category', 'faq')}_{index:03d}"),
            "title": source.get("title", ref),
            "content": text,
            "category": source.get("category", "faq"),
            "subcategory": source.get("subcategory", "general"),
            "source": {"type": source_type, "ref": ref, "page": source.get("page"), "url": ref if source_type == "web" else None},
            "language": source.get("language", "en"),
            "market": source.get("market", "global"),
            "version": source.get("version", "1.0"),
            "status": "active",
            "effective_date": source.get("effective_date"),
            "pii": False,
            "tags": source.get("tags", []),
        })
    return records, source_rows, error_rows


def extract_url_text(url: str) -> str:
    if trafilatura is None:
        return ""
    downloaded = trafilatura.fetch_url(url)
    if not downloaded:
        return ""
    text = trafilatura.extract(downloaded, include_comments=False, output_format="txt") or ""
    return normalize_whitespace(text)


def extract_pdf_text(path: str) -> str:
    if pdfplumber is None:
        return ""
    text_chunks: list[str] = []
    try:
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text() or ""
                text_chunks.append(page_text)
    except Exception:
        text_chunks = []
    if not text_chunks and fitz is not None:
        try:
            doc = fitz.open(path)
            text_chunks = [page.get_text() for page in doc]
        except Exception:
            text_chunks = []
    return normalize_whitespace("\n".join(text_chunks))


def build_sources_manifest() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for src in SEED_SOURCES:
        source_id = src["source_id"]
        ref = src["ref"]
        source_type = src["type"]
        status = src["status"]
        date_fetched = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        rows.append(
            {
                "source_id": source_id,
                "ref": ref,
                "type": source_type,
                "date_fetched": date_fetched,
                "method": src["method"],
                "status": status,
                "label": src["label"],
            }
        )
    return rows


def build_error_manifest() -> list[dict[str, Any]]:
    return [
        {
            "source_id": "src_004",
            "ref": "duplicate_fee_table.pdf",
            "error_type": "conflicting_fee_numbers",
            "message": "Two versions of the fee schedule disagree on penalty calculations.",
            "status": "flagged",
        }
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the cleaned, deduplicated knowledge base.")
    parser.add_argument("--real-sources", type=Path, help="JSON manifest containing real web and PDF sources.")
    args = parser.parse_args()
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    if args.real_sources:
        source_records, source_rows, error_rows = extract_manifest_records(args.real_sources)
        raw_records = SAMPLE_RECORDS + source_records
    else:
        source_rows = build_sources_manifest()
        error_rows = build_error_manifest()
        raw_records = SAMPLE_RECORDS

    sanitized_records = [sanitize_record(record) for record in raw_records]
    record_rows, duplicate_rows = deduplicate_records(sanitized_records)
    write_csv(
        SOURCES_CSV,
        ["source_id", "ref", "type", "date_fetched", "method", "status", "label"],
        source_rows,
    )

    write_csv(
        ERRORS_CSV,
        ["source_id", "ref", "error_type", "message", "status"],
        error_rows,
    )
    write_csv(
        DUPLICATES_CSV,
        ["duplicate_record_id", "canonical_record_id", "method", "similarity"],
        duplicate_rows,
    )

    with RECORDS_JSONL.open("w", encoding="utf-8") as f:
        for row in record_rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(f"sources_written={len(source_rows)}")
    print(f"errors_written={len(error_rows)}")
    print(f"records_written={len(record_rows)}")
    print(f"duplicates_logged={len(duplicate_rows)}")
    print(f"records_path={RECORDS_JSONL}")


if __name__ == "__main__":
    main()
