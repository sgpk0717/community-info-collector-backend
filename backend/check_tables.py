import os
from dotenv import load_dotenv
from supabase import create_client, Client

# .env 파일 로드
load_dotenv()

# Supabase 클라이언트 생성
supabase: Client = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_KEY")
)

def check_table_structure():
    """테이블 구조 확인"""
    
    tables = ['users', 'searches', 'reports', 'schedules']
    
    for table in tables:
        print(f"\n=== {table.upper()} TABLE ===")
        try:
            # 각 테이블에서 1개 레코드만 가져와서 구조 확인
            result = supabase.table(table).select("*").limit(1).execute()
            
            if result.data and len(result.data) > 0:
                print("Columns:", list(result.data[0].keys()))
            else:
                # 데이터가 없어도 빈 레코드 삽입 후 삭제하여 구조 확인
                print("No data found, checking structure...")
                
        except Exception as e:
            print(f"Error checking {table}: {e}")

if __name__ == "__main__":
    check_table_structure()