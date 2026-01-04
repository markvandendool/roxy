# ROXY MOONSHOT UPGRADE PLAN
## Industry-Grade Streaming AI System Transformation

**Version:** 2.0 MOONSHOT  
**Date:** 2026-01-01  
**Status:** Post-Stress-Test Analysis Complete  
**Current Readiness:** 35% → Target: 95%

---

## EXECUTIVE SUMMARY

After comprehensive stress testing and industry research analysis, ROXY demonstrates **solid foundational security** (A- grade) but lacks **production-scale features** for real-world deployment. This plan transforms ROXY from a "working prototype" into an **industry-grade streaming AI system** using proven open-source tools and best practices.

### Current State (Evidence-Based)
```
✅ Token Authentication:    100% (impenetrable in stress tests)
✅ Concurrent Handling:      100% (10 parallel requests, zero errors)
✅ Injection Protection:     100% (all attack vectors blocked)
✅ Load Tolerance:           EXCELLENT (50 req/3min stable)
⚠️ Streaming (SSE):          0% (not implemented)
⚠️ RAG Optimization:         30% (basic vector search only)
⚠️ Monitoring:               10% (observability.py exists, unused)
⚠️ Scaling:                  0% (single instance only)
⚠️ Model Intelligence:       0% (no routing/classification)
❌ User Feedback:            0% (no collection mechanism)
```

### Target Architecture (Industry Standard)
```
📡 SSE Streaming with Redis pub/sub for multi-instance scaling
🔍 Hybrid RAG (BM25 + Vector) with optimized chunking
🚀 GPU-batched inference with 8-bit quantization
🧠 Mixture-of-Experts routing (3-tier: fast/balanced/deep)
📊 Prometheus + Grafana real-time monitoring
🔁 Continuous feedback loop (RLHF-ready)
🔒 HTTPS/TLS + comprehensive input validation
🎯 99.9% uptime with auto-healing
```

---

## PHASE 1: STREAMING FOUNDATION (Week 1-2)
**Goal:** Real-time SSE streaming with production-grade reliability

### 1.1 Implement SSE Streaming ✅ HIGH PRIORITY
**Impact:** +50% perceived performance, -70% time-to-first-token

**Technical Spec:**
```python
# Add to roxy_core.py
@app.route('/stream', methods=['POST'])
async def stream_response():
    async def event_generator():
        # Heartbeat every 30s to prevent proxy timeout
        last_heartbeat = time.time()
        
        async for token in llm_stream():
            # Send token
            yield f"data: {json.dumps({'token': token})}\n\n"
            
            # Periodic heartbeat
            if time.time() - last_heartbeat > 30:
                yield ":keepalive\n\n"
                last_heartbeat = time.time()
        
        # Signal completion
        yield f"event: complete\ndata: {json.dumps({'done': True})}\n\n"
    
    return Response(
        event_generator(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no'  # Nginx compatibility
        }
    )
```

**Implementation Steps:**
1. Add SSE endpoint to `roxy_core.py` 
2. Modify LLM calls to use streaming APIs (Ollama supports `/api/generate` with `stream=true`)
3. Add heartbeat mechanism (`:keepalive\n\n` every 30s)
4. Update `roxy_client.py` to use EventSource API
5. Add auto-reconnect with exponential backoff
6. Test with stress: 50 concurrent SSE streams

**Dependencies:**
- No new packages (stdlib only)
- Ollama already supports streaming

**Success Criteria:**
- [ ] SSE endpoint responds with `text/event-stream`
- [ ] Tokens stream in real-time (<100ms per token)
- [ ] Heartbeat prevents timeout on 5min idle streams
- [ ] Client auto-reconnects on disconnect
- [ ] 50 concurrent streams handled without errors

---

### 1.2 Redis Pub/Sub for Multi-Instance Scaling
**Impact:** Horizontal scaling to 10+ instances, 1000+ concurrent users

**Architecture:**
```
┌─────────────┐
│   Nginx     │ ← Load Balancer (sticky sessions)
│   (proxy)   │
└──────┬──────┘
       │
       ├─────────┬─────────┬─────────┐
       │         │         │         │
   ┌───▼───┐ ┌──▼───┐ ┌──▼───┐ ┌──▼───┐
   │ROXY #1│ │ROXY#2│ │ROXY#3│ │ROXY#N│
   └───┬───┘ └──┬───┘ └──┬───┘ └──┬───┘
       │        │        │        │
       └────────┴────────┴────────┘
                  │
           ┌──────▼──────┐
           │Redis Pub/Sub│ ← Message Broker
           └─────────────┘
```

