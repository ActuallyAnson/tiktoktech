import streamlit as st
import pandas as pd
import time
import json
import os
from pathlib import Path

# Import the necessary classes
from src.processors.gemini_classifier import GeminiClassifier
import subprocess

def run_full_pipeline(input_file, output_dir="outputs", delay=1.0):
    """
    Run the full compliance pipeline as a subprocess from the Streamlit app
    
    Args:
        input_file: Path to the input CSV file
        output_dir: Directory to store outputs
        delay: Minimum delay between LLM calls (seconds)
    
    Returns:
        Path to the final results file if successful, None otherwise
    """
    # Create a placeholder for the output
    output_area = st.empty()
    progress_bar = st.progress(0)
    
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Build the command
    cmd = [
        "python", "-m", "src.pipelines.start_pipeline",
        "--input", str(input_file),
        "--outdir", str(output_dir),
        "--llm-min-interval", str(delay)
    ]
    
    # Run the process
    try:
        output_text = ""
        
        # Start the process
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        # Track progress
        pipeline_stages = 5  # prescan → enrich → route → agents → finalize
        current_stage = 0
        
        # Read output in real-time
        for line in iter(process.stdout.readline, ""):
            output_text += line
            output_area.text_area("Pipeline Output", output_text, height=200)
            
            # Try to parse progress from output
            if ("done" in line.lower() or 
                "complete" in line.lower() or 
                "finished" in line.lower() or
                "success" in line.lower() or
                any(char in line for char in ["✓", "✗", "√", "x"])):
                current_stage += 1
                progress = min(current_stage / pipeline_stages, 1.0)
                progress_bar.progress(progress)
        
        # Wait for process to complete
        rc = process.wait()
        
        # Final progress update
        progress_bar.progress(1.0)
        
        # Check result
        if rc == 0:
            st.success("Pipeline completed successfully!")
            return Path(output_dir) / "final_results.csv"
        else:
            st.error(f"Pipeline failed with exit code {rc}")
            return None
            
    except Exception as e:
        st.error(f"Failed to run pipeline: {str(e)}")
        return None

