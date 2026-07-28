import argparse
import json
import os
import shutil
import sys
import time
from langchain_community.document_loaders import CSVLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings

# --- CONFIGURATION ---
# Paths are anchored to the repo root so the script behaves the same no matter
# which directory it is invoked from.
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_CSV_PATH = os.path.join(REPO_ROOT, "data", "cybercrime_complaints_300k_fixed.csv")
# Must stay in sync with settings.CHROMA_DB_DIR in app/core/config.py, which is
# where the API expects to find the store at import time.
DEFAULT_CHROMA_DB_DIR = os.path.join(REPO_ROOT, "data", "ChromaDB_Indian")
EMBEDDING_MODEL = "nomic-embed-text"  # Ensure this model is pulled in Ollama

# The column whose text gets embedded and searched.
CONTENT_COLUMN = "complaint_text"

# Every other column, kept alongside each vector so results can be filtered
# and traced back to the original complaint.
METADATA_COLUMNS = [
    "complaint_id",
    "primary_category",
    "sub_category",
    "severity_level",
    "priority",
    "amount_lost",
    "platform",
    "routing_department",
    "jurisdiction",
    "keywords",
    "incident_date",
    "user_name",
    "user_city",
]

# Ollama's model runner crashes if it is handed thousands of texts in one
# request, so documents are embedded in small batches instead.
EMBED_BATCH_SIZE = 200

# The status messages below use emoji, which the default Windows console
# encoding (cp1252) cannot represent when output is piped or redirected.
sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def format_duration(seconds):
    """Turns a number of seconds into something like '1h 04m 09s'."""
    seconds = int(seconds)
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours}h {minutes:02d}m {secs:02d}s"
    if minutes:
        return f"{minutes}m {secs:02d}s"
    return f"{secs}s"


def clean_metadata(metadata):
    """Chroma only stores str/int/float/bool, so coerce everything else."""
    cleaned = {}
    for key, value in metadata.items():
        if value is None:
            cleaned[key] = ""
        elif isinstance(value, (str, int, float, bool)):
            cleaned[key] = value
        else:
            cleaned[key] = str(value)
    return cleaned


def count_rows(csv_path):
    """Counts data rows without holding the file in memory."""
    with open(csv_path, "r", encoding="utf-8", newline="") as handle:
        return max(sum(1 for _ in handle) - 1, 0)  # minus the header


def checkpoint_path_for(db_dir):
    return os.path.join(db_dir, "ingest_checkpoint.json")


def load_checkpoint(checkpoint_path):
    """Returns how many CSV rows a previous run already ingested."""
    if not os.path.exists(checkpoint_path):
        return 0
    try:
        with open(checkpoint_path, "r", encoding="utf-8") as handle:
            return int(json.load(handle).get("rows_done", 0))
    except (ValueError, OSError):
        return 0


def save_checkpoint(rows_done, checkpoint_path):
    with open(checkpoint_path, "w", encoding="utf-8") as handle:
        json.dump({"rows_done": rows_done}, handle)


def add_batch_with_retry(vectorstore, batch, attempts=4):
    """Adds one batch, retrying if the Ollama runner drops the connection."""
    for attempt in range(1, attempts + 1):
        try:
            vectorstore.add_documents(batch)
            return
        except Exception as exc:
            if attempt == attempts:
                raise
            wait = 5 * attempt
            print(
                f"\n   !  Batch failed: {exc}"
                f"\n      Retry {attempt}/{attempts - 1} in {wait}s...",
                flush=True,
            )
            time.sleep(wait)


