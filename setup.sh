#!/bin/bash

echo "🚀 Setting up Virtual Debate Panel environment"

# Check if Poetry is installed
if ! command -v poetry &> /dev/null
then
    echo "❌ Poetry not found. Please install Poetry first: https://python-poetry.org/docs/#installation"
    exit 1
fi

# Install dependencies
echo "📦 Installing dependencies via Poetry"
poetry install

# Set up environment variables
echo "🔧 Setting up environment variables"
if [ ! -f .env ]; then
    echo "⚠️ .env file not found. Creating from template..."
    cp .env.example .env
    echo "✏️ Please edit .env and add your API keys, then re-run this script."
    exit 1
fi

# Load API key from Secret Manager and write to .env
echo "🔑 Loading GEMINI_API_KEY from Google Secret Manager..."
GEMINI_KEY="$(gcloud secrets versions access latest --secret=GEMINI_API_KEY 2>/dev/null)"

if [ -n "$GEMINI_KEY" ]; then
    echo "✅ API key retrieved from Secret Manager"
    export GEMINI_API_KEY="$GEMINI_KEY"

    # Update .env file with the key (macOS compatible sed)
    if [[ "$OSTYPE" == "darwin"* ]]; then
        sed -i '' "s|^GEMINI_API_KEY=.*|GEMINI_API_KEY=$GEMINI_KEY|" .env
    else
        sed -i "s|^GEMINI_API_KEY=.*|GEMINI_API_KEY=$GEMINI_KEY|" .env
    fi
    echo "✅ Updated .env file with API key"
else
    echo "⚠️ Could not retrieve API key from Secret Manager. Using .env value if set."
fi

# Initialize database
echo "💾 Initializing database"
poetry run python scripts/init_database.py

echo "✅ Setup complete! You can now run the application with:"
echo "  poetry run uvicorn src.api.main:app --reload --port 8000"