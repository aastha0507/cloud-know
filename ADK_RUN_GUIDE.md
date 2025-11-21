# Running ADK Web UI for CloudKnow

## Quick Start

```bash
cd /Users/diksharanjan/cloudknow
source venv/bin/activate
./RUN_ADK.sh
```

Or manually:

```bash
cd /Users/diksharanjan/cloudknow
source venv/bin/activate
adk web agents_dir --no-reload
```

## What This Does

- Starts ADK web UI on `http://localhost:8000` (or the port shown)
- Scans `agents_dir/` for agents
- Finds `cloudknow_agent` in `agents_dir/cloudknow_agent/`

## Using the UI

1. Open the URL shown (usually `http://localhost:8000`)
2. In the dropdown, select **"cloudknow_agent"**
3. Start chatting!

## Example Queries

### Query Documents
```
What are the data privacy rules in my documents?
```

### Ingest from Google Drive
```
Ingest files from folder 1nNsuC0z8IvbM2lAS4hCMMvJzaHF1DxFW
```

### Query with Context
```
What files in folder 1nNsuC0z8IvbM2lAS4hCMMvJzaHF1DxFW contain compliance information?
```

## Troubleshooting

### If you see "No root_agent found"
- Make sure you're running: `adk web agents_dir` (not just `adk web`)
- Check that `agents_dir/cloudknow_agent/agent.py` exists and has `root_agent` variable

### If imports fail
- Make sure you're in the project root directory
- The agent should automatically add the project root to Python path

### If the UI doesn't respond
- Check the terminal for error messages
- Make sure your `.env` file has the required variables
- Check that MongoDB and Spanner are accessible

