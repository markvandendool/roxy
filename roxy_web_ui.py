#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║   🌐 ROXY WEB UI - ULTRA PREMIUM DASHBOARD                                   ║
║                                                                              ║
║   A world-class web interface inspired by Open-WebUI & LobeChat              ║
║                                                                              ║
║   Features:                                                                  ║
║   • Beautiful dark mode chat interface                                       ║
║   • Real-time streaming responses                                            ║
║   • Voice input/output support                                               ║
║   • Infrastructure status dashboard                                          ║
║   • Expert router visualization                                              ║
║   • Markdown rendering with syntax highlighting                              ║
║   • Mobile responsive design                                                 ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from aiohttp import web, WSMsgType
import aiohttp_cors

# Configuration
HOST = os.getenv("ROXY_WEB_HOST", "0.0.0.0")
PORT = int(os.getenv("ROXY_WEB_PORT", "8780"))
ROXY_HOST = os.getenv("ROXY_HOST", "127.0.0.1")
ROXY_PORT = int(os.getenv("ROXY_PORT", "8766"))
ROXY_BASE_URL = f"http://{ROXY_HOST}:{ROXY_PORT}"
TOKEN_PATH = Path.home() / ".roxy" / "secret.token"


def get_token() -> str:
    """Get ROXY authentication token."""
    if TOKEN_PATH.exists():
        return TOKEN_PATH.read_text().strip()
    return ""


