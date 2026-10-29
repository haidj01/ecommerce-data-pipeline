# 로컬 Kafka 환경 구성 가이드

로컬에서 MSK Connect와 동일한 방식으로 Kafka → S3 Avro 파이프라인을 구축하는 가이드입니다.

## 📋 개요

### 아키텍처

```
[로컬 개발 - 비용 $0]
Producer (Python) → Local Kafka (Docker) → Kafka Connect (S3 Sink) → S3 (Avro)
                         ↓
                   Schema Registry (Avro schemas)

[AWS Demo - 비용 ~$3/day]
Producer (ECS/Local) → MSK → MSK Connect → S3 (Avro)
```

### 비용 절감 효과

| 환경 | 월 비용 | 개발 기간 절감 (3개월 기준) |
|------|---------|---------------------------|
| **로컬 Kafka (Docker)** | **$0** | - |
| AWS MSK (kafka.t3.small × 2) | ~$90/month | **-$270** |
| S3 Storage (동일) | ~$0.10/month | ~$0.30 |

**결과:** 개발 단계에서 MSK 비용($270) 절감, Demo 당일만 배포 (~$3)

### MSK 비용 상세 (참고)

현재 설정 기준 (kafka.t3.small × 2 brokers):

| 항목 | 계산 | 월 비용 |
|------|------|---------|
| Broker 인스턴스 | 2 brokers × $0.046/hour × 730 hours | ~$67.16 |
| Storage (EBS GP3) | 2 brokers × 100GB × $0.10/GB-month | ~$20.00 |
| CloudWatch Logs | ~5GB/month × $0.50/GB | ~$2.50 |
| Data Transfer | (minimal within VPC) | ~$0-5 |
| **총 월 비용** | | **~$89-95** |
| **일 비용** | | **~$3** |

MSK Connect 추가 시: +$80-160/month (Worker MCU 비용)

## 🗂️ 생성된 파일

```
docker/
├── docker-compose.yml                    # Kafka, Schema Registry, Kafka Connect, Kafka UI
├── kafka-connect/
│   ├── Dockerfile                        # S3 Sink Connector 자동 설치
│   └── plugins/                          # Connector plugins 저장 위치
├── connectors/
│   ├── s3-sink-customer-events.json      # customer-events → S3 설정
│   ├── s3-sink-orders.json               # orders → S3 설정
│   └── s3-sink-inventory-events.json     # inventory-events → S3 설정
├── .env.example                          # AWS credentials 템플릿
└── README.md                             # 상세 사용 가이드
```

## 📦 포함된 서비스

| 서비스 | 포트 | 설명 |
|--------|------|------|
| **Zookeeper** | 2181 | Kafka 메타데이터 관리 |
| **Kafka** | 9092 | Kafka broker (PLAINTEXT) |
| **Schema Registry** | 8081 | Avro 스키마 관리 |
| **Kafka Connect** | 8083 | S3 Sink Connector |
| **Kafka UI** | 8080 | 모니터링 대시보드 (optional) |

## 🚀 Quick Start

### Step 1: S3 Bucket 생성 (Terraform)

먼저 S3 bucket을 생성합니다:

```bash
cd infra
terraform apply -target=module.storage
```

출력 예시:
```
Outputs:

landing_bucket_arn = "arn:aws:s3:::ecommerce-pipeline-landing-979126074847-demo"
landing_bucket_name = "ecommerce-pipeline-landing-979126074847-demo"
```

**bucket name을 복사하세요** (다음 단계에서 사용).

### Step 2: AWS Credentials 설정

```bash
cd ../docker
cp .env.example .env

# .env 파일 편집
vim .env
```

**`.env` 파일 내용:**
```bash
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
AWS_DEFAULT_REGION=us-east-1
S3_BUCKET_NAME=ecommerce-pipeline-landing-979126074847-demo
```

⚠️ **중요:** `.env` 파일은 `.gitignore`에 포함되어 있으므로 git에 커밋되지 않습니다.

### Step 3: Docker Compose 시작

```bash
# 서비스 시작 (최초 2-3분 소요)
docker-compose up -d

# 로그 확인
docker-compose logs -f

# 서비스 상태 확인
docker-compose ps
```

