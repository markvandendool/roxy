#!/bin/bash
# ROXY Cron Jobs

# Activate venv
source ~/.roxy/venv/bin/activate

case "$1" in
  briefing)
    python3 ~/.roxy/daily_briefing.py --speak
    ;;
  rag-sync)
    python3 ~/.roxy/add_git_history_to_rag.py ~/mindsong-juke-hub --days 1
    ;;
  rag-full)
    python3 ~/.roxy/bootstrap_rag.py ~/.roxy/docs
    ;;
  *)
    echo "Usage: $0 {briefing|rag-sync|rag-full}"
    exit 1
esac
