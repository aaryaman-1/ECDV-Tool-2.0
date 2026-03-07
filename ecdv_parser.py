import pandas as pd
import re


# ==========================================================
# FROZEN CORE PARSER (DO NOT MODIFY)
# ==========================================================

def parse_vertical_format_general(user_input: str) -> pd.DataFrame:

    raw_lines = user_input.splitlines()
    lines = [line.rstrip("\n") for line in raw_lines]

    if len(lines) < 2:
        raise ValueError("Input must contain header row and values.")

    raw_headers = re.split(r'\t+|\s+', lines[0].strip())
    n_cols = len(raw_headers)

    processed_headers = []

    for header in raw_headers:
        if header.startswith("B0"):
            processed_headers.append(header[2:])
        elif header.startswith("D"):
            processed_headers.append(header[1:])
        elif header.startswith("F"):
            processed_headers.append(header[1:])
        else:
            raise ValueError(f"Unexpected header format: {header}")

    rows = []
    current_row = [None] * n_cols
    current_col = 0

    def finalize_row():
        nonlocal current_row, current_col

        finalized = [
            [] if val is None else val
            for val in current_row
        ]

        rows.append(finalized)
        current_row = [None] * n_cols
        current_col = 0

    for line in lines[1:]:

        if line.strip() == "" and "\t" not in line:
            if any(val is not None for val in current_row):
                finalize_row()
            continue

        segments = line.split("\t")

        for seg in segments:

            seg = seg.strip()

            if seg.startswith("+"):

                seg = seg[1:].strip()

                if re.match(r"^\(\w+\)$", seg):
                    value = "!" + seg[1:-1]
                else:
                    value = seg

                target_col = current_col - 1

                if target_col >= 0:

                    if current_row[target_col] is None:
                        current_row[target_col] = [value]

                    elif isinstance(current_row[target_col], list):
                        current_row[target_col].append(value)

                    else:
                        current_row[target_col] = [
                            current_row[target_col],
                            value
                        ]

                continue

            if seg == "":
                value = []

            else:
                if re.match(r"^\(\w+\)$", seg):
                    value = "!" + seg[1:-1]
                else:
                    value = seg

            while current_col < n_cols and current_row[current_col] is not None:
                current_col += 1

            if current_col >= n_cols:
                finalize_row()

            if isinstance(value, str) and value.startswith("!"):
                current_row[current_col] = [value]
            else:
                current_row[current_col] = value

            current_col += 1

            if current_col == n_cols:
                finalize_row()

    if any(val is not None for val in current_row):
        finalize_row()

    data = {col: [] for col in processed_headers}

    for row in rows:
        for col_name, val in zip(processed_headers, row):
            data[col_name].append(val)

    return pd.DataFrame(data)


# ==========================================================
# MULTI BLOCK PARSER
# ==========================================================

def parse_multiblock_format(user_input: str) -> pd.DataFrame:

    lines = user_input.splitlines()

    header_pattern = re.compile(r'^[A-Z0-9]+\t')
    row_pattern = re.compile(r'^\((\d+)\)\t')

    blocks = []
    current_block = []

    for line in lines:

        if header_pattern.match(line) and current_block:
            blocks.append(current_block)
            current_block = []

        current_block.append(line)

    if current_block:
        blocks.append(current_block)

    block_dataframes = []

    for block in blocks:

        header = block[0]
        header_tokens = [h for h in header.split("\t") if h.strip() != ""]
        n_cols = len(header_tokens)

        # --------------------------------------------------
        # CASE 1: FULL 8 COLUMN BLOCK
        # --------------------------------------------------

        if n_cols == 8:

            cleaned_lines = []

            for line in block:
                line = re.sub(r'^\(\d+\)\t', '', line)
                cleaned_lines.append(line)

            block_text = "\n".join(cleaned_lines)

            df_block = parse_vertical_format_general(block_text)

            block_dataframes.append(df_block)

            continue

        # --------------------------------------------------
        # CASE 2: PARTIAL BLOCK (<8 columns)
        # --------------------------------------------------

        rows = {}
        current_row = None

        for line in block[1:]:

            row_match = row_pattern.match(line)

            if row_match:
                current_row = int(row_match.group(1)) - 1
                rows.setdefault(current_row, [])
                line = re.sub(r'^\(\d+\)\t', '', line)

            if current_row is None:
                continue

            segments = line.split("\t")

            for seg in segments:

                if len(rows[current_row]) >= n_cols:
                    continue

                clean = seg.strip()

                if clean == "":
                    rows[current_row].append("")
                else:
                    rows[current_row].append(clean)

        # --------------------------------------------------
        # FIXED ROW RECONSTRUCTION
        # --------------------------------------------------

        reconstructed = [header]

        for r in sorted(rows.keys()):

            row_values = rows[r]

            if len(row_values) < n_cols:
                row_values += [""] * (n_cols - len(row_values))

            reconstructed.append("\t".join(row_values))
            reconstructed.append("")

        block_text = "\n".join(reconstructed)

        df_block = parse_vertical_format_general(block_text)

        block_dataframes.append(df_block)

    row_counts = [df.shape[0] for df in block_dataframes]

    if len(set(row_counts)) != 1:

        print("\n===== DEBUG: BLOCK DATAFRAMES =====\n")

        for i, df_block in enumerate(block_dataframes, start=1):
            print(f"\n--- Block {i} ---")
            print(f"Rows: {df_block.shape[0]}, Columns: {df_block.shape[1]}")
            print(df_block)
            print()

        print("\n===================================\n")

        raise ValueError(
            f"Row count mismatch between blocks: {row_counts}"
        )

    df_final = pd.concat(block_dataframes, axis=1)

    return df_final


# ==========================================================
# ROUTER
# ==========================================================

def parse_ecdv_general(user_input: str) -> pd.DataFrame:

    row_number_pattern = re.compile(r'^\(\d+\)\t', re.MULTILINE)

    if not row_number_pattern.search(user_input):
        return parse_vertical_format_general(user_input)

    return parse_multiblock_format(user_input)