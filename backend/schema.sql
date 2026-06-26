-- TruthTrace AI Database Schema (MySQL 8+)

CREATE DATABASE IF NOT EXISTS truthtrace
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE truthtrace;

CREATE TABLE IF NOT EXISTS verification_records (
    id VARCHAR(36) PRIMARY KEY,
    session_id VARCHAR(255),
    user_id VARCHAR(255),
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    confidence_score DOUBLE NOT NULL,
    verification_status VARCHAR(50) NOT NULL,
    sources_count INT DEFAULT 0,
    contradictions_count INT DEFAULT 0,
    sources JSON,
    contradictions JSON,
    trust_report JSON,
    claims JSON,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_verification_session (session_id),
    INDEX idx_verification_user (user_id),
    INDEX idx_verification_created (created_at DESC),
    INDEX idx_verification_status (verification_status)
);

CREATE TABLE IF NOT EXISTS analytics_snapshots (
    id VARCHAR(36) PRIMARY KEY,
    total_queries INT DEFAULT 0,
    verification_rate DOUBLE DEFAULT 0.0,
    average_confidence DOUBLE DEFAULT 0.0,
    sources_used INT DEFAULT 0,
    snapshot_data JSON,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_analytics_created (created_at DESC)
);
