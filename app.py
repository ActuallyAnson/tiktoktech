import streamlit as st
import pandas as pd
import time
import json
import os
from pathlib import Path

from src.processors.gemini_classifier import GeminiClassifier
import subprocess

def run_full_pipeline(input_file, output_dir="outputs", delay=1.0):
    """
    Run the full compliance pipeline as a subprocess from the Streamlit app
    """
    output_area = st.empty()
    progress_bar = st.progress(0)
    os.makedirs(output_dir, exist_ok=True)
    cmd = [
        "python", "-m", "src.pipelines.start_pipeline",
        "--input", str(input_file),
        "--outdir", str(output_dir),
        "--llm-min-interval", str(delay)
    ]
    try:
        output_text = ""
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        pipeline_stages = 5
        current_stage = 0
        for line in iter(process.stdout.readline, ""):
            output_text += line
            output_area.text_area("Pipeline Output", output_text, height=200)
            if ("done" in line.lower() or 
                "complete" in line.lower() or 
                "finished" in line.lower() or
                "success" in line.lower() or
                any(char in line for char in ["✓", "✗", "√", "x"])):
                current_stage += 1
                progress = min(current_stage / pipeline_stages, 1.0)
                progress_bar.progress(progress)
        rc = process.wait()
        progress_bar.progress(1.0)
        if rc == 0:
            st.success("Pipeline completed successfully!")
            return Path(output_dir) / "final_results.csv"
        else:
            st.error(f"Pipeline failed with exit code {rc}")
            return None
    except Exception as e:
        st.error(f"Failed to run pipeline: {str(e)}")
        return None

st.set_page_config(
    page_title="Geo-Compliance Classifier", 
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("Geo-Compliance Classifier")
st.markdown("""
    This tool classifies TikTok features to determine if they require geo-specific compliance logic.
""")

with st.sidebar:
    st.header("Settings")
    delay = st.slider(
        "Delay between API calls (seconds)", 
        min_value=0.0, 
        max_value=5.0, 
        value=1.0, 
        step=0.1,
        help="Add delay between API calls to avoid rate limiting"
    )
    batch_size = st.slider(
        "Batch size", 
        min_value=1, 
        max_value=10, 
        value=5,
        help="Number of features to process in one API call (larger batches are more efficient)"
    )
    with st.expander("Terminology"):
        try:
            terminology_path = Path("data") / "terminology.json"
            if terminology_path.exists():
                with open(terminology_path, 'r') as f:
                    terminology = json.load(f)
                    st.json(terminology)
            else:
                st.info("Terminology file not found")
        except Exception as e:
            st.error(f"Error loading terminology: {str(e)}")

def display_results(result):
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Classification Results")
        classification = result.get("classification", "UNKNOWN")
        if classification == "REQUIRED":
            st.error(f"**Classification:** {classification}")
        elif classification == "NOT REQUIRED":
            st.success(f"**Classification:** {classification}")
        else:
            st.warning(f"**Classification:** {classification}")
        st.metric("Confidence", f"{result.get('confidence', 0.0):.2f}")
    with col2:
        st.subheader("Details")
        st.write("**Reasoning:**", result.get("reasoning", "No reasoning provided"))
    regulations = result.get("related_regulations", [])
    if regulations:
        st.subheader("Related Regulations")
        for reg in regulations:
            st.markdown(f"- {reg}")

# Batch Classification Only
st.header("Batch Feature Classification")
st.markdown("""
    Upload a CSV file with the following columns: 
    - `feature_name`: Name of the feature to classify
    - `feature_description`: Description of the feature
""")

uploaded_file = st.file_uploader("Choose CSV File", type="csv")

if uploaded_file is not None:
    try:
        df = pd.read_csv(uploaded_file)
        if not {"feature_name", "feature_description"}.issubset(df.columns):
            st.error("CSV file must contain 'feature_name' and 'feature_description' columns.")
        else:
            st.success("CSV file loaded successfully!")
            with st.expander("Preview Data"):
                st.dataframe(df.head())
            st.info(f"Found {len(df)} features to classify")
            with st.expander("Pipeline Settings"):
                delay = st.slider(
                    "LLM call interval (seconds)", 
                    min_value=0.0, 
                    max_value=5.0, 
                    value=1.0, 
                    step=0.1,
                    help="Minimum delay between LLM API calls"
                )
                output_dir = st.text_input(
                    "Output directory", 
                    value="outputs",
                    help="Directory where pipeline results will be saved"
                )
            if st.button("Start Compliance Pipeline", type="primary"):
                temp_input = "temp_input.csv"
                df.to_csv(temp_input, index=False)
                with st.spinner("Running compliance pipeline..."):
                    final_csv = run_full_pipeline(
                        input_file=temp_input,
                        output_dir=output_dir,
                        delay=delay
                    )
                try:
                    os.remove(temp_input)
                except:
                    pass
                if final_csv and final_csv.exists():
                    try:
                        results_df = pd.read_csv(final_csv)
                        st.success(f"Pipeline complete! Processed {len(results_df)} features.")
                        needs_review_df = results_df[results_df['classification'] == 'NEEDS HUMAN REVIEW']
                        human_review_count = len(needs_review_df)
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Total Features", len(results_df))
                        with col2:
                            st.metric("Need Human Review", human_review_count)
                        with col3:
                            st.metric("Automated Classification", len(results_df) - human_review_count)
                        if human_review_count > 0:
                            st.warning(f"⚠️ {human_review_count} features require human review")
                            with st.expander("Features Requiring Human Review", expanded=True):
                                st.dataframe(needs_review_df)
                            human_review_csv = needs_review_df.to_csv(index=False).encode("utf-8")
                            st.download_button(
                                label="Download Human Review Items as CSV",
                                data=human_review_csv,
                                file_name="human_review_items.csv",
                                mime="text/csv",
                            )
                        st.subheader("All Results")
                        st.dataframe(results_df)
                        csv_data = results_df.to_csv(index=False).encode("utf-8")
                        st.download_button(
                            label="Download All Results as CSV",
                            data=csv_data,
                            file_name="compliance_results.csv",
                            mime="text/csv",
                        )
                    except Exception as e:
                        st.error(f"Error loading results: {str(e)}")
    except Exception as e:
        st.error(f"Failed to process file: {str(e)}")

st.markdown("---")
st.caption("Geo-Compliance Classifier Tool | TikTok Internal Tool")
