ALTER TABLE documents ADD COLUMN IF NOT EXISTS workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS uploaded_by UUID REFERENCES users(id) ON DELETE SET NULL;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS original_filename TEXT;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS extension VARCHAR(20);
ALTER TABLE documents ADD COLUMN IF NOT EXISTS declared_mime VARCHAR(100);
ALTER TABLE documents ADD COLUMN IF NOT EXISTS detected_mime VARCHAR(100);
ALTER TABLE documents ADD COLUMN IF NOT EXISTS file_size BIGINT;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS sha256 CHAR(64);
ALTER TABLE documents ADD COLUMN IF NOT EXISTS scan_status VARCHAR(50) DEFAULT 'pending';
ALTER TABLE documents ADD COLUMN IF NOT EXISTS processing_status VARCHAR(50) DEFAULT 'uploaded';
ALTER TABLE documents ADD COLUMN IF NOT EXISTS document_type VARCHAR(50);

CREATE INDEX IF NOT EXISTS idx_documents_workspace_created
  ON documents (workspace_id, created_at DESC);

CREATE UNIQUE INDEX IF NOT EXISTS uq_document_workspace_hash
  ON documents (workspace_id, sha256)
  WHERE workspace_id IS NOT NULL AND sha256 IS NOT NULL;
