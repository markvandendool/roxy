#!/bin/bash
# Setup NATS JetStream for StackKraft Content Pipeline
# Requires: NATS server running with JetStream enabled

set -e

echo "=== StackKraft NATS JetStream Configuration ==="
echo ""

# Check if NATS is accessible
if ! docker exec roxy-nats nats --version &>/dev/null; then
    echo "❌ NATS not accessible. Ensure roxy-nats container is running."
    exit 1
fi

echo "✅ NATS server accessible"
echo ""

# Create content extraction stream
echo "[1/4] Creating CONTENT_EXTRACT stream..."
docker exec roxy-nats nats stream add CONTENT_EXTRACT \
  --subjects "content.extract.*" \
  --storage file \
  --retention limits \
  --max-age 168h \
  --max-msgs 10000 \
  --max-bytes 10GB \
  --replicas 1 \
  --discard old \
  --dupe-window 2m \
  --no-allow-rollup \
  --no-deny-delete \
  --no-deny-purge 2>&1 || echo "Stream may already exist"

echo ""

# Create content publishing stream
echo "[2/4] Creating CONTENT_PUBLISH stream..."
docker exec roxy-nats nats stream add CONTENT_PUBLISH \
  --subjects "content.publish.*" \
  --storage file \
  --retention limits \
  --max-age 168h \
  --max-msgs 50000 \
  --max-bytes 50GB \
  --max-msgs-per-subject 1000 \
  --replicas 1 \
  --discard old \
  --dupe-window 2m 2>&1 || echo "Stream may already exist"

echo ""

# Create content analytics stream
echo "[3/4] Creating CONTENT_ANALYTICS stream..."
docker exec roxy-nats nats stream add CONTENT_ANALYTICS \
  --subjects "content.analytics.*" \
  --storage file \
  --retention limits \
  --max-age 720h \
  --max-msgs 100000 \
  --max-bytes 100GB \
  --replicas 1 \
  --discard old 2>&1 || echo "Stream may already exist"

echo ""

# Create consumers
echo "[4/4] Creating consumers..."

# Extract worker consumer
docker exec roxy-nats nats consumer add CONTENT_EXTRACT extract_worker \
  --filter "content.extract.request" \
  --ack explicit \
  --pull \
  --deliver all \
  --max-deliver 3 \
  --max-ack-pending 10 \
  --ack-wait 5m \
  --replay instant 2>&1 || echo "Consumer may already exist"

echo ""

# Publish worker consumers (one per platform)
for platform in tiktok youtube instagram twitter; do
    docker exec roxy-nats nats consumer add CONTENT_PUBLISH "publish_${platform}" \
      --filter "content.publish.${platform}" \
      --ack explicit \
      --pull \
      --deliver all \
      --max-deliver 5 \
      --max-ack-pending 100 \
      --ack-wait 2m \
      --replay instant 2>&1 || echo "Consumer may already exist"
done

echo ""

# Analytics sync consumer
docker exec roxy-nats nats consumer add CONTENT_ANALYTICS analytics_sync \
  --filter "content.analytics.sync" \
  --ack explicit \
  --pull \
  --deliver all \
  --max-deliver 3 \
  --max-ack-pending 50 \
  --ack-wait 10m \
  --replay instant 2>&1 || echo "Consumer may already exist"

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║           NATS JetStream Configuration Complete               ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "Streams created:"
echo "  • CONTENT_EXTRACT (content.extract.*) - 7 day retention"
echo "  • CONTENT_PUBLISH (content.publish.*) - 7 day retention"
echo "  • CONTENT_ANALYTICS (content.analytics.*) - 30 day retention"
echo ""
echo "Consumers created:"
echo "  • extract_worker (extraction jobs)"
echo "  • publish_tiktok, publish_youtube, publish_instagram, publish_twitter"
echo "  • analytics_sync (engagement tracking)"
echo ""
echo "Test publishing:"
echo "  docker exec roxy-nats nats pub content.extract.request '{\"video\": \"/path/to/video.mp4\"}'"
echo ""
echo "Monitor streams:"
echo "  docker exec roxy-nats nats stream ls"
echo "  docker exec roxy-nats nats stream info CONTENT_PUBLISH"
echo ""
