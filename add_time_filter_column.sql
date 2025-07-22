-- reports 테이블에 time_filter 컬럼 추가
-- 기존 데이터는 NULL로 설정됨

ALTER TABLE reports 
ADD COLUMN IF NOT EXISTS time_filter text;

-- 컬럼 추가 확인
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'reports' 
AND column_name = 'time_filter';