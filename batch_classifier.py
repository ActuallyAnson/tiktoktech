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
        
    def process_csv(self, input_file: str, output_file: Optional[str] = None, batch_size: int = 5) -> pd.DataFrame:
        """
        Process features from CSV file using batch processing for efficiency.
        
        Args:
            input_file: Path to input CSV with columns 'feature_name', 'feature_description'
            output_file: Optional path to save results CSV
            batch_size: Number of features to process in each API call (default: 5)
        
        Returns:
            DataFrame with classification results
        """
        print(f"Loading features from {input_file}")
        
        # Load input data
        df = pd.read_csv(input_file)
        
        # Validate required columns
        required_cols = ['feature_name', 'feature_description']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            raise ValueError(f"Missing required columns: {missing_cols}")
        
        print(f"🔍 Processing {len(df)} features in batches of {batch_size}...")
        start_time = time.time()
        
        # Process features in batches
        all_results = []
        total_batches = (len(df) + batch_size - 1) // batch_size  # Ceiling division
        
        for batch_num in range(total_batches):
            start_idx = batch_num * batch_size
            end_idx = min(start_idx + batch_size, len(df))
            batch_df = df.iloc[start_idx:end_idx]
            
            print(f"  📦 Batch {batch_num + 1}/{total_batches}: Processing features {start_idx + 1}-{end_idx}...")
            
            try:
                # Prepare batch data
                features_batch = []
                for _, row in batch_df.iterrows():
                    features_batch.append({
                        'feature_name': row['feature_name'],
                        'feature_description': row['feature_description']
                    })
                
                # Process batch using the batch classifier
                batch_results = self.classifier.classify_features_batch(features_batch, batch_size)
                
                # Add metadata to each result
                for i, result in enumerate(batch_results):
                    row = batch_df.iloc[i]
                    result.update({
                        'input_feature_name': row['feature_name'],
                        'input_feature_description': row['feature_description'],
                        'processed_at': pd.Timestamp.now().isoformat()
                    })
                
                all_results.extend(batch_results)
                print(f"    ✅ Batch {batch_num + 1} completed successfully!")
                
                # Rate limiting between batches
                if batch_num < total_batches - 1:  # Don't delay after last batch
                    print(f"    ⏳ Waiting {self.delay}s before next batch...")
                    time.sleep(self.delay)
                    
            except Exception as e:
                error_msg = str(e)
                if "429" in error_msg or "quota" in error_msg.lower():
                    print(f"    ⚠️  Rate limit exceeded. Waiting extra time...")
                    time.sleep(10)  # Extra wait for rate limit errors
                    print(f"    ❌ Rate limit error for batch {batch_num + 1}: {error_msg[:100]}...")
                else:
                    print(f"    ❌ Error processing batch {batch_num + 1}: {error_msg[:100]}...")
                
                # Add error results for this batch
                for _, row in batch_df.iterrows():
                    all_results.append({
                        'input_feature_name': row['feature_name'],
                        'input_feature_description': row['feature_description'],
                        'classification': 'ERROR',
                        'reasoning': f'Batch processing error: {error_msg}',
                        'confidence': 0.0,
                        'related_regulations': [],
                        'original_feature_name': row['feature_name'],
                        'expanded_feature_name': row['feature_name'],
                        'processed_at': pd.Timestamp.now().isoformat()
                    })
        
        # Convert to DataFrame
        results_df = pd.DataFrame(all_results)
        
        # Calculate processing time
        end_time = time.time()
        processing_time = end_time - start_time
        print(f"⚡ Total processing time: {processing_time:.1f} seconds")
        if len(df) > 0:
            print(f"📊 Average time per feature: {processing_time/len(df):.2f} seconds")
            print(f"🚀 Speed improvement: ~{batch_size}x faster with batching!")
        
        # Save results if output file specified
        if output_file:
            results_df.to_csv(output_file, index=False)
            print(f"💾 Results saved to {output_file}")
        
        return results_df
        
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
    
    # Use batch processing for maximum efficiency!
    # With 5 features per batch, we reduce API calls from 30 to 6
    batch_classifier = BatchClassifier(delay_seconds=5.0)  # 5 seconds between batches for rate limits
    
    # Ensure outputs directory exists
    os.makedirs('outputs', exist_ok=True)
    
    # Check if the real sample data exists
    sample_data_path = 'data/sample_features.csv'
    if Path(sample_data_path).exists():
        print(f"🎯 Processing real TikTok sample data from {sample_data_path}")
        print(f"💡 Using batch processing: 5 features per API call for efficiency!")
        results_df = batch_classifier.process_csv(sample_data_path, 'outputs/sample_results.csv', batch_size=5)
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
        
        results_df = batch_classifier.process_csv('sample_features.csv', 'outputs/sample_results.csv', batch_size=3)
    
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