**Implementation:**
```python
# Add to roxy_core.py
import redis.asyncio as redis

redis_client = redis.from_url("redis://localhost:6379")
pubsub = redis_client.pubsub()

async def publish_to_all_instances(channel, message):
    """Broadcast message to all ROXY instances"""
    await redis_client.publish(channel, json.dumps(message))

async def subscribe_to_updates():
    """Listen for messages from other instances"""
    await pubsub.subscribe('roxy:updates')
    async for message in pubsub.listen():
        if message['type'] == 'message':
            data = json.loads(message['data'])
            # Forward to connected SSE clients
            await broadcast_to_clients(data)
```

**Setup:**
1. Install Redis: `sudo apt install redis-server`
2. Add redis-py: `pip install redis[asyncio]`
3. Configure Nginx with `ip_hash` for sticky sessions
4. Add pub/sub handlers to roxy_core.py
5. Test with 3 instances behind Nginx

**Success Criteria:**
- [ ] 3 ROXY instances run simultaneously
- [ ] Message sent to instance #1 appears on clients connected to #2, #3
- [ ] Load balancer distributes evenly
- [ ] No message loss during instance restart

---

## PHASE 2: INTELLIGENT RAG (Week 3-4)
**Goal:** +50% retrieval quality, +40% answer accuracy

### 2.1 Hybrid Search (BM25 + Vector)
**Impact:** Catches both semantic and lexical matches

**Technical Spec:**
```python
# Add to roxy_commands.py or new rag/hybrid_search.py
from rank_bm25 import BM25Okapi
import numpy as np

class HybridRetriever:
    def __init__(self, vector_db, documents):
        self.vector_db = vector_db
        # Build BM25 index
        tokenized_docs = [doc.split() for doc in documents]
        self.bm25 = BM25Okapi(tokenized_docs)
        self.documents = documents
    
    def search(self, query, top_k=5, alpha=0.5):
        """
        alpha: weight for vector search (1-alpha for BM25)
        """
        # Vector search
        vector_results = self.vector_db.query(
            query_texts=[query],
            n_results=top_k*2
        )
        vector_scores = 1 / (1 + np.array(vector_results['distances'][0]))
        
        # BM25 search
        bm25_scores = self.bm25.get_scores(query.split())
        
        # Combine scores (Reciprocal Rank Fusion)
        combined_scores = {}
        for idx, (v_score, b_score) in enumerate(zip(vector_scores, bm25_scores)):
            combined_scores[idx] = alpha * v_score + (1-alpha) * b_score
        
        # Sort by combined score
        top_indices = sorted(combined_scores, key=combined_scores.get, reverse=True)[:top_k]
        return [self.documents[i] for i in top_indices]
```

**Implementation:**
1. Install: `pip install rank-bm25`
2. Create `~/.roxy/rag/hybrid_search.py`
3. Modify `query_rag()` in roxy_commands.py to use hybrid retriever
4. Benchmark against current vector-only search
5. Tune `alpha` parameter (0.3-0.7 range)

**Success Criteria:**
- [ ] Hybrid search finds results missed by vector-only
- [ ] Keyword queries (exact phrases) rank higher
- [ ] Semantic queries still work well
- [ ] Latency <200ms for retrieval

---

### 2.2 Optimized Chunking
**Impact:** +30% context relevance, -20% hallucinations

**Current Problem:**
- Unknown chunk size (need to measure)
- No overlap between chunks
- Loss of context at boundaries

**Solution:**
```python
# Add to bootstrap_rag.py or new rag/chunker.py
from typing import List

class OptimizedChunker:
    def __init__(self, 
                 chunk_size=400,      # tokens
                 overlap=80,          # 20% overlap
                 min_chunk_size=100):
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.min_chunk_size = min_chunk_size
    
    def chunk_text(self, text: str, metadata: dict = None) -> List[dict]:
        """Smart chunking with overlap and metadata preservation"""
        # Tokenize
        tokens = text.split()  # Simple split, use tiktoken for accuracy
        
        chunks = []
        start = 0
        
        while start < len(tokens):
            end = min(start + self.chunk_size, len(tokens))
            chunk_tokens = tokens[start:end]
            
            # Don't create tiny trailing chunks
            if len(chunk_tokens) < self.min_chunk_size and chunks:
                # Merge with previous chunk
                chunks[-1]['text'] += ' ' + ' '.join(chunk_tokens)
            else:
                chunks.append({
                    'text': ' '.join(chunk_tokens),
                    'metadata': {
                        **metadata,
                        'chunk_index': len(chunks),
                        'start_token': start,
                        'end_token': end
                    }
                })
            
            # Move window with overlap
            start += self.chunk_size - self.overlap
        
        return chunks
```

