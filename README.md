# TikTok Geo-Regulation Compliance Detection System

## Overview

An automated system that utilizes LLM capabilities to flag features that require geo-specific compliance logic, turning regulatory detection from a blind spot into a traceable, auditable output.

## Problem Statement

As TikTok operates globally, every product feature must dynamically satisfy dozens of geographic regulations – from Brazil's data localization to GDPR. This system helps identify:

- Whether a feature requires dedicated logic to comply with region-specific legal obligations
- How many features have been rolled out to ensure compliance with specific regulations
- Automated visibility into compliance gaps before they become legal risks

## Key Features

- **Automated Compliance Detection**: Uses LLM to analyze feature descriptions and flag geo-compliance requirements
- **Regulation Mapping**: Maps features to specific regulations (EU DSA, California SB976, Florida Online Protections, Utah Social Media Act, US NCMEC reporting)
- **Audit Trail Generation**: Creates traceable evidence for regulatory inquiries
- **Multi-Agent Processing**: Self-evolving system with human feedback integration
- **Domain-Specific Knowledge**: Handles internal jargon and feature codenames

## Project Structure

```
tiktoktech/
├── src/
│   ├── agents/              # Multi-agent system components
│   ├── models/              # Data models and schemas
│   ├── processors/          # Feature analysis processors
│   ├── regulations/         # Regulation knowledge base
│   ├── utils/              # Utility functions
│   └── main.py             # Main application entry point
├── data/
│   ├── sample_features.csv  # Sample feature dataset
│   ├── regulations.json     # Regulation definitions
│   └── terminology.json    # Internal terminology mapping
├── outputs/
│   ├── compliance_reports/  # Generated compliance reports
│   └── audit_trails/       # Audit trail outputs
├── tests/                  # Unit and integration tests
├── config/                 # Configuration files
├── requirements.txt        # Python dependencies
└── .env.example           # Environment variables template
```

## Target Regulations

1. **EU Digital Service Act (DSA)**
2. **California SB976** - Protecting Our Kids from Social Media Addiction Act
3. **Florida Online Protections for Minors**
4. **Utah Social Media Regulation Act**
5. **US NCMEC Reporting Requirements** - Child sexual abuse content reporting

## Development Tools & Technologies

- **Language**: Python 3.13+
- **LLM Framework**: Google Gemini 2.5 Flash
- **Web Interface**: Streamlit
- **Data Processing**: Pandas, NumPy
- **Visualization**: Plotly, Matplotlib, Seaborn


## Installation & Setup

1. Clone the repository:
```bash
git clone https://github.com/ActuallyAnson/tiktoktech.git
cd tiktoktech
```

2. Create and activate virtual environment:
```bash
python -m venv venv #(or python3 -m venv venv)
source .venv/bin/activate #linux & Macos 
# On Windows: venv\Scripts\activate
```

3. Install dependencies:
## Installation & Setup

### Prerequisites

- Python 3.11+
- Slack workspace admin access (for Slack integration)
- Google Gemini API key

### Quick Installation (Recommended)

```bash
git clone https://github.com/your-username/tiktoktech.git
cd tiktoktech
./install.sh
```

The installation script will:
- ✅ Check Python version compatibility
- 📦 Install all dependencies 
- 📋 Create `.env` file from template
- 🔍 Verify installation

### Manual Installation

1. **Clone and Install Dependencies**

```bash
git clone https://github.com/your-username/tiktoktech.git
cd tiktoktech
pip install -r requirements.txt
```

2. **Environment Configuration**

```bash
cp .env.example .env
```

Edit `.env` with your API keys:
```bash
# Gemini API Configuration
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash

# Slack Bot Configuration (Optional - for team integration)
SLACK_BOT_TOKEN=xoxb-your-bot-token-here
SLACK_APP_TOKEN=xapp-your-app-token-here
```

3. **Verify Installation**

```bash
python3 verify_installation.py
```

### Slack Integration Setup (Optional)

For team collaboration via Slack:

1. **Follow the detailed guide**: See `SLACK_SETUP.md` for complete Slack app setup
2. **Quick setup**: 
   - Go to https://api.slack.com/apps
   - Create new app "TikTok Compliance Classifier"
   - Add bot scopes: `app_mentions:read`, `channels:history`, `chat:write`, `commands`, `files:read`, `files:write`
   - Enable Socket Mode
   - Install to workspace
   - Copy tokens to `.env`

### Installation Verification

Run the verification script to ensure everything is working:

```bash
python3 verify_installation.py
```

This will check:
- ✅ Python version compatibility
- 📦 Required dependencies
- 🔐 Environment variables
- 📁 Data files
- 🧪 Basic functionality

## Usage

### Method 1: Batch Processing (Command Line)

```bash
python3 batch_classifier.py
```

### Method 2: Slack Integration (Team Collaboration)

1. **Start the bot**:
   ```bash
   python3 slack_bot.py
   ```

2. **Upload CSV files**: Drag and drop CSV files into any Slack channel where the bot is present

3. **Use slash commands**:
   ```
   /classify Feature name | Feature description
   /compliance-help
   ```

### Method 3: Single Feature Classification

```bash
python3 -c "
from src.processors.gemini_classifier import GeminiClassifier
classifier = GeminiClassifier()
result = classifier.classify_feature('Age verification', 'Enhanced age verification for COPPA compliance')
print(result)
"
```



## Expected Outputs



## Internal Terminology Support

The system understands TikTok's internal terminology:

| Term | Explanation |
|------|-------------|
| ASL | Age-sensitive logic |
| GH | Geo-handler for region-based routing |
| CDS | Compliance Detection System |
| Jellybean | Internal parental control system |
| Snowcap | Child safety policy framework |
| T5 | Tier 5 sensitivity data |
| ... | (Complete mapping in data/terminology.json) |

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Testing

Run the test suite:
```bash
pytest tests/
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Workshop Information

**Workshop**: From Guesswork to Governance: Automating Geo-Regulation with LLM  
**Date**: August 27, 2025  
**Time**: 2:30-3:00 PM  

## Contact

For questions about this project, please contact the development team or open an issue on GitHub.
