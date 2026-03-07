import pandas as pd
from itertools import product
import re

# NEW IMPORT (for OCM parser)
from ecdv_parser import parse_ecdv_general


def generate_ecdv(df, CM, Family):

    df = df.copy()

    # ==================================================
    # VT → CM Mapping
    # ==================================================
    VT_CM_MAP = {
        'CJ': '09',
        '88': '02',
        '89': '01',
        '82': '04',
        'FV': '07',
        'FL': '11',
        'EL': '49',
        'EN': '47',
        'GL': '48',
        'RL': '46',
        'VB': '36',
        'VN': '44',
    }

    if 'VT' in df.columns:
        expected_vt = VT_CM_MAP.get(str(CM))
        if expected_vt is None:
            raise ValueError(f"CM '{CM}' not defined in VT mapping.")

        def valid_VT(val):
            if isinstance(val, list) and len(val) == 0:
                return True
            if pd.isna(val):
                return True
            return str(val).zfill(2) == expected_vt

        df = df[df['VT'].apply(valid_VT)]
        df = df.drop(columns=['VT'])

    # ==================================================
    # A → Family[0]
    # ==================================================
    if 'A' in df.columns:

        expected_A = str(Family[0]).zfill(2)

        def valid_A(val):
            if isinstance(val, list) and len(val) == 0:
                return True
            if pd.isna(val):
                return True
            return str(val).zfill(2) == expected_A

        df = df[df['A'].apply(valid_A)]
        df = df.drop(columns=['A'])

    # ==================================================
    # C → Family[2:4]
    # ==================================================
    if 'C' in df.columns:

        expected_C = Family[2:4]

        def valid_C(val):
            if isinstance(val, list) and len(val) == 0:
                return True
            if pd.isna(val):
                return True
            return str(val) == expected_C

        df = df[df['C'].apply(valid_C)]
        df = df.drop(columns=['C'])

    # ==================================================
    # B and ZZ → Family[1]
    # ==================================================

    family_second_char = Family[1]

    if family_second_char == "G":
        valid_values = {"01", "0V"}
    else:
        valid_values = {f"0{family_second_char}"}

    for col in ['B', 'ZZ']:
        if col in df.columns:

            def valid_B(val):
                if isinstance(val, list) and len(val) == 0:
                    return True
                if pd.isna(val):
                    return True
                return str(val).zfill(2) in valid_values

            df = df[df[col].apply(valid_B)]

            if col == 'B':
                df = df.drop(columns=['B'])

    # ==================================================
    # Normalize Values
    # ==================================================
    def normalize_value(v):
        s = str(v)
        if s.isdigit() and len(s) == 1:
            return s.zfill(2)
        return s

    # ==================================================
    # Detect Common Columns
    # ==================================================
    common_parts = []
    non_common_columns = []

    for col in df.columns:
        column_values = df[col].tolist()

        if len(set(map(str, column_values))) == 1:
            val = column_values[0]
            if not isinstance(val, list):
                val_str = normalize_value(val)
                if not val_str.startswith("!"):
                    common_parts.append(f"{col}{val_str}")
                    continue

        non_common_columns.append(col)

    # ==================================================
    # Build Permutations
    # ==================================================
    result = []

    for row_index, row in df.iterrows():
        values = []

        for col in non_common_columns:

            val = row[col]

            if isinstance(val, list):
                if len(val) == 0:
                    continue
            else:
                if pd.isna(val):
                    continue
                val = [val]

            val = [normalize_value(v) for v in val]

            normal_vals = [v for v in val if not v.startswith("!")]
            exception_vals = [v for v in val if v.startswith("!")]

            if normal_vals and exception_vals:
                raise ValueError(
                    f"Mixed include/exclude in column '{col}' row {row_index}"
                )

            if exception_vals:
                grouped = "".join(f"({col}{v[1:]})" for v in exception_vals)
                values.append([grouped])
            elif normal_vals:
                values.append([f"{col}{v}" for v in normal_vals])

        if not values:
            continue

        for combo in product(*values):

            formatted = ""

            for part in combo:
                if part.startswith("("):
                    formatted += part
                else:
                    if formatted and not formatted.endswith(")"):
                        formatted += "."
                    formatted += part

            result.append(formatted)

    body = "/".join(result)
    prefix = f"{CM}.{Family}."

    if not common_parts and not body:
        return "No combinations for this product line"
        
    if common_parts and body:
        return f"{prefix}{'.'.join(common_parts)}<{body}*"
    elif common_parts and not body:
        return f"{prefix}{'.'.join(common_parts)}*"
    else:
        return f"{prefix}{body}*"


def parse_excel_logical_input(logical_input: str) -> pd.DataFrame:

    logical_input = logical_input.replace("\n", " ").strip()

    blocks = re.findall(r"\((.*?)\)", logical_input)

    if not blocks:
        raise ValueError("No valid '( ... )' blocks found.")

    parsed_rows = []

    for block in blocks:

        conditions = [c.strip() for c in block.split("AND") if c.strip()]
        row_dict = {}

        for cond in conditions:

            is_not = False

            if cond.startswith("NOT "):
                is_not = True
                cond = cond[4:].strip()

            match_d = re.match(r"D([A-Z0-9]+)_(\w+)", cond)
            match_b0 = re.match(r"B0([A-Z0-9]+)_(\w+)", cond)

            if match_d:
                column = match_d.group(1)
                value = match_d.group(2)

            elif match_b0:
                column = match_b0.group(1)
                value = match_b0.group(2)

            else:
                continue

            if is_not:
                value = f"!{value}"

            if column in row_dict:
                existing = row_dict[column]

                if isinstance(existing, list):
                    existing.append(value)
                else:
                    row_dict[column] = [existing, value]
            else:
                row_dict[column] = value

        parsed_rows.append(row_dict)

    all_columns = sorted({col for row in parsed_rows for col in row.keys()})

    final_rows = []

    for row in parsed_rows:
        formatted_row = {}
        for col in all_columns:
            if col in row:
                formatted_row[col] = row[col]
            else:
                formatted_row[col] = []
        final_rows.append(formatted_row)

    df = pd.DataFrame(final_rows)

    return df