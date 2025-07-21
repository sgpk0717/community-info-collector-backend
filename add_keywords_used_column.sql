-- Supabase reports 테이블에 keywords_used 컬럼 추가
-- 이 SQL을 Supabase SQL Editor에서 실행하세요

-- keywords_used 컬럼 추가 (JSONB 타입)
ALTER TABLE public.reports 
ADD COLUMN IF NOT EXISTS keywords_used JSONB;

-- 컬럼에 대한 설명 추가
COMMENT ON COLUMN public.reports.keywords_used IS '분석에 사용된 키워드 정보 (원본 키워드, 번역된 키워드, 확장 키워드 등)';

-- 기존 데이터에 대해 NULL 허용
-- 새로운 보고서부터는 이 정보가 저장됩니다