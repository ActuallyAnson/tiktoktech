"""
Slack Bot Integration for TikTok Geo-Compliance Classification
Allows teams to classify features directly from Slack using slash commands.
"""

import os
import json
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from dotenv import load_dotenv
from src.processors.gemini_classifier import GeminiClassifier
from src.processors.text_preprocessor import expand_terminology
import pandas as pd
from datetime import datetime

# Load environment variables
load_dotenv()

# Initialize Slack app
app = App(token=os.environ.get("SLACK_BOT_TOKEN"))

# Initialize classifier
classifier = GeminiClassifier()

@app.command("/classify")
def classify_feature_command(ack, respond, command):
    """
    Slash command to classify a single feature.
    Usage: /classify feature_name | feature_description
    """
    ack()
    
    try:
        # Parse the command text
        text = command['text'].strip()
        if '|' not in text:
            respond({
                "text": "❌ Please use format: `/classify feature_name | feature_description`",
                "response_type": "ephemeral"
            })
            return
        
        feature_name, feature_description = text.split('|', 1)
        feature_name = feature_name.strip()
        feature_description = feature_description.strip()
        
        if not feature_name or not feature_description:
            respond({
                "text": "❌ Both feature name and description are required",
                "response_type": "ephemeral"
            })
            return
        
        # Show processing message
        respond({
            "text": f"🔍 Classifying feature: *{feature_name}*...",
            "response_type": "ephemeral"
        })
        
        # Classify the feature
        result = classifier.classify_feature(feature_name, feature_description)
        
        # Format the response
        if 'Error!' in result:
            respond({
                "text": f"❌ Error classifying feature: {result['Error!']}",
                "response_type": "ephemeral"
            })
        else:
            classification = result.get('classification', 'UNKNOWN')
            confidence = result.get('confidence', 0)
            reasoning = result.get('reasoning', 'No reasoning provided')
            regulations = result.get('related_regulations', [])
            
            # Choose emoji based on classification
            emoji = {
                'REQUIRED': '🔴',
                'NOT REQUIRED': '✅', 
                'NEEDS HUMAN REVIEW': '🟡'
            }.get(classification, '❓')
            
            blocks = [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"{emoji} Compliance Classification"
                    }
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*Feature:* {feature_name}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Classification:* {classification}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Confidence:* {confidence:.1%}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Regulations:* {', '.join(regulations) if regulations else 'None'}"
                        }
                    ]
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Reasoning:*\n{reasoning}"
                    }
                }
            ]
            
            respond({
                "text": f"📊 Classification Result for {feature_name}",
                "blocks": blocks,
                "response_type": "in_channel"  # Make it visible to everyone
            })
            
    except Exception as e:
        respond({
            "text": f"❌ Unexpected error: {str(e)}",
            "response_type": "ephemeral"
        })

@app.command("/classify-batch")
def classify_batch_command(ack, respond, command):
    """
    Slash command to classify multiple features from text.
    Usage: /classify-batch feature1|desc1;feature2|desc2;...
    """
    ack()
    
    try:
        text = command['text'].strip()
        if not text:
            respond({
                "text": "❌ Please provide features in format: `feature1|desc1;feature2|desc2;...`",
                "response_type": "ephemeral"
            })
            return
        
        # Parse multiple features
        feature_pairs = text.split(';')
        features_batch = []
        
        for pair in feature_pairs:
            if '|' not in pair:
                continue
            name, desc = pair.split('|', 1)
            features_batch.append({
                'feature_name': name.strip(),
                'feature_description': desc.strip()
            })
        
        if not features_batch:
            respond({
                "text": "❌ No valid features found. Use format: `feature1|desc1;feature2|desc2;...`",
                "response_type": "ephemeral"
            })
            return
        
        # Show processing message
        respond({
            "text": f"🔍 Processing {len(features_batch)} features...",
            "response_type": "ephemeral"
        })
        
        # Classify batch
        results = classifier.classify_features_batch(features_batch)
        
        # Format results
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"📊 Batch Classification Results ({len(results)} features)"
                }
            }
        ]
        
        # Summary
        required_count = sum(1 for r in results if r.get('classification') == 'REQUIRED')
        not_required_count = sum(1 for r in results if r.get('classification') == 'NOT REQUIRED')
        review_count = sum(1 for r in results if r.get('classification') == 'NEEDS HUMAN REVIEW')
        
        blocks.append({
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": f"🔴 *Required:* {required_count}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"✅ *Not Required:* {not_required_count}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"🟡 *Needs Review:* {review_count}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"📈 *Total:* {len(results)}"
                }
            ]
        })
        
        blocks.append({"type": "divider"})
        
        # Individual results (limit to 10 for readability)
        for i, result in enumerate(results[:10]):
            emoji = {
                'REQUIRED': '🔴',
                'NOT REQUIRED': '✅', 
                'NEEDS HUMAN REVIEW': '🟡'
            }.get(result.get('classification'), '❓')
            
            feature_name = result.get('original_feature_name', f'Feature {i+1}')
            classification = result.get('classification', 'UNKNOWN')
            confidence = result.get('confidence', 0)
            
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"{emoji} *{feature_name}*\n*{classification}* ({confidence:.1%} confidence)"
                }
            })
        
        if len(results) > 10:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"_... and {len(results) - 10} more features_"
                }
            })
        
        respond({
            "text": f"📊 Batch Classification Results ({len(results)} features)",
            "blocks": blocks,
            "response_type": "in_channel"
        })
        
    except Exception as e:
        respond({
            "text": f"❌ Batch processing error: {str(e)}",
            "response_type": "ephemeral"
        })

