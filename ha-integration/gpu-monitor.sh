#!/bin/bash
# Roxy GPU Monitor - Export to Home Assistant sensors

OUTPUT_FILE="/tmp/roxy-gpu-status.json"

while true; do
    # Get GPU data
    GPU_DATA=$(rocm-smi --showtemp --showuse --showpower --json 2>/dev/null)
    
    if [ -n "$GPU_DATA" ]; then
        echo "$GPU_DATA" > "$OUTPUT_FILE"
        
        # Parse for quick display
        TEMP=$(echo "$GPU_DATA" | jq -r '.card1["Temperature (Sensor edge) (C)"] // "N/A"' 2>/dev/null)
        POWER=$(echo "$GPU_DATA" | jq -r '.card1["Average Graphics Package Power (W)"] // "N/A"' 2>/dev/null)
        USE=$(echo "$GPU_DATA" | jq -r '.card1["GPU use (%)"] // "N/A"' 2>/dev/null)
        
        # Update HA sensors via REST API (if configured)
        if [ -f ~/.roxy/ha-integration/.env ]; then
            source ~/.roxy/ha-integration/.env
            curl -s -X POST "$HA_URL/api/states/sensor.roxy_gpu_temp" \
                -H "Authorization: Bearer $HA_TOKEN" \
                -H "Content-Type: application/json" \
                -d "{\"state\": \"$TEMP\", \"attributes\": {\"unit_of_measurement\": \"°C\", \"friendly_name\": \"Roxy GPU Temperature\"}}" > /dev/null 2>&1
            
            curl -s -X POST "$HA_URL/api/states/sensor.roxy_gpu_power" \
                -H "Authorization: Bearer $HA_TOKEN" \
                -H "Content-Type: application/json" \
                -d "{\"state\": \"$POWER\", \"attributes\": {\"unit_of_measurement\": \"W\", \"friendly_name\": \"Roxy GPU Power\"}}" > /dev/null 2>&1
            
            curl -s -X POST "$HA_URL/api/states/sensor.roxy_gpu_use" \
                -H "Authorization: Bearer $HA_TOKEN" \
                -H "Content-Type: application/json" \
                -d "{\"state\": \"$USE\", \"attributes\": {\"unit_of_measurement\": \"%\", \"friendly_name\": \"Roxy GPU Usage\"}}" > /dev/null 2>&1
        fi
    fi
    
    sleep 10
done
