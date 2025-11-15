-- Add countries column to semantic_groups table
-- This allows downstream services to access countries without re-querying entities

ALTER TABLE public.semantic_groups
ADD COLUMN IF NOT EXISTS countries TEXT[];

-- Create index for country-based queries
CREATE INDEX IF NOT EXISTS idx_semantic_groups_countries ON public.semantic_groups USING GIN(countries);

-- Add comment
COMMENT ON COLUMN public.semantic_groups.countries IS 'List of ISO country codes extracted from NER entities';

