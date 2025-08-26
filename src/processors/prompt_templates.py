"""
Prompt templates for Gemini geo-compliance classification.
Training documents for LLM
"""

"""
    Build a prompt for classifying a feature's geo-compliance requirements.
"""

def build_classification_prompt(feature_name: str, feature_description: str) -> str:

    
    system_instructions = """You are analyzing TikTok features for geo-compliance requirements.

Your task: Determine if a feature requires geo-specific compliance logic.

Classification rules:
REQUIRED: Feature mentions specific laws/regulations for specific regions
NOT REQUIRED: Universal features or business-only geo-targeting  
NEEDS HUMAN REVIEW: Ambiguous cases where intent is unclear

Key indicators for REQUIRED:
- Explicit law names (Utah Social Media Regulation Act, California SB976, EU DSA)
- Compliance language ("To comply with", "In line with federal law")
- Region-specific legal requirements

Key indicators for NOT REQUIRED:
- Universal features ("all regions", "platform-wide")
- Business testing ("trial run", "experimentation")
- No legal context"""

    few_shot_examples = """
Examples:

Example 1:
Feature: "Curfew login blocker with Age-sensitive logic and Geo-handler for Utah minors"
Description: "To comply with the Utah Social Media Regulation Act, we are implementing a curfew-based login restriction for users under 18..."
Classification: REQUIRED
Reasoning: Explicitly mentions compliance with Utah Social Media Regulation Act, specific regional law
Confidence: 0.95

Example 2:
Feature: "Universal Personalized feed deactivation on guest mode"
Description: "By default, Personalized feed will be turned off for all users browsing in guest mode."
Classification: NOT REQUIRED
Reasoning: Universal feature with no legal requirements, business decision
Confidence: 0.9

Example 3:
Feature: "Trial run of video replies in EU"
Description: "Roll out video reply functionality to users in EEA only. Geo-handler will manage exposure control, and Baseline Behavior is used to baseline feedback."
Classification: NOT REQUIRED
Reasoning: Business testing in EU region, no legal compliance mentioned
Confidence: 0.85
"""

    new_feature = f"""
Now classify this feature:

Feature: "{feature_name}"
Description: "{feature_description}"
"""

    output_format = """
Provide your response in this exact JSON format:
{
  "classification": "REQUIRED" | "NOT REQUIRED" | "NEEDS HUMAN REVIEW",
  "reasoning": "Clear explanation of your decision",
  "confidence": 0.0-1.0,
  "related_regulations": ["list of specific laws/regulations mentioned, if any"]
}"""

    return system_instructions + few_shot_examples + new_feature + output_format
