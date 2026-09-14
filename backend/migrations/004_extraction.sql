CREATE TABLE IF NOT EXISTS extraction_fields (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  field_name TEXT NOT NULL,
  raw_value TEXT,
  normalized_value TEXT,
  confidence DOUBLE PRECISION,
  page_number INTEGER,
  evidence_snippet TEXT,
  UNIQUE (document_id, field_name)
);