@app.event("file_shared")
def handle_file_upload(event, say, client):
    """
    Handle CSV file uploads and process them through batch classifier.
    """
    try:
        file_id = event["file_id"]
        
        # Get file info
        file_info = client.files_info(file=file_id)
        file_data = file_info["file"]
        
        # Check if it's a CSV file
        if not (file_data["filetype"] == "csv" or file_data["name"].endswith('.csv')):
            say(f"❌ Please upload a CSV file. Received: {file_data['name']}")
            return
        
        # Download the file
        file_content = client.files_info(file=file_id, token=os.environ.get("SLACK_BOT_TOKEN"))
        file_url = file_content["file"]["url_private"]
        
        # Send processing message
        say(f"🔍 Processing CSV file: *{file_data['name']}*...")
        say("⏳ This may take a few minutes depending on file size...")
        
        # Download and save the file temporarily
        import requests
        headers = {"Authorization": f"Bearer {os.environ.get('SLACK_BOT_TOKEN')}"}
        response = requests.get(file_url, headers=headers)
        
        if response.status_code != 200:
            say("❌ Failed to download file from Slack")
            return
        
        # Save temporarily
        temp_file_path = f"temp_{file_data['name']}"
        with open(temp_file_path, 'wb') as f:
            f.write(response.content)
        
        # Process with batch classifier
        from batch_classifier import BatchClassifier
        
        batch_classifier = BatchClassifier(delay_seconds=5.0)
        results_df = batch_classifier.process_csv(
            temp_file_path, 
            f"outputs/slack_{datetime.now().strftime('%Y%m%d_%H%M%S')}_results.csv",
            batch_size=5
        )
        
        # Generate summary
        summary = batch_classifier.generate_summary_report(results_df)
        
        # Create summary blocks for Slack
        total = summary['total_features']
        breakdown = summary['classification_breakdown']
        confidence_stats = summary['confidence_statistics']
        
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"🎯 Compliance Classification Results"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*File:* {file_data['name']}\n*Total Features:* {total}"
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"🔴 *Required:* {breakdown.get('REQUIRED', 0)}"
                    },
                    {
                        "type": "mrkdwn", 
                        "text": f"✅ *Not Required:* {breakdown.get('NOT REQUIRED', 0)}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"🟡 *Needs Review:* {breakdown.get('NEEDS HUMAN REVIEW', 0)}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"📊 *Avg Confidence:* {confidence_stats['mean_confidence']:.1%}"
                    }
                ]
            }
        ]
        
        # Add top required features
        required_features = results_df[results_df['classification'] == 'REQUIRED'].head(5)
        if len(required_features) > 0:
            required_text = "\n".join([
                f"• {row['input_feature_name'][:50]}..." 
                for _, row in required_features.iterrows()
            ])
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*🔴 Top Required Features:*\n{required_text}"
                }
            })
        
        # Send results with text fallback
        say(
            text=f"🎯 Compliance Classification Results for {file_data['name']}",
            blocks=blocks
        )
        
        # Upload detailed results file back to Slack
        # Use the same timestamp from when we created the output file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f"outputs/slack_{timestamp}_results.csv"
        
        # Try to find the actual output file that was created
        import glob
        output_files = glob.glob("outputs/slack_*_results.csv")
        if output_files:
            # Use the most recent file
            output_file = max(output_files, key=os.path.getctime)
        
        if os.path.exists(output_file):
            try:
                # Get the channel where the file was shared
                channel_id = file_data.get("channels", [None])[0] if file_data.get("channels") else None
                if not channel_id:
                    # Try to get from the file event
                    channel_id = event.get("channel_id")
                
                response = client.files_upload_v2(
                    channel=channel_id,
                    file=output_file,
                    title=f"Detailed Results - {file_data['name']}",
                    initial_comment="📋 Here are the detailed classification results!"
                )
                say(f"✅ Detailed results uploaded: {os.path.basename(output_file)}")
            except Exception as upload_error:
                say(f"⚠️ Results processed but file upload failed: {str(upload_error)}")
                say(f"📁 Results saved locally as: {output_file}")
                # Try alternative upload method
                try:
                    with open(output_file, 'rb') as file_content:
                        client.files_upload(
                            channels=file_data.get("channels", [None])[0] if file_data.get("channels") else None,
                            file=file_content,
                            filename=os.path.basename(output_file),
                            title=f"Detailed Results - {file_data['name']}",
                            initial_comment="📋 Detailed classification results (alternative upload)"
                        )
                    say("✅ File uploaded using alternative method!")
                except Exception as alt_error:
                    say(f"❌ Both upload methods failed: {str(alt_error)}")
        else:
            say(f"⚠️ Results processed but output file not found: {output_file}")
        
        # Clean up temp file
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
            
    except Exception as e:
        say(f"❌ Error processing file: {str(e)}")
        # Clean up temp file on error
        temp_file_path = f"temp_{event.get('file', {}).get('name', 'unknown')}"
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)

