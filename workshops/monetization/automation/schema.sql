-- StackKraft Enterprise Content Distribution System
-- PostgreSQL Database Schema

-- Drop existing tables if rerunning
DROP TABLE IF EXISTS analytics CASCADE;
DROP TABLE IF EXISTS posts CASCADE;
DROP TABLE IF EXISTS rate_limits CASCADE;
DROP TABLE IF EXISTS optimal_times CASCADE;

-- Content posts tracking
CREATE TABLE posts (
    id SERIAL PRIMARY KEY,
    clip_id VARCHAR(255) NOT NULL,
    platform VARCHAR(50) NOT NULL CHECK (platform IN ('tiktok', 'youtube', 'instagram', 'twitter', 'linkedin', 'facebook')),
    platform_post_id VARCHAR(255),
    title TEXT NOT NULL,
    description TEXT,
    video_path TEXT NOT NULL,
    thumbnail_path TEXT,
    duration_seconds INT,
    file_size_bytes BIGINT,
    aspect_ratio VARCHAR(10),
    status VARCHAR(50) DEFAULT 'pending' CHECK (status IN ('pending', 'queued', 'processing', 'posted', 'failed', 'deleted')),
    scheduled_at TIMESTAMP,
    published_at TIMESTAMP,
    retry_count INT DEFAULT 0,
    max_retries INT DEFAULT 3,
    error_message TEXT,
    metadata JSONB, -- Store platform-specific metadata
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_posts_status ON posts(status);
CREATE INDEX idx_posts_platform ON posts(platform);
CREATE INDEX idx_posts_scheduled ON posts(scheduled_at) WHERE status = 'queued';
CREATE INDEX idx_posts_clip_id ON posts(clip_id);
CREATE INDEX idx_posts_published_at ON posts(published_at);
CREATE INDEX idx_posts_metadata ON posts USING GIN(metadata);

-- Trigger to update updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_posts_updated_at BEFORE UPDATE ON posts
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Analytics tracking
CREATE TABLE analytics (
    id SERIAL PRIMARY KEY,
    post_id INT REFERENCES posts(id) ON DELETE CASCADE,
    platform VARCHAR(50) NOT NULL,
    views INT DEFAULT 0,
    likes INT DEFAULT 0,
    comments INT DEFAULT 0,
    shares INT DEFAULT 0,
    saves INT DEFAULT 0,
    watch_time_seconds BIGINT DEFAULT 0,
    engagement_rate DECIMAL(5,2), -- (likes + comments + shares) / views * 100
    click_through_rate DECIMAL(5,2),
    revenue_cents INT DEFAULT 0,
    currency VARCHAR(3) DEFAULT 'USD',
    metrics JSONB, -- Platform-specific metrics
    synced_at TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_analytics_post_id ON analytics(post_id);
CREATE INDEX idx_analytics_synced_at ON analytics(synced_at);
CREATE INDEX idx_analytics_engagement ON analytics(engagement_rate DESC);

-- Rate limiting tracking per platform/endpoint
CREATE TABLE rate_limits (
    id SERIAL PRIMARY KEY,
    platform VARCHAR(50) NOT NULL,
    endpoint VARCHAR(255) NOT NULL,
    limit_total INT NOT NULL,
    limit_remaining INT NOT NULL,
    limit_window_seconds INT DEFAULT 3600, -- 1 hour default
    reset_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(platform, endpoint)
);

CREATE INDEX idx_rate_limits_platform ON rate_limits(platform);
CREATE INDEX idx_rate_limits_reset ON rate_limits(reset_at);

-- Posting schedule optimization (ML-driven)
CREATE TABLE optimal_times (
    id SERIAL PRIMARY KEY,
    platform VARCHAR(50) NOT NULL,
    day_of_week INT NOT NULL CHECK (day_of_week BETWEEN 0 AND 6), -- 0=Sunday
    hour INT NOT NULL CHECK (hour BETWEEN 0 AND 23),
    avg_engagement DECIMAL(5,2),
    avg_views INT,
    avg_revenue_cents INT,
    sample_size INT DEFAULT 0,
    confidence_score DECIMAL(3,2), -- 0.00 to 1.00
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(platform, day_of_week, hour)
);

CREATE INDEX idx_optimal_platform ON optimal_times(platform);
CREATE INDEX idx_optimal_engagement ON optimal_times(avg_engagement DESC);

-- Initial rate limits (will be updated dynamically)
INSERT INTO rate_limits (platform, endpoint, limit_total, limit_remaining, limit_window_seconds, reset_at) VALUES
    ('youtube', 'videos.insert', 100, 100, 86400, NOW() + INTERVAL '1 day'),
    ('tiktok', 'content.publish', 100, 100, 86400, NOW() + INTERVAL '1 day'),
    ('instagram', 'media.publish', 25, 25, 86400, NOW() + INTERVAL '1 day'),
    ('twitter', 'tweets', 50, 50, 86400, NOW() + INTERVAL '1 day');

-- Views for reporting
CREATE VIEW posts_summary AS
SELECT 
    platform,
    status,
    COUNT(*) as total_posts,
    AVG(retry_count) as avg_retries,
    MIN(created_at) as first_post,
    MAX(published_at) as last_published
FROM posts
GROUP BY platform, status;

CREATE VIEW engagement_summary AS
SELECT 
    p.platform,
    COUNT(DISTINCT p.id) as total_posts,
    SUM(a.views) as total_views,
    SUM(a.likes) as total_likes,
    SUM(a.comments) as total_comments,
    SUM(a.shares) as total_shares,
    AVG(a.engagement_rate) as avg_engagement_rate,
    SUM(a.revenue_cents) / 100.0 as total_revenue_dollars
FROM posts p
LEFT JOIN analytics a ON p.id = a.post_id
WHERE p.status = 'posted'
GROUP BY p.platform;

-- Grant permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO roxy;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO roxy;
GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public TO roxy;

-- Success message
\echo 'Database schema created successfully!'
\echo 'Tables: posts, analytics, rate_limits, optimal_times'
\echo 'Views: posts_summary, engagement_summary'
