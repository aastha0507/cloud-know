#!/bin/bash

# Script to run ADK web UI for CloudKnow

cd /Users/diksharanjan/cloudknow
source venv/bin/activate

echo "🚀 Starting ADK Web UI..."
echo "📁 Agents directory: agents_dir/"
echo ""

# Run ADK web with explicit agents directory
adk web agents_dir --no-reload

