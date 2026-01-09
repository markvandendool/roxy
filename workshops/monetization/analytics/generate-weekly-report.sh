#!/bin/bash
# Weekly Report Generator
# Generates weekly performance report from analytics data

ANALYTICS_DIR="$HOME/.roxy/workshops/monetization/analytics"
TRACKER_FILE="$ANALYTICS_DIR/revenue-tracker.csv"
WEEK_NUM=$(date +%W)
YEAR=$(date +%Y)
REPORT_FILE="$ANALYTICS_DIR/reports/week-$WEEK_NUM-$YEAR.md"

# Check if tracker exists
if [ ! -f "$TRACKER_FILE" ]; then
    echo "Error: Revenue tracker not found. Run init-tracker.sh first."
    exit 1
fi

# Calculate date range (last 7 days)
START_DATE=$(date -d "7 days ago" +%Y-%m-%d)
END_DATE=$(date +%Y-%m-%d)

# Generate report
cat > "$REPORT_FILE" <<EOF
# Week $WEEK_NUM - $YEAR Performance Report

**Date Range:** $START_DATE to $END_DATE  
**Generated:** $(date '+%Y-%m-%d %H:%M:%S')

## Revenue Summary

EOF

# Total revenue this week
TOTAL=$(awk -F, -v start="$START_DATE" -v end="$END_DATE" '
    NR>1 && $1>=start && $1<=end {sum+=$3} 
    END {print sum}
' "$TRACKER_FILE")

echo "**Total Revenue:** \$$TOTAL" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

# Revenue by source
echo "### By Source" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"
awk -F, -v start="$START_DATE" -v end="$END_DATE" '
    NR>1 && $1>=start && $1<=end {sources[$2]+=$3; count[$2]++} 
    END {
        for (s in sources) 
            print "- **"s":** $"sources[s]" ("count[s]" sales)"
    }
' "$TRACKER_FILE" >> "$REPORT_FILE"

echo "" >> "$REPORT_FILE"

# Revenue by product
echo "### By Product" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"
awk -F, -v start="$START_DATE" -v end="$END_DATE" '
    NR>1 && $1>=start && $1<=end {products[$4]+=$3; count[$4]++} 
    END {
        for (p in products) 
            print "- **"p":** $"products[p]" ("count[p]" sales)"
    }
' "$TRACKER_FILE" >> "$REPORT_FILE"

echo "" >> "$REPORT_FILE"

# Daily breakdown
echo "### Daily Breakdown" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"
awk -F, -v start="$START_DATE" -v end="$END_DATE" '
    NR>1 && $1>=start && $1<=end {daily[$1]+=$3} 
    END {
        for (d in daily) 
            print "- "d": $"daily[d]
    }
' "$TRACKER_FILE" | sort >> "$REPORT_FILE"

echo "" >> "$REPORT_FILE"

# Goals & Next Steps
cat >> "$REPORT_FILE" <<EOF
## Goals for Next Week

- [ ] Reach \$XXX in revenue
- [ ] Ship X new videos
- [ ] Add X new products
- [ ] Submit X grant applications

## Insights

<!-- Add insights here manually -->
- What worked well?
- What to improve?
- New opportunities?

## Action Items

<!-- Add action items here manually -->
- [ ] Action item 1
- [ ] Action item 2
- [ ] Action item 3

---

**Previous Reports:** [analytics/reports/](.)
EOF

echo "Report generated: $REPORT_FILE"
cat "$REPORT_FILE"