**예상 출력:**
```
NAME                        IMAGE                                    STATUS
ecommerce-kafka             confluentinc/cp-kafka:7.6.0             Up
ecommerce-kafka-connect     docker-kafka-connect                     Up
ecommerce-kafka-ui          provectuslabs/kafka-ui:latest           Up
ecommerce-schema-registry   confluentinc/cp-schema-registry:7.6.0   Up
ecommerce-zookeeper         confluentinc/cp-zookeeper:7.6.0         Up
```

**초기 시작 시간:** Kafka Connect가 S3 Sink Connector를 다운로드하는 데 2-3분 소요.

### Step 4: Kafka UI 확인

브라우저에서 http://localhost:8080 접속

확인 사항:
- ✅ Kafka broker가 healthy 상태
- ✅ Schema Registry 연결됨
- ✅ Kafka Connect 실행 중

### Step 5: S3 Sink Connector 생성

```bash
cd docker

# customer-events topic → S3 connector
curl -X POST http://localhost:8083/connectors \
  -H "Content-Type: application/json" \
  -d @connectors/s3-sink-customer-events.json

# orders topic → S3 connector
curl -X POST http://localhost:8083/connectors \
  -H "Content-Type: application/json" \
  -d @connectors/s3-sink-orders.json

# inventory-events topic → S3 connector
curl -X POST http://localhost:8083/connectors \
  -H "Content-Type: application/json" \
  -d @connectors/s3-sink-inventory-events.json
```

**Connector 상태 확인:**
```bash
# 개별 connector 상태
curl http://localhost:8083/connectors/s3-sink-customer-events/status | jq

# 모든 connectors 목록
curl http://localhost:8083/connectors | jq

# Kafka UI에서도 확인 가능 (http://localhost:8080)
```

**예상 출력:**
```json
{
  "name": "s3-sink-customer-events",
  "connector": {
    "state": "RUNNING",
    "worker_id": "kafka-connect:8083"
  },
  "tasks": [
    {
      "id": 0,
      "state": "RUNNING",
      "worker_id": "kafka-connect:8083"
    }
  ]
}
```

### Step 6: 테스트 메시지 전송

```bash
# Kafka console producer로 테스트 메시지 전송
docker-compose exec kafka kafka-console-producer \
  --bootstrap-server kafka:29092 \
  --topic customer-events

# 메시지 입력 (JSON 형식):
{"customer_id": "CUST-001", "name": "John Doe", "email": "john@example.com"}
{"customer_id": "CUST-002", "name": "Jane Smith", "email": "jane@example.com"}

# Ctrl+C로 종료
```

**1분 후 S3 확인:**
```bash
aws s3 ls s3://ecommerce-pipeline-landing-979126074847-demo/stream/customer-events/ --recursive
```

**예상 출력:**
```
2024-10-29 10:15:32       1245 stream/customer-events/2024-10-29/customer-events+0+0000000000.avro
```

**파일 다운로드 및 확인:**
```bash
# Avro 파일 다운로드
aws s3 cp s3://YOUR_BUCKET/stream/customer-events/2024-10-29/customer-events+0+0000000000.avro ./test.avro

# Avro 파일 읽기 (avro-tools 필요)
# brew install avro-tools
avro-tools tojson test.avro
```

## 🔧 S3 Sink Connector 설정

Connector는 다음과 같이 구성됩니다:

| 설정 | 값 | 설명 |
|------|-----|------|
| `connector.class` | `S3SinkConnector` | Confluent S3 Sink Connector |
| `topics` | `customer-events` | 대상 topic |
| `s3.bucket.name` | `${env:S3_BUCKET_NAME}` | S3 bucket (.env에서 읽음) |
| `format.class` | `AvroFormat` | Avro 형식으로 저장 |
| `flush.size` | 1000 | 1000개 메시지마다 파일 생성 |
| `rotate.schedule.interval.ms` | 60000 | 1분마다 파일 rotation |
| `partitioner.class` | `TimeBasedPartitioner` | 시간 기반 파티셔닝 |
| `path.format` | `'stream/customer-events/'YYYY-MM-dd` | S3 경로 형식 |
| `schema.compatibility` | `NONE` | Schema Registry 미사용 (개발용) |
| `errors.tolerance` | `all` | 에러 무시 (로그만 기록) |

