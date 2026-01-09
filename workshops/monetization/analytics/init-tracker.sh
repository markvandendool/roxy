#!/bin/bash
# Revenue Tracker CSV Generator
# Creates analytics/revenue-tracker.csv with sample data and formulas

ANALYTICS_DIR="$HOME/.roxy/workshops/monetization/analytics"
TRACKER_FILE="$ANALYTICS_DIR/revenue-tracker.csv"

# Create analytics directory if it doesn't exist
mkdir -p "$ANALYTICS_DIR/reports"
mkdir -p "$ANALYTICS_DIR/archives"

# Create CSV header if file doesn't exist
if [ ! -f "$TRACKER_FILE" ]; then
    echo "date,source,amount,product,notes" > "$TRACKER_FILE"
    echo "Created revenue tracker: $TRACKER_FILE"
fi

# Add sample entry for today
echo "$(date '+%Y-%m-%d'),Manual,0,Initial Setup,Workshop created" >> "$TRACKER_FILE"

echo "Revenue tracker initialized ✓"
echo ""
echo "Usage:"
echo "  # Add sale:"
echo "  echo \"\$(date '+%Y-%m-%d'),Gumroad,49,Roxy Infrastructure,First sale!\" >> $TRACKER_FILE"
echo ""
echo "  # View total:"
echo "  awk -F, 'NR>1 {sum+=\$3} END {print \"Total: \$\"sum}' $TRACKER_FILE"
echo ""
echo "  # View by source:"
echo "  awk -F, 'NR>1 {sources[\$2]+=\$3} END {for (s in sources) print s\": \$\"sources[s]}' $TRACKER_FILE"
echo ""
echo "File: $TRACKER_FILE"
