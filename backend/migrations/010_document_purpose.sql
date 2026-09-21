-- Purpose-first upload: classify before field extraction.
ALTER TABLE documents ADD COLUMN IF NOT EXISTS purpose_status VARCHAR(50);
ALTER TABLE documents ADD COLUMN IF NOT EXISTS purpose_category VARCHAR(100);
ALTER TABLE documents ADD COLUMN IF NOT EXISTS purpose_subtype VARCHAR(100);
ALTER TABLE documents ADD COLUMN IF NOT EXISTS purpose_reason TEXT;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS purpose_confidence DOUBLE PRECISION;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS page_count INTEGER;
