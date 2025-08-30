-- Migration: Add thread_shares table for sharing functionality
-- Created: 2025-08-23

-- Create thread_shares table
CREATE TABLE IF NOT EXISTS thread_shares (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    thread_id UUID NOT NULL REFERENCES threads(thread_id) ON DELETE CASCADE,
    public_id UUID NOT NULL UNIQUE,
    title TEXT,
    description TEXT,
    is_public BOOLEAN DEFAULT true,
    allow_comments BOOLEAN DEFAULT false,
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_thread_shares_thread_id ON thread_shares(thread_id);
CREATE INDEX IF NOT EXISTS idx_thread_shares_public_id ON thread_shares(public_id);
CREATE INDEX IF NOT EXISTS idx_thread_shares_expires_at ON thread_shares(expires_at);

-- Add RLS (Row Level Security) policies
ALTER TABLE thread_shares ENABLE ROW LEVEL SECURITY;

-- Policy: Users can manage shares for their own threads
CREATE POLICY "Users can manage their thread shares" ON thread_shares
    FOR ALL USING (
        thread_id IN (
            SELECT thread_id FROM threads 
            WHERE account_id = auth.uid()
        )
    );

-- Policy: Public shares are readable by anyone
CREATE POLICY "Public shares are readable" ON thread_shares
    FOR SELECT USING (is_public = true);

-- Add updated_at trigger
CREATE OR REPLACE FUNCTION update_thread_shares_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_thread_shares_updated_at
    BEFORE UPDATE ON thread_shares
    FOR EACH ROW
    EXECUTE FUNCTION update_thread_shares_updated_at();

-- Add comments for documentation
COMMENT ON TABLE thread_shares IS 'Stores sharing configuration for threads';
COMMENT ON COLUMN thread_shares.thread_id IS 'Reference to the shared thread';
COMMENT ON COLUMN thread_shares.public_id IS 'Public UUID for accessing the shared thread';
COMMENT ON COLUMN thread_shares.title IS 'Custom title for the shared thread';
COMMENT ON COLUMN thread_shares.description IS 'Description of the shared thread';
COMMENT ON COLUMN thread_shares.is_public IS 'Whether the thread is publicly accessible';
COMMENT ON COLUMN thread_shares.allow_comments IS 'Whether comments are allowed on the shared thread';
COMMENT ON COLUMN thread_shares.expires_at IS 'When the share link expires (null = never)';

