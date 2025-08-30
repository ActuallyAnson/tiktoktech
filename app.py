import streamlit as st
import pandas as pd
import time
import json
import os
from pathlib import Path

# Import the necessary classes
from src.processors.gemini_classifier import GeminiClassifier
from batch_classifier import BatchClassifier  # Assumes batch_classifier.py is at project root

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
    
    if st.button("Classify Feature", type="primary"):
        if feature_name.strip() and feature_description.strip():
            with st.spinner("Classifying..."):
                classifier = GeminiClassifier()
                try:
                    result = classifier.classify_feature(feature_name, feature_description)
                    st.success("Classification complete!")
                    display_results(result)
                    
                    # Show raw JSON for debugging
                    with st.expander("View Raw Response"):
                        st.json(result)
                        
                except Exception as e:
                    st.error(f"Error in classification: {str(e)}")
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
                
                # Processing options
                col1, col2 = st.columns(2)
                
                with col1:
                    use_batching = st.checkbox("Use batch processing", value=True, 
                                              help="Process multiple features in a single API call (faster)")
                
                if st.button("Start Batch Classification", type="primary"):
                    # Initialize the batch classifier
                    batch_classifier = BatchClassifier(delay_seconds=delay)
                    
                    # Setup progress tracking
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    # Prepare features list
                    features = []
                    for _, row in df.iterrows():
                        features.append({
                            "name": row["feature_name"], 
                            "description": row["feature_description"]
                        })
                    
                    with st.spinner("Processing batch classification..."):
                        if use_batching and len(features) > 1:
                            # Use advanced batch processing
                            status_text.text("Using optimized batch processing...")
                            
                            # Save to temporary CSV for batch processing
                            temp_csv = "temp_batch.csv"
                            df.to_csv(temp_csv, index=False)
                            
                            # Process with batch API
                            results_df = batch_classifier.process_csv(
                                temp_csv, 
                                output_file=None, 
                                batch_size=batch_size
                            )
                            
                            # Clean up temp file
                            try:
                                os.remove(temp_csv)
                            except:
                                pass
                                
                        else:
                            # Use simple list processing for small batches
                            results = []
                            for i, feature in enumerate(features):
                                # Update progress
                                progress = (i + 1) / len(features)
                                progress_bar.progress(progress)
                                status_text.text(f"Processing feature {i+1} of {len(features)}: {feature['name']}")
                                
                                try:
                                    result = batch_classifier.classifier.classify_feature(
                                        feature["name"], 
                                        feature["description"]
                                    )
                                    results.append(result)
                                    
                                    # Add delay between calls
                                    if i < len(features) - 1:
                                        time.sleep(delay)
                                        
                                except Exception as e:
                                    results.append({
                                        'classification': 'ERROR',
                                        'reasoning': f'Processing error: {str(e)}',
                                        'confidence': 0.0,
                                        'related_regulations': [],
                                        'original_feature_name': feature['name']
                                    })
                            
                            # Convert to DataFrame
                            results_df = pd.DataFrame(results)
                    
                    # Clear progress indicators
                    progress_bar.empty()
                    status_text.empty()
                    
                    # Show success message
                    st.success(f"Batch classification complete! Processed {len(results_df)} features.")
                    
                    # Display results
                    st.subheader("Results")
                    st.dataframe(results_df)
                    
                    # Generate and display summary report
                    try:
                        summary_report = batch_classifier.generate_summary_report(results_df)
                        
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            st.metric("Total Features", summary_report['total_features'])
                        
                        with col2:
                            st.metric("High Confidence", summary_report['high_confidence_count'])
                        
                        with col3:
                            st.metric("Need Review", summary_report['needs_human_review_count'])
                            
                        st.subheader("Classification Breakdown")
                        st.json(summary_report['classification_breakdown'])
                        
                        # Save options
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            # Provide a download button for the results
                            csv = results_df.to_csv(index=False).encode("utf-8")
                            st.download_button(
                                label="Download Results as CSV",
                                data=csv,
                                file_name="batch_classification_results.csv",
                                mime="text/csv",
                            )
                            
                        with col2:
                            # Provide download for summary report
                            summary_json = json.dumps(summary_report, indent=2, default=str)
                            st.download_button(
                                label="Download Summary Report",
                                data=summary_json,
                                file_name="classification_summary.json",
                                mime="application/json",
                            )
                            
                    except Exception as e:
                        st.error(f"Error generating summary report: {str(e)}")
                        
        except Exception as e:
            st.error(f"Failed to process file: {str(e)}")

# Add footer
st.markdown("---")
st.caption("Geo-Compliance Classifier Tool | TikTok Internal Tool")
