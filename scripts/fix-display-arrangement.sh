#!/bin/bash
ROXY_ROOT="${ROXY_ROOT:-$HOME/.roxy}"
#
# Fix display arrangement - Set Samsung (central) as primary
# Arrange: Left | Samsung (Primary/Center) | Right
#

echo "🖥️  Fixing Display Arrangement..."
echo ""

# Get current monitor info
MONITORS=$(xrandr --listmonitors 2>/dev/null | tail -n +2)

if [ -z "$MONITORS" ]; then
    echo "❌ Cannot detect monitors via xrandr"
    echo "   Trying alternative method..."
    xrandr 2>/dev/null | grep " connected" | head -5
    exit 1
fi

echo "📊 Current monitors:"
echo "$MONITORS"
echo ""

# Get all connected outputs
OUTPUTS=$(xrandr 2>/dev/null | grep " connected" | awk '{print $1}')

echo "🔍 Connected outputs:"
for output in $OUTPUTS; do
    RES=$(xrandr 2>/dev/null | grep -A1 "^$output" | grep -E "^\s+[0-9]+x[0-9]+" | head -1 | awk '{print $1}')
    echo "   $output: $RES"
done

echo ""
echo "⚠️  Please identify which output is your Samsung (central) monitor:"
echo "   (Look at the output names above)"
echo ""
read -p "Enter Samsung output name (e.g., DP-8, HDMI-1): " SAMSUNG_OUTPUT

if [ -z "$SAMSUNG_OUTPUT" ]; then
    echo "❌ No output specified"
    exit 1
fi

# Verify output exists
if ! xrandr 2>/dev/null | grep -q "^$SAMSUNG_OUTPUT connected"; then
    echo "❌ Output '$SAMSUNG_OUTPUT' not found or not connected"
    exit 1
fi

echo ""
echo "✅ Setting $SAMSUNG_OUTPUT as primary display..."

# Set as primary
xrandr --output "$SAMSUNG_OUTPUT" --primary

if [ $? -eq 0 ]; then
    echo "✅ Primary display set to $SAMSUNG_OUTPUT"
else
    echo "❌ Failed to set primary display"
    exit 1
fi

echo ""
echo "📐 Current arrangement:"
xrandr --listmonitors 2>/dev/null

echo ""
echo "💡 To arrange displays (left, center, right):"
echo "   xrandr --output LEFT_OUTPUT --left-of $SAMSUNG_OUTPUT"
echo "   xrandr --output RIGHT_OUTPUT --right-of $SAMSUNG_OUTPUT"
echo ""
echo "   Or use GNOME Settings > Displays for GUI arrangement"









