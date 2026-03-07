# 주문번호 기반 픽업 API 구현 명세

## 상태

- 단계: 설계 갱신
- 전체 상태: 사용자 승인 대기
- 이번 변경 요청: `order_id` 를 날짜+티켓번호만 남기고, 요청 요약은 `summary_desc` 로 응답에서 분리한다

## 1. 목표와 배경

기존 주문번호는 `TYYYYMMDD-NNNNNN_{slug}` 형식이라 사람이 읽기에는 편하지만, 프론트에서 식별자로 다루기엔 길고 URL/표시 폭이 불필요하게 커진다.  
이번 변경의 목표는 외부 식별자를 `TYYYYMMDD-NNNNNN` 으로 단순화하고, 사람이 읽을 요청 요약은 API 응답 필드 `summary_desc` 로 분리해 주문번호와 설명의 역할을 나누는 것이다.

## 2. 범위

### 포함

- 새 주문 생성 시 `order_id` 형식을 `TYYYYMMDD-NNNNNN` 으로 축약
- 주문 생성 응답에 `summary_desc` 추가
- 상태 조회 응답에도 `summary_desc` 추가
- 내부 상태 저장 구조를 새 필드 기준으로 정리
- README 예시 및 테스트 갱신

### 제외

- HTTPS 지원 추가
- 인증/권한 추가
- 기존 `summary.md` 내용 포맷 변경
- 과거 run 폴더명 일괄 마이그레이션

## 3. 사용자 시나리오

### 시나리오 A: 프론트가 주문 접수 후 번호만 저장

1. 프론트가 `POST /orders` 호출
2. 서버가 `T20260307-000123` 같은 짧은 `order_id` 반환
3. 프론트는 화면에는 `summary_desc` 를 보여주고, 내부 추적 키는 `order_id` 만 사용

### 시나리오 B: 프론트가 상태 화면에 설명을 같이 표시

1. 프론트가 `GET /orders/{order_id}/status` 호출
2. 서버가 `status`, `summary_desc`, 파일 경로를 함께 반환
3. 프론트는 설명 텍스트를 따로 저장하지 않아도 된다

### 시나리오 C: 기존 주문 조회

1. 과거 주문 폴더명이 `T20260307-000001_기존-slug` 형태여도
2. 기존 상태 조회/픽업은 계속 동작해야 한다

## 4. 기능 목록과 우선순위

### P0

- 새 `order_id` 생성 규칙 적용
- `summary_desc` 응답 필드 추가
- 기존 API 테스트와 워커 동작 유지

### P1

- `status.json` 에 `summary_desc` 저장
- README 예시를 새 계약으로 정리

### P2

- 과거 slug 포함 주문 ID 파싱을 유지하는 호환성 테스트 추가

## 5. 데이터와 모델

### 새 주문번호 규칙

- 형식: `TYYYYMMDD-NNNNNN`
- 예시: `T20260307-000001`
- suffix slug 는 새 주문 생성 시 더 이상 사용하지 않는다

### 상태 데이터

`OrderStatusRecord` 와 `status.json` 에 아래 필드를 유지한다.

- `order_id`
- `crew_id`
- `status`
- `summary_desc`
- `requested_at`
- `summary_file`
- `started_at`
- `finished_at`
- `failure_file`
- `error_type`
- `error_message`

기존 `user_request_preview` 는 읽기 호환을 위해 당분간 fallback 으로 지원하되, 신규 기록은 `summary_desc` 로 통일한다.

## 6. API / 이벤트 / 흐름

### `POST /orders`

- 입력: `crew_id`, `user_request`
- 응답:
  - `order_id`
  - `status`
  - `summary_desc`
  - `status_url`
  - `pickup_url`
  - `summary_file`
  - `requested_at`

### `GET /orders/{order_id}/status`

- `status.json` 기반 응답
- `summary_desc` 포함

### `GET /pickup/{order_id}`

- 동작 변경 없음
- 내부적으로는 `status.json` 의 새 필드 구조와 함께 동작

### 흐름

1. API 접수 시 짧은 `order_id` 발급
2. `summary_desc` 는 요청 요약으로 생성
3. 워커는 동일한 짧은 `order_id` 폴더를 처리
4. 프론트는 `order_id` 로 조회하고, 표시 텍스트는 `summary_desc` 를 사용

## 7. UI / UX

- 별도 UI 구현은 없음
- 프론트 표기 가이드:
  - 주문번호: `order_id`
  - 사용자에게 보여줄 설명: `summary_desc`