**생성되는 S3 경로:**
```
s3://ecommerce-pipeline-landing-ACCOUNT_ID-demo/
  stream/
    customer-events/
      2024-10-29/
        customer-events+0+0000000000.avro
        customer-events+0+0000001000.avro
    orders/
      2024-10-29/
        orders+0+0000000000.avro
    inventory-events/
      2024-10-29/
        inventory-events+0+0000000000.avro
```

## 📊 개발 워크플로우

### Phase 1: 로컬 개발 (비용 $0)

```bash
# 1. 로컬 Kafka 시작
cd docker
docker-compose up -d

# 2. Producer 개발 및 테스트
cd ../producers
python customer_registration_producer.py --local

# 3. S3 확인
aws s3 ls s3://YOUR_BUCKET/stream/customer-events/ --recursive

# 4. Databricks Bronze 테스트
# Auto Loader로 S3 → Bronze 수집
```

**개발 기간:** 2-3개월 → **절감 비용: ~$270**

### Phase 2: AWS Demo (당일만, 비용 ~$3)

```bash
# 1. MSK 배포
cd infra
terraform apply -target=module.kafka
# 15분 소요

# 2. Producer를 MSK로 전환
cd ../producers
python customer_registration_producer.py --aws

# 3. Demo 실행
# - OpenSearch 실시간 대시보드
# - Databricks AI/BI 대시보드

# 4. Demo 완료 후 즉시 삭제
cd ../infra
terraform destroy -target=module.kafka
# 15분 소요
```

**Demo 비용:** ~$3 (1일)

### 코드 재사용 (로컬 ↔ AWS)

**동일한 Producer 코드**가 로컬과 AWS 모두에서 동작하도록 구현:

```python
# customer_registration_producer.py
import argparse

def get_kafka_config(env):
    if env == 'local':
        return {
            'bootstrap.servers': 'localhost:9092',
            'schema.registry.url': 'http://localhost:8081'
        }
    elif env == 'aws':
        return {
            'bootstrap.servers': os.environ['MSK_BOOTSTRAP_SERVERS'],
            'security.protocol': 'SASL_SSL',
            'sasl.mechanism': 'AWS_MSK_IAM',
            # ... IAM auth config
        }

parser = argparse.ArgumentParser()
parser.add_argument('--local', action='store_true')
parser.add_argument('--aws', action='store_true')
args = parser.parse_args()

config = get_kafka_config('local' if args.local else 'aws')
```

## 🛠️ 유용한 Commands

### Docker Compose 관리

```bash
# 서비스 시작
docker-compose up -d

# 서비스 중지
docker-compose down

# 로그 확인
docker-compose logs -f [service_name]

# 특정 서비스 재시작
docker-compose restart kafka-connect

# 전체 삭제 (데이터 포함)
docker-compose down -v
```

### Kafka 관리

```bash
# Kafka 컨테이너 접속
docker-compose exec kafka bash

# Topics 목록
docker-compose exec kafka kafka-topics \
  --bootstrap-server kafka:29092 --list

# Topic 상세 정보
docker-compose exec kafka kafka-topics \
  --bootstrap-server kafka:29092 \
  --describe --topic customer-events

# Consumer로 메시지 읽기
docker-compose exec kafka kafka-console-consumer \
  --bootstrap-server kafka:29092 \
  --topic customer-events \
  --from-beginning

# Topic 삭제
docker-compose exec kafka kafka-topics \
  --bootstrap-server kafka:29092 \
  --delete --topic customer-events
```

### Kafka Connect 관리

```bash
# Connector 목록
curl http://localhost:8083/connectors | jq

# Connector 상태
curl http://localhost:8083/connectors/s3-sink-customer-events/status | jq

# Connector 재시작
curl -X POST http://localhost:8083/connectors/s3-sink-customer-events/restart

# Connector 삭제
curl -X DELETE http://localhost:8083/connectors/s3-sink-customer-events

# Task 재시작
curl -X POST http://localhost:8083/connectors/s3-sink-customer-events/tasks/0/restart
```

## 🔍 트러블슈팅

### 1. Kafka Connect가 시작되지 않음

**증상:** `ecommerce-kafka-connect` 컨테이너가 계속 재시작

**확인:**
```bash
docker-compose logs kafka-connect
```