**Implementation:**
1. Measure current chunk sizes: `grep -o "chunk" ~/.roxy/chroma_db/* | wc -l`
2. Install tiktoken: `pip install tiktoken`
3. Create `~/.roxy/rag/chunker.py`
4. Re-index existing docs with new chunking strategy
5. A/B test: old chunks vs new chunks on 100 test queries

**Success Criteria:**
- [ ] Chunks are 100-500 tokens each
- [ ] 10-20% overlap between adjacent chunks
- [ ] Context spans chunk boundaries (test with multi-sentence queries)
- [ ] Re-indexing completes in <30min

---

## PHASE 3: PERFORMANCE OPTIMIZATION (Week 5-6)
**Goal:** 3x throughput, -60% latency, -50% GPU memory

### 3.1 GPU Batching
**Impact:** 3x throughput on multi-query scenarios

**Technical Spec:**
```python
# Add to roxy_core.py
import asyncio
from collections import deque

class BatchProcessor:
    def __init__(self, max_batch_size=8, max_wait_ms=100):
        self.max_batch_size = max_batch_size
        self.max_wait_ms = max_wait_ms
        self.queue = deque()
        self.processing = False
    
    async def add_request(self, prompt: str) -> str:
        """Add request to batch queue"""
        future = asyncio.Future()
        self.queue.append((prompt, future))
        
        # Trigger batch processing
        if not self.processing:
            asyncio.create_task(self._process_batch())
        
        return await future
    
    async def _process_batch(self):
        """Process accumulated requests as batch"""
        self.processing = True
        await asyncio.sleep(self.max_wait_ms / 1000)  # Wait for more requests
        
        # Collect batch
        batch = []
        futures = []
        while self.queue and len(batch) < self.max_batch_size:
            prompt, future = self.queue.popleft()
            batch.append(prompt)
            futures.append(future)
        
        if not batch:
            self.processing = False
            return
        
        # Process batch
        try:
            results = await self._llm_batch_inference(batch)
            for future, result in zip(futures, results):
                future.set_result(result)
        except Exception as e:
            for future in futures:
                future.set_exception(e)
        
        self.processing = False
        
        # Process next batch if queue not empty
        if self.queue:
            asyncio.create_task(self._process_batch())
    
    async def _llm_batch_inference(self, prompts: List[str]) -> List[str]:
        """Actual LLM call with batch"""
        # Call Ollama with batch (if supported) or parallel requests
        tasks = [self._single_inference(p) for p in prompts]
        return await asyncio.gather(*tasks)
```

**Implementation:**
1. Add BatchProcessor to roxy_core.py
2. Modify `/run` endpoint to use batch processor
3. Test with 20 concurrent requests (should batch into 3 groups of 8)
4. Measure latency: individual vs batched

**Success Criteria:**
- [ ] 8 requests processed in single LLM call
- [ ] Throughput: 50 req/min → 150 req/min
- [ ] Latency: <200ms penalty for batching
- [ ] GPU utilization: 40% → 90%

---

### 3.2 8-bit Quantization
**Impact:** 2x faster inference, -50% GPU memory, <2% quality loss

**Implementation:**
```bash
# Add quantized model to Ollama
ollama pull llama3:8b-q8_0  # 8-bit quantized version

# Or use bitsandbytes for local models
pip install bitsandbytes

# In Python
from transformers import AutoModelForCausalLM
model = AutoModelForCausalLM.from_pretrained(
    "meta-llama/Llama-2-7b",
    load_in_8bit=True,  # Enable 8-bit quantization
    device_map="auto"
)
```

**Testing:**
1. Benchmark current model: tokens/sec, memory usage
2. Switch to quantized version
3. Re-benchmark: measure speed gain
4. Quality test: 100 queries, compare answers (should be >98% similar)

**Success Criteria:**
- [ ] Inference speed: 20 tok/s → 40 tok/s
- [ ] GPU memory: 16GB → 8GB
- [ ] Quality score: >98% vs full precision
- [ ] No crashes or OOM errors

---

## PHASE 4: INTELLIGENCE LAYER (Week 7-8)
**Goal:** Smart routing, intent classification, context management

### 4.1 Mixture-of-Experts Routing
**Impact:** -40% cost, +25% task completion, better resource usage

