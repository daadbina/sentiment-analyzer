-- Initial schema for clustering service
-- Creates tables for cluster registry and audit trail

CREATE SCHEMA IF NOT EXISTS clustering;

-- Clusters table
CREATE TABLE IF NOT EXISTS clustering.clusters (
    id SERIAL PRIMARY KEY,
    group_id UUID NOT NULL UNIQUE,
    article_ids TEXT[] NOT NULL,
    article_count INTEGER NOT NULL,
    similarity_avg FLOAT NOT NULL,
    topic_label VARCHAR(255),
    centroid_vector FLOAT8[] NOT NULL,
    metadata JSONB,
    stability_score FLOAT DEFAULT 0.5,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100) DEFAULT 'clustering-service'
);

-- Cluster history table for temporal tracking
CREATE TABLE IF NOT EXISTS clustering.cluster_history (
    id SERIAL PRIMARY KEY,
    group_id UUID NOT NULL,
    article_ids TEXT[] NOT NULL,
    article_count INTEGER NOT NULL,
    centroid_vector FLOAT8[],
    similarity_avg FLOAT,
    snapshot_at TIMESTAMP WITH TIME ZONE NOT NULL,
    FOREIGN KEY (group_id) REFERENCES clustering.clusters(group_id) ON DELETE CASCADE
);

-- Cluster evolution table for tracking merges and splits
CREATE TABLE IF NOT EXISTS clustering.cluster_evolution (
    id SERIAL PRIMARY KEY,
    parent_group_id UUID,
    child_group_id UUID NOT NULL,
    evolution_type VARCHAR(50) NOT NULL,
    similarity_score FLOAT,
    evolved_at TIMESTAMP WITH TIME ZONE NOT NULL,
    metadata JSONB,
    FOREIGN KEY (child_group_id) REFERENCES clustering.clusters(group_id) ON DELETE CASCADE
);

-- Audit trail table
CREATE TABLE IF NOT EXISTS clustering.audit_log (
    id SERIAL PRIMARY KEY,
    group_id UUID,
    action VARCHAR(100) NOT NULL,
    details JSONB,
    performed_by VARCHAR(100) DEFAULT 'clustering-service',
    performed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_clusters_created_at ON clustering.clusters(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_clusters_stability ON clustering.clusters(stability_score DESC);
CREATE INDEX IF NOT EXISTS idx_cluster_history_group_id ON clustering.cluster_history(group_id, snapshot_at DESC);
CREATE INDEX IF NOT EXISTS idx_cluster_evolution_type ON clustering.cluster_evolution(evolution_type);
CREATE INDEX IF NOT EXISTS idx_audit_log_action ON clustering.audit_log(action);

-- Create views for common queries
CREATE OR REPLACE VIEW clustering.recent_clusters AS
SELECT 
    group_id,
    article_count,
    similarity_avg,
    topic_label,
    stability_score,
    created_at
FROM clustering.clusters
WHERE created_at > NOW() - INTERVAL '7 days'
ORDER BY created_at DESC;

CREATE OR REPLACE VIEW clustering.stable_clusters AS
SELECT 
    group_id,
    article_count,
    similarity_avg,
    topic_label,
    stability_score,
    created_at
FROM clustering.clusters
WHERE stability_score >= 0.70
ORDER BY stability_score DESC;

CREATE OR REPLACE VIEW clustering.cluster_statistics AS
SELECT 
    COUNT(*) as total_clusters,
    AVG(article_count) as avg_articles_per_cluster,
    MAX(article_count) as max_articles,
    MIN(article_count) as min_articles,
    AVG(similarity_avg) as avg_similarity,
    AVG(stability_score) as avg_stability,
    COUNT(CASE WHEN stability_score >= 0.70 THEN 1 END) as stable_clusters
FROM clustering.clusters
WHERE created_at > NOW() - INTERVAL '24 hours';

