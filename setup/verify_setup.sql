-- Verify semantic model upload
-- Run this in Snowflake to confirm the setup

USE ROLE SYSADMIN;
USE WAREHOUSE TEST;
USE DATABASE PLAYGROUND_LM;
USE SCHEMA GCP_REPORTING_ORCHESTRATOR;

-- List files in the semantic models stage
LIST @SEMANTIC_MODELS;

-- Read the semantic model content
SELECT $1 FROM @SEMANTIC_MODELS/semantic_model_latest.yaml;

-- Verify all stages exist
SHOW STAGES IN SCHEMA GCP_REPORTING_ORCHESTRATOR;

-- Check table exists
SHOW TABLES LIKE 'INCREMENTALITY_ANALYSIS_DUMMY';

-- Sample query on the table
SELECT COUNT(*) as total_rows FROM INCREMENTALITY_ANALYSIS_DUMMY;
