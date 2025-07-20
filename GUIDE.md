# Community Info Collector v2.0 프로젝트 분석 보고서

## 개요

이 문서는 Community Info Collector v2.0 프로젝트의 핵심 기능들을 상세히 분석한 기술 문서입니다. 새로운 프로젝트에 활용하실 수 있도록 샘플 코드와 함께 구체적이고 깊이 있는 내용을 담았습니다.

## 목차

1. [키워드 기반 커뮤니티 분석 및 보고서 생성 기능](#1-키워드-기반-커뮤니티-분석-및-보고서-생성-기능)
2. [스케줄링 기능](#2-스케줄링-기능)
3. [데이터베이스 테이블 스키마](#3-데이터베이스-테이블-스키마-supabase-기준)
4. [프론트엔드(React Native 앱) 로직](#4-프론트엔드react-native-앱-로직-상세-분석)

---

## 1. 키워드 기반 커뮤니티 분석 및 보고서 생성 기능

이 기능은 사용자가 입력한 키워드를 바탕으로 여러 소셜 미디어 플랫폼(현재는 주로 Reddit)에서 관련 게시물을 수집하고, LLM(거대 언어 모델)을 이용해 분석 보고서를 생성하는 핵심적인 역할을 합니다.

### 1.1. API 엔드포인트 및 파라미터

보고서 생성을 위한 메인 API 엔드포인트는 다음과 같습니다.

*   **Endpoint:** `POST /search`
*   **파일 위치:** `app/api/endpoints.py`
*   **함수:** `search_and_analyze`

**요청 파라미터 (Request Body):**

`SearchRequest` 스키마(`app/schemas/schemas.py`)에 정의된 파라미터들은 다음과 같습니다.

| 파라미터 | 타입 | 필수 여부 | 설명 |
| :--- | :--- | :--- | :--- |
| `query` | `string` | **Yes** | 분석을 원하는 키워드입니다. |
| `sources` | `List[str]` | **Yes** | 검색할 소셜 미디어 플랫폼 목록입니다. 예: `["reddit", "threads"]` |
| `user_nickname` | `string` | **Yes** | 요청한 사용자의 닉네임입니다. 생성된 보고서를 특정 사용자와 연결하는 데 사용됩니다. |
| `session_id` | `string` | No | 클라이언트에서 생성한 고유 세션 ID입니다. 생략 시 서버에서 새로 생성됩니다. |
| `push_token` | `string` | No | 분석 완료 시 푸시 알림을 보낼 대상의 토큰입니다. (주로 모바일 앱에서 사용) |
| `length` | `string` | No | 생성할 보고서의 길이를 지정합니다. `simple`, `moderate`, `detailed` 중 선택 가능하며, 기본값은 `moderate`입니다. |
| `schedule_yn` | `string` | No | 스케줄링 여부를 나타냅니다. `Y` 또는 `N` 값을 가집니다. |
| `schedule_period` | `integer` | `schedule_yn`이 'Y'일 때 **Yes** | 스케줄링 주기(분 단위)입니다. |
| `schedule_count` | `integer` | `schedule_yn`이 'Y'일 때 **Yes** | 스케줄링 반복 횟수입니다. |
| `schedule_start_time` | `datetime` | `schedule_yn`이 'Y'일 때 **Yes** | 스케줄링 시작 시간입니다. |

**API 호출 예시 (cURL):**

```bash
curl -X POST "http://127.0.0.1:8000/search" \
-H "Content-Type: application/json" \
-d '{
  "query": "인공지능 주식",
  "sources": ["reddit"],
  "user_nickname": "testuser",
  "length": "detailed",
  "schedule_yn": "N"
}'
```

### 1.2. 기능 상세 분석

`search_and_analyze` 함수는 다음과 같은 순서로 동작합니다.

1.  **초기화 및 진행 상태 업데이트**:
    *   `session_id`를 기반으로 `progress_service`를 통해 현재 진행 상태를 "분석 준비 중"으로 업데이트합니다. 이는 프론트엔드에서 사용자에게 현재 어떤 작업이 수행 중인지 시각적으로 보여주는 데 사용됩니다.

2.  **스케줄링 처리 (선택 사항)**:
    *   만약 `schedule_yn`이 'Y'이면, `supabase_schedule_service`를 호출하여 요청된 파라미터(`schedule_period`, `schedule_count`, `schedule_start_time` 등)에 따라 Supabase DB에 새로운 스케줄을 생성합니다. 이 로직은 `app/api/endpoints.py`의 60-88 라인에 구현되어 있습니다.

3.  **게시물 수집**:
    *   **Reddit 검색 (고급 가중치 시스템)**: `sources`에 'reddit'이 포함된 경우, `app/services/advanced_search_service.py`의 `AdvancedSearchService`를 사용합니다.
        *   **키워드 확장**: 먼저 `LLMService` (내부적으로 GPT-4 모델 사용)를 호출하여 사용자가 입력한 `query`를 더 효과적인 여러 검색어로 확장합니다.
        *   **가중치 기반 검색**: 확장된 키워드를 사용하여 Reddit에서 관련성이 높은 게시물을 검색하고, 자체적인 가중치 로직에 따라 게시물을 수집합니다.
        *   **폴백(Fallback) 로직**: 만약 고급 검색에 실패하면, `app/services/reddit_service.py`의 기본적인 검색 기능(`search_posts`)으로 전환하여 안정성을 확보합니다.
    *   **기타 플랫폼 검색**: 'threads'와 같은 다른 플랫폼의 경우, 각각의 서비스(`threads_service`)를 병렬로 호출하여 게시물을 수집합니다. `asyncio.gather`를 사용하여 여러 작업을 동시에 효율적으로 처리합니다.

4.  **분석 및 보고서 생성**:
    *   **검증된 분석 시스템 (Verified Analysis)**: `app/services/verified_analysis_service.py`의 `VerifiedAnalysisService`를 사용하여 수집된 게시물(`saved_posts`)을 분석합니다.
        *   이 서비스는 LLM(GPT-4)을 호출하여 **단순 요약뿐만 아니라, 통계, 핵심 인용, 감성 분석, 원본 게시물 링크 매핑 등 다각적인 분석**이 포함된 종합 보고서를 생성합니다.
    *   **LLM 프롬프트**: `VerifiedAnalysisService` 내부에서 동적으로 생성되는 프롬프트는 대략 다음과 같은 구조를 가집니다.
        ```
        "당신은 전문 커뮤니티 분석가입니다. 다음은 '{query}' 키워드로 수집된 게시물들입니다.

        [게시물 데이터 목록...]

        이 데이터를 바탕으로 다음 항목을 포함하는 '{length}' 수준의 상세한 보고서를 한국어로 작성해주세요:
        1. 핵심 요약 (Summary): 전체 내용을 2-3 문단으로 요약합니다.
        2. 주요 토픽 분석 (Topic Analysis): 논의되는 주요 주제들을 3-5가지로 분류하고 각각을 설명합니다.
        3. 긍정/부정 여론 (Sentiment Analysis): 전반적인 여론의 긍정, 부정, 중립 비율과 그 근거를 제시합니다.
        4. 주요 인용문 (Key Quotes): 가장 인상적이거나 핵심적인 댓글 또는 게시물 내용을 3가지 인용합니다.
        5. 관련 링크 (Associated Links): 분석에 사용된 가장 중요한 원본 게시물 링크 5개를 목록으로 제공합니다.
        6. 종합 결론 (Overall Conclusion): 분석 결과를 종합하여 최종 결론을 내립니다."
        ```
        *실제 프롬프트는 `app/services/verified_analysis_service.py` 파일 내에 더 정교하게 구현되어 있습니다.*
    *   **폴백(Fallback) 로직**: `VerifiedAnalysisService` 실패 시, `app/services/llm_service.py`의 기본 보고서 생성 기능(`generate_report`)으로 전환됩니다.

5.  **보고서 및 메타데이터 저장**:
    *   생성된 보고서(`full_report`, `summary`), 수집된 게시물 수(`posts_collected`), 사용된 세션 ID(`session_id`) 등을 `supabase_reports_service`를 통해 Supabase의 `reports` 테이블에 저장합니다.
    *   또한, 분석에 사용된 주요 게시물들의 메타데이터(URL, 제목, 점수 등)를 `posts_metadata` 컬럼에 JSON 형태로 저장하여, 나중에 사용자가 보고서에서 원본 글로 바로 이동할 수 있게 합니다.

6.  **푸시 알림 및 응답 반환**:
    *   `push_token`이 제공된 경우, `push_notification_service`를 통해 "분석이 완료되었습니다"라는 내용의 푸시 알림을 비동기적으로 발송합니다.
    *   최종적으로 생성된 보고서 데이터(`summary`, `full_report`)와 함께 `session_id`, `query_id` 등을 포함한 `SearchResponse` 객체를 클라이언트에 반환합니다.

---

## 2. 스케줄링 기능

이 프로젝트의 스케줄링 기능은 사용자가 지정한 키워드와 주기에 따라 자동으로 보고서 생성을 반복 실행하는 강력한 기능입니다. Supabase 데이터베이스와 `APScheduler` 라이브러리를 결합하여 안정적이고 확장성 있는 시스템을 구축했습니다.

### 2.1. 스케줄링 시스템 구조

스케줄링 기능은 크게 두 가지 서비스가 협력하여 동작합니다.

1.  **`SupabaseScheduleService` (`app/services/supabase_schedule_service.py`)**:
    *   **역할**: Supabase의 `schedules` 테이블과 직접 통신하며 스케줄 데이터의 CRUD(생성, 조회, 수정, 삭제)를 담당합니다.
    *   **주요 기능**:
        *   `create_schedule`: 새로운 스케줄을 DB에 저장합니다.
        *   `get_schedules_to_execute`: 현재 시간이 `next_run`을 지난 'active' 상태의 스케줄 목록을 조회합니다.
        *   `try_acquire_schedule_lock`: 여러 서버 인스턴스가 동시에 같은 스케줄을 실행하는 것을 방지하기 위해 `is_executing` 플래그를 `True`로 설정하여 원자적으로 락(Lock)을 획득합니다.
        *   `release_schedule_lock`: 스케줄 실행이 완료되면 `is_executing` 플래그를 `False`로 변경하여 락을 해제합니다.
        *   `update_schedule_after_execution`: 스케줄이 성공적으로 실행된 후, `completed_reports` 카운트를 1 증가시키고 다음 실행 시간(`next_run`)을 업데이트합니다. 만약 `total_reports`에 도달하면 상태를 `completed`로 변경합니다.

2.  **`SupabaseSchedulerService` (`app/services/supabase_scheduler_service.py`)**:
    *   **역할**: 실제 스케줄링 로직을 실행하는 주체입니다. `APScheduler`를 사용하여 주기적으로 작업을 트리거하고, `SupabaseScheduleService`를 통해 DB와 상호작용합니다.
    *   **주요 기능**:
        *   **스케줄 체커 (Checker)**: `APScheduler`의 `CronTrigger`를 사용하여 **10분 주기(`minute='0,10,20,30,40,50'`)**로 `_check_and_execute_schedules` 메소드를 실행합니다. 이 메소드는 실행 시간이 된 스케줄이 있는지 DB에 확인합니다.
        *   **실행 큐 (Queue)**: 실행해야 할 스케줄을 바로 실행하지 않고, `asyncio.Queue`에 넣어 순차적으로 처리합니다. 이를 통해 한 번에 너무 많은 작업이 몰려 서버에 과부하가 걸리는 것을 방지합니다.
        *   **워커 (Worker)**: 별도의 비동기 태스크(`_schedule_worker`)가 큐를 계속 감시하다가, 새로운 스케줄이 들어오면 하나씩 꺼내어 실제 분석 작업을 수행하는 `_execute_schedule` 메소드를 호출합니다.
        *   **재시도 로직**: 스케줄 실행 중 일시적인 오류(네트워크 문제 등)가 발생하면, 최대 3회까지 5초 간격으로 재시도하여 안정성을 높입니다.

### 2.2. 스케줄링 기능의 전체 흐름

사용자가 스케줄 생성을 요청했을 때부터 보고서가 생성되기까지의 전체 흐름은 다음과 같습니다.

1.  **스케줄 생성 (사용자 요청)**:
    *   사용자가 프론트엔드 앱에서 키워드, 주기, 횟수 등을 설정하여 스케줄 생성을 요청합니다.
    *   `POST /search` API (또는 별도의 스케줄링 API)가 호출되고, `schedule_yn`이 'Y'이면 `SupabaseScheduleService`의 `create_schedule`가 호출되어 `schedules` 테이블에 새로운 레코드가 생성됩니다. 이때 `status`는 'active'로, `is_executing`은 `False`로 초기화됩니다.

2.  **스케줄 확인 (10분 주기)**:
    *   백그라운드에서 실행 중인 `SupabaseSchedulerService`가 10분마다 `_check_and_execute_schedules`를 실행합니다.
    *   `supabase_schedule_service.get_schedules_to_execute()`를 호출하여 `next_run` 시간이 지났고, `status`가 'active'이며, `is_executing`이 `False`인 스케줄을 모두 찾아냅니다.

3.  **락 획득 및 큐 추가**:
    *   찾아낸 각 스케줄에 대해 `try_acquire_schedule_lock`을 호출하여 DB 레벨에서 실행 락을 획득합니다.
    *   락 획득에 성공한 스케줄만 실행 큐(`_schedule_queue`)에 추가됩니다. 만약 다른 서버 인스턴스가 이미 락을 가져갔다면, 이번 주기에는 실행하지 않고 건너뜁니다.

4.  **스케줄 실행 (워커)**:
    *   `_schedule_worker`가 큐에서 대기 중인 스케줄을 가져옵니다.
    *   `_execute_schedule` 메소드가 호출되어 다음 작업이 순차적으로 진행됩니다.
        a.  `reddit_service`를 호출하여 키워드로 게시물을 수집합니다.
        b.  `verified_analysis_service`를 호출하여 수집된 데이터로 AI 보고서를 생성합니다.
        c.  `supabase_reports_service`를 통해 생성된 보고서를 `reports` 테이블에 저장합니다.

5.  **스케줄 업데이트 및 락 해제**:
    *   보고서 생성이 성공적으로 완료되면, `update_schedule_after_execution`을 호출하여 `completed_reports`를 1 증가시키고 `next_run`을 `interval_minutes`만큼 뒤로 설정합니다.
    *   만약 모든 횟수를 채웠다면(`completed_reports >= total_reports`), `status`를 'completed'로 변경하여 더 이상 실행되지 않도록 합니다.
    *   마지막으로, `release_schedule_lock`을 호출하여 `is_executing` 플래그를 `False`로 되돌려놓아 다음 스케줄링 주기에 다시 실행될 수 있도록 합니다.

### 2.3. 스케줄링 기능 호출 후 필요한 작업

*   **스케줄링 상태 확인**: 스케줄을 생성한 후, 프론트엔드에서는 주기적으로 `GET /api/v1/schedule/{user_nickname}`과 같은 API를 호출하여 현재 스케줄의 상태(`active`, `completed`, `cancelled`)와 진행 상황(`completed_reports`, `total_reports`)을 사용자에게 보여줄 수 있습니다.
*   **보고서 확인**: 스케줄에 의해 생성된 보고서는 일반 보고서와 동일하게 `GET /reports/{user_nickname}` API를 통해 목록을 조회하고, `GET /reports/detail/{report_id}`를 통해 상세 내용을 확인할 수 있습니다.
*   **알림 처리**: 스케줄 실행이 완료되면 (선택적으로) 푸시 알림이 발송될 수 있으므로, 클라이언트 앱은 이 알림을 수신하고 적절히 처리하는 로직이 필요합니다.

---

## 3. 데이터베이스 테이블 스키마 (Supabase 기준)

프로젝트의 핵심 데이터는 Supabase에 저장되며, 주요 테이블은 `users`, `schedules`, `reports`, `report_links` 입니다.

### 3.1. `users` 테이블

사용자 정보를 관리합니다.

| 컬럼명 | 데이터 타입 | 제약조건 | 설명 |
| :--- | :--- | :--- | :--- |
| `id` | `uuid` | **Primary Key**, `gen_random_uuid()` | 사용자의 고유 ID입니다. |
| `created_at` | `timestamp with time zone` | `now()` | 사용자 계정 생성 시각입니다. |
| `user_nickname` | `text` | **Unique**, Not Null | 사용자를 식별하는 고유한 닉네임입니다. |
| `email` | `text` | | 사용자의 이메일 주소입니다. (선택적) |
| `push_token` | `text` | | 푸시 알림을 위한 디바이스 토큰입니다. |

**SQL 스키마 예시:**

```sql
CREATE TABLE public.users (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    user_nickname text NOT NULL,
    email text NULL,
    push_token text NULL,
    CONSTRAINT users_pkey PRIMARY KEY (id),
    CONSTRAINT users_user_nickname_key UNIQUE (user_nickname)
);
```

### 3.2. `schedules` 테이블

자동 보고서 생성을 위한 스케줄 정보를 관리합니다.

| 컬럼명 | 데이터 타입 | 제약조건 | 설명 |
| :--- | :--- | :--- | :--- |
| `id` | `bigint` | **Primary Key** (Identity) | 스케줄의 고유 ID입니다. |
| `created_at` | `timestamp with time zone` | `now()` | 스케줄 생성 시각입니다. |
| `user_nickname` | `text` | Not Null | 스케줄을 생성한 사용자의 닉네임입니다. (`users.user_nickname` 참조) |
| `keyword` | `text` | Not Null | 분석할 키워드입니다. |
| `interval_minutes` | `integer` | Not Null | 보고서 생성 주기 (분 단위)입니다. |
| `total_reports` | `integer` | Not Null | 생성할 총 보고서 횟수입니다. |
| `completed_reports` | `integer` | `0` | 현재까지 생성된 보고서 횟수입니다. |
| `report_length` | `text` | `'moderate'` | 보고서 길이 (`simple`, `moderate`, `detailed`)입니다. |
| `sources` | `text[]` | `{'reddit'}` | 데이터 수집 소스 목록입니다. (배열 타입) |
| `status` | `text` | `'active'` | 스케줄 상태 (`active`, `paused`, `completed`, `cancelled`). |
| `next_run` | `timestamp with time zone` | | 다음 보고서 생성 예정 시각입니다. |
| `last_run` | `timestamp with time zone` | | 마지막으로 보고서가 생성된 시각입니다. |
| `notification_enabled` | `boolean` | `true` | 보고서 생성 시 알림 발송 여부입니다. |
| `is_executing` | `boolean` | `false` | 현재 이 스케줄이 실행 중인지 여부를 나타내는 락(Lock) 플래그입니다. |

**SQL 스키마 예시:**

```sql
CREATE TABLE public.schedules (
    id bigint NOT NULL GENERATED BY DEFAULT AS IDENTITY,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    user_nickname text NOT NULL,
    keyword text NOT NULL,
    interval_minutes integer NOT NULL,
    total_reports integer NOT NULL,
    completed_reports integer NOT NULL DEFAULT 0,
    report_length text NOT NULL DEFAULT 'moderate'::text,
    sources text[] NOT NULL DEFAULT '{reddit}'::text[],
    status text NOT NULL DEFAULT 'active'::text,
    next_run timestamp with time zone NULL,
    last_run timestamp with time zone NULL,
    notification_enabled boolean NOT NULL DEFAULT true,
    is_executing boolean NOT NULL DEFAULT false,
    CONSTRAINT schedules_pkey PRIMARY KEY (id),
    CONSTRAINT schedules_user_nickname_fkey FOREIGN KEY (user_nickname) REFERENCES users(user_nickname)
);
```

### 3.3. `reports` 테이블

생성된 분석 보고서를 저장합니다.

| 컬럼명 | 데이터 타입 | 제약조건 | 설명 |
| :--- | :--- | :--- | :--- |
| `id` | `uuid` | **Primary Key**, `gen_random_uuid()` | 보고서의 고유 ID입니다. |
| `created_at` | `timestamp with time zone` | `now()` | 보고서 생성 시각입니다. |
| `user_nickname` | `text` | | 보고서를 요청한 사용자의 닉네임입니다. (`users.user_nickname` 참조) |
| `query_text` | `text` | Not Null | 분석에 사용된 원본 키워드입니다. |
| `summary` | `text` | | LLM이 생성한 보고서의 핵심 요약 내용입니다. |
| `full_report` | `text` | | LLM이 생성한 전체 보고서 내용입니다. |
| `posts_collected` | `integer` | `0` | 분석에 사용된 총 게시물 수입니다. |
| `report_length` | `text` | `'moderate'` | 생성된 보고서의 길이입니다. |
| `session_id` | `text` | | 보고서 생성 요청의 세션 ID입니다. (진행 상태 추적용) |

**SQL 스키마 예시:**

```sql
CREATE TABLE public.reports (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    user_nickname text NULL,
    query_text text NOT NULL,
    summary text NULL,
    full_report text NULL,
    posts_collected integer NOT NULL DEFAULT 0,
    report_length text NOT NULL DEFAULT 'moderate'::text,
    session_id text NULL,
    CONSTRAINT reports_pkey PRIMARY KEY (id),
    CONSTRAINT reports_user_nickname_fkey FOREIGN KEY (user_nickname) REFERENCES users(user_nickname)
);
```

### 3.4. `report_links` 테이블

보고서에 인용되거나 참조된 원본 게시물 링크 정보를 관리합니다. `reports` 테이블과 1:N 관계입니다.

| 컬럼명 | 데이터 타입 | 제약조건 | 설명 |
| :--- | :--- | :--- | :--- |
| `id` | `bigint` | **Primary Key** (Identity) | 링크의 고유 ID입니다. |
| `created_at` | `timestamp with time zone` | `now()` | 레코드 생성 시각입니다. |
| `report_id` | `uuid` | Not Null | 이 링크가 속한 보고서의 ID입니다. (`reports.id` 참조) |
| `footnote_number` | `integer` | | 보고서 본문에 표시되는 각주 번호입니다. |
| `url` | `text` | Not Null | 원본 게시물의 URL입니다. |
| `title` | `text` | | 원본 게시물의 제목입니다. |
| `score` | `integer` | | 원본 게시물의 점수(추천/좋아요)입니다. |
| `comments` | `integer` | | 원본 게시물의 댓글 수입니다. |
| `created_utc` | `timestamp with time zone` | | 원본 게시물의 생성 시각(UTC)입니다. |
| `subreddit` | `text` | | Reddit 서브레딧 이름입니다. |
| `author` | `text` | | 원본 게시물의 작성자입니다. |
| `position_in_report` | `integer` | | 보고서 내 링크 목록에서의 순서입니다. |

**SQL 스키마 예시:**

```sql
CREATE TABLE public.report_links (
    id bigint NOT NULL GENERATED BY DEFAULT AS IDENTITY,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    report_id uuid NOT NULL,
    footnote_number integer NULL,
    url text NOT NULL,
    title text NULL,
    score integer NULL,
    comments integer NULL,
    created_utc timestamp with time zone NULL,
    subreddit text NULL,
    author text NULL,
    position_in_report integer NULL,
    CONSTRAINT report_links_pkey PRIMARY KEY (id),
    CONSTRAINT report_links_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports(id) ON DELETE CASCADE
);
```

---

## 4. 프론트엔드(React Native 앱) 로직 상세 분석

`RedditAnalyzerApp`은 사용자가 직접 키워드 분석을 요청하고, 스케줄을 관리하며, 생성된 보고서를 확인할 수 있는 React Native 기반의 모바일 애플리케이션입니다.

### 4.1. 앱의 전체 구조 및 화면 흐름 (Flow)

앱의 핵심 구조는 `App.tsx` 파일에 정의되어 있으며, 사용자의 인증 상태(`isAuthenticated`)에 따라 다른 화면을 보여주는 조건부 렌더링 방식을 사용합니다.

**앱 시작 시 흐름:**

1.  **초기 스플래시 스크린 (`SplashScreen`)**: 앱이 처음 실행되면 2초 동안 로고 애니메이션과 함께 스플래시 화면이 표시됩니다.
2.  **인증 상태 확인 (`AuthContext`)**: `AuthProvider`가 `checkAuthStatus` 함수를 실행하여 `AsyncStorage`에 저장된 사용자 정보(닉네임 등)가 있는지 확인합니다.
3.  **화면 분기**:
    *   **인증되지 않은 경우 (로그인 필요)**: `LoginScreen`과 `RegisterScreen`으로 구성된 `StackNavigator`가 렌더링됩니다.
        *   **`LoginScreen`**: 사용자는 닉네임을 입력하여 로그인을 시도합니다. `handleLogin` 함수는 `AuthContext`의 `login` 함수를 호출하여 서버에 로그인을 요청합니다.
        *   **`RegisterScreen`**: `LoginScreen`에서 "사용자 등록" 버튼을 누르면 이동합니다. 새로운 닉네임을 입력하고 중복 확인을 거쳐 `ApiService.registerUser`를 통해 서버에 등록을 요청합니다.
    *   **인증된 경우 (로그인 성공)**:
        *   **두 번째 스플래시 스크린 (`SecondSplashScreen`)**: 로그인 성공 직후, "환영합니다! {사용자명}님"과 같은 메시지를 보여주는 두 번째 스플래시 화면이 잠시 나타납니다.
        *   **메인 탭 네비게이터 (`MainTabNavigator`)**: 스플래시 화면이 사라진 후, 앱의 핵심 기능들을 담고 있는 하단 탭 네비게이터가 나타납니다.

**메인 앱의 구조 (하단 탭 네비게이터):**

메인 화면은 4개의 탭으로 구성되어 있습니다.

*   **실시간 분석 (`HomeScreen`)**:
    *   **역할**: 키워드를 입력하여 즉시 분석을 시작하고, 웹소켓(WebSocket)을 통해 실시간으로 진행 상황을 확인하는 화면입니다.
    *   **주요 기능**:
        *   **키워드 및 보고서 길이 입력**: 사용자가 분석할 키워드와 원하는 보고서의 길이(`simple`, `moderate`, `detailed`)를 선택합니다.
        *   **분석 시작**: '분석 시작' 버튼을 누르면 `handleAnalyze` 함수가 실행됩니다. 이 함수는 `ApiService.createSearchRequest`를 호출하여 백엔드에 `/search` API 요청을 보냅니다.
        *   **실시간 진행 상황**: API 요청이 성공하면 `session_id`를 반환받고, 이 ID를 사용하여 웹소켓(`ws://.../ws/progress/{session_id}`)에 연결합니다. 서버는 분석 각 단계(키워드 확장, 데이터 수집, AI 분석 등)가 완료될 때마다 진행률(%)과 상태 메시지를 웹소켓으로 전송하고, `HomeScreen`은 이 정보를 받아 프로그레스 바와 텍스트로 사용자에게 실시간 피드백을 제공합니다.
        *   **결과 표시**: 분석이 완료되면(`progress.stage === 'completed'`), 생성된 보고서 요약을 화면 하단에 표시하고, '전체 보고서 보기' 버튼을 활성화하여 `ReportsScreen`으로 이동할 수 있도록 안내합니다.
*   **스케줄 등록 (`ScheduleCreateScreen`)**:
    *   **역할**: 정기적인 자동 분석을 위한 새로운 스케줄을 생성하는 화면입니다.
    *   **주요 기능**: 사용자는 분석할 키워드, 실행 주기(예: 60분), 총 실행 횟수, 보고서 길이 등을 입력하고 '스케줄 생성' 버튼을 눌러 `ApiService.createSchedule`을 호출, 백엔드에 스케줄 생성을 요청합니다.
*   **스케줄 목록 (`ScheduleListScreen`)**:
    *   **역할**: 사용자가 생성한 모든 스케줄의 목록과 상태를 확인하고 관리하는 화면입니다.
    *   **주요 기능**: `useFocusEffect`를 사용하여 화면에 들어올 때마다 `ApiService.getUserSchedules`를 호출하여 최신 스케줄 목록을 가져옵니다. '진행중', '완료됨', '취소됨' 등 상태별로 스케줄을 필터링하여 볼 수 있으며, 각 스케줄을 일시정지, 재개 또는 삭제하는 기능이 포함되어 있습니다.
*   **보고서 (`ReportsScreen`)**:
    *   **역할**: 사용자가 요청했거나 스케줄에 의해 생성된 모든 분석 보고서의 목록을 확인하는 화면입니다.
    *   **주요 기능**:
        *   **보고서 목록 조회**: `ApiService.getUserReports`를 호출하여 해당 사용자의 모든 보고서 목록을 가져와 최신순으로 표시합니다.
        *   **새로고침**: 화면을 아래로 당겨(`Pull-to-refresh`) 목록을 새로고침할 수 있습니다.
        *   **상세 보고서 보기**: 목록에서 특정 보고서를 선택하면, `Modal` 창이 열리고 `ReportRenderer` 컴포넌트를 통해 마크다운 형식의 전체 보고서 내용이 렌더링됩니다.
        *   **보고서 삭제**: 선택 모드를 활성화하여 여러 보고서를 한 번에 삭제할 수 있습니다.

### 4.2. 핵심 서비스 로직

앱의 비즈니스 로직과 서버 통신은 주로 `src/services/` 디렉토리의 서비스 파일들에서 처리됩니다.

*   **`api.service.ts`**:
    *   **역할**: 백엔드 API와의 모든 HTTP 통신을 담당하는 중앙 집중식 서비스입니다. `fetch`를 기반으로 하며, `POST /search`, `GET /reports/{user_nickname}` 등 모든 API 엔드포인트 호출 함수를 정의합니다.
    *   **주요 함수**: `loginUser`, `registerUser`, `createSearchRequest`, `getUserReports`, `createSchedule` 등.
*   **`auth.service.ts`**:
    *   **역할**: 사용자 인증 관련 상태를 관리합니다. `AsyncStorage`에 사용자 정보를 저장하고, 앱 시작 시 이를 불러와 로그인 상태를 유지합니다.
    *   **주요 함수**: `initialize` (앱 초기화 시 사용자 정보 로드/생성), `updateUserNickname` (로그인 성공 시 닉네임 저장), `getCurrentUser`.
*   **`notification.service.ts`**:
    *   **역할**: Expo의 푸시 알림 기능을 래핑하여 알림 권한 요청, 푸시 토큰 획득, 알림 리스너 설정 등을 처리합니다.
    *   **주요 함수**: `initialize` (권한 요청 및 토큰 획득), `sendAnalysisCompleteNotification` (서버에서 호출되지만, 클라이언트에서 토큰을 제공).
*   **`storage.service.ts`**:
    *   **역할**: `AsyncStorage`를 사용하여 사용자 정보(`user`), 저장된 닉네임(`savedNickname`) 등 앱의 영구적인 데이터를 관리합니다.

---

이상으로 Community Info Collector v2.0 프로젝트의 핵심 기능, 스케줄링, 데이터베이스 스키마, 프론트엔드 앱 로직에 대한 상세 분석 보고서 작성을 마칩니다. 이 내용이 새로운 프로젝트를 구성하시는 데 큰 도움이 되기를 바랍니다. 추가적으로 궁금한 점이 있으시면 언제든지 질문해주세요!