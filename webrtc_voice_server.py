#!/usr/bin/env python3
"""
ROXY WebRTC Voice Server
Browser-based real-time voice chat

Run with: python webrtc_voice_server.py
Then open: http://localhost:8767/voice
"""

import asyncio
import json
import logging
import os
import uuid
from pathlib import Path
from typing import Dict, Set

from aiohttp import web
from aiortc import RTCPeerConnection, RTCSessionDescription
from aiortc.contrib.media import MediaRelay

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("webrtc")

# Global state
pcs: Set[RTCPeerConnection] = set()
relay = MediaRelay()

# HTML page for voice chat
VOICE_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>🎤 ROXY Voice Chat</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', system-ui, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            color: #e0e0e0;
        }
        
        .container {
            text-align: center;
            max-width: 600px;
            padding: 40px;
        }
        
        h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
            background: linear-gradient(90deg, #00d4ff, #7b2cbf);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        
        .subtitle {
            color: #888;
            margin-bottom: 40px;
        }
        
        .status-ring {
            width: 200px;
            height: 200px;
            border-radius: 50%;
            margin: 0 auto 30px;
            display: flex;
            justify-content: center;
            align-items: center;
            position: relative;
            transition: all 0.3s ease;
        }
        
        .status-ring::before {
            content: '';
            position: absolute;
            inset: -4px;
            border-radius: 50%;
            background: conic-gradient(from 0deg, #00d4ff, #7b2cbf, #00d4ff);
            opacity: 0;
            transition: opacity 0.3s;
        }
        
        .status-ring.listening::before {
            opacity: 1;
            animation: rotate 2s linear infinite;
        }
        
        .status-ring.speaking::before {
            opacity: 1;
            background: conic-gradient(from 0deg, #00ff88, #00d4ff, #00ff88);
            animation: rotate 1s linear infinite;
        }
        
        @keyframes rotate {
            from { transform: rotate(0deg); }
            to { transform: rotate(360deg); }
        }
        
        .mic-button {
            width: 180px;
            height: 180px;
            border-radius: 50%;
            border: none;
            background: linear-gradient(145deg, #1e2235, #16192a);
            color: #00d4ff;
            font-size: 60px;
            cursor: pointer;
            transition: all 0.2s;
            box-shadow: 
                5px 5px 20px rgba(0,0,0,0.3),
                -5px -5px 20px rgba(255,255,255,0.05);
            position: relative;
            z-index: 1;
        }
        
        .mic-button:hover {
            transform: scale(1.05);
            color: #7b2cbf;
        }
        
        .mic-button:active,
        .mic-button.active {
            transform: scale(0.95);
            background: linear-gradient(145deg, #16192a, #1e2235);
            color: #ff4757;
            box-shadow: 
                inset 5px 5px 20px rgba(0,0,0,0.3),
                inset -5px -5px 20px rgba(255,255,255,0.05);
        }
        
        #status {
            font-size: 1.2em;
            margin: 20px 0;
            padding: 15px 30px;
            background: rgba(255,255,255,0.05);
            border-radius: 30px;
            display: inline-block;
        }
        
        .transcript-box {
            margin-top: 30px;
            background: rgba(0,0,0,0.3);
            border-radius: 15px;
            padding: 20px;
            text-align: left;
            max-height: 300px;
            overflow-y: auto;
        }
        
        .transcript-box h3 {
            color: #00d4ff;
            margin-bottom: 15px;
            font-size: 0.9em;
            text-transform: uppercase;
            letter-spacing: 2px;
        }
        
        .message {
            padding: 10px 15px;
            margin: 10px 0;
            border-radius: 10px;
            animation: fadeIn 0.3s ease;
        }
        
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        .message.user {
            background: rgba(123, 44, 191, 0.2);
            border-left: 3px solid #7b2cbf;
        }
        
        .message.ai {
            background: rgba(0, 212, 255, 0.2);
            border-left: 3px solid #00d4ff;
        }
        
        .message .label {
            font-size: 0.8em;
            color: #888;
            margin-bottom: 5px;
        }
        
        .controls {
            margin-top: 20px;
            display: flex;
            gap: 10px;
            justify-content: center;
        }
        
        .controls button {
            padding: 10px 20px;
            border: 1px solid #00d4ff;
            background: transparent;
            color: #00d4ff;
            border-radius: 20px;
            cursor: pointer;
            transition: all 0.2s;
        }
        
        .controls button:hover {
            background: #00d4ff;
            color: #1a1a2e;
        }
        
        .waveform {
            height: 60px;
            margin: 20px 0;
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 3px;
        }
        
        .waveform .bar {
            width: 4px;
            height: 20px;
            background: #00d4ff;
            border-radius: 2px;
            transition: height 0.1s;
        }
        
        .waveform.active .bar {
            animation: wave 0.5s ease-in-out infinite;
        }
        
        .waveform.active .bar:nth-child(1) { animation-delay: 0s; }
        .waveform.active .bar:nth-child(2) { animation-delay: 0.1s; }
        .waveform.active .bar:nth-child(3) { animation-delay: 0.2s; }
        .waveform.active .bar:nth-child(4) { animation-delay: 0.3s; }
        .waveform.active .bar:nth-child(5) { animation-delay: 0.4s; }
        
        @keyframes wave {
            0%, 100% { height: 20px; }
            50% { height: 50px; }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎤 ROXY Voice Chat</h1>
        <p class="subtitle">Real-time AI conversation with interruption support</p>
        
        <div class="status-ring" id="statusRing">
            <button class="mic-button" id="micBtn">🎙️</button>
        </div>
        
        <div class="waveform" id="waveform">
            <div class="bar"></div>
            <div class="bar"></div>
            <div class="bar"></div>
            <div class="bar"></div>
            <div class="bar"></div>
        </div>
        
        <div id="status">🔵 Click to start</div>
        
        <div class="transcript-box" id="transcriptBox">
            <h3>💬 Conversation</h3>
            <div id="messages"></div>
        </div>
        
        <div class="controls">
            <button id="clearBtn">Clear</button>
            <button id="modeBtn">Hold to Talk</button>
        </div>
    </div>

    <script>
        // State
        let isConnected = false;
        let isRecording = false;
        let holdToTalk = true;
        let mediaRecorder = null;
        let audioContext = null;
        let stream = null;
        let ws = null;
        
        // Elements
        const micBtn = document.getElementById('micBtn');
        const statusRing = document.getElementById('statusRing');
        const status = document.getElementById('status');
        const messages = document.getElementById('messages');
        const waveform = document.getElementById('waveform');
        const clearBtn = document.getElementById('clearBtn');
        const modeBtn = document.getElementById('modeBtn');
        
        // Initialize
        async function init() {
            try {
                // Get microphone
                stream = await navigator.mediaDevices.getUserMedia({
                    audio: {
                        echoCancellation: true,
                        noiseSuppression: true,
                        autoGainControl: true,
                        sampleRate: 16000
                    }
                });
                
                // Setup audio context for visualization
                audioContext = new AudioContext();
                const source = audioContext.createMediaStreamSource(stream);
                const analyser = audioContext.createAnalyser();
                source.connect(analyser);
                
                // Setup WebSocket
                connectWebSocket();
                
                status.textContent = '🟢 Ready - Hold button to talk';
                
            } catch (err) {
                status.textContent = '❌ Microphone access denied';
                console.error(err);
            }
        }
        
        function connectWebSocket() {
            ws = new WebSocket(`ws://${window.location.host}/ws`);
            
            ws.onopen = () => {
                isConnected = true;
                console.log('WebSocket connected');
            };
            
            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                
                if (data.type === 'transcript') {
                    addMessage('user', data.text);
                    status.textContent = '🟡 Processing...';
                    statusRing.className = 'status-ring';
                }
                
                if (data.type === 'response') {
                    addMessage('ai', data.text);
                    status.textContent = '🟢 Ready';
                    
                    // Play audio if available
                    if (data.audio) {
                        playAudio(data.audio);
                    }
                }
                
                if (data.type === 'speaking') {
                    status.textContent = '🔊 Speaking...';
                    statusRing.className = 'status-ring speaking';
                }
                
                if (data.type === 'error') {
                    status.textContent = '❌ ' + data.text;
                }
            };
            
            ws.onclose = () => {
                isConnected = false;
                status.textContent = '🔴 Disconnected - Reconnecting...';
                setTimeout(connectWebSocket, 2000);
            };
        }
        
        function startRecording() {
            if (!stream || isRecording) return;
            
            isRecording = true;
            micBtn.classList.add('active');
            statusRing.className = 'status-ring listening';
            waveform.classList.add('active');
            status.textContent = '🔴 Listening...';
            
            // Send audio chunks via WebSocket
            const options = { mimeType: 'audio/webm;codecs=opus' };
            mediaRecorder = new MediaRecorder(stream, options);
            
            mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0 && ws && ws.readyState === WebSocket.OPEN) {
                    event.data.arrayBuffer().then(buffer => {
                        ws.send(buffer);
                    });
                }
            };
            
            mediaRecorder.start(100); // Send chunks every 100ms
        }
        
        function stopRecording() {
            if (!isRecording) return;
            
            isRecording = false;
            micBtn.classList.remove('active');
            statusRing.className = 'status-ring';
            waveform.classList.remove('active');
            status.textContent = '🟡 Processing...';
            
            if (mediaRecorder && mediaRecorder.state !== 'inactive') {
                mediaRecorder.stop();
                
                // Signal end of speech
                if (ws && ws.readyState === WebSocket.OPEN) {
                    ws.send(JSON.stringify({ type: 'end_speech' }));
                }
            }
        }
        
        function addMessage(type, text) {
            const div = document.createElement('div');
            div.className = `message ${type}`;
            div.innerHTML = `
                <div class="label">${type === 'user' ? '👤 You' : '🤖 ROXY'}</div>
                <div>${text}</div>
            `;
            messages.appendChild(div);
            messages.scrollTop = messages.scrollHeight;
        }
        
        function playAudio(base64Audio) {
            const audio = new Audio(`data:audio/mp3;base64,${base64Audio}`);
            audio.play();
        }
        
        // Event listeners
        if (holdToTalk) {
            micBtn.addEventListener('mousedown', startRecording);
            micBtn.addEventListener('mouseup', stopRecording);
            micBtn.addEventListener('mouseleave', stopRecording);
            micBtn.addEventListener('touchstart', startRecording);
            micBtn.addEventListener('touchend', stopRecording);
        } else {
            micBtn.addEventListener('click', () => {
                if (isRecording) {
                    stopRecording();
                } else {
                    startRecording();
                }
            });
        }
        
        clearBtn.addEventListener('click', () => {
            messages.innerHTML = '';
        });
        
        modeBtn.addEventListener('click', () => {
            holdToTalk = !holdToTalk;
            modeBtn.textContent = holdToTalk ? 'Hold to Talk' : 'Push to Talk';
        });
        
        // Start
        init();
    </script>
</body>
</html>
"""


class VoiceSession:
    """Handles a single voice chat session"""
    
    def __init__(self, ws):
        self.ws = ws
        self.audio_buffer = bytearray()
        self.is_speaking = False
        
        # Load ROXY token
        token_file = Path.home() / ".roxy" / "secret.token"
        self.roxy_token = token_file.read_text().strip() if token_file.exists() else ""
    
    async def handle_message(self, data):
        """Handle incoming message from client"""
        
        if isinstance(data, bytes):
            # Audio data
            self.audio_buffer.extend(data)
            
        elif isinstance(data, str):
            msg = json.loads(data)
            
            if msg.get("type") == "end_speech":
                # Process accumulated audio
                await self.process_audio()
    
    async def process_audio(self):
        """Process accumulated audio and respond"""
        
        if len(self.audio_buffer) < 1000:
            self.audio_buffer.clear()
            return
        
        # Save audio to temp file
        audio_path = f"/tmp/voice_{uuid.uuid4().hex}.webm"
        with open(audio_path, "wb") as f:
            f.write(self.audio_buffer)
        
        self.audio_buffer.clear()
        
        try:
            # Transcribe with Whisper
            transcript = await self.transcribe(audio_path)
            
            if transcript and len(transcript) > 1:
                # Send transcript to client
                await self.ws.send_str(json.dumps({
                    "type": "transcript",
                    "text": transcript
                }))
                
                # Query ROXY
                response = await self.query_roxy(transcript)
                
                # Send response
                await self.ws.send_str(json.dumps({
                    "type": "response", 
                    "text": response
                }))
                
        except Exception as e:
            logger.error(f"Error processing audio: {e}")
            await self.ws.send_str(json.dumps({
                "type": "error",
                "text": str(e)
            }))
        
        finally:
            # Cleanup
            if os.path.exists(audio_path):
                os.remove(audio_path)
    
    async def transcribe(self, audio_path: str) -> str:
        """Transcribe audio file with Whisper"""
        
        try:
            from faster_whisper import WhisperModel
            model = WhisperModel("tiny", device="cpu", compute_type="int8")
            segments, _ = model.transcribe(audio_path, language="en")
            return " ".join([s.text for s in segments]).strip()
        except:
            import whisper
            model = whisper.load_model("tiny")
            result = model.transcribe(audio_path, language="en")
            return result["text"].strip()
    
    async def query_roxy(self, text: str) -> str:
        """Query ROXY for response"""
        
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "http://127.0.0.1:8766/run",
                headers={
                    "X-ROXY-Token": self.roxy_token,
                    "Content-Type": "application/json"
                },
                json={"command": text},
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("response", data.get("result", str(data)))
                else:
                    return f"Error: HTTP {resp.status}"


async def index(request):
    """Serve the voice chat HTML page"""
    return web.Response(text=VOICE_HTML, content_type="text/html")


async def websocket_handler(request):
    """Handle WebSocket connections"""
    
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    
    session = VoiceSession(ws)
    logger.info("New voice session started")
    
    try:
        async for msg in ws:
            if msg.type == web.WSMsgType.TEXT:
                await session.handle_message(msg.data)
            elif msg.type == web.WSMsgType.BINARY:
                await session.handle_message(msg.data)
            elif msg.type == web.WSMsgType.ERROR:
                logger.error(f"WebSocket error: {ws.exception()}")
    finally:
        logger.info("Voice session ended")
    
    return ws


async def offer_handler(request):
    """Handle WebRTC offer"""
    
    params = await request.json()
    offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])
    
    pc = RTCPeerConnection()
    pcs.add(pc)
    
    @pc.on("connectionstatechange")
    async def on_connectionstatechange():
        if pc.connectionState == "failed":
            await pc.close()
            pcs.discard(pc)
    
    @pc.on("track")
    def on_track(track):
        if track.kind == "audio":
            logger.info(f"Audio track received: {track.id}")
    
    await pc.setRemoteDescription(offer)
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)
    
    return web.Response(
        content_type="application/json",
        text=json.dumps({
            "sdp": pc.localDescription.sdp,
            "type": pc.localDescription.type
        })
    )


async def on_shutdown(app):
    """Cleanup on shutdown"""
    coros = [pc.close() for pc in pcs]
    await asyncio.gather(*coros)
    pcs.clear()


def create_app():
    """Create the web application"""
    
    app = web.Application()
    app.on_shutdown.append(on_shutdown)
    
    app.router.add_get("/", index)
    app.router.add_get("/voice", index)
    app.router.add_get("/ws", websocket_handler)
    app.router.add_post("/offer", offer_handler)
    
    return app


if __name__ == "__main__":
    app = create_app()
    
    print("\n" + "="*60)
    print("🎤 ROXY WebRTC Voice Server")
    print("="*60)
    print("Open in browser: http://localhost:8767/voice")
    print("Press Ctrl+C to stop")
    print("="*60 + "\n")
    
    web.run_app(app, host="0.0.0.0", port=8767)