**3-Tier Model Strategy:**
```
┌─────────────────────────────────────┐
│     Intent Classifier (Fast)       │ ← TinyBERT/DistilBERT
└──────────────┬──────────────────────┘
               │
       ┌───────┴───────┐
       │               │
  ┌────▼────┐    ┌────▼────┐    ┌──────▼──────┐
  │ Simple  │    │Balanced │    │   Complex   │
  │ (Fast)  │    │(Medium) │    │   (Deep)    │
  │ llama3  │    │ llama3  │    │ mixtral/gpt │
  │ 3B-q8   │    │ 8B      │    │ 70B         │
  └─────────┘    └─────────┘    └─────────────┘
   ↑                ↑                  ↑
   │                │                  │
"help"       "summarize this"   "analyze complex
"status"      "explain X"        multi-step problem"
```

**Implementation:**
```python
# Add to ~/.roxy/llm_router.py
from transformers import pipeline

class IntentClassifier:
    def __init__(self):
        self.classifier = pipeline(
            "text-classification",
            model="distilbert-base-uncased-finetuned-sst-2-english"
        )
        
        self.routing_rules = {
            'simple': ['help', 'status', 'list', 'show', 'get'],
            'medium': ['explain', 'summarize', 'compare', 'describe'],
            'complex': ['analyze', 'debug', 'optimize', 'design', 'plan']
        }
    
    def route(self, query: str) -> str:
        """Determine which model tier to use"""
        # Check keywords first (fast path)
        query_lower = query.lower()
        for tier, keywords in self.routing_rules.items():
            if any(kw in query_lower for kw in keywords):
                return tier
        
        # Use classifier for ambiguous queries
        result = self.classifier(query[:512])[0]
        complexity = result['score']
        
        if complexity < 0.3:
            return 'simple'
        elif complexity < 0.7:
            return 'medium'
        else:
            return 'complex'

# In roxy_core.py
router = IntentClassifier()
tier = router.route(user_query)

if tier == 'simple':
    model = "llama3:3b-q8_0"
elif tier == 'medium':
    model = "llama3:8b"
else:
    model = "mixtral:8x7b"  # or gpt-4 via API
```

**Implementation:**
1. Install transformers: `pip install transformers`
2. Create `~/.roxy/llm_router.py`
3. Add 3 model endpoints to Ollama
4. Integrate router into roxy_core.py
5. Test routing accuracy on 100 diverse queries

**Success Criteria:**
- [ ] 80%+ of simple queries routed to fast model
- [ ] Complex queries get deep model
- [ ] Routing latency <50ms
- [ ] Cost reduction: 40% (measure token usage)

---

### 4.2 Context Window Management
**Impact:** +50% context retention in long conversations

**Implementation:**
```python
# Add to ~/.roxy/context_manager.py (enhance existing)
import tiktoken

class ContextWindowManager:
    def __init__(self, max_tokens=4096, target_tokens=3072):
        self.max_tokens = max_tokens
        self.target_tokens = target_tokens
        self.encoder = tiktoken.get_encoding("cl100k_base")
    
    def compress_history(self, messages: List[dict]) -> List[dict]:
        """Compress conversation history to fit context window"""
        # Count current tokens
        total_tokens = sum(
            len(self.encoder.encode(m['content'])) 
            for m in messages
        )
        
        if total_tokens <= self.target_tokens:
            return messages  # Fits, no compression needed
        
        # Strategy: Keep system + last N messages + summarize middle
        system_msg = messages[0] if messages[0]['role'] == 'system' else None
        recent = messages[-5:]  # Keep last 5 messages
        
        # Summarize the middle section
        middle = messages[1:-5] if len(messages) > 6 else []
        if middle:
            summary = self._summarize_messages(middle)
            return [system_msg, summary] + recent if system_msg else [summary] + recent
        
        return [system_msg] + recent if system_msg else recent
    
    def _summarize_messages(self, messages: List[dict]) -> dict:
        """Create summary of message sequence"""
        combined = "\n".join(m['content'] for m in messages)
        summary_prompt = f"Summarize this conversation briefly:\n{combined}"
        
        # Call small/fast model for summary
        summary = self._quick_summary(summary_prompt)
        
        return {
            'role': 'assistant',
            'content': f"[Summary of previous conversation: {summary}]"
        }
```

**Success Criteria:**
- [ ] 20-message conversations stay under 4K tokens
- [ ] Summary preserves key facts
- [ ] No context loss on important details

---

## PHASE 5: MONITORING & OBSERVABILITY (Week 9-10)
**Goal:** Real-time visibility, proactive alerts, performance tracking

### 5.1 Prometheus + Grafana Stack
**Impact:** Full production visibility, 5min MTTR (mean time to resolution)

