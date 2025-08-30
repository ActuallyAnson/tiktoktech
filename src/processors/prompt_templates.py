"""
Prompt templates for Gemini geo-compliance classification.
Training documents for LLM
"""

"""
    Build a prompt for classifying a feature's geo-compliance requirements.
"""

def build_classification_prompt(feature_name: str, feature_description: str,context: str) -> str:

    
    system_instructions = """
    
System:
You are an expert assistant. You must answer questions **only using the context provided**. 
Do not generate information from your training data, prior knowledge, or the internet. 
If the answer is not in the context, respond with "I don’t know" or "Not enough information in context".
    
You are analyzing TikTok features for geo-compliance requirements.

Your task: Determine if a feature requires geo-specific compliance logic.

Classification rules:
REQUIRED: Feature mentions specific laws/regulations for specific regions
NOT REQUIRED: Universal features or business-only geo-targeting  
NEEDS HUMAN REVIEW: Ambiguous cases where intent is unclear

Key indicators for REQUIRED:
- Explicit law names:
  * EU Digital Service Act (DSA)
  * California's "Protecting Our Kids from Social Media Addiction Act"
  * Florida's "Online Protections for Minors"
  * Utah Social Media Regulation Act
  * US NCMEC reporting requirements for child safety content
- Compliance language ("To comply with", "In line with federal law")
- Region-specific legal requirements
- Age-related restrictions for minors
- Content moderation for child safety

Key indicators for NOT REQUIRED:
- Universal features ("all regions", "platform-wide")
- Business testing ("trial run", "experimentation")
- No legal context
"""

    few_shot_examples = """
Examples:

Example 1:
Feature: "Curfew login blocker with Age-sensitive logic and Geo-handler for Utah minors"
Description: "To comply with the Utah Social Media Regulation Act, we are implementing a curfew-based login restriction for users under 18..."
Classification: REQUIRED
Reasoning: Explicitly mentions compliance with Utah Social Media Regulation Act, specific regional law for minor protection
Confidence: 0.95

Example 2:
Feature: "California social media addiction warning system"
Description: "Implementing addiction warning notifications for California users under Protecting Our Kids from Social Media Addiction Act"
Classification: REQUIRED
Reasoning: Explicitly references California's Protecting Our Kids from Social Media Addiction Act, state-specific compliance requirement
Confidence: 0.95

Example 3:
Feature: "Florida minor content filtering"
Description: "Age verification and content filtering system for Florida users to comply with Online Protections for Minors law"
Classification: REQUIRED
Reasoning: Specifically mentions Florida's Online Protections for Minors law, state-specific minor protection requirement
Confidence: 0.95

Example 4:
Feature: "EU DSA content moderation reporting"
Description: "Automated reporting system for content moderation decisions to comply with EU Digital Service Act requirements"
Classification: REQUIRED
Reasoning: Explicitly mentions EU Digital Service Act (DSA) compliance, region-specific legal requirement
Confidence: 0.95

Example 5:
Feature: "NCMEC automated reporting system"
Description: "System to automatically report suspected child sexual abuse content to NCMEC as required by US law"
Classification: REQUIRED
Reasoning: Mentions NCMEC reporting requirements, specific US legal obligation for child safety
Confidence: 0.95

Example 6:
Feature: "Universal Personalized feed deactivation on guest mode"
Description: "By default, Personalized feed will be turned off for all users browsing in guest mode."
Classification: NOT REQUIRED
Reasoning: Universal feature with no legal requirements, business decision
Confidence: 0.9

Example 7:
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

    return system_instructions + few_shot_examples + new_feature + output_format + context
