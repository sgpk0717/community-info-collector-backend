from app.core.dependencies import get_supabase_client
import json

def test_supabase_connection():
    """Supabase 연결 및 테이블 구조 확인"""
    client = get_supabase_client()
    
    try:
        # users 테이블 정보 조회 (한 개 레코드만)
        print("1. users 테이블 구조 확인:")
        result = client.table('users').select("*").limit(1).execute()
        if result.data:
            print("샘플 데이터:", json.dumps(result.data[0], indent=2))
            print("컬럼명:", list(result.data[0].keys()))
        else:
            print("users 테이블이 비어있습니다.")
            # 테이블 구조를 알기 위해 빈 레코드를 조회
            try:
                # 존재하지 않는 ID로 조회하여 구조 확인
                result = client.table('users').select("*").eq('id', '00000000-0000-0000-0000-000000000000').execute()
                print("빈 조회 결과:", result)
            except Exception as e:
                print(f"조회 중 오류: {str(e)}")
        
        print("\n2. reports 테이블 구조 확인:")
        result = client.table('reports').select("*").limit(1).execute()
        if result.data:
            print("샘플 데이터:", json.dumps(result.data[0], indent=2, default=str))
            print("컬럼명:", list(result.data[0].keys()))
        else:
            print("reports 테이블이 비어있습니다.")
            
        print("\n3. schedules 테이블 구조 확인:")
        result = client.table('schedules').select("*").limit(1).execute()
        if result.data:
            print("샘플 데이터:", json.dumps(result.data[0], indent=2, default=str))
            print("컬럼명:", list(result.data[0].keys()))
        else:
            print("schedules 테이블이 비어있습니다.")
            
    except Exception as e:
        print(f"오류 발생: {str(e)}")
        print(f"오류 타입: {type(e).__name__}")
        if hasattr(e, 'response'):
            print(f"응답 내용: {e.response}")

if __name__ == "__main__":
    test_supabase_connection()