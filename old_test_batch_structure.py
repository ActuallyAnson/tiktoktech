#!/usr/bin/env python3
"""
Test script to verify batch processing structure without making API calls.
This will help verify the batching logic is correct before using a real API key.
"""

import pandas as pd
from pathlib import Path

def test_batch_structure():
    """Test that the batch processing divides features correctly."""
    
    # Load the sample data
    sample_data_path = 'data/sample_features.csv'
    if not Path(sample_data_path).exists():
        print(f"❌ Sample data not found at {sample_data_path}")
        return
    
    df = pd.read_csv(sample_data_path)
    print(f"📊 Loaded {len(df)} features from {sample_data_path}")
    
    # Test batch division logic
    batch_size = 5
    total_batches = (len(df) + batch_size - 1) // batch_size  # Ceiling division
    
    print(f"\n🔍 Batch Processing Structure:")
    print(f"  Total features: {len(df)}")
    print(f"  Batch size: {batch_size}")
    print(f"  Total batches needed: {total_batches}")
    print(f"  API calls needed: {total_batches} (vs {len(df)} without batching)")
    print(f"  Efficiency gain: {len(df) / total_batches:.1f}x reduction in API calls")
    
    print(f"\n📦 Batch Breakdown:")
    for batch_num in range(total_batches):
        start_idx = batch_num * batch_size
        end_idx = min(start_idx + batch_size, len(df))
        batch_df = df.iloc[start_idx:end_idx]
        
        print(f"  Batch {batch_num + 1}: Features {start_idx + 1}-{end_idx} ({len(batch_df)} features)")
        for i, row in batch_df.iterrows():
            print(f"    - {row['feature_name'][:50]}...")
    
    # Test prompt structure
    print(f"\n🤖 Sample Batch Prompt Structure:")
    batch_num = 0
    start_idx = batch_num * batch_size
    end_idx = min(start_idx + batch_size, len(df))
    batch_df = df.iloc[start_idx:end_idx]
    
    print("Features to analyze:")
    for idx, (i, row) in enumerate(batch_df.iterrows()):
        feature_index = idx  # 0-based within batch
        print(f"""
Feature {feature_index}:
Name: {row['feature_name']}
Description: {row['feature_description'][:100]}...
""")
    
    print("✅ Batch structure test completed!")

if __name__ == "__main__":
    test_batch_structure()
