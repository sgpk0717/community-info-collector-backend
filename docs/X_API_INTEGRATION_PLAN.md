# X(Twitter) API 통합 작업 계획서

## 개요
Reddit API에 이어 X(Twitter) API를 통합하여 멀티 플랫폼 소셜 미디어 분석 시스템을 구축합니다.
Free 티어의 극심한 제한(월 10,000건)을 고려하여 스마트한 사용량 관리 시스템을 구현합니다.

## 핵심 전략
- **Reddit 90% + X 10%** 비율로 데이터 수집
- 일일 할당량 자동 계산 및 관리
- 중요도 기반 선택적 수집

---

## 1. 데이터베이스 스키마 추가

### 1.1 X API 사용량 추적 테이블
```sql
-- x_api_usage 테이블 생성
CREATE TABLE public.x_api_usage (
    id BIGSERIAL PRIMARY KEY,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    user_nickname TEXT NOT NULL,
    endpoint TEXT NOT NULL,  -- 'search', 'user_timeline' 등
    tweets_read INTEGER NOT NULL DEFAULT 0,
    requests_made INTEGER NOT NULL DEFAULT 0,
    month_year TEXT NOT NULL,  -- 'YYYY-MM' 형식
    CONSTRAINT x_api_usage_unique UNIQUE (user_nickname, endpoint, month_year)
);

-- 인덱스 추가
CREATE INDEX idx_x_api_usage_month_year ON x_api_usage(month_year);
CREATE INDEX idx_x_api_usage_user_nickname ON x_api_usage(user_nickname);
```

### 1.2 X 게시물 저장 테이블
```sql
-- x_posts 테이블 생성 (Reddit posts와 유사한 구조)
CREATE TABLE public.x_posts (
    id TEXT PRIMARY KEY,  -- Tweet ID
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    text TEXT NOT NULL,
    author_username TEXT NOT NULL,
    author_name TEXT,
    retweet_count INTEGER DEFAULT 0,
    like_count INTEGER DEFAULT 0,
    reply_count INTEGER DEFAULT 0,
    created_utc DOUBLE PRECISION,
    url TEXT NOT NULL,
    lang TEXT,
    keyword_source TEXT,
    collected_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

---

## 2. 백엔드 구현 계획

### 2.1 새로 추가할 서비스 파일들

#### `/app/services/x_service.py`
```python
class XService:
    """X(Twitter) API 서비스 - Free 티어 최적화"""
    
    def __init__(self):
        self.client = tweepy.Client(bearer_token=X_BEARER_TOKEN)
        self.usage_service = XUsageService()
        self.daily_limit_calculator = DailyLimitCalculator()
    
    async def search_tweets(self, query: str, max_results: int = 10):
        """트윗 검색 - 사용량 체크 후 실행"""
        
        # 1. 일일 할당량 체크
        if not await self.usage_service.can_use_api():
            logger.warning(f"X API 일일 할당량 초과. Reddit만 사용합니다.")
            return []
        
        # 2. 실제 API 호출
        tweets = self.client.search_recent_tweets(
            query=query,
            max_results=min(max_results, 10),  # Free 티어는 요청당 최대 10개
            tweet_fields=['created_at', 'author_id', 'public_metrics']
        )
        
        # 3. 사용량 기록
        await self.usage_service.record_usage(
            endpoint='search',
            tweets_count=len(tweets.data) if tweets.data else 0
        )
        
        return self._process_tweets(tweets)
```

#### `/app/services/x_usage_service.py`
```python
class XUsageService:
    """X API 사용량 관리 서비스"""
    
    MONTHLY_LIMIT = 10000  # Free 티어 월 한도
    SAFETY_MARGIN = 0.9    # 90%만 사용 (안전 마진)
    
    async def can_use_api(self) -> bool:
        """API 사용 가능 여부 확인"""
        
        # 현재 월의 사용량 조회
        current_usage = await self.get_current_month_usage()
        
        # 남은 일수 계산
        days_remaining = self._get_days_remaining_in_month()
        
        # 일일 할당량 계산
        remaining_quota = (self.MONTHLY_LIMIT * self.SAFETY_MARGIN) - current_usage
        daily_allowance = remaining_quota / days_remaining
        
        # 오늘 사용량
        today_usage = await self.get_today_usage()
        
        return today_usage < daily_allowance
    
    async def record_usage(self, endpoint: str, tweets_count: int):
        """사용량 기록"""
        # Supabase에 사용량 업데이트
        pass
```

#### `/app/services/multi_platform_service.py`
```python
class MultiPlatformService:
    """멀티 플랫폼 통합 검색 서비스"""
    
    def __init__(self):
        self.reddit_service = RedditService()
        self.x_service = XService()
        
    async def search_all_platforms(self, query: str, sources: List[str]):
        """모든 플랫폼에서 검색"""
        
        all_posts = []
        
        # Reddit 검색 (무제한)
        if 'reddit' in sources:
            reddit_posts = await self.reddit_service.search_posts(
                query=query,
                limit=50  # Reddit은 충분히 많이
            )
            all_posts.extend(self._normalize_reddit_posts(reddit_posts))
        
        # X 검색 (극도로 제한적)
        if 'x' in sources:
            x_posts = await self.x_service.search_tweets(
                query=query,
                max_results=5  # X는 최소한만
            )
            all_posts.extend(self._normalize_x_posts(x_posts))
        
        return all_posts