# Set page configuration
st.set_page_config(
    page_title="Geo-Compliance Classifier", 
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("Geo-Compliance Classifier")
st.markdown("""
    This tool classifies TikTok features to determine if they require geo-specific compliance logic.
""")

# Sidebar for navigation and settings
with st.sidebar:
    st.header("Navigation")
    mode = st.selectbox("Select Mode", ["Single Classification", "Batch Classification"])
    
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
    
    # Display terminology info in sidebar
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

# Function to display the classification results
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
        
    # Related regulations
    regulations = result.get("related_regulations", [])
    if regulations:
        st.subheader("Related Regulations")
        for reg in regulations:
            st.markdown(f"- {reg}")

# Single Classification Mode
if mode == "Single Classification":
    st.header("Single Feature Classification")
    
    col1, col2 = st.columns(2)
    
    with col1:
        feature_name = st.text_input("Feature Name", placeholder="Enter the feature name")
    
    with col2:
        feature_description = st.text_area("Feature Description", placeholder="Enter the feature description", height=100)
    
    # Pipeline settings for single feature
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
    
    if st.button("Classify Feature", type="primary"):
        if feature_name.strip() and feature_description.strip():
            with st.spinner("Classifying through pipeline..."):
                # Create a single-row DataFrame
                single_feature_df = pd.DataFrame([{
                    "feature_name": feature_name,
                    "feature_description": feature_description
                }])
                
                # Save as temporary CSV
                temp_input = "temp_single_feature.csv"
                single_feature_df.to_csv(temp_input, index=False)
                
                # Run the pipeline
                final_csv = run_full_pipeline(
                    input_file=temp_input,
                    output_dir=output_dir,
                    delay=delay
                )
                
                # Clean up temp file
                try:
                    os.remove(temp_input)
                except:
                    pass
                
                # Display results if successful
                if final_csv and final_csv.exists():
                    try:
                        # Load the final results
                        results_df = pd.read_csv(final_csv)
        
                        # Show success message
                        st.success(f"Pipeline complete! Processed {len(results_df)} features.")
        
                        # Check if there are features needing human review
                        needs_review_df = results_df[results_df['classification'] == 'NEEDS HUMAN REVIEW']
                        human_review_count = len(needs_review_df)
        
                        # Display results summary
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Total Features", len(results_df))
                        with col2:
                            st.metric("Need Human Review", human_review_count)
                        with col3:
                            st.metric("Automated Classification", len(results_df) - human_review_count)
        
                        # Display human review features first if there are any
                        if human_review_count > 0:
                            st.warning(f"⚠️ {human_review_count} features require human review")
            
                            with st.expander("Features Requiring Human Review", expanded=True):
                                st.dataframe(needs_review_df)
                
                            # Download just the human review items
                            human_review_csv = needs_review_df.to_csv(index=False).encode("utf-8")
                            st.download_button(
                                label="Download Human Review Items as CSV",
                                data=human_review_csv,
                                file_name="human_review_items.csv",
                                mime="text/csv",
                            )
        
                        # Display all results
                        st.subheader("All Results")
                        st.dataframe(results_df)
        
                        # Provide download button for all results
                        csv_data = results_df.to_csv(index=False).encode("utf-8")
                        st.download_button(
                            label="Download All Results as CSV",
                            data=csv_data,
                            file_name="compliance_results.csv",
                            mime="text/csv",
                        )
        
                    except Exception as e:
                        st.error(f"Error loading results: {str(e)}")
        else:
            st.warning("Please provide both a feature name and description.")

# Batch Classification Mode
else:  
    st.header("Batch Feature Classification")
    st.markdown("""
        Upload a CSV file with the following columns: 
        - `feature_name`: Name of the feature to classify
        - `feature_description`: Description of the feature
    """)
    
    # File upload
    uploaded_file = st.file_uploader("Choose CSV File", type="csv")
    
    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file)
            
            # Validate required columns
            if not {"feature_name", "feature_description"}.issubset(df.columns):
                st.error("CSV file must contain 'feature_name' and 'feature_description' columns.")
            else:
                st.success("CSV file loaded successfully!")
                
                # Preview data
                with st.expander("Preview Data"):
                    st.dataframe(df.head())
                
                st.info(f"Found {len(df)} features to classify")
                
                # Pipeline settings
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
                    # Save uploaded file to disk temporarily
                    temp_input = "temp_input.csv"
                    df.to_csv(temp_input, index=False)
                    
                    # Run the pipeline
                    with st.spinner("Running compliance pipeline..."):
                        final_csv = run_full_pipeline(
                            input_file=temp_input,
                            output_dir=output_dir,
                            delay=delay
                        )
                    
                    # Clean up temp file
                    try:
                        os.remove(temp_input)
                    except:
                        pass
                    
                    # Display results if successful
                    if final_csv and final_csv.exists():
                        try:
                            # Load the final results
                            results_df = pd.read_csv(final_csv)
        
                            # Show success message
                            st.success(f"Pipeline complete! Processed {len(results_df)} features.")
        
                            # Check if there are features needing human review
                            needs_review_df = results_df[results_df['classification'] == 'NEEDS HUMAN REVIEW']
                            human_review_count = len(needs_review_df)
        
                            # Display results summary
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric("Total Features", len(results_df))
                            with col2:
                                st.metric("Need Human Review", human_review_count)
                            with col3:
                                st.metric("Automated Classification", len(results_df) - human_review_count)
        
                            # Display human review features first if there are any
                            if human_review_count > 0:
                                st.warning(f"⚠️ {human_review_count} features require human review")
            
                                with st.expander("Features Requiring Human Review", expanded=True):
                                    st.dataframe(needs_review_df)
                
                                # Download just the human review items
                                human_review_csv = needs_review_df.to_csv(index=False).encode("utf-8")
                                st.download_button(
                                    label="Download Human Review Items as CSV",
                                    data=human_review_csv,
                                    file_name="human_review_items.csv",
                                    mime="text/csv",
                                )
        
                            # Display all results
                            st.subheader("All Results")
                            st.dataframe(results_df)
        
                            # Provide download button for all results
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

# Add footer
st.markdown("---")
st.caption("Geo-Compliance Classifier Tool | TikTok Internal Tool")
