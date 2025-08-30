"""
Test script for GeminiClassifier to validate geo-compliance detection.
"""

from src.processors.gemini_classifier import GeminiClassifier
import json

def test_classifier():
    """Test the classifier with various scenarios"""
    
    classifier = GeminiClassifier()
    
    # Test cases: (feature_name, feature_description, expected_result)
    test_cases = [
        # Clear compliance cases
        ("ASL for EU", "Age-sensitive logic implementation for European Union GDPR compliance", "REQUIRED"),
        ("China content filter", "Content filtering system specifically for Chinese regulatory requirements", "REQUIRED"),
        ("COPPA update", "Children's Online Privacy Protection Act compliance update for US users", "REQUIRED"),
        
        # Clear non-compliance cases  
        ("Bug fix", "Fixed memory leak in video processing pipeline", "NOT REQUIRED"),
        ("Performance optimization", "Improved video loading speed by 20%", "NOT REQUIRED"),
        ("UI update", "Updated button colors for better user experience", "NOT REQUIRED"),
        ("PF algorithm", "Updated personalized feed algorithm", "NOT REQUIRED"),
        
        # Edge cases - ambiguous (should trigger human review)
        ("Age verification", "Enhanced age verification system", "NEEDS HUMAN REVIEW"), 
        ("Location services", "Improved location-based features", "NEEDS HUMAN REVIEW"),
    ]
    
    print("🧪 Testing GeminiClassifier...")
    print("=" * 50)
    
    results = []
    
    for i, (name, desc, expected) in enumerate(test_cases, 1):
        print(f"\n📋 Test {i}: {name}")
        print(f"Description: {desc}")
        print(f"Expected: {expected}")
        
        try:
            result = classifier.classify_feature(name, desc)
            
            # Extract key info
            classification = result.get('classification', 'UNKNOWN')
            confidence = result.get('confidence', 0.0)
            reasoning = result.get('reasoning', 'No reasoning provided')
            
            print(f"Result: {classification} (confidence: {confidence})")
            print(f"Reasoning: {reasoning[:100]}...")
            
            # Check if it matches expectation
            match = "MATCH" if classification == expected else "DIFFERENT"
            print(f"{match}")
            
            results.append({
                'test_name': name,
                'expected': expected,
                'actual': classification,
                'confidence': confidence,
                'match': classification == expected
            })
            
        except Exception as e:
            print(f"ERROR: {str(e)}")
            results.append({
                'test_name': name,
                'expected': expected,
                'actual': 'ERROR',
                'confidence': 0.0,
                'match': False
            })
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY")
    print("=" * 50)
    
    total_tests = len(results)
    matches = sum(1 for r in results if r['match'])
    
    print(f"Total tests: {total_tests}")
    print(f"Correct classifications: {matches}")
    print(f"Accuracy: {matches/total_tests*100:.1f}%")
    
    print("\n📈 Detailed Results:")
    for result in results:
        status = "✅" if result['match'] else "❌"
        print(f"{status} {result['test_name']}: {result['expected']} → {result['actual']} ({result['confidence']})")
    
    return results

if __name__ == "__main__":
    test_results = test_classifier()