# ═══════════════════════════════════════════════════════════════════════════════
# HTML Template - Ultra Premium Design
# ═══════════════════════════════════════════════════════════════════════════════

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🚀 ROXY - AI Operating System</title>
    <link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>🚀</text></svg>">
    
    <!-- Fonts -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    
    <!-- Highlight.js for code blocks -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/tokyo-night-dark.min.css">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>
    
    <!-- Marked for Markdown -->
    <script src="https://cdnjs.cloudflare.com/ajax/libs/marked/12.0.0/marked.min.js"></script>
    
    <style>
        /* ══════════════════════════════════════════════════════════════════════
           CSS Variables - Premium Dark Theme
           ══════════════════════════════════════════════════════════════════════ */
        :root {
            /* Colors - Deep Space Theme */
            --bg-primary: #0a0a0f;
            --bg-secondary: #12121a;
            --bg-tertiary: #1a1a25;
            --bg-hover: #252535;
            --bg-active: #2a2a40;
            
            /* Accent Colors */
            --accent-primary: #6366f1;
            --accent-secondary: #8b5cf6;
            --accent-success: #22c55e;
            --accent-warning: #f59e0b;
            --accent-error: #ef4444;
            --accent-info: #3b82f6;
            
            /* Text */
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
            --text-muted: #64748b;
            
            /* Borders */
            --border-color: #2d2d3a;
            --border-hover: #3d3d4a;
            
            /* Shadows */
            --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.3);
            --shadow-md: 0 4px 6px rgba(0, 0, 0, 0.4);
            --shadow-lg: 0 10px 15px rgba(0, 0, 0, 0.5);
            --shadow-glow: 0 0 20px rgba(99, 102, 241, 0.3);
            
            /* Gradients */
            --gradient-primary: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
            --gradient-dark: linear-gradient(180deg, #12121a 0%, #0a0a0f 100%);
            
            /* Fonts */
            --font-sans: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            --font-mono: 'JetBrains Mono', 'Fira Code', monospace;
            
            /* Spacing */
            --spacing-xs: 0.25rem;
            --spacing-sm: 0.5rem;
            --spacing-md: 1rem;
            --spacing-lg: 1.5rem;
            --spacing-xl: 2rem;
            
            /* Border Radius */
            --radius-sm: 0.375rem;
            --radius-md: 0.5rem;
            --radius-lg: 0.75rem;
            --radius-xl: 1rem;
            --radius-full: 9999px;
            
            /* Transitions */
            --transition-fast: 150ms ease;
            --transition-normal: 250ms ease;
            --transition-slow: 350ms ease;
        }
        
        /* ══════════════════════════════════════════════════════════════════════
           Reset & Base
           ══════════════════════════════════════════════════════════════════════ */
        *, *::before, *::after {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }
        
        html {
            font-size: 16px;
            -webkit-font-smoothing: antialiased;
            -moz-osx-font-smoothing: grayscale;
        }
        
        body {
            font-family: var(--font-sans);
            background: var(--bg-primary);
            color: var(--text-primary);
            line-height: 1.6;
            min-height: 100vh;
            overflow: hidden;
        }
        
        /* ══════════════════════════════════════════════════════════════════════
           Layout
           ══════════════════════════════════════════════════════════════════════ */
        .app {
            display: flex;
            height: 100vh;
        }
        
        /* Sidebar */
        .sidebar {
            width: 280px;
            background: var(--bg-secondary);
            border-right: 1px solid var(--border-color);
            display: flex;
            flex-direction: column;
            transition: transform var(--transition-normal);
        }
        
        .sidebar-header {
            padding: var(--spacing-lg);
            border-bottom: 1px solid var(--border-color);
        }
        
        .logo {
            display: flex;
            align-items: center;
            gap: var(--spacing-sm);
            font-size: 1.5rem;
            font-weight: 700;
            color: var(--text-primary);
        }
        
        .logo-icon {
            font-size: 2rem;
        }
        
        .logo-text {
            background: var(--gradient-primary);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        
        .sidebar-content {
            flex: 1;
            overflow-y: auto;
            padding: var(--spacing-md);
        }
        
        .sidebar-section {
            margin-bottom: var(--spacing-lg);
        }
        
        .sidebar-section-title {
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
            color: var(--text-muted);
            margin-bottom: var(--spacing-sm);
            padding: 0 var(--spacing-sm);
        }
        
        .sidebar-item {
            display: flex;
            align-items: center;
            gap: var(--spacing-sm);
            padding: var(--spacing-sm) var(--spacing-md);
            border-radius: var(--radius-md);
            color: var(--text-secondary);
            cursor: pointer;
            transition: all var(--transition-fast);
        }
        
        .sidebar-item:hover {
            background: var(--bg-hover);
            color: var(--text-primary);
        }
        
        .sidebar-item.active {
            background: var(--accent-primary);
            color: white;
        }
        
        /* Status Indicators */
        .status-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: var(--spacing-sm);
            padding: var(--spacing-md);
            background: var(--bg-tertiary);
            border-radius: var(--radius-lg);
        }
        
        .status-item {
            display: flex;
            align-items: center;
            gap: var(--spacing-xs);
            font-size: 0.75rem;
        }
        
        .status-dot {
            width: 8px;
            height: 8px;
            border-radius: var(--radius-full);
            animation: pulse 2s infinite;
        }
        
        .status-dot.online { background: var(--accent-success); }
        .status-dot.offline { background: var(--accent-error); }
        .status-dot.loading { background: var(--accent-warning); }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        
        /* Main Content */
        .main {
            flex: 1;
            display: flex;
            flex-direction: column;
            background: var(--gradient-dark);
        }
        
        /* Header */
        .header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: var(--spacing-md) var(--spacing-lg);
            border-bottom: 1px solid var(--border-color);
            background: var(--bg-secondary);
        }
        
        .header-title {
            font-size: 1.125rem;
            font-weight: 600;
        }
        
        .header-actions {
            display: flex;
            gap: var(--spacing-sm);
        }
        
        /* Chat Container */
        .chat-container {
            flex: 1;
            overflow-y: auto;
            padding: var(--spacing-lg);
            display: flex;
            flex-direction: column;
            gap: var(--spacing-lg);
        }
        
        /* Message Styles */
        .message {
            display: flex;
            gap: var(--spacing-md);
            max-width: 900px;
            margin: 0 auto;
            width: 100%;
            animation: fadeIn 0.3s ease;
        }
        
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        .message.user {
            flex-direction: row-reverse;
        }
        
        .message-avatar {
            width: 40px;
            height: 40px;
            border-radius: var(--radius-lg);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.25rem;
            flex-shrink: 0;
        }
        
        .message.user .message-avatar {
            background: var(--gradient-primary);
        }
        
        .message.assistant .message-avatar {
            background: var(--bg-tertiary);
            border: 1px solid var(--border-color);
        }
        
        .message-content {
            flex: 1;
            min-width: 0;
        }
        
        .message-bubble {
            padding: var(--spacing-md) var(--spacing-lg);
            border-radius: var(--radius-xl);
            line-height: 1.7;
        }
        
        .message.user .message-bubble {
            background: var(--accent-primary);
            color: white;
            border-bottom-right-radius: var(--radius-sm);
        }
        
        .message.assistant .message-bubble {
            background: var(--bg-tertiary);
            border: 1px solid var(--border-color);
            border-bottom-left-radius: var(--radius-sm);
        }
        
        .message-meta {
            display: flex;
            align-items: center;
            gap: var(--spacing-sm);
            margin-top: var(--spacing-xs);
            font-size: 0.75rem;
            color: var(--text-muted);
        }
        
        .message.user .message-meta {
            justify-content: flex-end;
        }
        
        /* Markdown Rendering */
        .message-bubble h1, .message-bubble h2, .message-bubble h3 {
            margin-top: var(--spacing-md);
            margin-bottom: var(--spacing-sm);
            font-weight: 600;
        }
        
        .message-bubble h1 { font-size: 1.5rem; }
        .message-bubble h2 { font-size: 1.25rem; }
        .message-bubble h3 { font-size: 1.125rem; }
        
        .message-bubble p {
            margin-bottom: var(--spacing-sm);
        }
        
        .message-bubble code {
            font-family: var(--font-mono);
            background: rgba(0, 0, 0, 0.3);
            padding: 0.125rem 0.375rem;
            border-radius: var(--radius-sm);
            font-size: 0.875rem;
        }
        
        .message-bubble pre {
            margin: var(--spacing-md) 0;
            border-radius: var(--radius-md);
            overflow-x: auto;
        }
        
        .message-bubble pre code {
            display: block;
            padding: var(--spacing-md);
            background: #1a1b26;
            border-radius: var(--radius-md);
            font-size: 0.875rem;
            line-height: 1.5;
        }
        
        .message-bubble ul, .message-bubble ol {
            padding-left: var(--spacing-lg);
            margin-bottom: var(--spacing-sm);
        }
        
        .message-bubble li {
            margin-bottom: var(--spacing-xs);
        }
        
        .message-bubble blockquote {
            border-left: 3px solid var(--accent-primary);
            padding-left: var(--spacing-md);
            color: var(--text-secondary);
            margin: var(--spacing-md) 0;
        }
        
        /* Input Area */
        .input-container {
            padding: var(--spacing-lg);
            background: var(--bg-secondary);
            border-top: 1px solid var(--border-color);
        }
        
        .input-wrapper {
            max-width: 900px;
            margin: 0 auto;
            display: flex;
            gap: var(--spacing-sm);
            align-items: flex-end;
        }
        
        .input-box {
            flex: 1;
            position: relative;
        }
        
        .input-field {
            width: 100%;
            padding: var(--spacing-md) var(--spacing-lg);
            padding-right: 100px;
            background: var(--bg-tertiary);
            border: 1px solid var(--border-color);
            border-radius: var(--radius-xl);
            color: var(--text-primary);
            font-family: var(--font-sans);
            font-size: 1rem;
            resize: none;
            min-height: 56px;
            max-height: 200px;
            transition: all var(--transition-fast);
        }
        
        .input-field:focus {
            outline: none;
            border-color: var(--accent-primary);
            box-shadow: var(--shadow-glow);
        }
        
        .input-field::placeholder {
            color: var(--text-muted);
        }
        
        .input-actions {
            position: absolute;
            right: var(--spacing-sm);
            bottom: var(--spacing-sm);
            display: flex;
            gap: var(--spacing-xs);
        }
        
        /* Buttons */
        .btn {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: var(--spacing-xs);
            padding: var(--spacing-sm) var(--spacing-md);
            border: none;
            border-radius: var(--radius-md);
            font-family: var(--font-sans);
            font-size: 0.875rem;
            font-weight: 500;
            cursor: pointer;
            transition: all var(--transition-fast);
        }
        
        .btn-icon {
            width: 40px;
            height: 40px;
            padding: 0;
            border-radius: var(--radius-lg);
            font-size: 1.25rem;
        }
        
        .btn-primary {
            background: var(--gradient-primary);
            color: white;
        }
        
        .btn-primary:hover {
            transform: scale(1.05);
            box-shadow: var(--shadow-glow);
        }
        
        .btn-secondary {
            background: var(--bg-tertiary);
            color: var(--text-secondary);
            border: 1px solid var(--border-color);
        }
        
        .btn-secondary:hover {
            background: var(--bg-hover);
            color: var(--text-primary);
        }
        
        .btn-ghost {
            background: transparent;
            color: var(--text-secondary);
        }
        
        .btn-ghost:hover {
            background: var(--bg-hover);
            color: var(--text-primary);
        }
        
        /* Voice Button Animation */
        .btn-voice.recording {
            background: var(--accent-error);
            animation: voicePulse 1s infinite;
        }
        
        @keyframes voicePulse {
            0%, 100% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.4); }
            50% { box-shadow: 0 0 0 10px rgba(239, 68, 68, 0); }
        }
        
        /* Typing Indicator */
        .typing-indicator {
            display: flex;
            align-items: center;
            gap: 4px;
            padding: var(--spacing-md);
        }
        
        .typing-indicator span {
            width: 8px;
            height: 8px;
            background: var(--accent-primary);
            border-radius: var(--radius-full);
            animation: typing 1.4s infinite;
        }
        
        .typing-indicator span:nth-child(2) { animation-delay: 0.2s; }
        .typing-indicator span:nth-child(3) { animation-delay: 0.4s; }
        
        @keyframes typing {
            0%, 100% { opacity: 0.4; transform: scale(0.8); }
            50% { opacity: 1; transform: scale(1); }
        }
        
        /* Expert Badge */
        .expert-badge {
            display: inline-flex;
            align-items: center;
            gap: var(--spacing-xs);
            padding: 2px 8px;
            background: var(--bg-active);
            border-radius: var(--radius-full);
            font-size: 0.75rem;
            color: var(--accent-secondary);
        }
        
        /* Scrollbar */
        ::-webkit-scrollbar {
            width: 8px;
            height: 8px;
        }
        
        ::-webkit-scrollbar-track {
            background: transparent;
        }
        
        ::-webkit-scrollbar-thumb {
            background: var(--border-color);
            border-radius: var(--radius-full);
        }
        
        ::-webkit-scrollbar-thumb:hover {
            background: var(--border-hover);
        }
        
        /* Responsive */
        @media (max-width: 768px) {
            .sidebar {
                position: fixed;
                left: 0;
                top: 0;
                height: 100%;
                z-index: 100;
                transform: translateX(-100%);
            }
            
            .sidebar.open {
                transform: translateX(0);
            }
            
            .menu-toggle {
                display: block !important;
            }
        }
        
        .menu-toggle {
            display: none;
        }
        
        /* Welcome Screen */
        .welcome {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            height: 100%;
            text-align: center;
            padding: var(--spacing-xl);
        }
        
        .welcome-icon {
            font-size: 4rem;
            margin-bottom: var(--spacing-lg);
        }
        
        .welcome-title {
            font-size: 2rem;
            font-weight: 700;
            margin-bottom: var(--spacing-md);
            background: var(--gradient-primary);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        
        .welcome-subtitle {
            color: var(--text-secondary);
            font-size: 1.125rem;
            max-width: 500px;
            margin-bottom: var(--spacing-xl);
        }
        
        .quick-actions {
            display: flex;
            flex-wrap: wrap;
            gap: var(--spacing-md);
            justify-content: center;
        }
        
        .quick-action {
            display: flex;
            align-items: center;
            gap: var(--spacing-sm);
            padding: var(--spacing-md) var(--spacing-lg);
            background: var(--bg-tertiary);
            border: 1px solid var(--border-color);
            border-radius: var(--radius-lg);
            color: var(--text-secondary);
            cursor: pointer;
            transition: all var(--transition-fast);
        }
        
        .quick-action:hover {
            background: var(--bg-hover);
            border-color: var(--accent-primary);
            color: var(--text-primary);
            transform: translateY(-2px);
        }
        
        .quick-action-icon {
            font-size: 1.5rem;
        }
    </style>
</head>
<body>
    <div class="app">
        <!-- Sidebar -->
        <aside class="sidebar">
            <div class="sidebar-header">
                <div class="logo">
                    <span class="logo-icon">🚀</span>
                    <span class="logo-text">ROXY</span>
                </div>
            </div>
            
            <div class="sidebar-content">
                <div class="sidebar-section">
                    <div class="sidebar-section-title">Status</div>
                    <div class="status-grid">
                        <div class="status-item">
                            <span class="status-dot" id="status-core"></span>
                            <span>Core</span>
                        </div>
                        <div class="status-item">
                            <span class="status-dot" id="status-redis"></span>
                            <span>Redis</span>
                        </div>
                        <div class="status-item">
                            <span class="status-dot" id="status-postgres"></span>
                            <span>PostgreSQL</span>
                        </div>
                        <div class="status-item">
                            <span class="status-dot" id="status-nats"></span>
                            <span>NATS</span>
                        </div>
                    </div>
                </div>
                
                <div class="sidebar-section">
                    <div class="sidebar-section-title">Conversations</div>
                    <div class="sidebar-item active">
                        <span>💬</span>
                        <span>New Chat</span>
                    </div>
                </div>
                
                <div class="sidebar-section">
                    <div class="sidebar-section-title">Experts</div>
                    <div class="sidebar-item">
                        <span>🧠</span>
                        <span>deepseek-coder</span>
                    </div>
                    <div class="sidebar-item">
                        <span>🔢</span>
                        <span>wizard-math</span>
                    </div>
                    <div class="sidebar-item">
                        <span>💡</span>
                        <span>llama3</span>
                    </div>
                    <div class="sidebar-item">
                        <span>⚡</span>
                        <span>qwen2.5-coder</span>
                    </div>
                </div>
            </div>
        </aside>
        
        <!-- Main Content -->
        <main class="main">
            <header class="header">
                <button class="btn btn-ghost menu-toggle" onclick="toggleSidebar()">☰</button>
                <div class="header-title">🚀 Chat with ROXY</div>
                <div class="header-actions">
                    <button class="btn btn-ghost btn-icon" onclick="refreshStatus()" title="Refresh">🔄</button>
                    <button class="btn btn-ghost btn-icon" onclick="clearChat()" title="Clear Chat">🗑️</button>
                </div>
            </header>
            
            <div class="chat-container" id="chat-container">
                <!-- Welcome Screen -->
                <div class="welcome" id="welcome">
                    <div class="welcome-icon">🚀</div>
                    <h1 class="welcome-title">Welcome to ROXY</h1>
                    <p class="welcome-subtitle">
                        Your AI Operating System. Ask me anything about code, system tasks, 
                        data analysis, or just have a conversation!
                    </p>
                    <div class="quick-actions">
                        <div class="quick-action" onclick="sendQuickAction('Write a Python script to analyze CSV data')">
                            <span class="quick-action-icon">💻</span>
                            <span>Write Code</span>
                        </div>
                        <div class="quick-action" onclick="sendQuickAction('Explain how neural networks work')">
                            <span class="quick-action-icon">🧠</span>
                            <span>Explain AI</span>
                        </div>
                        <div class="quick-action" onclick="sendQuickAction('Help me solve this math problem')">
                            <span class="quick-action-icon">🔢</span>
                            <span>Math Help</span>
                        </div>
                        <div class="quick-action" onclick="sendQuickAction('What creative project should I work on?')">
                            <span class="quick-action-icon">🎨</span>
                            <span>Be Creative</span>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="input-container">
                <div class="input-wrapper">
                    <div class="input-box">
                        <textarea 
                            class="input-field" 
                            id="message-input" 
                            placeholder="Ask ROXY anything..."
                            rows="1"
                            onkeydown="handleKeyDown(event)"
                            oninput="autoResize(this)"
                        ></textarea>
                        <div class="input-actions">
                            <button class="btn btn-secondary btn-icon btn-voice" id="voice-btn" onclick="toggleVoice()" title="Voice Input">
                                🎤
                            </button>
                            <button class="btn btn-primary btn-icon" onclick="sendMessage()" title="Send">
                                📤
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </main>
    </div>
    
    <script>
        // ══════════════════════════════════════════════════════════════════════
        // Configuration
        // ══════════════════════════════════════════════════════════════════════
        const ROXY_API = '/api';
        let isRecording = false;
        let recognition = null;
        
        // Configure marked for Markdown rendering
        marked.setOptions({
            highlight: function(code, lang) {
                if (lang && hljs.getLanguage(lang)) {
                    return hljs.highlight(code, { language: lang }).value;
                }
                return hljs.highlightAuto(code).value;
            },
            breaks: true,
            gfm: true
        });
        
        // ══════════════════════════════════════════════════════════════════════
        // Status Management
        // ══════════════════════════════════════════════════════════════════════
        async function refreshStatus() {
            try {
                const res = await fetch(`${ROXY_API}/status`);
                const data = await res.json();
                
                setStatus('status-core', data.core ? 'online' : 'offline');
                setStatus('status-redis', data.redis ? 'online' : 'offline');
                setStatus('status-postgres', data.postgres ? 'online' : 'offline');
                setStatus('status-nats', data.nats ? 'online' : 'offline');
            } catch (e) {
                setStatus('status-core', 'offline');
                setStatus('status-redis', 'offline');
                setStatus('status-postgres', 'offline');
                setStatus('status-nats', 'offline');
            }
        }
        
        function setStatus(id, status) {
            const el = document.getElementById(id);
            if (el) {
                el.className = 'status-dot ' + status;
            }
        }
        
        // ══════════════════════════════════════════════════════════════════════
        // Chat Functions
        // ══════════════════════════════════════════════════════════════════════
        function hideWelcome() {
            const welcome = document.getElementById('welcome');
            if (welcome) {
                welcome.style.display = 'none';
            }
        }
        
        function addMessage(role, content, expert = null) {
            hideWelcome();
            const container = document.getElementById('chat-container');
            const msgDiv = document.createElement('div');
            msgDiv.className = `message ${role}`;
            
            const avatar = role === 'user' ? '👤' : '🤖';
            const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
            
            let expertBadge = '';
            if (expert && role === 'assistant') {
                expertBadge = `<span class="expert-badge">🧠 ${expert}</span>`;
            }
            
            // Render markdown for assistant messages
            const renderedContent = role === 'assistant' ? marked.parse(content) : escapeHtml(content);
            
            msgDiv.innerHTML = `
                <div class="message-avatar">${avatar}</div>
                <div class="message-content">
                    <div class="message-bubble">${renderedContent}</div>
                    <div class="message-meta">
                        ${expertBadge}
                        <span>${time}</span>
                    </div>
                </div>
            `;
            
            container.appendChild(msgDiv);
            container.scrollTop = container.scrollHeight;
            
            // Highlight code blocks
            msgDiv.querySelectorAll('pre code').forEach((block) => {
                hljs.highlightElement(block);
            });
        }
        
        function addTypingIndicator() {
            hideWelcome();
            const container = document.getElementById('chat-container');
            const indicator = document.createElement('div');
            indicator.id = 'typing-indicator';
            indicator.className = 'message assistant';
            indicator.innerHTML = `
                <div class="message-avatar">🤖</div>
                <div class="message-content">
                    <div class="message-bubble">
                        <div class="typing-indicator">
                            <span></span>
                            <span></span>
                            <span></span>
                        </div>
                    </div>
                </div>
            `;
            container.appendChild(indicator);
            container.scrollTop = container.scrollHeight;
        }
        
        function removeTypingIndicator() {
            const indicator = document.getElementById('typing-indicator');
            if (indicator) {
                indicator.remove();
            }
        }
        
        async function sendMessage() {
            const input = document.getElementById('message-input');
            const message = input.value.trim();
            
            if (!message) return;
            
            addMessage('user', message);
            input.value = '';
            autoResize(input);
            
            addTypingIndicator();
            
            try {
                const res = await fetch(`${ROXY_API}/chat`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message })
                });
                
                const data = await res.json();
                removeTypingIndicator();
                
                if (data.error) {
                    addMessage('assistant', `⚠️ Error: ${data.error}`);
                } else {
                    addMessage('assistant', data.response, data.expert);
                }
            } catch (e) {
                removeTypingIndicator();
                addMessage('assistant', `⚠️ Connection error: ${e.message}`);
            }
        }
        
        function sendQuickAction(text) {
            document.getElementById('message-input').value = text;
            sendMessage();
        }
        
        function clearChat() {
            const container = document.getElementById('chat-container');
            container.innerHTML = '';
            const welcome = document.getElementById('welcome');
            if (welcome) {
                welcome.style.display = 'flex';
            } else {
                // Recreate welcome if it was removed
                location.reload();
            }
        }
        
        // ══════════════════════════════════════════════════════════════════════
        // Voice Input
        // ══════════════════════════════════════════════════════════════════════
        function toggleVoice() {
            const btn = document.getElementById('voice-btn');
            
            if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
                alert('Voice input is not supported in your browser.');
                return;
            }
            
            if (isRecording) {
                stopRecording();
            } else {
                startRecording();
            }
        }
        
        function startRecording() {
            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            recognition = new SpeechRecognition();
            recognition.continuous = false;
            recognition.interimResults = true;
            recognition.lang = 'en-US';
            
            recognition.onstart = () => {
                isRecording = true;
                document.getElementById('voice-btn').classList.add('recording');
            };
            
            recognition.onresult = (event) => {
                const transcript = Array.from(event.results)
                    .map(result => result[0].transcript)
                    .join('');
                document.getElementById('message-input').value = transcript;
            };
            
            recognition.onend = () => {
                isRecording = false;
                document.getElementById('voice-btn').classList.remove('recording');
                // Auto-send after voice input
                const input = document.getElementById('message-input');
                if (input.value.trim()) {
                    sendMessage();
                }
            };
            
            recognition.onerror = (event) => {
                console.error('Speech recognition error:', event.error);
                isRecording = false;
                document.getElementById('voice-btn').classList.remove('recording');
            };
            
            recognition.start();
        }
        
        function stopRecording() {
            if (recognition) {
                recognition.stop();
            }
        }
        
        // ══════════════════════════════════════════════════════════════════════
        // UI Helpers
        // ══════════════════════════════════════════════════════════════════════
        function handleKeyDown(event) {
            if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault();
                sendMessage();
            }
        }
        
        function autoResize(textarea) {
            textarea.style.height = 'auto';
            textarea.style.height = Math.min(textarea.scrollHeight, 200) + 'px';
        }
        
        function toggleSidebar() {
            document.querySelector('.sidebar').classList.toggle('open');
        }
        
        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
        
        // ══════════════════════════════════════════════════════════════════════
        // Initialize
        // ══════════════════════════════════════════════════════════════════════
        document.addEventListener('DOMContentLoaded', () => {
            refreshStatus();
            setInterval(refreshStatus, 30000);
            
            // Focus input
            document.getElementById('message-input').focus();
        });
    </script>
