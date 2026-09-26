-- ==============================================================================
-- Facebook Group Research Agent - Supabase Database Schema
-- Migration / Initial Setup: supabase/schema.sql
-- ==============================================================================

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ------------------------------------------------------------------------------
-- 1. GROUPS TABLE
-- Stores unique Facebook groups discovered through search queries.
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS groups (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    facebook_url TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    description TEXT,
    member_count BIGINT,
    member_count_text TEXT,
    privacy TEXT,
    niche TEXT,
    country TEXT,
    source TEXT DEFAULT 'facebook_search',
    matched_keywords TEXT[] DEFAULT '{}',
    discovered_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for fast lookups and dashboard sorting
CREATE INDEX IF NOT EXISTS idx_groups_facebook_url ON groups(facebook_url);
CREATE INDEX IF NOT EXISTS idx_groups_discovered_at ON groups(discovered_at DESC);
CREATE INDEX IF NOT EXISTS idx_groups_niche ON groups(niche);
CREATE INDEX IF NOT EXISTS idx_groups_country ON groups(country);

-- ------------------------------------------------------------------------------
-- 2. ANALYSES TABLE
-- Stores Gemini LLM intelligence, activity score, rules & external link audits.
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS analyses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    group_id UUID NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
    activity_status TEXT,
    activity_score NUMERIC(5, 2),
    external_link_status TEXT,
    external_link_evidence TEXT,
    rules_summary TEXT,
    activity_summary TEXT,
    overall_summary TEXT,
    rules_evidence JSONB DEFAULT '{}'::jsonb,
    recent_posts_evidence JSONB DEFAULT '[]'::jsonb,
    external_urls TEXT[] DEFAULT '{}',
    analysis_raw_json JSONB DEFAULT '{}'::jsonb,
    analyzed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT unique_group_analysis UNIQUE (group_id)
);

-- Indexes for analyses filtering and joining
CREATE INDEX IF NOT EXISTS idx_analyses_group_id ON analyses(group_id);
CREATE INDEX IF NOT EXISTS idx_analyses_activity_status ON analyses(activity_status);
CREATE INDEX IF NOT EXISTS idx_analyses_external_link_status ON analyses(external_link_status);
CREATE INDEX IF NOT EXISTS idx_analyses_analyzed_at ON analyses(analyzed_at DESC);

-- ------------------------------------------------------------------------------
-- 3. AUTOMATIC updated_at TRIGGER FUNCTION
-- ------------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_groups_updated_at ON groups;
CREATE TRIGGER trg_groups_updated_at
    BEFORE UPDATE ON groups
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS trg_analyses_updated_at ON analyses;
CREATE TRIGGER trg_analyses_updated_at
    BEFORE UPDATE ON analyses
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
