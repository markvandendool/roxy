# ROXY Service Management Guide

Complete guide for managing ROXY services running 24/7 with GPU acceleration.

## Available Services

### JARVIS Service

Permanent resident AI that learns and remembers everything.

**Service**: `jarvis.service`

**Commands**:
```bash
# Start service
sudo systemctl start jarvis

# Stop service
sudo systemctl stop jarvis

# Restart service
sudo systemctl restart jarvis

# Check status
sudo systemctl status jarvis

# View logs
sudo journalctl -u jarvis -f

# Enable on boot
sudo systemctl enable jarvis
```

### Voice Pipeline Service

Voice interface with wake word detection, transcription, and TTS.

**Service**: `roxy-voice.service`

**Commands**:
```bash
# Start service
sudo systemctl start roxy-voice

# Stop service
sudo systemctl stop roxy-voice

# Check status
sudo systemctl status roxy-voice

# View logs
sudo journalctl -u roxy-voice -f
```

### Ollama Service

LLM inference service (required for JARVIS).

**Service**: `ollama.service`

**Commands**:
```bash
# Check status
sudo systemctl status ollama

# View logs
sudo journalctl -u ollama -f
```

## Health Monitoring

### Check All Services

```bash
/opt/roxy/scripts/check-roxy-services.sh
```

### Monitor GPU Usage

```bash
/opt/roxy/scripts/monitor-gpu-services.sh
```

### Continuous Monitoring

```bash
watch -n 2 /opt/roxy/scripts/check-roxy-services.sh
```

## Service Configuration

All services load environment variables from `/opt/roxy/.env`:

- `ROXY_GPU_ENABLED`: Enable/disable GPU acceleration
- `ROXY_GPU_DEVICE`: GPU device (cuda)
- `ROXY_GPU_COMPUTE_TYPE`: Compute type (float16)
- `OLLAMA_HOST`: Ollama server URL
- `OLLAMA_MODEL`: LLM model to use

## GPU Resource Management

### Monitoring GPU Usage

```bash
# Real-time GPU monitoring
rocm-smi

# Continuous monitoring
watch -n 1 rocm-smi

# Check GPU processes
lsof /dev/dri/card*
```

### GPU Memory Management

Services automatically manage GPU memory. If you see out-of-memory errors:

1. Reduce model sizes (use smaller Whisper/TTS models)
2. Use smaller LLM models
3. Ensure only necessary services are running

## Troubleshooting

### Service Won't Start

1. Check service status: `sudo systemctl status <service>`
2. View logs: `sudo journalctl -u <service> -n 50`
3. Check environment: Verify `/opt/roxy/.env` exists and is readable
4. Check permissions: Ensure user has access to GPU devices

### Service Crashes

1. Check logs for errors: `sudo journalctl -u <service> -f`
2. Verify GPU availability: `rocm-smi`
3. Check system resources: `free -h`, `df -h`
4. Restart service: `sudo systemctl restart <service>`

### GPU Not Being Used

1. Verify GPU configuration: `/opt/roxy/scripts/validate-gpu-config.sh`
2. Check service environment: `sudo systemctl show <service> | grep Environment`
3. Verify GPU access: `ls -l /dev/dri/card*`
4. Check service logs for GPU errors

## Performance Tuning

### Optimize for Speed

- Use `float16` compute type (already configured)
- Use GPU-optimized models
- Ensure services have GPU access

### Optimize for Memory

- Use smaller models when possible
- Limit concurrent operations
- Monitor GPU memory usage

## Service Dependencies

- **JARVIS** depends on **Ollama**
- **Voice Pipeline** is independent
- All services can share GPU resources

## Auto-Start on Boot

Services are configured to start on boot:

```bash
# Enable services
sudo systemctl enable jarvis
sudo systemctl enable roxy-voice  # Optional
```

## Logs Location

Service logs are in systemd journal:

```bash
# View all ROXY service logs
sudo journalctl -u jarvis -u roxy-voice -u ollama

# Follow logs in real-time
sudo journalctl -u jarvis -f
```

## Updating Services

After updating code:

```bash
# Restart services to pick up changes
sudo systemctl restart jarvis
sudo systemctl restart roxy-voice
```










