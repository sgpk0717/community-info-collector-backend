# X(Twitter) API 사용 가이드

## 환경변수 설정

### 1. X API 활성화/비활성화

```bash
# 개발/테스트 환경 (기본값)
USE_X_API=false

# 프로덕션 환경
USE_X_API=true
```

### 2. X API 자격 증명

X API를 사용하려면 다음 5개의 환경변수가 필요합니다:

```bash
X_BEARER_TOKEN=your_bearer_token
X_API_KEY=your_api_key
X_API_SECRET=your_api_secret
X_ACCESS_TOKEN=your_access_token
X_ACCESS_TOKEN_SECRET=your_access_token_secret
```

## 사용량 정책

### Free 티어 제한
- **월간 한도**: 10,000 트윗
- **안전 마진**: 90% (실제 9,000 트윗만 사용)
- **요청당**: 최소 10개, 최대 100개 트윗

### 일일 할당량 자동 계산
```
일일 할당량 = (9,000 - 현재월 사용량) / 남은 일수
```

### 예시
- **월초 (30일)**: 일일 300개 → 최대 30회 검색
- **월중 (15일)**: 일일 150개 → 최대 15회 검색  
- **월말 (5일)**: 일일 50개 → 최대 5회 검색

## API 엔드포인트

### 1. 사용 가능한 플랫폼 조회
```
GET /api/v1/platforms/available
```

응답 예시 (X API 비활성화 시):
```json
{
  "success": true,
  "platforms": [
    {
      "value": "reddit",
      "label": "Reddit",
      "icon": "🟢",
      "enabled": true,
      "status": "unlimited"
    }
  ],
  "supported": ["reddit"]
}
```

응답 예시 (X API 활성화 시):
```json
{
  "success": true,
  "platforms": [
    {
      "value": "reddit",
      "label": "Reddit",
      "icon": "🟢",
      "enabled": true,
      "status": "unlimited"
    },
    {
      "value": "x",
      "label": "X (Twitter)",
      "icon": "🐦",
      "enabled": true,
      "badge": "Limited",
      "status": "limited",
      "monthly_limit": 10000
    }
  ],
  "supported": ["reddit", "x"]
}
```

### 2. X API 사용량 조회
```
GET /api/v1/platforms/x/usage
```

응답 예시:
```json
{
  "success": true,
  "usage": {
    "month": "2025-07",
    "total_tweets": 150,
    "total_requests": 15,
    "usage_by_endpoint": {
      "search": {"tweets": 150, "requests": 15}
    },
    "remaining": 9850,
    "usage_percentage": 1.5
  },
  "use_x_api": true
}
```

## 개발 가이드

### 테스트 환경 설정
```bash
# .env 파일
USE_X_API=false  # X API 비활성화
```

### 프로덕션 환경 설정
```bash
# .env 파일
USE_X_API=true   # X API 활성화
X_BEARER_TOKEN=실제_토큰_값
# ... 나머지 X API 키들
```

### 테스트 실행
```bash
# X API 비활성화 상태 테스트
python test_x_disabled.py

# 전체 통합 테스트
python test_x_integration.py
```

## 동작 방식

### USE_X_API=false 일 때
1. X API 호출 완전 차단
2. 검색 요청에 'x' 포함되어도 무시
3. Reddit 데이터만으로 분석 진행
4. 사용자에게는 정상 서비스 제공

### USE_X_API=true 일 때
1. 일일 할당량 체크
2. 할당량 초과 시 자동으로 Reddit 전용 모드
3. 모든 사용량 DB에 기록
4. 플랫폼별 90:10 비율로 데이터 수집

## 주의사항

1. **Rate Limit**: 15분당 제한이 있으므로 재시도 로직 포함
2. **월말 주의**: 할당량이 적을 때는 더 보수적으로 사용
3. **개발 시**: 반드시 `USE_X_API=false`로 설정
4. **배포 시**: 프로덕션 환경에서만 `true`로 설정