**Architecture:**
```
┌──────────────┐
│  ROXY Core   │ ← Exports metrics on :8767/metrics
└──────┬───────┘
       │
┌──────▼───────┐
│  Prometheus  │ ← Scrapes metrics every 15s
│  (Time-series│    Stores 30 days history
│    DB)       │
└──────┬───────┘
       │
┌──────▼───────┐
│   Grafana    │ ← Visualizes dashboards
│  (Dashboard) │    Alerts on anomalies
└──────────────┘
```

**Implementation:**
```python
# Add to roxy_core.py
from prometheus_client import Counter, Histogram, Gauge, generate_latest

# Define metrics
requests_total = Counter('roxy_requests_total', 'Total requests', ['endpoint', 'status'])
request_duration = Histogram('roxy_request_duration_seconds', 'Request latency')
active_streams = Gauge('roxy_active_sse_streams', 'Number of active SSE connections')
llm_tokens = Counter('roxy_llm_tokens_total', 'Total tokens processed', ['model'])
rag_latency = Histogram('roxy_rag_latency_seconds', 'RAG retrieval time')
cache_hits = Counter('roxy_cache_hits_total', 'Cache hit/miss', ['result'])

# Add metrics endpoint
@app.route('/metrics')
def metrics():
    return Response(generate_latest(), mimetype='text/plain')

# Instrument code
@request_duration.time()
def handle_request():
    requests_total.labels(endpoint='/run', status='success').inc()
    # ... process request
```

**Setup:**
```bash
# Install Prometheus
wget https://github.com/prometheus/prometheus/releases/download/v2.48.0/prometheus-2.48.0.linux-amd64.tar.gz
tar xvf prometheus-*.tar.gz
cd prometheus-*

# Configure prometheus.yml
cat > prometheus.yml << EOF
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'roxy'
    static_configs:
      - targets: ['localhost:8767']
EOF

# Start
./prometheus --config.file=prometheus.yml

# Install Grafana
sudo apt install grafana
sudo systemctl start grafana-server

# Access Grafana at http://localhost:3000
# Default login: admin/admin
```

**Grafana Dashboards:**
1. **Request Overview**
   - Requests/sec (by endpoint)
   - Error rate %
   - P50/P95/P99 latency
   - Active SSE streams

2. **LLM Performance**
   - Tokens/sec
   - Model usage breakdown
   - Avg response time by model
   - Queue depth (if batching)

3. **RAG Metrics**
   - Retrieval latency
   - Documents retrieved per query
   - Cache hit rate
   - Hybrid search score distribution

4. **System Resources**
   - CPU usage
   - GPU memory
   - Redis connections
   - Disk I/O

**Alerts:**
```yaml
# alerting.yml
groups:
  - name: roxy_alerts
    rules:
      - alert: HighErrorRate
        expr: rate(roxy_requests_total{status="error"}[5m]) > 0.05
        for: 2m
        annotations:
          summary: "Error rate >5% for 2 minutes"
      
      - alert: HighLatency
        expr: histogram_quantile(0.95, roxy_request_duration_seconds) > 5
        for: 5m
        annotations:
          summary: "P95 latency >5s for 5 minutes"
```

**Success Criteria:**
- [ ] Prometheus scraping ROXY every 15s
- [ ] Grafana shows 4 dashboards with real-time data
- [ ] Alerts fire on >5% error rate
- [ ] Historical data retained for 30 days

---

### 5.2 Structured Logging with ELK Stack
**Impact:** Searchable logs, root-cause analysis in minutes

**Setup:**
```bash
# Install Elasticsearch
wget https://artifacts.elastic.co/downloads/elasticsearch/elasticsearch-8.11.0-linux-x86_64.tar.gz
tar xvf elasticsearch-*.tar.gz
cd elasticsearch-*/
./bin/elasticsearch

# Install Logstash
wget https://artifacts.elastic.co/downloads/logstash/logstash-8.11.0-linux-x86_64.tar.gz
tar xvf logstash-*.tar.gz

# Configure Logstash pipeline
cat > logstash.conf << EOF
input {
  file {
    path => "/home/mark/.roxy/logs/*.log"
    start_position => "beginning"
  }
}

filter {
  json {
    source => "message"
  }
}

output {
  elasticsearch {
    hosts => ["localhost:9200"]
    index => "roxy-logs-%{+YYYY.MM.dd}"
  }
}
EOF

# Install Kibana
wget https://artifacts.elastic.co/downloads/kibana/kibana-8.11.0-linux-amd64.tar.gz
tar xvf kibana-*.tar.gz
cd kibana-*/
./bin/kibana
```