</body>
</html>
"""


# ═══════════════════════════════════════════════════════════════════════════════
# API Routes
# ═══════════════════════════════════════════════════════════════════════════════

async def index(request: web.Request) -> web.Response:
    """Serve the main HTML page."""
    return web.Response(text=HTML_TEMPLATE, content_type="text/html")


async def api_status(request: web.Request) -> web.Response:
    """Get infrastructure status."""
    import aiohttp
    
    token = get_token()
    headers = {"X-ROXY-Token": token}
    
    status = {
        "core": False,
        "redis": False,
        "postgres": False,
        "nats": False,
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            # Check core
            try:
                async with session.get(
                    f"{ROXY_BASE_URL}/ping",
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as resp:
                    status["core"] = resp.status == 200
            except Exception:
                pass
            
            # Check infrastructure
            try:
                async with session.get(
                    f"{ROXY_BASE_URL}/infrastructure",
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        status["redis"] = data.get("redis", {}).get("status") == "connected"
                        status["postgres"] = data.get("postgres", {}).get("status") == "connected"
                        status["nats"] = data.get("nats", {}).get("status") == "connected"
            except Exception:
                pass
    except Exception:
        pass
    
    return web.json_response(status)


async def api_chat(request: web.Request) -> web.Response:
    """Send a chat message to ROXY."""
    import aiohttp
    
    try:
        data = await request.json()
        message = data.get("message", "")
        
        if not message:
            return web.json_response({"error": "No message provided"}, status=400)
        
        token = get_token()
        headers = {
            "X-ROXY-Token": token,
            "Content-Type": "application/json",
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{ROXY_BASE_URL}/expert",
                headers=headers,
                json={"message": message},
                timeout=aiohttp.ClientTimeout(total=120)
            ) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    return web.json_response({
                        "response": result.get("response", "No response"),
                        "expert": result.get("expert", "unknown"),
                    })
                else:
                    error_text = await resp.text()
                    return web.json_response({
                        "error": f"ROXY error: {error_text}"
                    }, status=resp.status)
    
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


# ═══════════════════════════════════════════════════════════════════════════════
# Application Setup
# ═══════════════════════════════════════════════════════════════════════════════

def create_app() -> web.Application:
    """Create and configure the web application."""
    app = web.Application()
    
    # Add routes
    app.router.add_get("/", index)
    app.router.add_get("/api/status", api_status)
    app.router.add_post("/api/chat", api_chat)
    
    # Enable CORS
    cors = aiohttp_cors.setup(app, defaults={
        "*": aiohttp_cors.ResourceOptions(
            allow_credentials=True,
            expose_headers="*",
            allow_headers="*",
        )
    })
    
    for route in list(app.router.routes()):
        cors.add(route)
    
    return app


def main():
    """Run the web server."""
    print(f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║   🌐 ROXY Web UI - Ultra Premium Dashboard                                   ║
║                                                                              ║
║   Starting server at http://{HOST}:{PORT}                                     ║
║                                                                              ║
║   Open your browser and navigate to the URL above!                           ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
    """)
    
    app = create_app()
    web.run_app(app, host=HOST, port=PORT, print=None)


if __name__ == "__main__":
    main()
