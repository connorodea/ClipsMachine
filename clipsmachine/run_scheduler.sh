#!/bin/bash
#
# ClipsMachine Scheduler - Run with cron for automated posting
#
# Add to crontab with: crontab -e
# Then add this line to run every hour:
# 0 * * * * /path/to/clipsmachine/run_scheduler.sh
#
# Or every 15 minutes for more frequent checking:
# */15 * * * * /path/to/clipsmachine/run_scheduler.sh
#

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Activate virtual environment if it exists
if [ -d "$SCRIPT_DIR/.venv" ]; then
    source "$SCRIPT_DIR/.venv/bin/activate"
fi

# Set environment variables if needed
# export OPENAI_API_KEY="your-key-here"
# export AWS_ACCESS_KEY_ID="your-key-here"
# export AWS_SECRET_ACCESS_KEY="your-secret-here"

# Run the scheduler
cd "$SCRIPT_DIR"
clipsmachine schedule-run >> scheduler.log 2>&1

# Exit
exit 0
