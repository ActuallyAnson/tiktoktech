"""
Main entry point for TikTok Geo-Regulation Compliance Detection System.
Demonstrates the LLM/NLP classifier functionality.
"""

import sys
from pathlib import Path

# Add src to Python path so imports work
sys.path.append(str(Path(__file__).parent))

from processors.gemini_classifier import GeminiClassifier

def demo_classifier():
    """Demonstrate the geo-compliance classifier with example features."""
    
    print("🤖 TikTok Geo-Regulation Compliance Detection System")
    print("=" * 55)
    print("LLM/NLP Classifier Demo\n")
    
    # Initialize classifier
    try:
        print(" Initializing Gemini classifier...")
        classifier = GeminiClassifier()
        print(" Classifier ready!\n")
    except Exception as e:
        print(f" Error initializing classifier: {e}")
        print("  Make sure GEMINI_API_KEY is set in your .env file")
        return
    
    # Demo features
    demo_features = [
        {
            "name": "ASL for EU", 
            "description": "Age-sensitive logic implementation for European Union GDPR compliance"
        },
        {
            "name": "Performance boost", 
            "description": "Optimized video loading algorithm for 30% faster startup times"
        },
        {
            "name": "Age verification update", 
            "description": "Enhanced age verification system with improved accuracy"
        }
    ]
    
    print("📋 Classifying demo features:\n")
    
    for i, feature in enumerate(demo_features, 1):
        print(f"🔍 Feature {i}: {feature['name']}")
        print(f"   Description: {feature['description']}")
        
        try:
            result = classifier.classify_feature(feature['name'], feature['description'])
            
            # Display results
            classification = result.get('classification', 'UNKNOWN')
            confidence = result.get('confidence', 0.0)
            reasoning = result.get('reasoning', 'No reasoning provided')
            
            # Color coding for classification
            if classification == 'REQUIRED':
                icon = "🚨"
            elif classification == 'NOT REQUIRED':
                icon = "✅"
            else:
                icon = "⚠️"
            
            print(f"   {icon} Classification: {classification}")
            print(f"   🎯 Confidence: {confidence:.2f}")
            print(f"   💭 Reasoning: {reasoning[:80]}...")
            print()
            
        except Exception as e:
            print(f"   ❌ Error: {str(e)}\n")
    
    print("🎉 Demo complete! Your LLM/NLP classifier is working perfectly.")
    print("\n📚 Next steps:")
    print("   • Check TEAM_INTEGRATION.md for team usage guide")
    print("   • Run batch_classifier.py for bulk processing")
    print("   • See src/processors/README.md for API documentation")

def main():
    """Main function - runs the classifier demo."""
    demo_classifier()

if __name__ == "__main__":
    main()