```

### 2.2 기존 파일 수정 사항

#### `/app/services/analysis_service.py`
- `process_search_request` 메서드 수정하여 `MultiPlatformService` 사용
- X 플랫폼 데이터도 동일한 형식으로 정규화하여 처리

#### `/app/schemas/search.py`
```python
# sources 필드에 'x' 추가
sources: List[Literal["reddit", "x"]] = ["reddit"]
```

---

## 3. 프론트엔드 수정 사항

### 3.1 홈 화면 수정
```typescript
// HomeScreen.tsx
const platformOptions = [
  { label: 'Reddit', value: 'reddit', enabled: true },
  { label: 'X (Twitter)', value: 'x', enabled: true, badge: 'Limited' }
];

// X 선택 시 경고 메시지
{selectedPlatforms.includes('x') && (
  <Text style={styles.warningText}>
    ⚠️ X는 무료 계정으로 월 10,000건만 수집 가능합니다.
  </Text>
)}
```

### 3.2 보고서 카드 수정
- 각 게시물/트윗의 출처 플랫폼 표시
- 플랫폼별 아이콘 추가

---

## 4. 환경 변수 추가

### `.env` 파일
```
# X API Credentials
X_BEARER_TOKEN=your_bearer_token_here
X_API_KEY=your_api_key_here
X_API_SECRET=your_api_secret_here
X_ACCESS_TOKEN=your_access_token_here
X_ACCESS_TOKEN_SECRET=your_access_token_secret_here
```

---

## 5. 작업 순서

### Phase 1: 데이터베이스 준비 (담당: 사용자)
1. [ ] Supabase에 `x_api_usage` 테이블 생성
2. [ ] Supabase에 `x_posts` 테이블 생성
3. [ ] 필요한 인덱스 추가

### Phase 2: X API 자격 증명 (담당: 사용자)
1. [ ] X Developer Portal에서 앱 생성
2. [ ] Free 티어 API 키 발급
3. [ ] `.env` 파일에 API 키 추가

### Phase 3: 백엔드 구현 (담당: Claude)
1. [ ] `x_service.py` 구현
2. [ ] `x_usage_service.py` 구현
3. [ ] `multi_platform_service.py` 구현
4. [ ] `analysis_service.py` 수정
5. [ ] 스키마 업데이트

### Phase 4: 프론트엔드 수정 (담당: Claude)
1. [ ] HomeScreen에 X 플랫폼 옵션 추가
2. [ ] 경고 메시지 UI 구현
3. [ ] 보고서에 플랫폼 출처 표시

### Phase 5: 테스트 및 최적화 (담당: 함께)
1. [ ] 통합 테스트
2. [ ] 사용량 추적 검증
3. [ ] 일일 할당량 로직 테스트

---

## 6. 사용자가 준비해야 할 사항

### 6.1 X Developer 계정 설정
1. https://developer.twitter.com 접속
2. 개발자 계정 신청 (무료)
3. 새 앱 생성
4. API 키 및 토큰 발급

### 6.2 Supabase 테이블 생성
위의 SQL 스크립트를 Supabase SQL Editor에서 실행

### 6.3 환경 변수 설정
발급받은 X API 자격 증명을 `.env` 파일에 추가

---

## 7. 예상 결과

### 7.1 데이터 수집 비율
```
일반 키워드 검색 시:
- Reddit: 45-50개 게시물
- X: 3-5개 트윗

하루 최대 (333건 기준):
- 약 66회 검색 가능 (트윗 5개씩)
- 또는 33명 사용자 × 하루 2회 검색
```

### 7.2 보고서 개선
- 기존 Reddit 중심 분석 + X의 실시간 반응 추가
- 플랫폼별 여론 차이 비교 가능
- 더 다양한 관점의 종합 분석

---

## 8. 주의사항

1. **Rate Limit 엄수**: 429 에러 시 지수 백오프
2. **월말 주의**: 할당량 고갈 방지를 위해 월말에는 더 보수적으로
3. **캐싱 필수**: 동일 검색어는 24시간 캐싱
4. **우선순위**: 항상 Reddit 우선, X는 보조

---

## 9. 향후 확장 가능성

1. **유료 티어 전환 시**
   - Basic ($100/월): 여전히 월 10,000건
   - Pro ($5,000/월): 월 1,000,000건
   
2. **다른 플랫폼 추가**
   - Mastodon (무료, 개방형)
   - Threads (Meta)
   - Discord 공개 서버

---

이 계획서를 기반으로 단계별로 진행하시겠습니까?