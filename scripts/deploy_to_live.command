#!/bin/bash
# Double-click to deploy eBirdChecklistNameFromGPS.py to the live location.
# Opens Terminal, runs the deploy, then waits so you can see the result.

cd "$(dirname "$0")"
python3 deploy_to_live.py
echo ""
read -p "Press Enter to close..."