**일반적인 원인:**
- AWS credentials가 `.env`에 설정되지 않음
- S3 bucket에 접근 권한 없음

**해결:**
```bash
# .env 파일 확인
cat docker/.env

# AWS credentials 테스트
aws s3 ls s3://YOUR_BUCKET/

# IAM 권한 확인 (s3:PutObject 필요)
```

### 2. S3에 파일이 생성되지 않음

**증상:** Connector는 RUNNING이지만 S3에 파일이 없음

**확인:**
```bash
# 1. Connector 상태 확인
curl http://localhost:8083/connectors/s3-sink-customer-events/status | jq

# 2. Task 상태가 RUNNING인지 확인
# "state": "RUNNING"이어야 함

# 3. 메시지 전송 확인
docker-compose exec kafka kafka-console-consumer \
  --bootstrap-server kafka:29092 \
  --topic customer-events \
  --from-beginning

# 4. Connector 로그 확인
docker-compose logs kafka-connect | grep s3-sink-customer-events
```

**원인 및 해결:**
- **메시지가 없음:** Producer에서 메시지를 전송했는지 확인
- **Flush 간격:** 1000개 메시지 or 1분 대기 필요
- **S3 권한:** IAM user에 s3:PutObject 권한 확인

### 3. Schema Registry 연결 오류

**증상:** `Schema registry not reachable`

**확인:**
```bash
# Schema Registry health check
curl http://localhost:8081/subjects

# 빈 배열 [] 반환되어야 함

# Schema Registry 상태
docker-compose ps schema-registry
```

**해결:**
```bash
# Schema Registry 재시작
docker-compose restart schema-registry

# 로그 확인
docker-compose logs schema-registry
```

### 4. 포트 충돌

**증상:** `bind: address already in use`

**확인:**
```bash
# 포트 사용 확인
lsof -i :9092
lsof -i :8080
```

**해결:**

**Option 1: 로컬 Kafka 중지**
```bash
brew services stop kafka
```

**Option 2: 포트 변경**
```yaml
# docker-compose.yml 수정
ports:
  - "19092:9092"  # 9092 대신 19092 사용
```

### 5. Avro 직렬화 오류

**증상:** Producer에서 Avro 직렬화 실패

**확인:**
```bash
# Schema Registry에 스키마가 등록되었는지 확인
curl http://localhost:8081/subjects
```

**해결:**
```python
# Producer 코드에서 schema.registry.url 확인
producer_conf = {
    'bootstrap.servers': 'localhost:9092',
    'schema.registry.url': 'http://localhost:8081'
}
```

## 📚 다음 단계

1. ✅ 로컬 Kafka 환경 구축 완료
2. ✅ S3 Sink Connector 설정 완료
3. [ ] **Customer registration producer 개발** (`producers/customer_registration_producer.py`)
4. [ ] Order producer 개발 (`producers/order_producer.py`)
5. [ ] Inventory event producer 개발
6. [ ] Avro schema를 Schema Registry에 등록
7. [ ] S3 → Databricks Bronze Auto Loader 테스트
8. [ ] Silver/Gold transformations
9. [ ] Demo 당일: MSK 배포 및 전환

## 🔗 참고 자료

- [Confluent Kafka Docker Images](https://hub.docker.com/u/confluentinc)
- [Kafka Connect S3 Sink Connector](https://docs.confluent.io/kafka-connectors/s3-sink/current/overview.html)
- [Schema Registry Documentation](https://docs.confluent.io/platform/current/schema-registry/index.html)
- [Kafka UI](https://github.com/provectus/kafka-ui)
- [AWS MSK Pricing](https://aws.amazon.com/msk/pricing/)
- [로컬 RDS 접근 가이드](./rds_local_access.md)
- [MSK 로컬 접근 가이드](./msk_local_access.md)

## 💰 비용 요약

| 항목 | 로컬 개발 | AWS Demo (1일) |
|------|-----------|---------------|
| Kafka | $0 | ~$3 |
| S3 Storage | ~$0.10/month | ~$0.003/day |
| Data Transfer | $0 | $0 (same VPC) |
| **총계** | **~$0.10/month** | **~$3/day** |

**3개월 개발 기간 절감:**
- MSK 미사용: -$270
- Demo 1일만: +$3
- **순 절감: $267**