**Enhance Logging:**
```python
# In roxy_core.py, switch to structured JSON logging
import logging
import json_log_formatter

formatter = json_log_formatter.JSONFormatter()

handler = logging.FileHandler('/home/mark/.roxy/logs/roxy-core.json')
handler.setFormatter(formatter)

logger = logging.getLogger()
logger.addHandler(handler)

# Now logs are JSON:
logger.info('Request processed', extra={
    'endpoint': '/run',
    'duration_ms': 234,
    'tokens': 156,
    'model': 'llama3:8b',
    'user_id': 'mark',
    'cache_hit': True
})
```

**Success Criteria:**
- [ ] All logs in Elasticsearch within 5s
- [ ] Kibana search: find all errors in last hour
- [ ] Dashboard: visualize request flow
- [ ] Alert on repeated errors (same stack trace >10 times/min)

---

## PHASE 6: USER FEEDBACK & CONTINUOUS IMPROVEMENT (Week 11-12)
**Goal:** Learn from every interaction, +20% quality over time

### 6.1 Feedback Collection System
**Impact:** Data for RLHF, prompt refinement, model selection

**Implementation:**
```python
# Add to roxy_client.py
class FeedbackCollector:
    def __init__(self):
        self.feedback_db = Path.home() / ".roxy" / "data" / "feedback.jsonl"
        self.feedback_db.parent.mkdir(exist_ok=True)
    
    def collect_feedback(self, interaction_id: str, query: str, response: str):
        """Present feedback options after response"""
        print("\n" + "="*60)
        print("Rate this response:")
        print("  [1] 👍 Excellent")
        print("  [2] 😊 Good")
        print("  [3] 😐 Okay")
        print("  [4] 😞 Poor")
        print("  [5] 👎 Terrible")
        print("  [c] Provide correction")
        print("  [s] Skip")
        print("="*60)
        
        choice = input("Your rating: ").strip().lower()
        
        feedback = {
            'timestamp': datetime.now().isoformat(),
            'interaction_id': interaction_id,
            'query': query,
            'response': response,
            'rating': None,
            'correction': None,
            'implicit_signals': {}
        }
        
        if choice in ['1', '2', '3', '4', '5']:
            feedback['rating'] = int(choice)
        elif choice == 'c':
            correction = input("What should the answer be? ")
            feedback['correction'] = correction
            feedback['rating'] = 4  # Implicit poor rating
        
        # Record implicit signals
        feedback['implicit_signals'] = {
            'response_length': len(response),
            'time_to_respond': self.last_response_time,
            'follow_up_query': None  # Set on next query
        }
        
        # Save to JSONL
        with open(self.feedback_db, 'a') as f:
            f.write(json.dumps(feedback) + '\n')
        
        return feedback
```

**Analytics:**
```python
# Add ~/.roxy/feedback_analyzer.py
import pandas as pd

class FeedbackAnalyzer:
    def __init__(self, feedback_file):
        self.df = pd.read_json(feedback_file, lines=True)
    
    def get_insights(self):
        """Generate actionable insights"""
        return {
            'avg_rating': self.df['rating'].mean(),
            'poor_responses': self.df[self.df['rating'] <= 2],
            'common_failures': self._find_patterns(self.df[self.df['rating'] <= 2]),
            'high_rated_patterns': self._find_patterns(self.df[self.df['rating'] >= 4]),
            'correction_needed_topics': self._extract_topics(self.df[self.df['correction'].notna()])
        }
    
    def _find_patterns(self, df):
        """Find common patterns in queries"""
        # Simple keyword frequency
        from collections import Counter
        all_words = ' '.join(df['query']).lower().split()
        return Counter(all_words).most_common(20)
```

**Success Criteria:**
- [ ] Feedback collected on 80%+ interactions
- [ ] Data stored in searchable format
- [ ] Weekly report: avg rating, common failures
- [ ] Actionable insights: "improve X type of query"

---

### 6.2 RLHF Pipeline (Preparation)
**Impact:** Model aligned to user preferences

**Data Preparation:**
```python
# Convert feedback to RLHF training data
def prepare_rlhf_dataset(feedback_db):
    """Convert user feedback to preference pairs"""
    with open(feedback_db) as f:
        feedback = [json.loads(line) for line in f]
    
    # Group by query
    from collections import defaultdict
    by_query = defaultdict(list)
    for item in feedback:
        by_query[item['query']].append(item)
    
    # Create preference pairs (chosen vs rejected)
    pairs = []
    for query, responses in by_query.items():
        # Sort by rating
        sorted_resp = sorted(responses, key=lambda x: x.get('rating', 3), reverse=True)
        
        if len(sorted_resp) >= 2:
            chosen = sorted_resp[0]
            rejected = sorted_resp[-1]
            
            if chosen['rating'] > rejected['rating']:
                pairs.append({
                    'query': query,
                    'chosen': chosen['response'],
                    'rejected': rejected['response']
                })
    
    return pairs

# Save for future RLHF training
pairs = prepare_rlhf_dataset('~/.roxy/data/feedback.jsonl')
with open('~/.roxy/data/rlhf_pairs.jsonl', 'w') as f:
    for pair in pairs:
        f.write(json.dumps(pair) + '\n')
```

