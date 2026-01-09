-- CITADEL MCP Servers - Supabase Table Migrations
-- Run these migrations in your Supabase SQL editor to create tables for MCP servers

-- 1. Social Media Posts Table
CREATE TABLE IF NOT EXISTS social_posts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    platform TEXT NOT NULL CHECK (platform IN ('youtube', 'discord', 'telegram', 'postiz', 'twitter', 'facebook', 'instagram')),
    content TEXT NOT NULL,
    post_id TEXT, -- External post ID from platform
    media_url TEXT,
    engagement INTEGER DEFAULT 0,
    reach INTEGER DEFAULT 0,
    scheduled_at TIMESTAMPTZ,
    published_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB
);

-- Indexes for social_posts
CREATE INDEX IF NOT EXISTS idx_social_posts_platform ON social_posts(platform);
CREATE INDEX IF NOT EXISTS idx_social_posts_created_at ON social_posts(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_social_posts_post_id ON social_posts(post_id) WHERE post_id IS NOT NULL;

-- 2. AI Memories Table (for Mem0-like persistent memory)
CREATE TABLE IF NOT EXISTS ai_memories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    memory_text TEXT NOT NULL,
    metadata JSONB,
    embedding VECTOR(1536), -- For semantic search (optional, requires pgvector extension)
    importance_score FLOAT DEFAULT 0.5,
    access_count INTEGER DEFAULT 0,
    last_accessed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for ai_memories
CREATE INDEX IF NOT EXISTS idx_ai_memories_user_id ON ai_memories(user_id);
CREATE INDEX IF NOT EXISTS idx_ai_memories_created_at ON ai_memories(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_ai_memories_importance ON ai_memories(importance_score DESC);

-- 3. Approval Requests Table (Human-in-the-Loop)
CREATE TABLE IF NOT EXISTS approval_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    action TEXT NOT NULL,
    description TEXT NOT NULL,
    context JSONB,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected', 'expired')),
    requested_by TEXT, -- User ID or system identifier
    approved_by TEXT,
    approved_at TIMESTAMPTZ,
    rejection_reason TEXT,
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for approval_requests
CREATE INDEX IF NOT EXISTS idx_approval_requests_status ON approval_requests(status);
CREATE INDEX IF NOT EXISTS idx_approval_requests_created_at ON approval_requests(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_approval_requests_requested_by ON approval_requests(requested_by) WHERE requested_by IS NOT NULL;

-- 4. Row Level Security (RLS) Policies
-- Enable RLS on all tables
ALTER TABLE social_posts ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_memories ENABLE ROW LEVEL SECURITY;
ALTER TABLE approval_requests ENABLE ROW LEVEL SECURITY;

-- Basic policies (adjust based on your auth setup)
-- Allow service role to do everything
CREATE POLICY IF NOT EXISTS "Service role full access on social_posts"
    ON social_posts FOR ALL
    USING (auth.role() = 'service_role');

CREATE POLICY IF NOT EXISTS "Service role full access on ai_memories"
    ON ai_memories FOR ALL
    USING (auth.role() = 'service_role');

CREATE POLICY IF NOT EXISTS "Service role full access on approval_requests"
    ON approval_requests FOR ALL
    USING (auth.role() = 'service_role');

-- Allow authenticated users to read their own data
CREATE POLICY IF NOT EXISTS "Users can read own ai_memories"
    ON ai_memories FOR SELECT
    USING (auth.uid()::text = user_id);

CREATE POLICY IF NOT EXISTS "Users can read own approval_requests"
    ON approval_requests FOR SELECT
    USING (auth.uid()::text = requested_by);

-- 5. Functions for automatic updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Triggers for updated_at
CREATE TRIGGER update_social_posts_updated_at
    BEFORE UPDATE ON social_posts
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_ai_memories_updated_at
    BEFORE UPDATE ON ai_memories
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_approval_requests_updated_at
    BEFORE UPDATE ON approval_requests
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- 6. Function to update last_accessed_at for ai_memories
CREATE OR REPLACE FUNCTION update_memory_access()
RETURNS TRIGGER AS $$
BEGIN
    NEW.last_accessed_at = NOW();
    NEW.access_count = OLD.access_count + 1;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Note: This trigger would need to be created per use case
-- Uncomment if you want automatic access tracking
-- CREATE TRIGGER update_ai_memories_access
--     BEFORE UPDATE ON ai_memories
--     FOR EACH ROW
--     WHEN (OLD.last_accessed_at IS DISTINCT FROM NEW.last_accessed_at)
--     EXECUTE FUNCTION update_memory_access();

-- 7. View for social media analytics
CREATE OR REPLACE VIEW social_analytics AS
SELECT
    platform,
    COUNT(*) as total_posts,
    SUM(engagement) as total_engagement,
    SUM(reach) as total_reach,
    AVG(engagement) as avg_engagement,
    AVG(reach) as avg_reach,
    DATE_TRUNC('day', created_at) as date
FROM social_posts
GROUP BY platform, DATE_TRUNC('day', created_at)
ORDER BY date DESC;

-- 8. View for approval statistics
CREATE OR REPLACE VIEW approval_stats AS
SELECT
    status,
    COUNT(*) as count,
    AVG(EXTRACT(EPOCH FROM (COALESCE(approved_at, NOW()) - created_at))) as avg_response_time_seconds
FROM approval_requests
GROUP BY status;

-- Comments
COMMENT ON TABLE social_posts IS 'Stores social media posts from all platforms for tracking and analytics';
COMMENT ON TABLE ai_memories IS 'Persistent memory storage for AI systems (Mem0-like functionality)';
COMMENT ON TABLE approval_requests IS 'Human-in-the-loop approval requests for AI actions';
COMMENT ON VIEW social_analytics IS 'Aggregated social media analytics by platform and date';
COMMENT ON VIEW approval_stats IS 'Statistics on approval request status and response times';







