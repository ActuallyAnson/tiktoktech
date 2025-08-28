"""
Batch processor for classifying multiple features at once.
For Data Engineers processing large datasets.
"""

import os
import pandas as pd
import json
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
from src.processors.gemini_classifier import GeminiClassifier

class BatchClassifier:
    def __init__(self, delay_seconds: float = 1.0):
        """Initialize batch classifier with rate limiting."""
        self.classifier = GeminiClassifier()
        self.delay = delay_seconds  # Delay between API calls to avoid rate limits
        
    def process_csv(self, input_file: str, output_file: Optional[str] = None) -> pd.DataFrame:
        """
        Process a CSV file of features.
        
        Expected CSV columns:
        - feature_name: Name of the feature
        - feature_description: Description of what it does
        
        Returns DataFrame with classification results.
        """
        print(f"Loading features from {input_file}")
        
        # Load input data
        df = pd.read_csv(input_file)
        
        # Validate required columns
        required_cols = ['feature_name', 'feature_description']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            raise ValueError(f"Missing required columns: {missing_cols}")
        
        print(f"🔍 Processing {len(df)} features...")
        start_time = time.time()
        
        # Process each feature
        results = []
        for i, row in df.iterrows():            
            print(f"  [{len(results)+1}/{len(df)}] Processing: {str(row['feature_name'])[:50]}...")
            
            try:
                result = self.classifier.classify_feature(
                    row['feature_name'], 
                    row['feature_description']
                )
                
                # Add original row data
                result.update({
                    'input_feature_name': row['feature_name'],
                    'input_feature_description': row['feature_description'],
                    'processed_at': pd.Timestamp.now().isoformat()
                })
                
                results.append(result)
                
                # Rate limiting
                if len(results) < len(df):  # Don't delay after last item
                    time.sleep(self.delay)
                    
            except Exception as e:
                print(f"Error: {str(e)}")
                results.append({
                    'input_feature_name': row['feature_name'],
                    'input_feature_description': row['feature_description'],
                    'classification': 'ERROR',
                    'reasoning': f'Processing error: {str(e)}',
                    'confidence': 0.0,
                    'related_regulations': [],
                    'processed_at': pd.Timestamp.now().isoformat()
                })
        
        # Convert to DataFrame
        results_df = pd.DataFrame(results)
        
        # Save results if output file specified
        if output_file:
            results_df.to_csv(output_file, index=False)
            print(f"Results saved to {output_file}")
        
        return results_df
    
    def process_features_list(self, features: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """
        Process a list of feature dictionaries.
        
        Args:
            features: List of dicts with 'name' and 'description' keys
            
        Returns:
            List of classification results
        """
        results = []
        
        for i, feature in enumerate(features):
            print(f"[{i+1}/{len(features)}] Processing: {feature['name']}")
            
            try:
                result = self.classifier.classify_feature(
                    feature['name'], 
                    feature['description']
                )
                results.append(result)
                
                if i < len(features) - 1:
                    time.sleep(self.delay)
                    
            except Exception as e:
                print(f"Error processing {feature['name']}: {str(e)}")
                results.append({
                    'classification': 'ERROR',
                    'reasoning': f'Processing error: {str(e)}',
                    'confidence': 0.0,
                    'original_feature_name': feature['name']
                })
        
        return results
    
    def generate_summary_report(self, results_df: pd.DataFrame) -> Dict[str, Any]:
        """Generate a summary report of classification results."""
        
        total_features = len(results_df)
        
        # Count by classification
        classification_counts = results_df['classification'].value_counts().to_dict()
        
        # Confidence statistics
        confidence_stats = {
            'mean_confidence': results_df['confidence'].mean(),
            'median_confidence': results_df['confidence'].median(),
            'min_confidence': results_df['confidence'].min(),
            'max_confidence': results_df['confidence'].max()
        }
        
        # High-confidence vs low-confidence breakdown
        high_confidence = results_df[results_df['confidence'] >= 0.9]
        needs_review = results_df[results_df['classification'] == 'NEEDS HUMAN REVIEW']
        
        summary = {
            'total_features': total_features,
            'classification_breakdown': classification_counts,
            'confidence_statistics': confidence_stats,
            'high_confidence_count': len(high_confidence),
            'needs_human_review_count': len(needs_review),
            'error_count': len(results_df[results_df['classification'] == 'ERROR']),
            'processing_timestamp': pd.Timestamp.now().isoformat()
        }
        
        return summary

def main():
    """Example usage of batch classifier with real TikTok sample data."""
    
    # Use the real sample data that contains TikTok terminology and complex features
    batch_classifier = BatchClassifier(delay_seconds=0.1)  # Much faster: 0.1 seconds instead of 0.5
    
    # Ensure outputs directory exists
    os.makedirs('outputs', exist_ok=True)
    
    # Check if the real sample data exists
    sample_data_path = 'data/sample_features.csv'
    if Path(sample_data_path).exists():
        print(f"🎯 Processing real TikTok sample data from {sample_data_path}")
        results_df = batch_classifier.process_csv(sample_data_path, 'outputs/sample_results.csv')
    else:
        print(f"⚠️  Real sample data not found at {sample_data_path}")
        print("📝 Creating simple test data for demo purposes...")
        
        # Fallback: Create simple sample data for testing
        sample_features = [
            {"name": "ASL for EU", "description": "Age-sensitive logic for GDPR compliance"},
            {"name": "Bug fix", "description": "Fixed memory leak in video processing"},
            {"name": "Age verification", "description": "Enhanced age verification system"},
        ]
        
        # Save sample data to CSV
        sample_df = pd.DataFrame([
            {"feature_name": f["name"], "feature_description": f["description"]} 
            for f in sample_features
        ])
        sample_df.to_csv('sample_features.csv', index=False)
        print("📁 Created sample_features.csv")
        
        results_df = batch_classifier.process_csv('sample_features.csv', 'outputs/sample_results.csv')
    
    # Generate summary report
    summary = batch_classifier.generate_summary_report(results_df)
    
    print("\nBATCH PROCESSING SUMMARY")
    print("=" * 40)
    print(f"Total features processed: {summary['total_features']}")
    print(f"Classification breakdown: {summary['classification_breakdown']}")
    print(f"High confidence classifications: {summary['high_confidence_count']}")
    print(f"Needs human review: {summary['needs_human_review_count']}")
    
    # Save summary as JSON
    with open('outputs/batch_summary.json', 'w') as f:
        json.dump(summary, f, indent=2, default=str)
    print("Summary saved to outputs/batch_summary.json")

if __name__ == "__main__":
    main()
