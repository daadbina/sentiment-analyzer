-- Create semantic_groups table in public schema
-- This table is used by labeler, feature-engineering, and other downstream services

CREATE TABLE IF NOT EXISTS public.semantic_groups (
    id SERIAL PRIMARY KEY,
    group_id UUID NOT NULL UNIQUE,
    article_ids TEXT[],
    article_count INTEGER NOT NULL DEFAULT 0,
    similarity_avg FLOAT NOT NULL DEFAULT 0.0,
    topic_label VARCHAR(255),
    centroid_vector TEXT,  -- JSON string representation of vector
    cluster_metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_semantic_groups_group_id ON public.semantic_groups(group_id);
CREATE INDEX IF NOT EXISTS idx_semantic_groups_created_at ON public.semantic_groups(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_semantic_groups_article_count ON public.semantic_groups(article_count DESC);