@app.command("/compliance-help")
def help_command(ack, respond):
    """Show help for compliance classification commands."""
    ack()
    
    help_text = """
🤖 *TikTok Geo-Compliance Classifier*

*Available Commands:*

• `/classify feature_name | feature_description`
  Classify a single feature for geo-compliance requirements

• `/classify-batch feature1|desc1;feature2|desc2;...`
  Classify multiple features at once

• `/compliance-help`
  Show this help message

*📁 File Upload Processing:*
• **Drop a CSV file** into this channel with columns:
  - `feature_name` (name of the feature)
  - `feature_description` (what it does)
• The bot will automatically process it and return:
  - Summary statistics
  - Detailed results file
  - Top required features

*Example CSV format:*
```
feature_name,feature_description
Age verification,Enhanced age verification for COPPA compliance
Chat limits,Restrict chat features for underage users
Bug fix,Fixed memory leak in video processing
```

*Single Feature Example:*
```
/classify Age verification | Enhanced age verification system for COPPA compliance
```

*Batch Example:*
```
/classify-batch ASL for EU|Age logic for GDPR;Bug fix|Memory leak fix;Chat limits|Restrict chat for minors
```

*Classifications:*
🔴 *REQUIRED* - Needs geo-specific compliance logic
✅ *NOT REQUIRED* - General feature, no geo-compliance needed  
🟡 *NEEDS HUMAN REVIEW* - Ambiguous, requires manual review

*Supported Regulations:*
• EU Digital Services Act (DSA)
• California SB976
• Florida HB 3  
• Utah Social Media Regulation Act
• US NCMEC reporting requirements
"""
    
    respond({
        "text": help_text,
        "response_type": "ephemeral"
    })

# Event listener for app mentions
@app.event("app_mention")
def handle_app_mention(event, say):
    """Handle when the bot is mentioned in a channel."""
    text = event.get('text', '').lower()
    
    if 'classify' in text:
        say({
            "text": "👋 I can help classify TikTok features for geo-compliance! Use `/classify feature_name | description` or `/compliance-help` for more info.",
            "thread_ts": event.get('ts')
        })
    else:
        say({
            "text": "👋 Hi! I'm the TikTok Geo-Compliance Classifier. Use `/compliance-help` to see what I can do!",
            "thread_ts": event.get('ts')
        })

if __name__ == "__main__":
    # Start the app
    handler = SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"])
    print("🚀 TikTok Compliance Slack Bot is starting...")
    handler.start()
