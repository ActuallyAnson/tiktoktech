"""
Batch processor for classifying multiple features at once.
For Data Engineers processing large datasets.
"""

import os
import pandas as pd
import json
import time
import hashlib
import zipfile
from web3 import Web3
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from src.processors.gemini_classifier import GeminiClassifier

class BatchClassifier:
    def __init__(self, delay_seconds: float = 1.0):
        """Initialize batch classifier with rate limiting."""
        self.classifier = GeminiClassifier()
        self.delay = delay_seconds  # Delay between API calls to avoid rate limits
        
    def process_csv(self, input_file: str, batch_size: int = 5) -> pd.DataFrame:
        """
        Process features from CSV file using batch processing for efficiency.
        
        Args:
            input_file: Path to input CSV with columns 'feature_name', 'feature_description'
            output_dir: Optional directory to save results CSV
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
                        'feature_description': row['feature_description'],
                        'processed_at': pd.Timestamp.now().isoformat()
                    })
                
                # Process batch using the batch classifier
                batch_results = self.classifier.classify_features_batch(features_batch, batch_size)
                
                # Add metadata to each result
                for i, result in enumerate(batch_results):
                    row = batch_df.iloc[i]
                    result.update({
                        'input_feature_name': row['feature_name'],
                        'input_feature_description': row['feature_description'],
                        'processed_at': row.get('processed_at', pd.Timestamp.now().isoformat())
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
                        'classification': 'ERROR',
                        'reasoning': f'Batch processing error: {error_msg}',
                        'confidence': 0.0,
                        'related_regulations': [],
                        'input_feature_name': row['feature_name'],
                        'input_feature_description': row['feature_description'],
                        'expanded_feature_name': '',
                        'expanded_feature_description': '',
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

        return results_df

    def generate_report(self, results_df: pd.DataFrame, output_dir: str) -> bool:
        """
        Generate a comprehensive report with error handling.
        Args:
            results_df (pd.DataFrame): The DataFrame containing the results to report.
            output_dir (str): The directory where the report files will be saved.

        Returns: 
            bool: True if the report was created successfully, False otherwise.
        """
        try:
            # Validate inputs
            if results_df.empty:
                return False
            
            if not isinstance(results_df, pd.DataFrame):
                return False

            # Create output directory with error handling
            try:
                os.makedirs(output_dir, exist_ok=True)
                if not os.path.isdir(output_dir):
                    return False
            except (OSError, PermissionError) as e:
                return False

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Create CSV report
            report_filename = f"report_{timestamp}_data.csv"
            report_path = os.path.join(output_dir, report_filename)
            try:
                results_df.to_csv(report_path, index=False)
                if not os.path.exists(report_path) or os.path.getsize(report_path) == 0:
                    return False
            except (IOError, PermissionError) as e:
                return False

            # Create summary
            try:
                summary = self.generate_summary_report(results_df)
                if not summary:
                    return False
            except Exception as e:
                return False

            # Save summary JSON
            summary_filename = f"report_{timestamp}_summary.json"
            summary_path = os.path.join(output_dir, summary_filename)
            try:
                with open(summary_path, 'w') as f:
                    json.dump(summary, f, indent=2)
                if not os.path.exists(summary_path) or os.path.getsize(summary_path) == 0:
                    return False
            except (IOError, PermissionError, TypeError) as e:
                return False

            # Create zip archive
            zip_filename = f"report_{timestamp}.zip"
            zip_path = os.path.join(output_dir, zip_filename)
            try:
                with zipfile.ZipFile(zip_path, 'w') as zipf:
                    zipf.write(report_path, arcname=report_filename)
                    zipf.write(summary_path, arcname=summary_filename)
                
                if not os.path.exists(zip_path) or os.path.getsize(zip_path) == 0:
                    return False
            except (zipfile.BadZipFile, IOError, PermissionError) as e:
                return False

            # Create hash file
            hash_filename = f"report_{timestamp}_hash.txt"
            hash_path = os.path.join(output_dir, hash_filename)
            try:
                hash_value = self.hash_file(zip_path)
                if not hash_value:
                    return False

                with open(hash_path, 'w') as f:
                    f.write("Hash: " + hash_value + "\n")
                
                if not os.path.exists(hash_path) or os.path.getsize(hash_path) == 0:
                    return False
                
            except Exception as e:
                return False

            # Clean up temporary files
            try:
                os.remove(report_path)
                os.remove(summary_path)
            except OSError:
                # Non-critical if temp files can't be removed
                pass

            # Print summary
            print("\nBATCH PROCESSING SUMMARY")
            print("=" * 40)
            print(f"Total features processed: {summary.get('total_features', 'N/A')}")
            print(f"Classification breakdown: {summary.get('classification_breakdown', 'N/A')}")
            print(f"High confidence classifications: {summary.get('high_confidence_count', 'N/A')}")
            print(f"Needs human review: {summary.get('needs_human_review_count', 'N/A')}")

            print(f"📊 Report saved to {zip_path}")
            print(f"💾 Hash saved to {hash_path}")

            tx_id = self.log_on_chain(hash_value)
            if tx_id != '':
                with open(hash_path, 'a') as f:
                    f.write(f"Transaction ID: {tx_id}\n")
                    f.write(f"View on Etherscan: https://sepolia.etherscan.io/tx/{tx_id}\n")

            return True

        except Exception as e:
            return False

    def log_on_chain(self, hash_value: str) -> str:
        """
        Log the hash value on the Ethereum Sepolia Testnet by 
        sending a self transaction with the hash in the data field
        Args:
            hash_value: The hash value to log
        Return:
            The transaction ID if successful, empty string otherwise
        """
        api_key = os.environ['SEPOLIA_API_KEY']
        provider = os.environ['SEPOLIA_API_PROVIDER'].lower()
        private_key = os.environ['ETH_PRIVATE_KEY'] 

        if api_key == 'your_sepolia_api_key_here' or private_key == 'your_ethereum_private_key_here':
            api_key = ''
            private_key = ''

        if (api_key and provider and private_key):
            match provider:
                case 'alchemy':
                    rpc_url = f"https://eth-sepolia.g.alchemy.com/v2/{api_key}"
                case 'infura':
                    rpc_url = f"https://sepolia.infura.io/v3/{api_key}"
                case 'quicknode':
                    rpc_url = f"https://aged-thrilling-theorem.ethereum-sepolia.quiknode.pro/{api_key}/"
                
            w3 = Web3(Web3.HTTPProvider(rpc_url))
            if not w3.is_connected():
                print("❌ Failed to connect to Ethereum network, check your API provider and key.\nSupported providers: alchemy, infura, quicknode")
                return ''

            acct = w3.eth.account.from_key(private_key)
            balance = w3.eth.get_balance(acct.address)
            balance_eth = w3.from_wei(balance, 'ether')

            data_bytes = len(hash_value) // 2  # Each hex pair = 1 byte
            gas_for_data = data_bytes * 16  # 16 gas per non-zero byte (assuming worst case)
            estimated_gas = 21000 + gas_for_data + 1000  # Base + data + buffer

            gas_price = w3.eth.gas_price
            estimated_cost = w3.from_wei(gas_price * estimated_gas, 'ether')
            
            if balance_eth < estimated_cost:
                print(f"Insufficient funds: {balance_eth} ETH (need ~{estimated_cost} ETH)")
                return False

            tx = {
                "to": acct.address,  # Self-send to embed data
                "value": 0,          
                "gas": estimated_gas,        
                "gasPrice": gas_price,
                "nonce": w3.eth.get_transaction_count(acct.address),
                "data": "0x" + hash_value  # Embed hash in transaction data
            }

            try:
                estimated_gas_web3 = w3.eth.estimate_gas(tx)
                tx["gas"] = estimated_gas_web3
                
                signed = acct.sign_transaction(tx)
                tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
                tx_hash_str = f"0x{tx_hash.hex()}"
                print(f"✅ Hash log transaction successful!")
                print(f"Transaction hash: {tx_hash_str}")
                print(f"View on Etherscan: https://sepolia.etherscan.io/tx/{tx_hash_str}")
                return tx_hash_str

            except Exception as e:
                print(f"❌ Hash log transaction failed: {e}")
                return ''
        else:
            print("🔒 Hash log transaction skipped (Missing required environment variables)")
            return ''

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

    def hash_file(self, filename, algorithm='sha256') -> str:
        """Generate a hash for a file."""
        hash_obj = hashlib.new(algorithm)
        with open(filename, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_obj.update(chunk)
        return hash_obj.hexdigest()

def main():
    """Example usage of batch classifier with real TikTok sample data."""
    
    # Use batch processing for maximum efficiency!
    # With 5 features per batch, we reduce API calls from 30 to 6
    batch_classifier = BatchClassifier(delay_seconds=5.0)  # 5 seconds between batches for rate limits

    batch_classifier.log_on_chain('')  # Test logging function (will skip if env vars missing)
    return

    # Check if the real sample data exists
    sample_data_path = 'data/sample_features.csv'
    if Path(sample_data_path).exists():
        print(f"🎯 Processing real TikTok sample data from {sample_data_path}")
        print(f"💡 Using batch processing: 5 features per API call for efficiency!")
        results_df = batch_classifier.process_csv(sample_data_path, batch_size=5)
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

        results_df = batch_classifier.process_csv('sample_features.csv', batch_size=3)

    if batch_classifier.generate_report(results_df, 'outputs'):
        print("📊 Report generated successfully!")
    else:
        print("❌ Failed to generate report.")

if __name__ == "__main__":
    main()