**Note:** Actual RLHF training requires significant compute. This prepares the data; training can be done later with tools like [TRL (Transformer Reinforcement Learning)](https://github.com/huggingface/trl) or [DeepSpeed-Chat](https://github.com/microsoft/DeepSpeed).

**Success Criteria:**
- [ ] 1000+ feedback items collected
- [ ] 200+ preference pairs generated
- [ ] Data formatted for TRL/DeepSpeed
- [ ] Baseline model performance measured (before RLHF)

---

## PHASE 7: SECURITY HARDENING (Week 13-14)
**Goal:** Production-grade security, compliance-ready

### 7.1 HTTPS/TLS Deployment
**Impact:** Encrypted traffic, prevents MITM attacks

**Setup with Let's Encrypt:**
```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx

# Get certificate (requires domain)
sudo certbot --nginx -d roxy.yourdomain.com

# Auto-renewal
sudo certbot renew --dry-run
```

**Nginx Config:**
```nginx
server {
    listen 443 ssl http2;
    server_name roxy.yourdomain.com;
    
    ssl_certificate /etc/letsencrypt/live/roxy.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/roxy.yourdomain.com/privkey.pem;
    
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    
    # SSE support
    location /stream {
        proxy_pass http://127.0.0.1:8766;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
        proxy_buffering off;
        proxy_cache off;
    }
    
    location / {
        proxy_pass http://127.0.0.1:8766;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

**Success Criteria:**
- [ ] HTTPS working on all endpoints
- [ ] TLS 1.3 enforced
- [ ] A+ rating on SSL Labs test
- [ ] Auto-renewal configured

---

### 7.2 Input Validation & Sanitization
**Impact:** Prevents injection attacks, path traversal

**Implementation:**
```python
# Add to ~/.roxy/security.py
import re
from pathlib import Path

class InputValidator:
    def __init__(self, allowed_dirs=["/home/mark/mindsong-juke-hub"]):
        self.allowed_dirs = [Path(d).resolve() for d in allowed_dirs]
        self.dangerous_patterns = [
            r'\.\./\.\.',  # Path traversal
            r'&&|\|\|',    # Command chaining
            r';',          # Command separator
            r'\$\(',       # Command substitution
            r'`',          # Backticks
            r'\x00'        # Null bytes
        ]
    
    def validate_file_path(self, path: str) -> Path:
        """Ensure file path is within allowed directories"""
        resolved = Path(path).resolve()
        
        # Check if within allowed dirs
        if not any(str(resolved).startswith(str(allowed)) for allowed in self.allowed_dirs):
            raise ValueError(f"Access denied: {path} is outside allowed directories")
        
        # Check for dangerous patterns
        if any(re.search(pattern, str(path)) for pattern in self.dangerous_patterns):
            raise ValueError(f"Dangerous pattern detected in path: {path}")
        
        return resolved
    
    def sanitize_command(self, cmd: str) -> str:
        """Remove dangerous characters from commands"""
        # Check for injection patterns
        for pattern in self.dangerous_patterns:
            if re.search(pattern, cmd):
                raise ValueError(f"Dangerous pattern detected: {pattern}")
        
        # Limit length
        if len(cmd) > 10000:
            raise ValueError("Command too long (max 10000 chars)")
        
        return cmd

# Use in roxy_core.py
validator = InputValidator()

def handle_file_operation(file_path):
    validated_path = validator.validate_file_path(file_path)
    # ... proceed with file operation
```

**Success Criteria:**
- [ ] Path traversal attacks blocked
- [ ] Command injection attempts fail
- [ ] All file operations go through validator
- [ ] Stress test: 0 successful attacks

---

### 7.3 Dependency Scanning & Updates
**Impact:** Proactive vulnerability detection

**Setup:**
```bash
# Install security tools
pip install bandit safety

# Scan code for vulnerabilities
bandit -r ~/.roxy/ -f json -o security-report.json

# Check dependencies
safety check --json

# Install Trivy for container scanning
wget https://github.com/aquasecurity/trivy/releases/download/v0.48.0/trivy_0.48.0_Linux-64bit.tar.gz
tar xvf trivy*.tar.gz
sudo mv trivy /usr/local/bin/

# Scan Python environment
trivy fs --scanners vuln ~/.roxy/venv/
```

**Automated Scanning:**
```yaml
# Add to .github/workflows/security.yml
name: Security Scan

on:
  push:
    branches: [main]
  schedule:
    - cron: '0 0 * * 0'  # Weekly

jobs:
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Run Bandit
        run: |
          pip install bandit
          bandit -r . -f json -o bandit-report.json
      
      - name: Run Safety
        run: |
          pip install safety
          safety check --json
      
      - name: Upload reports
        uses: actions/upload-artifact@v3
        with:
          name: security-reports
          path: |
            bandit-report.json
            safety-report.json
```

**Success Criteria:**
- [ ] Zero high-severity vulnerabilities
- [ ] Weekly automated scans
- [ ] Alerts on new CVEs
- [ ] All dependencies <6 months old

---

## IMPLEMENTATION TIMELINE

```
Week 1-2:   SSE Streaming + Redis Pub/Sub
Week 3-4:   Hybrid RAG + Optimized Chunking
Week 5-6:   GPU Batching + 8-bit Quantization
Week 7-8:   Model Routing + Context Management
Week 9-10:  Prometheus + Grafana + ELK Stack
Week 11-12: Feedback Collection + RLHF Prep
Week 13-14: HTTPS + Security Hardening

Total: 14 weeks (3.5 months)
```

---

## SUCCESS METRICS

### Before (Current State)
```
Latency (P95):              8-10 seconds
Throughput:                 16 req/min
RAG Accuracy:               70% (estimated)
Uptime:                     Unknown (no monitoring)
Security Score:             A- (stress test)
Concurrent Users:           10 (tested max)
Cost per 1K requests:       Unknown
```

### After (Target State)
```
Latency (P95):              <2 seconds (-75%)
Throughput:                 150 req/min (+837%)
RAG Accuracy:               90% (+20pp)
Uptime:                     99.9% (monitored)
Security Score:             A+ (hardened)
Concurrent Users:           1000+ (scaled)
Cost per 1K requests:       -60% (routing + caching)
```

---

## RISK MITIGATION

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| SSE connection drops | Medium | High | Heartbeat + auto-reconnect |
| Redis single point of failure | Medium | High | Redis Sentinel (HA) |
| LLM API rate limits | Low | Medium | Fallback models + caching |
| Data migration errors | Medium | High | Backup before re-indexing |
| Security vulnerabilities | Low | Critical | Weekly scans + rapid patching |
| Performance regression | Medium | Medium | A/B testing + rollback plan |

---

## RESOURCE REQUIREMENTS

### Compute
- **Current:** 1 instance, 4GB RAM, 1 GPU
- **Target:** 3 instances, 8GB RAM each, shared GPU pool
- **Additional:** Redis server (2GB RAM)

### Storage
- **ChromaDB:** 10GB → 50GB (more docs + metadata)
- **Logs:** 1GB/week → 5GB/week (structured logs)
- **Prometheus:** 10GB (30 days history)

### Network
- **Bandwidth:** 10 Mbps → 100 Mbps (SSE streams)
- **Connections:** 50 concurrent → 1000+ concurrent

### Software Licenses
- All open-source (MIT/Apache 2.0)
- Total cost: $0

---

## ROLLBACK PLAN

Every phase has a rollback strategy:

1. **Git tags** before each major change
2. **Database backups** before re-indexing
3. **A/B testing** for new features (10% traffic)
4. **Feature flags** in config.json
5. **Automated tests** prevent regressions

**Rollback procedure:**
```bash
# Immediate rollback
git checkout <previous-tag>
systemctl --user restart roxy-core

# Database rollback
cp ~/.roxy/chroma_db.backup ~/.roxy/chroma_db

# Config rollback
mv config.json config.json.new
mv config.json.backup config.json
```

---

## CONCLUSION

This plan transforms ROXY from a **working prototype** into a **production-grade streaming AI system** using industry best practices and proven open-source tools. Every improvement is:

- ✅ **Evidence-based** (stress test results, industry research)
- ✅ **Measurable** (specific metrics, success criteria)
- ✅ **Testable** (clear verification steps)
- ✅ **Reversible** (rollback plans)
- ✅ **Cost-effective** (100% open-source)

**Expected Outcome:** A scalable, reliable, intelligent AI assistant that rivals commercial offerings while remaining fully under your control.

**Next Step:** Begin Phase 1 - SSE Streaming implementation (estimated 2 weeks).

---

*End of ROXY MOONSHOT UPGRADE PLAN v2.0*
