#!/bin/bash
#===============================================================================
# ROXY Content Pipeline - Modeled on SilverStone Architecture
# Monitors recordings, transcribes, detects viral moments, extracts clips
#===============================================================================

# Configuration
ROXY_HOME="${ROXY_HOME:-$HOME/.roxy}"
PIPELINE_HOME="$ROXY_HOME/content-pipeline"
WATCH_DIR="$PIPELINE_HOME/input"
WORK_DIR="$PIPELINE_HOME/work"
OUTPUT_DIR="$PIPELINE_HOME/output"
LOG="$ROXY_HOME/logs/content-pipeline.log"
ERR_LOG="$ROXY_HOME/logs/content-pipeline.err"
PROCESSED_LOG="$ROXY_HOME/logs/roxy_content_processed.txt"

# Pipeline scripts
TRANSCRIBER="$PIPELINE_HOME/transcriber.py"
VIRAL_DETECTOR="$PIPELINE_HOME/viral_detector.py"
CLIP_EXTRACTOR="$PIPELINE_HOME/clip_extractor.py"

# Create directories
mkdir -p "$WATCH_DIR" "$WORK_DIR" "$OUTPUT_DIR" "$(dirname $LOG)"
touch "$PROCESSED_LOG"

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S'): $1" | tee -a "$LOG"
}

log_err() {
    echo "$(date '+%Y-%m-%d %H:%M:%S'): ERROR: $1" | tee -a "$ERR_LOG"
}

process_video() {
    local INPUT_FILE="$1"
    local BASENAME=$(basename "$INPUT_FILE")
    local NAME="${BASENAME%.*}"
    local LOCK_FILE="/tmp/roxy_pipeline_${NAME}.lock"
    
    # Check if already processed
    if grep -Fxq "$BASENAME" "$PROCESSED_LOG"; then
        log "Already processed: $BASENAME"
        return 0
    fi
    
    # Acquire lock
    if ! mkdir "$LOCK_FILE" 2>/dev/null; then
        log "Lock exists for: $BASENAME"
        return 0
    fi
    
    log "=========================================="
    log "Processing: $BASENAME"
    log "=========================================="
    
    # Create work directory for this file
    local WORK="$WORK_DIR/$NAME"
    mkdir -p "$WORK"
    
    # Wait for file to be fully written
    log "Waiting for file to stabilize..."
    while lsof "$INPUT_FILE" >/dev/null 2>&1; do
        sleep 1
    done
    sleep 2  # Extra buffer
    
    # Step 1: Transcription
    log "Step 1/3: Transcribing with Whisper..."
    if python3 "$TRANSCRIBER" "$INPUT_FILE" "$WORK" 2>> "$ERR_LOG"; then
        log "Transcription complete"
    else
        log_err "Transcription failed for $BASENAME"
        rm -rf "$LOCK_FILE"
        return 1
    fi
    
    # Step 2: Viral Moment Detection
    log "Step 2/3: Detecting viral moments with LLM..."
    local TRANSCRIPT_JSON="$WORK/${NAME}.json"
    local CLIPS_JSON="$WORK/${NAME}_clips.json"
    
    if python3 "$VIRAL_DETECTOR" "$TRANSCRIPT_JSON" "$CLIPS_JSON" 10 2>> "$ERR_LOG"; then
        log "Viral detection complete"
    else
        log_err "Viral detection failed for $BASENAME"
        rm -rf "$LOCK_FILE"
        return 1
    fi
    
    # Step 3: Extract Clips
    log "Step 3/3: Extracting clips..."
    local CLIPS_DIR="$OUTPUT_DIR/$NAME/clips"
    mkdir -p "$CLIPS_DIR"
    
    # Extract landscape clips
    if python3 "$CLIP_EXTRACTOR" "$INPUT_FILE" "$CLIPS_JSON" "$CLIPS_DIR/landscape" 2>> "$ERR_LOG"; then
        log "Landscape clips extracted"
    fi
    
    # Extract vertical clips
    if python3 "$CLIP_EXTRACTOR" "$INPUT_FILE" "$CLIPS_JSON" "$CLIPS_DIR/vertical" --vertical 2>> "$ERR_LOG"; then
        log "Vertical clips extracted"
    fi
    
    # Copy transcripts to output
    cp "$WORK"/*.{srt,vtt,txt,json} "$OUTPUT_DIR/$NAME/" 2>/dev/null
    
    # Mark as processed
    echo "$BASENAME" >> "$PROCESSED_LOG"
    
    log "=========================================="
    log "Pipeline complete for: $BASENAME"
    log "Output: $OUTPUT_DIR/$NAME/"
    log "=========================================="
    
    # Cleanup
    rm -rf "$LOCK_FILE"
    
    # Optional: Voice notification
    if command -v espeak &> /dev/null; then
        espeak "Content pipeline complete for $NAME" 2>/dev/null &
    fi
    
    return 0
}

# Main loop using inotifywait
log "Starting ROXY Content Pipeline"
log "Watching: $WATCH_DIR"
log "Output: $OUTPUT_DIR"

# Install inotify-tools if not present
if ! command -v inotifywait &> /dev/null; then
    log_err "inotifywait not found; install inotify-tools to enable watch mode."
    exit 1
fi

# Watch for new files
inotifywait -m -e close_write -e moved_to --format '%w%f' "$WATCH_DIR" | while read -r FILE; do
    # Check if it's a video file
    if [[ "$FILE" =~ \.(mp4|mkv|mov|avi|webm)$ ]]; then
        log "New video detected: $FILE"
        process_video "$FILE" &
    fi
done
