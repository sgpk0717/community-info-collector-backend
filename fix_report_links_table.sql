-- 1. 기존 report_links 데이터 모두 삭제
DELETE FROM report_links;

-- 2. created_utc 컬럼 타입을 double precision에서 timestamp with time zone으로 변경
ALTER TABLE report_links 
ALTER COLUMN created_utc TYPE timestamp with time zone 
USING to_timestamp(created_utc);

-- 3. 변경 확인
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'report_links' 
AND column_name = 'created_utc';