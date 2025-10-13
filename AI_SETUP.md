# AI Classification Setup Guide

This guide explains how to set up AI-powered text classification for invoice and financial document processing.

## 🚀 Quick Start

The AI classifier supports multiple backends and will automatically fall back to regex-based extraction if no AI models are available.

## 🤖 Supported AI Models

### 1. Ollama (Recommended - Local)
Ollama allows you to run large language models locally on your machine.

**Installation:**
```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Pull a model (choose one)
ollama pull llama2
ollama pull llama3
ollama pull mistral
```

**Configuration:**
```bash
# Set environment variable
export AI_MODEL_PREFERENCE=ollama
export OLLAMA_BASE_URL=http://localhost:11434
```

### 2. OpenAI (Cloud)
Use OpenAI's API for classification (requires API key).

**Configuration:**
```bash
# Set environment variables
export AI_MODEL_PREFERENCE=openai
export OPENAI_API_KEY=your_api_key_here
```

### 3. Regex Fallback (Default)
If no AI models are available, the system will use pattern-based extraction with lower confidence scores.

## 🔧 Environment Setup

Create a `.env` file in the project root:

```env
# Database Configuration
DATABASE_URL=postgresql://username:password@localhost:5432/carbon_dna

# AI Model Configuration
AI_MODEL_PREFERENCE=ollama
OLLAMA_BASE_URL=http://localhost:11434
OPENAI_API_KEY=your_openai_api_key_here

# API Configuration
API_BASE=http://127.0.0.1:8000
```

## 📊 Features

### Single Text Classification
- Paste any invoice or financial document text
- AI extracts structured carbon emission data
- Confidence scoring (0.0 to 1.0)
- Human review flags for uncertain classifications

### Batch Processing
- Process multiple texts at once
- Efficient for bulk invoice processing
- Individual confidence scores per text
- Error handling and reporting

### Confidence Scoring
- **High (0.8+)**: Auto-approved, high confidence
- **Medium (0.6-0.8)**: May need review
- **Low (<0.6)**: Requires human review

### Human Review Flags
- `needs_human_review: true` for uncertain classifications
- Allows for quality control and feedback loops
- Can be used to improve AI models over time

## 🎯 Usage Examples

### Single Text Input
```
Invoice #12345
From: Acme Office Supplies
Date: 2025-01-15
Total: $1,250.00
Description: Office supplies and equipment
```

### Batch Input
```
Invoice #12345
From: Acme Office Supplies
Date: 2025-01-15
Total: $1,250.00

Invoice #12346
From: City Utilities
Date: 2025-01-16
Total: $850.00
```

## 🔍 Extracted Data Fields

The AI classifier extracts the following fields:

- **supplier_name**: Company or vendor name
- **activity_type**: transportation, energy, waste, materials, other
- **amount**: Monetary value
- **currency**: USD, EUR, GBP, etc.
- **date**: Transaction date
- **description**: Brief description
- **scope**: 1, 2, or 3 (emission scope)
- **category**: Transportation, Energy, Waste, Materials, Other
- **subcategory**: More specific category
- **activity_amount**: Quantity (km, kWh, tonnes, etc.)
- **activity_unit**: Unit of measurement
- **fuel_type**: If applicable
- **vehicle_type**: If applicable
- **distance_km**: If applicable
- **mass_tonnes**: If applicable
- **energy_kwh**: If applicable

## 🛠️ Troubleshooting

### Ollama Issues
- Ensure Ollama is running: `ollama serve`
- Check if model is available: `ollama list`
- Verify port 11434 is accessible

### OpenAI Issues
- Verify API key is valid
- Check API quota and billing
- Ensure network connectivity

### Low Confidence Scores
- Try providing supplier name explicitly
- Use more detailed text descriptions
- Consider manual review for complex documents

## 📈 Performance Tips

1. **Use Ollama for local processing** - No API costs, better privacy
2. **Batch process multiple texts** - More efficient than individual requests
3. **Provide supplier names** - Improves classification accuracy
4. **Use detailed descriptions** - Better context for AI classification

## 🔒 Privacy & Security

- **Ollama**: All processing happens locally on your machine
- **OpenAI**: Data is sent to OpenAI's servers (check their privacy policy)
- **Regex Fallback**: No external API calls, completely local

## 🎉 Getting Started

1. Install dependencies: `pip install -r requirements.txt`
2. Set up your preferred AI model (Ollama recommended)
3. Configure environment variables
4. Start the application
5. Go to Upload page and try the AI Text Classification feature!

The system will automatically detect available AI models and use the best option available.
