#!/bin/bash
# Script to generate automation reports manually
# Usage: ./generate_reports.sh [crm] [time-window]

set -e

# Default values
CRM=${1:-all}
TIME_WINDOW=${2:-24}

echo "🤖 Generating automation reports..."
echo "CRM: $CRM"
echo "Time Window: $TIME_WINDOW hours"
echo ""

# Navigate to project directory
cd "$(dirname "$0")/.."

# Activate virtual environment if it exists
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
    echo "✅ Activated virtual environment"
elif [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
    echo "✅ Activated virtual environment"
fi

# Run the management command
python manage.py generate_automation_reports \
    --time-window "$TIME_WINDOW" \
    --detailed \
    --crm "$CRM" \
    --export-json \
    --output-dir logs/automation_reports

echo ""
echo "🎉 Automation reports generation completed!"
echo "📁 JSON exports saved to: logs/automation_reports/"
