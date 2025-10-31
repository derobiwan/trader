-- Database Initialization Script for LLM Crypto Trading System
-- Created: 2025-10-31

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- For text search
CREATE EXTENSION IF NOT EXISTS "btree_gin";  -- For GIN indexes

-- Create schema
CREATE SCHEMA IF NOT EXISTS trading;

-- Grant permissions
GRANT ALL PRIVILEGES ON SCHEMA trading TO trader;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA trading TO trader;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA trading TO trader;

-- Set default privileges
ALTER DEFAULT PRIVILEGES IN SCHEMA trading
GRANT ALL ON TABLES TO trader;
ALTER DEFAULT PRIVILEGES IN SCHEMA trading
GRANT ALL ON SEQUENCES TO trader;
