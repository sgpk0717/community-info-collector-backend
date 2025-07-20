-- Call Queue 테이블 생성
CREATE TABLE IF NOT EXISTS public.call_queue (
    id UUID NOT NULL DEFAULT gen_random_uuid(),
    source_url TEXT NOT NULL,
    api_params JSONB DEFAULT '{}'::jsonb,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    source_metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    scheduled_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    retry_count INTEGER NOT NULL DEFAULT 0,
    last_error TEXT,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    CONSTRAINT call_queue_pkey PRIMARY KEY (id),
    CONSTRAINT call_queue_status_check CHECK (status IN ('pending', 'processing', 'completed', 'error', 'failed_retry', 'failed_permanent'))
);

-- 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_call_queue_status ON public.call_queue(status);
CREATE INDEX IF NOT EXISTS idx_call_queue_created_at ON public.call_queue(created_at);
CREATE INDEX IF NOT EXISTS idx_call_queue_status_created ON public.call_queue(status, created_at);

-- Source Contents 테이블 생성 (VECTOR 대신 JSONB 사용)
CREATE TABLE IF NOT EXISTS public.source_contents (
    content_id UUID NOT NULL DEFAULT gen_random_uuid(),
    source_id TEXT NOT NULL,
    source_url TEXT NOT NULL,
    raw_text TEXT NOT NULL,
    processed_text TEXT,
    embedding JSONB,  -- VECTOR 대신 JSONB로 임베딩 저장
    topic_id INTEGER,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    CONSTRAINT source_contents_pkey PRIMARY KEY (content_id)
);

-- 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_source_contents_source_id ON public.source_contents(source_id);
CREATE INDEX IF NOT EXISTS idx_source_contents_topic_id ON public.source_contents(topic_id);

-- Analysis Sections 테이블 생성
CREATE TABLE IF NOT EXISTS public.analysis_sections (
    id UUID NOT NULL DEFAULT gen_random_uuid(),
    report_id UUID NOT NULL,
    topic_id INTEGER,
    topic_label TEXT,
    agent_persona TEXT,
    analysis_text TEXT,
    source_references JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    CONSTRAINT analysis_sections_pkey PRIMARY KEY (id),
    CONSTRAINT analysis_sections_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports(id) ON DELETE CASCADE
);

-- 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_analysis_sections_report_id ON public.analysis_sections(report_id);
CREATE INDEX IF NOT EXISTS idx_analysis_sections_topic_id ON public.analysis_sections(topic_id);