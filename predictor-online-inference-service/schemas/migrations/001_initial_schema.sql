-- Initial schema for predictor service
-- Creates tables for predictions and audit trail

CREATE SCHEMA IF NOT EXISTS predictor;

-- Predictions table
CREATE TABLE IF NOT EXISTS predictions (
    id SERIAL PRIMARY KEY,
    group_id VARCHAR(255) NOT NULL,
    domain VARCHAR(100) NOT NULL,
    prediction_probability FLOAT NOT NULL,
    prediction_confidence FLOAT NOT NULL,
    model_version VARCHAR(100) NOT NULL,
    features JSONB,
    predicted_at TIMESTAMP WITH TIME ZONE NOT NULL,
    trace_id VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Prediction audit log table
CREATE TABLE IF NOT EXISTS prediction_audit_log (
    id SERIAL PRIMARY KEY,
    group_id VARCHAR(255) NOT NULL,
    action VARCHAR(100) NOT NULL,
    details JSONB,
    performed_by VARCHAR(100) DEFAULT 'predictor-service',
    performed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_predictions_group_id ON predictions(group_id);
CREATE INDEX IF NOT EXISTS idx_predictions_domain ON predictions(domain);
CREATE INDEX IF NOT EXISTS idx_predictions_predicted_at ON predictions(predicted_at DESC);
CREATE INDEX IF NOT EXISTS idx_predictions_trace_id ON predictions(trace_id);
CREATE INDEX IF NOT EXISTS idx_prediction_audit_log_group_id ON prediction_audit_log(group_id);
CREATE INDEX IF NOT EXISTS idx_prediction_audit_log_action ON prediction_audit_log(action);

-- Create views for common queries
CREATE OR REPLACE VIEW recent_predictions AS
SELECT 
    id,
    group_id,
    domain,
    prediction_probability,
    prediction_confidence,
    model_version,
    predicted_at,
    trace_id
FROM predictions
WHERE predicted_at > NOW() - INTERVAL '7 days'
ORDER BY predicted_at DESC;

CREATE OR REPLACE VIEW high_confidence_predictions AS
SELECT 
    id,
    group_id,
    domain,
    prediction_probability,
    prediction_confidence,
    model_version,
    predicted_at
FROM predictions
WHERE prediction_confidence >= 0.80
ORDER BY prediction_confidence DESC, predicted_at DESC;

