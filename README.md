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
python -m venv .venv #(or python3 -m venv venv)
source .venv/bin/activate #linux & Macos 
# On Windows: .venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your OpenAI API key and other configurations
```


## Usage



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