def build_vector_store(
    csv_path=DEFAULT_CSV_PATH,
    db_dir=DEFAULT_CHROMA_DB_DIR,
    max_rows=None,
    batch_size=EMBED_BATCH_SIZE,
    fresh=False,
):
    if not os.path.exists(csv_path):
        raise FileNotFoundError(
            f"File not found at {csv_path}. "
            f"Put your complaints CSV in data/ or point --csv at it."
        )

    checkpoint_path = checkpoint_path_for(db_dir)

    print("1️⃣  Scanning the dataset...")
    total_rows = count_rows(csv_path)
    target_rows = min(max_rows, total_rows) if max_rows else total_rows
    print(f"   -> {total_rows:,} rows in the CSV; ingesting {target_rows:,}.")
    print(f"   -> 1 content column ({CONTENT_COLUMN}) + "
          f"{len(METADATA_COLUMNS)} metadata columns.")

    if fresh and os.path.exists(db_dir):
        print(f"   -> --fresh given, deleting {db_dir}")
        shutil.rmtree(db_dir)

    # A fresh clone has no data/ directory at all; the checkpoint is written
    # before Chroma gets a chance to create it.
    os.makedirs(db_dir, exist_ok=True)

    rows_done = load_checkpoint(checkpoint_path)
    if rows_done >= target_rows and rows_done > 0:
        print(f"\n✅ Already complete: {rows_done:,} rows ingested. "
              f"Use --fresh to rebuild from scratch.")
        return
    if rows_done:
        print(f"   -> Resuming from row {rows_done:,} "
              f"(delete {db_dir} or pass --fresh to start over).")

    print("\n2️⃣  Opening the CSV stream...")
    # encoding is required: CSVLoader otherwise opens the file with the
    # Windows locale encoding and mangles ₹ and other non-ASCII characters.
    loader = CSVLoader(
        file_path=csv_path,
        content_columns=[CONTENT_COLUMN],
        metadata_columns=METADATA_COLUMNS,
        encoding="utf-8",
    )

    # Long complaints get split; short ones pass through untouched.
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)

    print("\n3️⃣  Generating embeddings and writing to ChromaDB...")
    print("   (Ollama must be running - check with: ollama list)\n")

    embeddings = OllamaEmbeddings(model=EMBEDDING_MODEL)
    vectorstore = Chroma(
        embedding_function=embeddings,
        persist_directory=db_dir,
    )

    started = time.time()
    rows_at_start = rows_done
    chunks_written = 0
    batch = []

    def flush(batch, rows_done):
        """Embeds one pending batch and records progress."""
        nonlocal chunks_written
        if not batch:
            return
        add_batch_with_retry(vectorstore, batch)
        chunks_written += len(batch)
        save_checkpoint(rows_done, checkpoint_path)

        elapsed = time.time() - started
        rows_this_run = rows_done - rows_at_start
        rate = rows_this_run / elapsed if elapsed else 0
        remaining = target_rows - rows_done
        eta = remaining / rate if rate else 0
        percent = rows_done / target_rows * 100 if target_rows else 100

        print(
            f"\r   {percent:5.1f}%  |  {rows_done:,}/{target_rows:,} rows  |  "
            f"{rate:6.1f} rows/s  |  elapsed {format_duration(elapsed)}  |  "
            f"ETA {format_duration(eta)}   ",
            end="",
            flush=True,
        )
        # Leave a permanent line in the scrollback every 25k rows.
        if rows_done % 25000 < batch_size:
            print(flush=True)

    for row_index, document in enumerate(loader.lazy_load()):
        if row_index < rows_done:
            continue  # already ingested by an earlier run
        if row_index >= target_rows:
            break

        for chunk in text_splitter.split_documents([document]):
            chunk.metadata = clean_metadata(chunk.metadata)
            batch.append(chunk)

        # A row can produce several chunks, so the batch may overshoot slightly.
        if len(batch) >= batch_size:
            flush(batch, row_index + 1)
            batch = []

    if batch:
        flush(batch, target_rows)

    elapsed = time.time() - started
    print(f"\n\n✅ SUCCESS! {chunks_written:,} chunks written to {db_dir}")
    print(f"   Took {format_duration(elapsed)}.")
    print(f"   Collection now holds {vectorstore._collection.count():,} vectors.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Build the Indian cybercrime complaint vector store."
    )
    parser.add_argument(
        "--csv",
        default=DEFAULT_CSV_PATH,
        help=f"Path to the complaints CSV (default {DEFAULT_CSV_PATH}).",
    )
    parser.add_argument(
        "--db-dir",
        default=DEFAULT_CHROMA_DB_DIR,
        help=f"Where to persist the vector store (default {DEFAULT_CHROMA_DB_DIR}).",
    )
    parser.add_argument(
        "--max-rows",
        type=int,
        default=None,
        help="Only ingest the first N rows (handy for a quick smoke test).",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=EMBED_BATCH_SIZE,
        help=f"Documents per embedding request (default {EMBED_BATCH_SIZE}).",
    )
    parser.add_argument(
        "--fresh",
        action="store_true",
        help="Delete any existing store and start from row 0.",
    )
    args = parser.parse_args()

    build_vector_store(
        csv_path=args.csv,
        db_dir=args.db_dir,
        max_rows=args.max_rows,
        batch_size=args.batch_size,
        fresh=args.fresh,
    )
