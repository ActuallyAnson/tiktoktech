# Slack Integration Setup Guide

## 🎯 What This Does

Drop a CSV file into Slack → Bot processes it with your batch classifier → Get results back in Slack!

## 📋 Prerequisites

1. Python environment with dependencies installed
2. Gemini API key (already configured)
3. Slack workspace admin access

## 🔧 Setup Steps

### 1. Create Slack App

1. Go to https://api.slack.com/apps
2. Click "Create New App" → "From scratch"
3. Name: "TikTok Compliance Classifier"
4. Choose your workspace

### 2. Configure Bot Permissions

In your app settings, go to **OAuth & Permissions** and add these Bot Token Scopes:

**Required Scopes:**
- `app_mentions:read` - Listen to mentions
- `channels:history` - Read messages in channels
- `chat:write` - Send messages
- `commands` - Use slash commands
- `files:read` - Download uploaded files
- `files:write` - Upload result files

### 3. Enable Socket Mode

1. Go to **Socket Mode** in your app settings
2. Enable Socket Mode
3. Create an App-Level Token with `connections:write` scope
4. Copy the `xapp-` token

### 4. Create Bot Token

1. Go to **OAuth & Permissions**
2. Install app to your workspace
3. Copy the Bot User OAuth Token (`xoxb-` token)

### 5. Add Slash Commands

Go to **Slash Commands** and create these:

**Command: `/classify`**
- Request URL: Not needed (using Socket Mode)
- Short Description: "Classify a single feature for geo-compliance"
- Usage Hint: `feature_name | feature_description`

**Command: `/classify-batch`**
- Request URL: Not needed (using Socket Mode)
- Short Description: "Classify multiple features at once"
- Usage Hint: `feature1|desc1;feature2|desc2`

**Command: `/compliance-help`**
- Request URL: Not needed (using Socket Mode)
- Short Description: "Show help for compliance classifier"

### 6. Enable Events

1. Go to **Event Subscriptions**
2. Enable Events
3. Subscribe to these Bot Events:
   - `app_mention` - When bot is mentioned
   - `file_shared` - When files are uploaded

### 7. Update Environment Variables

Add to your `.env` file:
```bash
SLACK_BOT_TOKEN=xoxb-your-bot-token-here
SLACK_APP_TOKEN=xapp-your-app-token-here
```

## 🚀 Running the Bot

```bash
cd /path/to/tiktoktech
source venv/bin/activate
python slack_bot.py
```

You should see:
```
⚡️ Bolt app is running! (Socket Mode)
```

## 📁 How to Use

### Option 1: File Upload (Recommended)
1. **Drag and drop** a CSV file into any channel where the bot is present
2. CSV must have columns: `feature_name`, `feature_description`
3. Bot automatically processes and returns:
   - Summary statistics
   - Detailed results CSV file
   - Top required features

### Option 2: Slash Commands
```
/classify Age verification | Enhanced age verification for COPPA compliance
```

```
/classify-batch ASL for EU|Age logic for GDPR;Bug fix|Memory leak fix
```

### Option 3: Help
```
/compliance-help
```

## 📊 Example CSV Format

```csv
feature_name,feature_description
Curfew login blocker with ASL and GH for Utah minors,To comply with the Utah Social Media Regulation Act we are implementing a curfew-based login restriction
PF default toggle with NR enforcement for California teens,As part of compliance with California's SB976 the app will disable PF by default for users under 18
Chat UI overhaul,A new chat layout will be tested in multiple regions
```

## 🔍 What You Get Back

**Summary Message:**
- 🔴 Required: X features
- ✅ Not Required: Y features  
- 🟡 Needs Review: Z features
- 📊 Average Confidence: XX%

**Detailed CSV File:**
- Full classification results
- Confidence scores
- Related regulations
- Detailed reasoning

## 🛠 Troubleshooting

**Bot not responding to file uploads:**
- Check bot has `files:read` permission
- Ensure file is actually a CSV
- Check console for error messages

**Slash commands not working:**
- Verify commands are created in Slack app settings
- Check bot has `commands` scope
- Restart the bot after changes

**"Failed to download file":**
- Check `SLACK_BOT_TOKEN` is correct
- Ensure bot has file access permissions

## 🚀 Production Deployment

For production use:
1. Deploy to a server (not your local machine)
2. Use proper secrets management
3. Add error logging and monitoring
4. Consider rate limiting for large files

## 🎉 Ready to Go!

Your Slack integration is now ready to process TikTok compliance classifications! Just drop a CSV file and watch the magic happen! ✨
