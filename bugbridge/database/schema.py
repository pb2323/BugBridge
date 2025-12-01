"""
Database Schema SQL

PostgreSQL CREATE TABLE statements matching the ORM models.
"""

SCHEMA_SQL = """
-- Feedback Posts
CREATE TABLE IF NOT EXISTS feedback_posts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    canny_post_id VARCHAR(255) UNIQUE NOT NULL,
    board_id VARCHAR(255) NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    author_id VARCHAR(255),
    author_name VARCHAR(255),
    votes INTEGER DEFAULT 0,
    comments_count INTEGER DEFAULT 0,
    status VARCHAR(100),
    url TEXT,
    tags TEXT[],
    collected_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Analysis Results
CREATE TABLE IF NOT EXISTS analysis_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    feedback_post_id UUID REFERENCES feedback_posts(id) ON DELETE CASCADE,
    is_bug BOOLEAN,
    bug_severity VARCHAR(50),
    confidence FLOAT,
    sentiment VARCHAR(50),
    sentiment_score FLOAT,
    urgency VARCHAR(50),
    priority_score INTEGER,
    is_burning_issue BOOLEAN DEFAULT FALSE,
    analysis_data JSONB,
    analyzed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_analysis_results_post_id ON analysis_results(feedback_post_id);

-- Jira Tickets
CREATE TABLE IF NOT EXISTS jira_tickets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    feedback_post_id UUID REFERENCES feedback_posts(id) ON DELETE SET NULL,
    jira_issue_key VARCHAR(100) UNIQUE NOT NULL,
    jira_issue_id VARCHAR(255),
    jira_project_key VARCHAR(100),
    status VARCHAR(100),
    priority VARCHAR(50),
    assignee VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    resolved_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_jira_tickets_issue_key ON jira_tickets(jira_issue_key);
CREATE INDEX IF NOT EXISTS idx_jira_tickets_status ON jira_tickets(status);

-- Workflow States
CREATE TABLE IF NOT EXISTS workflow_states (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    feedback_post_id UUID REFERENCES feedback_posts(id) ON DELETE CASCADE,
    workflow_status VARCHAR(100) NOT NULL,
    state_data JSONB,
    last_updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_workflow_states_status ON workflow_states(workflow_status);

-- Notifications
CREATE TABLE IF NOT EXISTS notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    feedback_post_id UUID REFERENCES feedback_posts(id) ON DELETE CASCADE,
    jira_ticket_id UUID REFERENCES jira_tickets(id) ON DELETE SET NULL,
    notification_type VARCHAR(100) NOT NULL,
    notification_status VARCHAR(100) NOT NULL,
    reply_content TEXT,
    sent_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_notifications_status ON notifications(notification_status);

-- Reports
CREATE TABLE IF NOT EXISTS reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    report_type VARCHAR(100) NOT NULL,
    report_date DATE NOT NULL,
    report_content TEXT,
    metrics JSONB,
    generated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_reports_type ON reports(report_type);
CREATE INDEX IF NOT EXISTS idx_reports_date ON reports(report_date);

-- Users
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'viewer',
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_login_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
"""

