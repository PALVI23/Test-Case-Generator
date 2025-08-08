import streamlit as st
import pandas as pd
import subprocess
import os

st.set_page_config(layout="wide")
st.title("GenAI Test Case Generator")

# --- File Paths ---
input_data_dictionary_path = 'data_dictionary_try.xlsx'
formatted_dict_file = 'formatted_dictionary.csv'
test_cases_file = 'input_data_try.xlsx'
validated_data_file = 'validated_data.xlsx'

# --- Session State Initialization for a state machine ---
if "step" not in st.session_state:
    st.session_state.step = 1
    # On first run of a session, clean up files from previous sessions.
    for f in [formatted_dict_file, test_cases_file, validated_data_file, input_data_dictionary_path]:
        if os.path.exists(f):
            os.remove(f)

# --- Step 1: Upload Data Dictionary ---
st.header("Step 1: Upload Data Dictionary")
if not os.path.exists(input_data_dictionary_path):
    uploaded_file = st.file_uploader("Choose a .xlsx or .csv file", type=["xlsx", "csv"])
    if uploaded_file:
        df_dict = pd.read_excel(uploaded_file) if uploaded_file.name.endswith('xlsx') else pd.read_csv(uploaded_file)
        df_dict.to_excel(input_data_dictionary_path, index=False)
        st.rerun()
else:
    st.dataframe(pd.read_excel(input_data_dictionary_path))
    if st.session_state.step == 1:
        if st.button("Generate Test Cases"):
            with st.spinner("Running `generate_test_cases.py`..."):
                import sys

try:
    subprocess.run([sys.executable, "generate_test_cases.py"], check=True)
except subprocess.CalledProcessError as e:
    st.error(f"Subprocess failed with exit code {e.returncode}")
    st.error(f"Command: {e.cmd}")
    st.error(e.output)

            st.session_state.step = 2
            st.rerun()

# --- Step 2: Review and Refine Formatted Dictionary ---
if st.session_state.step >= 2:
    st.header("Step 2: Generate & Review Test Cases")
    df_formatted = pd.read_csv(formatted_dict_file)
    st.dataframe(df_formatted)

    if st.session_state.step == 2:
        feedback_enabled = st.toggle("Enable Feedback & Refinement")
        if feedback_enabled:
            with st.container(border=True):
                st.subheader("Refinement Controls")
                edited_df = st.data_editor(df_formatted, num_rows="dynamic", key="df_editor")
                feedback_text = st.text_area("Provide high-level feedback for all rules:", key="feedback_text_area")

                if st.button("Apply Feedback"):
                    edited_df.to_csv(formatted_dict_file, index=False)
                    if feedback_text:
                        with st.spinner("Incorporating feedback..."):
                            subprocess.run([
                                "python", "incorporate_feedback.py",
                                formatted_dict_file, feedback_text, formatted_dict_file
                            ], check=True)
                    st.rerun()

            if st.button("Accept Changes and Proceed to Synthetic Data Generation"):
                st.session_state.step = 3
                st.rerun()
        else:
            if st.button("Proceed to Synthetic Data Generation"):
                st.session_state.step = 3
                st.rerun()

# --- Step 3: Generate Synthetic Test Data ---
if st.session_state.step >= 3:
    st.header("Step 3: Generate Synthetic Test Data")
    if os.path.exists(test_cases_file):
        st.dataframe(pd.read_excel(test_cases_file))
    if st.session_state.step == 3:
        st.subheader("Synthetic Data Generation Parameters")
        col1, col2, col3 = st.columns(3)
        with col1:
            num_records = st.number_input("Total number of rows:", min_value=10, value=50)
        with col2:
            min_invalid_per_row = st.number_input("Min invalid values per row:", min_value=1, value=4)
        with col3:
            min_invalid_per_col = st.number_input("Min invalid values per column:", min_value=1, value=10)

        if st.button("Generate Synthetic Data"):
            with st.spinner("Running `create_synthetic_data.py`..."):
                subprocess.run([
                    "python", "create_synthetic_data.py",
                    str(num_records), str(min_invalid_per_row), str(min_invalid_per_col)
                ], check=True)
            st.session_state.step = 4
            st.rerun()

# --- Step 4: Validate Test Cases ---
if st.session_state.step >= 4:
    st.header("Step 4: Validate Test Cases")
    if st.session_state.step == 4:
        if st.button("Run Validation"):
            with st.spinner("Running `validate.py`..."):
                subprocess.run(["python", "validate.py"], check=True)
            st.session_state.step = 5
            st.rerun()

    if st.session_state.step >= 5:
        st.dataframe(pd.read_excel(validated_data_file))
        st.success("Workflow complete! Refresh the page to start a new workflow.")
