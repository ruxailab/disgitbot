# PR Automation System with Vertex AI

A comprehensive GitHub Pull Request automation system powered by **Vertex AI Gemini** that provides intelligent code reviews, automated labeling, smart reviewer assignment, and detailed metrics analysis.

## 🚀 Features

- **🤖 AI-Powered Code Reviews**: Comprehensive PR reviews using Vertex AI Gemini
- **🏷️ Smart Labeling**: Automatic PR categorization with confidence scoring
- **👥 Intelligent Reviewer Assignment**: Context-aware reviewer matching
- **📊 Detailed Metrics**: Risk assessment and complexity analysis
- **⚡ GitHub Actions Integration**: Seamless CI/CD pipeline integration
- **🔧 Rule-Based System**: Works offline without API dependencies for basic features

## 🏗️ Architecture

```
pr_review/
├── main.py                     # Main automation script
├── config.py                   # Configuration management
├── requirements.txt            # Python dependencies
├── test_system.py             # System testing
├── .env                       # Environment variables
├── utils/
│   ├── github_client.py       # GitHub API integration
│   ├── pr_labeler.py          # Rule-based PR labeling
│   ├── reviewer_assigner.py   # Smart reviewer assignment
│   └── vertex_ai_reviewer.py  # Vertex AI Gemini integration
├── data/
│   ├── pr_labels.json         # Label configuration
│   └── reviewers_config.json  # Reviewer expertise mapping
└── .github/
    └── workflows/
        └── pr-automation.yml  # GitHub Actions workflow
```

## 🛠️ Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Update `.env` file with your credentials:

```env
# GitHub Configuration
GITHUB_TOKEN=your_github_token_here
REPO_OWNER=your_org
REPO_NAME=your_repo

# Vertex AI Configuration
VERTEX_AI_PROJECT_ID=your_vertex_ai_project_id
VERTEX_AI_LOCATION=us-central1
GOOGLE_APPLICATION_CREDENTIALS=path/to/service-account-key.json

# Model Configuration
GEMINI_MODEL=gemini-1.5-pro
TEMPERATURE=0.3
MAX_OUTPUT_TOKENS=8192
```

### 3. Set Up Vertex AI

1. **Create a Google Cloud Project** and enable the Vertex AI API
2. **Create a Service Account** with Vertex AI permissions
3. **Download the service account key** (JSON file)
4. **Set the path** in `GOOGLE_APPLICATION_CREDENTIALS`

### 4. Test the System

```bash
python test_system.py
```

## 🎯 Usage

### Command Line Interface

```bash
# Run all automation features
python main.py --repo owner/repo --pr 123 --all --post

# Generate only AI review
python main.py --repo owner/repo --pr 123 --review --post

# Apply labels and assign reviewers
python main.py --repo owner/repo --pr 123 --label --assign --post

# Dry run (no GitHub posting)
python main.py --repo owner/repo --pr 123 --all --dry-run
```

### GitHub Actions Integration

The system includes a GitHub Actions workflow that automatically triggers on PR events:

```yaml
# .github/workflows/pr-automation.yml
name: PR Automation
on:
  pull_request:
    types: [opened, synchronize, reopened]
```

## 🤖 AI Features

### Vertex AI Gemini Integration

- **Comprehensive Code Reviews**: Detailed analysis with security, performance, and testing recommendations
- **Experience-Level Adaptation**: Reviews tailored for beginner, intermediate, or advanced developers
- **Quick Summaries**: AI-generated PR summaries for metrics reports
- **Structured Output**: Organized review sections with ratings

### Review Categories

- **📋 Summary**: Overview and assessment
- **✅ Strengths**: What's done well
- **⚠️ Issues**: Critical problems to address
- **💡 Suggestions**: Improvement recommendations
- **🔒 Security**: Security considerations
- **⚡ Performance**: Performance implications
- **🧪 Testing**: Testing recommendations

## 🏷️ Smart Labeling

The system uses rule-based classification with:

- **Keyword Matching**: Title and description analysis
- **File Pattern Recognition**: Technology stack detection
- **Regex Patterns**: Advanced pattern matching
- **Metrics-Based Scoring**: Risk and complexity assessment

### Supported Labels

- `feature`, `bugfix`, `hotfix`, `enhancement`
- `frontend`, `backend`, `api`, `database`
- `testing`, `documentation`, `security`
- `accessibility`, `performance`, `ui/ux`
- `breaking-change`, `dependencies`

## 👥 Reviewer Assignment

Smart reviewer assignment based on:

- **Expertise Matching**: Skills aligned with PR content
- **Workload Balancing**: Even distribution of review requests
- **Availability**: Active team member prioritization
- **Risk-Based Assignment**: Senior reviewers for high-risk changes

## 📊 Metrics & Analytics

### Calculated Metrics

- Lines added/deleted/changed
- Files modified count
- Function additions
- Risk level assessment
- Complexity indicators

### Risk Assessment

- **🟢 LOW**: < 100 lines changed
- **🟡 MEDIUM**: 100-500 lines changed  
- **🔴 HIGH**: > 500 lines changed

## 🔧 Configuration

### Label Rules (`data/pr_labels.json`)

```json
{
  "feature": {
    "keywords": ["add", "implement", "create", "new"],
    "confidence_boost": 0.2
  }
}
```

### Reviewer Config (`data/reviewers_config.json`)

```json
{
  "reviewers": [
    {
      "username": "reviewer1",
      "expertise": ["frontend", "accessibility"],
      "max_concurrent_reviews": 3
    }
  ]
}
```

## 🧪 Testing

Run the comprehensive test suite:

```bash
python test_system.py
```

Tests include:
- ✅ Configuration validation
- ✅ PR labeling accuracy
- ✅ Reviewer assignment logic
- ✅ Vertex AI integration

## 🚀 Deployment

### GitHub Actions Setup

1. **Add Repository Secrets**:
   - `GITHUB_TOKEN`: GitHub personal access token
   - `VERTEX_AI_PROJECT_ID`: Your Google Cloud project ID
   - `GOOGLE_APPLICATION_CREDENTIALS_JSON`: Service account key content

2. **Enable Actions**: Ensure GitHub Actions are enabled in your repository

3. **Deploy Workflow**: The workflow will automatically trigger on PR events

### Local Development

```bash
# Test with a real PR
python main.py --repo your-org/your-repo --pr 123 --all --dry-run

# Apply to production
python main.py --repo your-org/your-repo --pr 123 --all --post
```

## 🔍 Troubleshooting

### Common Issues

1. **Vertex AI Authentication**:
   ```bash
   export GOOGLE_APPLICATION_CREDENTIALS="path/to/key.json"
   ```

2. **GitHub Token Permissions**:
   - Ensure token has `repo` and `pull_requests` scopes

3. **Rate Limits**:
   - System respects GitHub API rate limits
   - Vertex AI has generous quotas for Gemini

### Debug Mode

```bash
# Enable verbose logging
export LOG_LEVEL=DEBUG
python main.py --repo owner/repo --pr 123 --all --dry-run
```

## 📈 Performance

- **Rule-based labeling**: ~100ms response time
- **Reviewer assignment**: ~50ms response time  
- **Vertex AI review**: ~5-15 seconds (depending on PR size)
- **Metrics calculation**: ~200ms response time

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `python test_system.py`
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License.

## 🆘 Support

For issues and questions:
- Create a GitHub issue
- Check the troubleshooting section
- Review the test output for configuration problems

---

*Powered by Vertex AI Gemini for intelligent code analysis* 