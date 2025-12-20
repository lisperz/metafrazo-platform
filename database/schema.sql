-- Video Text Inpainting Service Database Schema
-- PostgreSQL implementation with comprehensive user management and job tracking

-- ============================================================================
-- 1. USER MANAGEMENT TABLES
-- ============================================================================

-- Subscription tiers and plans
CREATE TABLE subscription_tiers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE, -- 'free', 'pro', 'enterprise'
    display_name VARCHAR(100) NOT NULL,
    description TEXT,
    price_monthly DECIMAL(10,2) DEFAULT 0,
    price_yearly DECIMAL(10,2) DEFAULT 0,
    credits_per_month INTEGER DEFAULT 0,
    max_video_length_seconds INTEGER DEFAULT 300, -- 5 minutes default
    max_file_size_mb INTEGER DEFAULT 500,
    max_concurrent_jobs INTEGER DEFAULT 1,
    api_access BOOLEAN DEFAULT FALSE,
    priority_processing BOOLEAN DEFAULT FALSE,
    features JSONB DEFAULT '[]', -- Array of feature flags
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Users table for authentication and profiles
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    company VARCHAR(255),
    phone VARCHAR(20),
    profile_picture_url TEXT,
    email_verified BOOLEAN DEFAULT FALSE,
    email_verification_token VARCHAR(255),
    password_reset_token VARCHAR(255),
    password_reset_expires TIMESTAMP,
    subscription_tier_id INTEGER REFERENCES subscription_tiers(id) DEFAULT 1,
    credits_balance INTEGER DEFAULT 100, -- Starting credits
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'suspended', 'deleted')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login_at TIMESTAMP,
    login_count INTEGER DEFAULT 0,
    preferences JSONB DEFAULT '{}', -- User preferences as JSON
    metadata JSONB DEFAULT '{}'     -- Additional flexible data
);

