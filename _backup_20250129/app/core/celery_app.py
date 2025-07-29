from celery import Celery
from kombu import Exchange, Queue
import os

# Redis URL 설정
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

# Celery 앱 생성
celery_app = Celery(
    'community_collector',
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=['app.tasks.api_tasks', 'app.tasks.dispatcher_tasks']
)

# Celery 설정
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    
    # 태스크 라우팅
    task_routes={
        'app.tasks.api_tasks.*': {'queue': 'api_calls'},
        'app.tasks.dispatcher_tasks.*': {'queue': 'dispatcher'},
    },
    
    # 큐 설정
    task_queues=(
        Queue('api_calls', Exchange('api_calls'), routing_key='api_calls'),
        Queue('dispatcher', Exchange('dispatcher'), routing_key='dispatcher'),
    ),
    
    # 재시도 설정
    task_annotations={
        'app.tasks.api_tasks.make_api_call': {
            'rate_limit': '1/s',  # 초당 1회 제한
            'max_retries': 3,
            'default_retry_delay': 60,  # 60초 후 재시도
        }
    },
    
    # Beat 스케줄 (주기적 작업)
    beat_schedule={
        'dispatch-api-calls': {
            'task': 'app.tasks.dispatcher_tasks.dispatch_pending_calls',
            'schedule': 1.0,  # 1초마다 실행
            'options': {'queue': 'dispatcher'}
        },
    },
)

# Celery 시작을 위한 헬퍼 함수
def start_worker():
    """워커 시작"""
    celery_app.start()

def start_beat():
    """Beat 스케줄러 시작"""
    celery_app.start()