## 8. 오류와 엣지 케이스

- 같은 날짜에 주문이 몰려도 순번은 계속 증가해야 한다
- 기존 slug 포함 폴더가 있어도 다음 순번 계산이 깨지면 안 된다
- 과거 `status.json` 에 `summary_desc` 가 없고 `user_request_preview` 만 있어도 읽을 수 있어야 한다
- `pickup` 은 새 필드 추가와 무관하게 기존 상태 코드 계약을 유지해야 한다

## 9. Definition of Done

- 신규 주문의 폴더명이 `TYYYYMMDD-NNNNNN` 형식으로 생성된다
- `POST /orders` 와 `GET /orders/{order_id}/status` 응답에 `summary_desc` 가 포함된다
- `status.json` 신규 기록이 `summary_desc` 를 사용한다
- 기존 slug 포함 주문에 대한 상태 조회/픽업 테스트가 통과한다
- README 예시가 새 응답 계약과 일치한다
- `uv run pytest`, `uv run ruff check src tests` 가 통과한다

## 10. 제약사항

- 응답과 문서는 한국어 기준으로 유지한다
- 수동 코드 수정은 `apply_patch` 로만 진행한다
- 기존 공개 엔드포인트 경로는 바꾸지 않는다
- 과거 주문 폴더를 강제로 rename 하지 않는다
- 새 필드명은 `summary_desc` 로 고정한다

## 우려사항과 선택지

### 우려 1: 기존 클라이언트가 `user_request_preview` 를 보고 있을 수 있음

- 선택지 A: 응답에서 즉시 제거
- 선택지 B: 상태 파일에는 새 필드만 쓰고, 응답에는 한동안 둘 다 노출

권장안:
- 상태 파일 신규 기록은 `summary_desc` 로 통일
- API 응답도 `summary_desc` 로 전환
- 다만 읽기 레이어에서는 과거 `user_request_preview` 를 fallback 으로 허용

이유:
- 외부 계약은 빨리 단순화하는 편이 낫고, 하위 호환은 서버 내부에서만 감당하면 된다

### 우려 2: 기존 slug 포함 주문번호와 신규 짧은 주문번호 혼재

- 선택지 A: 파싱 정규식으로 둘 다 허용
- 선택지 B: 마이그레이션 수행

권장안:
- A 선택

이유:
- 지금 필요한 건 신규 발급 규칙 변경이지, 기존 파일 시스템 정리 작업이 아니다

## 티켓 실행 순서

### T1. 주문번호/상태 모델 계약 갱신

- 목적: 새 `order_id` 형식과 `summary_desc` 필드를 데이터 모델에 반영
- 변경 파일:
  - `src/inhouse_crew/orders.py`
  - `tests/test_orders.py`
- 구현 상세:
  - slug 없는 주문번호 생성으로 변경
  - `OrderStatusRecord` 에 `summary_desc` 추가
  - `from_dict()` 는 과거 `user_request_preview` fallback 지원
  - 순번 계산 정규식은 과거 slug suffix 도 계속 허용
- 완료 기준:
  - 신규 주문번호가 suffix 없이 생성됨
  - 상태 파일이 `summary_desc` 를 기록함
- 검증:
  - `uv run pytest tests/test_orders.py`

### T2. API 응답 계약과 README 갱신

- 목적: 프론트가 `summary_desc` 를 응답에서 바로 받을 수 있게 변경
- 변경 파일:
  - `src/inhouse_crew/api.py`
  - `README.md`
  - `tests/test_api.py`
- 구현 상세:
  - `POST /orders` 응답에 `summary_desc` 추가
  - `GET /orders/{order_id}/status` 가 새 필드를 그대로 반환
  - README 예시를 짧은 주문번호 기준으로 수정
- 완료 기준:
  - API 응답과 문서가 새 계약과 일치
- 검증:
  - `uv run pytest tests/test_api.py`

### T3. 전체 회귀 검증

- 목적: 워커와 pickup 흐름이 새 계약에서도 유지되는지 확인
- 변경 파일:
  - 필요 시 `tests/test_worker.py`
  - 본 문서 상태 섹션
- 구현 상세:
  - 짧은 주문번호 기준 워커 동작 확인
  - 잔여 호환성 리스크 정리
- 완료 기준:
  - 전체 테스트와 린트 통과
- 검증:
  - `uv run pytest`
  - `uv run ruff check src tests`