-- User sessions for authentication
CREATE TABLE user_sessions (
    id SERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_token VARCHAR(255) UNIQUE NOT NULL,
    refresh_token VARCHAR(255) UNIQUE,
    ip_address INET,
    user_agent TEXT,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_accessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- 2. CREDITS AND BILLING SYSTEM
-- ============================================================================

-- Credit transactions and balance tracking
CREATE TABLE credit_transactions (
    id SERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    transaction_type VARCHAR(20) NOT NULL CHECK (transaction_type IN ('purchase', 'usage', 'refund', 'bonus', 'expiration')),
    amount INTEGER NOT NULL, -- Positive for credit, negative for debit
    balance_after INTEGER NOT NULL, -- Running balance after this transaction
    description TEXT,
    reference_type VARCHAR(50), -- 'payment', 'video_job', 'manual_adjustment'
    reference_id VARCHAR(255), -- ID of related payment or job
    expires_at TIMESTAMP, -- For credits that expire
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'
);

-- Credit packages for purchase
CREATE TABLE credit_packages (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    credits INTEGER NOT NULL,
    price DECIMAL(10,2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD',
    bonus_credits INTEGER DEFAULT 0, -- Extra credits for bulk purchases
    expiry_days INTEGER, -- Credits expire after X days
    is_active BOOLEAN DEFAULT TRUE,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- 3. VIDEO PROCESSING JOBS
-- ============================================================================

-- Main jobs table
CREATE TABLE video_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE, -- Nullable for embedded jobs

    -- Job identification
    original_filename VARCHAR(500) NOT NULL,
    display_name VARCHAR(500),

    -- Job status and progress
    status VARCHAR(20) NOT NULL DEFAULT 'queued' CHECK (status IN ('queued', 'uploading', 'processing', 'completed', 'failed', 'canceled')),
    progress_percentage INTEGER DEFAULT 0 CHECK (progress_percentage >= 0 AND progress_percentage <= 100),
    progress_message TEXT,

    -- Processing configuration
    processing_config JSONB NOT NULL DEFAULT '{}', -- Font, languages, regions, etc.
    zhaoli_task_id VARCHAR(255), -- External API task ID
    estimated_credits INTEGER,
    actual_credits_used INTEGER,

    -- Pro Video Editor Support
    is_pro_job BOOLEAN DEFAULT FALSE,
    segments_data JSONB, -- Segment configurations for Pro jobs

    -- Embedded Mode Support (phraze.so integration)
    is_embedded_job BOOLEAN DEFAULT FALSE,

    -- File information
    input_file_size_mb DECIMAL(8,2),
    output_file_size_mb DECIMAL(8,2),
    output_url TEXT, -- URL to download the processed video
    video_duration_seconds INTEGER,
    video_resolution VARCHAR(20), -- '1080p', '720p', etc.

    -- Processing times
    queued_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    processing_duration_seconds INTEGER,

    -- Error handling
    error_message TEXT,
    error_code VARCHAR(50),
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,

    -- Metadata and audit
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}' -- Flexible storage for additional data
);

-- Job status history for audit trail
CREATE TABLE job_status_history (
    id SERIAL PRIMARY KEY,
    job_id UUID NOT NULL REFERENCES video_jobs(id) ON DELETE CASCADE,
    old_status VARCHAR(20),
    new_status VARCHAR(20) NOT NULL,
    progress_percentage INTEGER,
    message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'
);

-- ============================================================================
-- 4. FILE MANAGEMENT
-- ============================================================================

-- File storage tracking
CREATE TABLE files (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    job_id UUID REFERENCES video_jobs(id) ON DELETE CASCADE,
    
    -- File identification
    filename VARCHAR(500) NOT NULL,
    original_filename VARCHAR(500),
    
    -- File type and purpose
    file_type VARCHAR(20) NOT NULL CHECK (file_type IN ('input_video', 'output_video', 'thumbnail', 'preview')),
    mime_type VARCHAR(100),
    file_extension VARCHAR(10),
    
    -- Storage information
    storage_provider VARCHAR(20) NOT NULL CHECK (storage_provider IN ('aws_s3', 'gcp_storage', 'local')) DEFAULT 'aws_s3',
    storage_path TEXT NOT NULL, -- Full path/URL to file
    storage_bucket VARCHAR(255),
    storage_region VARCHAR(50),
    
    -- File metadata
    file_size_bytes BIGINT,
    checksum_md5 VARCHAR(32),
    checksum_sha256 VARCHAR(64),
    
    -- Access control
    is_public BOOLEAN DEFAULT FALSE,
    public_url TEXT,
    download_count INTEGER DEFAULT 0,
    expires_at TIMESTAMP, -- For temporary files
    
    -- Audit
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'
);

-- ============================================================================
-- 5. API KEYS AND ACCESS CONTROL
-- ============================================================================

-- API keys for external access
CREATE TABLE api_keys (
    id SERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Key identification
    key_name VARCHAR(100) NOT NULL,
    api_key_hash VARCHAR(255) NOT NULL, -- Hashed version of the key
    api_key_prefix VARCHAR(20) NOT NULL, -- First few chars for identification
    
    -- Access control
    is_active BOOLEAN DEFAULT TRUE,
    permissions JSONB DEFAULT '[]', -- Array of allowed operations
    rate_limit_per_hour INTEGER DEFAULT 100,
    allowed_ips JSONB, -- Array of allowed IP addresses
    
    -- Usage tracking
    last_used_at TIMESTAMP,
    total_requests INTEGER DEFAULT 0,
    
    -- Lifecycle
    expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- 6. SYSTEM CONFIGURATION
-- ============================================================================

-- Global system settings
CREATE TABLE system_settings (
    id SERIAL PRIMARY KEY,
    setting_key VARCHAR(100) UNIQUE NOT NULL,
    setting_value TEXT,
    setting_type VARCHAR(20) DEFAULT 'string' CHECK (setting_type IN ('string', 'integer', 'boolean', 'json')),
    description TEXT,
    is_encrypted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- INDEXES FOR PERFORMANCE
-- ============================================================================

-- User table indexes
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_subscription_tier ON users(subscription_tier_id);
CREATE INDEX idx_users_status ON users(status);
CREATE INDEX idx_users_created_at ON users(created_at);

-- Session indexes
CREATE INDEX idx_user_sessions_token ON user_sessions(session_token);
CREATE INDEX idx_user_sessions_user_id ON user_sessions(user_id);
CREATE INDEX idx_user_sessions_expires_at ON user_sessions(expires_at);

-- Credit transaction indexes
CREATE INDEX idx_credit_transactions_user_id ON credit_transactions(user_id);
CREATE INDEX idx_credit_transactions_created_at ON credit_transactions(created_at);
CREATE INDEX idx_credit_transactions_type ON credit_transactions(transaction_type);

-- Video jobs indexes
CREATE INDEX idx_video_jobs_user_id ON video_jobs(user_id);
CREATE INDEX idx_video_jobs_status ON video_jobs(status);
CREATE INDEX idx_video_jobs_created_at ON video_jobs(created_at);
CREATE INDEX idx_video_jobs_zhaoli_task_id ON video_jobs(zhaoli_task_id);

-- Files indexes
CREATE INDEX idx_files_user_id ON files(user_id);
CREATE INDEX idx_files_job_id ON files(job_id);
CREATE INDEX idx_files_type ON files(file_type);
CREATE INDEX idx_files_created_at ON files(created_at);

-- API keys indexes
CREATE INDEX idx_api_keys_user_id ON api_keys(user_id);
CREATE INDEX idx_api_keys_hash ON api_keys(api_key_hash);
CREATE INDEX idx_api_keys_active ON api_keys(is_active);

-- ============================================================================
-- TRIGGERS FOR AUTOMATED UPDATES
-- ============================================================================

-- Automatically update updated_at timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply the trigger to relevant tables
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_subscription_tiers_updated_at BEFORE UPDATE ON subscription_tiers FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_video_jobs_updated_at BEFORE UPDATE ON video_jobs FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_files_updated_at BEFORE UPDATE ON files FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_api_keys_updated_at BEFORE UPDATE ON api_keys FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_system_settings_updated_at BEFORE UPDATE ON system_settings FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- SAMPLE DATA FOR DEVELOPMENT
-- ============================================================================

-- Insert default subscription tiers
INSERT INTO subscription_tiers (name, display_name, description, price_monthly, price_yearly, credits_per_month, max_video_length_seconds, max_file_size_mb, max_concurrent_jobs, features) VALUES
('free', 'Free Tier', 'Perfect for trying out our service', 0, 0, 100, 300, 100, 1, '["basic_processing"]'),
('pro', 'Pro Plan', 'For regular users and small businesses', 29.99, 299.99, 1000, 1800, 500, 3, '["basic_processing", "priority_support", "api_access"]'),
('enterprise', 'Enterprise Plan', 'For large organizations', 99.99, 999.99, 5000, 7200, 2000, 10, '["basic_processing", "priority_support", "api_access", "custom_models", "dedicated_support"]');

-- Insert default credit packages
INSERT INTO credit_packages (name, description, credits, price, bonus_credits, expiry_days) VALUES
('Starter Pack', 'Perfect for occasional use', 100, 9.99, 0, 365),
('Power Pack', 'Great value for regular users', 500, 39.99, 50, 365),
('Pro Pack', 'Best for heavy users', 1000, 69.99, 150, 365),
('Enterprise Pack', 'Maximum credits for teams', 5000, 299.99, 1000, 365);

-- Insert default system settings
INSERT INTO system_settings (setting_key, setting_value, setting_type, description) VALUES
('max_upload_size_mb', '1000', 'integer', 'Maximum file upload size in MB'),
('default_video_quality', '1080p', 'string', 'Default video processing quality'),
('support_email', 'support@example.com', 'string', 'Support email address'),
('maintenance_mode', 'false', 'boolean', 'Enable maintenance mode'),
('api_rate_limit_default', '100', 'integer', 'Default API rate limit per hour'),
('credit_cost_per_minute', '10', 'integer', 'Credits cost per minute of video');