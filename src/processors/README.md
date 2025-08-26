# TikTok Geo-Compliance Classifier

## Quick Start

```python
from src.processors.gemini_classifier import GeminiClassifier

# Initialize classifier
classifier = GeminiClassifier()

# Classify a feature
result = classifier.classify_feature(
    feature_name="ASL for EU",
    feature_description="Age-sensitive logic implementation for European Union GDPR compliance"
)

print(result)
# Output:
# {
#   "classification": "REQUIRED",
#   "reasoning": "Feature explicitly mentions GDPR compliance...",
#   "confidence": 0.98,
#   "related_regulations": ["European Union GDPR compliance"],
#   "original_feature_name": "ASL for EU",
#   "expanded_feature_name": "Age-sensitive logic for EU"
# }
```

## API Reference

### `GeminiClassifier.classify_feature(feature_name, feature_description)`

**Parameters:**
- `feature_name` (str): Short name of the feature (e.g., "ASL for EU")
- `feature_description` (str): Detailed description of what the feature does

**Returns:** Dictionary with the following fields:
- `classification`: "REQUIRED" | "NOT REQUIRED" | "NEEDS HUMAN REVIEW"
- `reasoning`: Explanation of the decision
- `confidence`: Float between 0.0-1.0 
- `related_regulations`: List of mentioned laws/regulations
- `original_feature_name`: Input name as provided
- `expanded_feature_name`: Name with abbreviations expanded

## Classification Logic

### REQUIRED
Features that mention specific laws/regulations for specific regions:
- ✅ "GDPR compliance for EU users"
- ✅ "COPPA implementation for US"
- ✅ "Chinese regulatory requirements"

### NOT REQUIRED  
Universal technical features with no legal context:
- ✅ "Bug fixes and performance improvements"
- ✅ "UI updates for better UX"
- ✅ "Algorithm optimization"

### NEEDS HUMAN REVIEW
Ambiguous cases where intent is unclear:
- ⚠️ "Enhanced age verification" (could be legal or business)
- ⚠️ "Location-based features" (privacy implications)
- ⚠️ "Content moderation updates" (could be regional)

## Integration Examples

### For Data Engineers
```python
import pandas as pd

# Process a CSV of features
df = pd.read_csv('features.csv')
results = []

for _, row in df.iterrows():
    result = classifier.classify_feature(row['name'], row['description'])
    results.append(result)

# Save results
pd.DataFrame(results).to_csv('classification_results.csv')
```

### For Backend Developers
```python
# API endpoint example
@app.post("/classify-feature")
async def classify_feature(request: FeatureRequest):
    try:
        result = classifier.classify_feature(
            request.feature_name, 
            request.feature_description
        )
        return {"success": True, "data": result}
    except Exception as e:
        return {"success": False, "error": str(e)}
```

### For Analysts
```python
# Filter high-confidence results
high_confidence = [r for r in results if r['confidence'] > 0.9]

# Get human review cases
needs_review = [r for r in results if r['classification'] == 'NEEDS HUMAN REVIEW']

# Compliance features by region
compliance_features = [r for r in results if r['classification'] == 'REQUIRED']
```

## Setup Requirements

1. **Environment Variables:**
   ```bash
   GEMINI_API_KEY=your_api_key_here
   ```

2. **Dependencies:**
   ```bash
   pip install google-generativeai python-dotenv pandas
   ```

3. **Data Files:**
   - `data/terminology.json` - TikTok abbreviation mappings

## Performance Notes

- **Confidence Scores:** 0.9+ = Very reliable, 0.8-0.9 = Good, <0.8 = Review recommended
- **Rate Limits:** Gemini API has rate limits - implement backoff for batch processing
- **Cost:** ~$0.001 per classification (varies by description length)

## Troubleshooting

**Common Issues:**
- `GEMINI_API_KEY not found`: Check your `.env` file
- `JSON parse errors`: Raw response available in error cases
- `Rate limit errors`: Add delays between API calls

**Error Handling:**
The classifier returns error information in the response:
```python
{
  "classification": "PARSE_ERROR",
  "reasoning": "Could not parse JSON: ...",
  "raw_response": "Original Gemini response text"
}
```
