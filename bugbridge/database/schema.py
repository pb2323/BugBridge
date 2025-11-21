"""Database schema SQL definitions"""

CREATE_TABLES_SQL = """
-- Feedback Posts Table
CREATE TABLE IF NOT EXISTS feedback_posts (
    id VARCHAR(36) PRIMARY KEY,
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
    tags JSONB,
    collected_at TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_feedback_posts_canny_id ON feedback_posts(canny_post_id);
CREATE INDEX IF NOT EXISTS idx_feedback_posts_collected_at ON feedback_posts(collected_at);

-- Analysis Results Table
CREATE TABLE IF NOT EXISTS analysis_results (
    id VARCHAR(36) PRIMARY KEY,
    feedback_post_id VARCHAR(36) REFERENCES feedback_posts(id),
    is_bug BOOLEAN,
    bug_severity VARCHAR(50),
    confidence FLOAT,
    sentiment VARCHAR(50),
    sentiment_score FLOAT,
    urgency VARCHAR(50),
    priority_score INTEGER,
    is_burning_issue BOOLEAN,
    analysis_data JSONB,
    analyzed_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_analysis_results_post_id ON analysis_results(feedback_post_id);

-- Jira Tickets Table
CREATE TABLE IF NOT EXISTS jira_tickets (
    id VARCHAR(36) PRIMARY KEY,
    feedback_post_id VARCHAR(36) REFERENCES feedback_posts(id),
    jira_issue_key VARCHAR(100) UNIQUE NOT NULL,
    jira_issue_id VARCHAR(255),
    jira_project_key VARCHAR(100),
    status VARCHAR(100),
    priority VARCHAR(50),
    assignee VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW(),
    resolved_at TIMESTAMP,
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_jira_tickets_issue_key ON jira_tickets(jira_issue_key);
CREATE INDEX IF NOT EXISTS idx_jira_tickets_status ON jira_tickets(status);

-- Workflow States Table
CREATE TABLE IF NOT EXISTS workflow_states (
    id VARCHAR(36) PRIMARY KEY,
    feedback_post_id VARCHAR(36) REFERENCES feedback_posts(id),
    workflow_status VARCHAR(100),
    state_data JSONB,
    last_updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_workflow_states_status ON workflow_states(workflow_status);

-- Notifications Table
CREATE TABLE IF NOT EXISTS notifications (
    id VARCHAR(36) PRIMARY KEY,
    feedback_post_id VARCHAR(36) REFERENCES feedback_posts(id),
    jira_ticket_id VARCHAR(36) REFERENCES jira_tickets(id),
    notification_type VARCHAR(100),
    notification_status VARCHAR(100),
    reply_content TEXT,
    sent_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Reports Table
CREATE TABLE IF NOT EXISTS reports (
    id VARCHAR(36) PRIMARY KEY,
    report_type VARCHAR(100),
    report_date DATE,
    report_content TEXT,
    metrics JSONB,
    generated_at TIMESTAMP DEFAULT NOW()
);
"""

DROP_TABLES_SQL = """
DROP TABLE IF EXISTS notifications CASCADE;
DROP TABLE IF EXISTS reports CASCADE;
DROP TABLE IF EXISTS workflow_states CASCADE;
DROP TABLE IF EXISTS jira_tickets CASCADE;
DROP TABLE IF EXISTS analysis_results CASCADE;
DROP TABLE IF EXISTS feedback_posts CASCADE;
"""
