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
│   ├── config/              # Configuration files
│   ├── llm/                 # LLM client and related logic
│   ├── pipelines/           # Processing pipelines
│   ├── processors/          # Feature analysis processors
│   ├── prompts/             # Prompt templates for LLMs
│   ├── utils/               # Utility functions
│   └── main.py              # Main application entry point
├── data/
│   ├── chunk_data_local.pkl # Local chunked data
│   ├── dataset.jsonl        # Feature dataset (JSONL)
│   ├── faiss_index_local.bin# FAISS index for embeddings
│   ├── sample_features.csv  # Sample feature dataset
│   ├── terminology.json     # Internal terminology mapping
│   └── url.json             # URL mapping data
├── outputs/
│   ├── logs/                # Pipeline logs
│   └── queues/              # Agent processing queues
├── app.py                   # Streamlit web interface
├── executable.bat           # Windows executable script
├── requirements.txt         # Python dependencies
├── slack_bot.py             # Slack integration bot
├── SLACK_SETUP.md           # Slack setup instructions
├── TEAM_INTEGRATION.md      # Team integration documentation
└── README.md                # Project documentation
```

## Target Regulations

1. **EU Digital Service Act (DSA)**
2. **California SB976** - Protecting Our Kids from Social Media Addiction Act
3. **Florida Online Protections for Minors**
4. **Utah Social Media Regulation Act**
5. **US NCMEC Reporting Requirements** - Child sexual abuse content reporting

## Development Tools & Technologies

**Language**: Python 3.11+
**LLM Framework**: Google Gemini 2.5 Flash
**Web Interface**: Streamlit
**Slack Integration**: Slack Bolt SDK
**Data Processing**: Pandas, NumPy
**Vector Search**: FAISS (for embedding search)
**Configuration**: Python-dotenv, custom config files
**Visualization**: Plotly, Matplotlib, Seaborn
**Machine Learning**: scikit-learn, sentence-transformers
**Blockchain/Web3**: web3 (Ethereum Sepolia integration)
**Utilities**: requests, tqdm, click, rich
**Testing**: pytest, pytest-asyncio
**Development**: black, flake8, mypy


## Installation & Setup

### Prerequisites

Python 3.11+
Google Gemini API key
Slack workspace admin access (for Slack integration, optional)
Ethereum Sepolia API key and private key (for blockchain features, optional)

### Installation

1. **Clone and Install Dependencies**

```bash
git clone https://github.com/your-username/tiktoktech.git
cd tiktoktech
pip install -r requirements.txt
```

2. **Environment Configuration**

```bash
python -m venv venv #(or python3 -m venv venv)
source .venv/bin/activate #linux & Macos 
# On Windows: venv\Scripts\activate
```

Edit `.env` with your API keys:
```bash
# Gemini API Configuration
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash

# Ethereum Sepolia Testnet Configuration (Optional)
SEPOLIA_API_PROVIDER=infura
SEPOLIA_API_KEY=your_sepolia_api_key_here
ETH_PRIVATE_KEY=your_ethereum_private_key_here

# Slack Bot Configuration (Optional - for team integration)
SLACK_BOT_TOKEN=xoxb-your-bot-token-here
SLACK_APP_TOKEN=xapp-your-app-token-here
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

## Usage

### Method 1: Command Line

```bash
python -m src.pipelines.start_pipeline --only-llm --llm-for-llm-categorized
```

### Method 2: Slack Integration (Team Collaboration)

1. **Start the bot**:
   ```bash
   python slack_bot.py
   ```

2. **Upload CSV files**: 
   Drag and drop CSV files into any Slack channel where the bot is present

### Method 3: Streamlit

1. **Start Streamlit**:
   ```bash
   python -m streamlit run app.py
   ```

2. **Upload CSV files**: 
   Drag and drop CSV files into the upload widget

3. **Press "Start Compliance Pipeline"**: 
   You can view the pipeline output and status directly in Streamlit

## Expected Outputs

All outputs are saved in the `outputs/` directory:

- `logs/`: Detailed logs for each pipeline stage and agent
- `queues/`: CSV files showing feature assignments and agent processing queues
- `final_report.zip`: Archive containing compliance results and reports from all agents
`final_report.hash`: Hash file containing the cryptographic hash of `final_report.zip` and (if blockchain API key is provided) the Ethereum transaction ID verifying the hash

These outputs provide traceability, auditability, and optional blockchain verification for compliance results.

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

## License

Copyright 2025 Bugs Debuggers

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

The full license text is provided in the LICENSE file included with this project.

## Contact

For questions about this project, please contact the development team or open an issue on GitHub.
