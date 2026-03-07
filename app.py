import streamlit as st
from ecdv_logic import parse_excel_logical_input, generate_ecdv, parse_ecdv_general

st.set_page_config(page_title="ECDV Automation Tool", layout="centered")

st.title("ECDV Automation Tool")

# =========================================
# Input Type Selection
# =========================================

input_type = st.radio(
    "Select Input Type",
    ["PLM ECDV input", "OCM ECDV input"]
)

# =========================================
# CM / Family Inputs
# =========================================

col1, col2 = st.columns(2)

with col1:
    cm = st.text_input("CM")

with col2:
    family = st.text_input("Family")

# =========================================
# Main Input Box
# =========================================

user_input = st.text_area(
    "Input",
    height=300,
    placeholder="Paste input here..."
)

# =========================================
# Generate Button
# =========================================

if st.button("Generate ECDV"):

    try:

        # ---------------------------------
        # Choose Parser
        # ---------------------------------

        if input_type == "PLM ECDV input":
            df = parse_excel_logical_input(user_input)
        else:
            df = parse_ecdv_general(user_input)

        # ---------------------------------
        # Generate Final ECDV
        # ---------------------------------

        result = generate_ecdv(df, cm, family)

        # =========================================
        # Output 1 — Final ECDV
        # =========================================

        st.success("ECDV Generated Successfully")

        st.subheader("Generated ECDV")

        st.code(result, language="text")

        st.download_button(
            label="Copy ECDV Output",
            data=result,
            file_name="ecdv_output.txt",
            mime="text/plain"
        )

        # =========================================
        # Output 2 — Parsed DataFrame
        # =========================================

        st.subheader("Parsed DataFrame")

        st.dataframe(df, use_container_width=True)

        df_csv = df.to_csv(index=False)

        st.download_button(
            label="Copy DataFrame (CSV)",
            data=df_csv,
            file_name="parsed_dataframe.csv",
            mime="text/csv"
        )

    except Exception as e:
        st.error(str(e))
