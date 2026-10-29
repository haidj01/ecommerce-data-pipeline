# Local Kafka Development Environment

Docker Compose 환경으로 로컬에서 MSK + MSK Connect와 동일한 Kafka → S3 Avro 파이프라인을 구축합니다.

## 아키텍처

```
Producer (Python) → Kafka → Kafka Connect (S3 Sink) → S3 (Avro files)
                      ↓
                Schema Registry (Avro schemas)
```

**비용:**
- 로컬 개발: $0 (S3 storage만 ~$0.10/month)
- AWS MSK 대비: ~$90/month 절감

## 포함된 서비스

| 서비스 | 포트 | 설명 |
|--------|------|------|
| Zookeeper | 2181 | Kafka 메타데이터 관리 |
| Kafka | 9092 | Kafka broker (PLAINTEXT) |
| Schema Registry | 8081 | Avro 스키마 관리 |
| Kafka Connect | 8083 | S3 Sink Connector |
| Kafka UI | 8080 | 모니터링 대시보드 (optional) |

## 사전 요구사항

### 1. Docker & Docker Compose 설치

```bash
# macOS
brew install docker docker-compose

# Ubuntu/Debian
sudo apt-get install docker.io docker-compose

# Verify
docker --version
docker-compose --version
```

### 2. AWS Credentials 설정

S3에 쓰기 위한 AWS credentials가 필요합니다.

```bash
cd docker
cp .env.example .env

# Edit .env with your AWS credentials
# AWS_ACCESS_KEY_ID=your-access-key-id
# AWS_SECRET_ACCESS_KEY=your-secret-access-key
# AWS_DEFAULT_REGION=us-east-1
# S3_BUCKET_NAME=ecommerce-pipeline-landing-ACCOUNT_ID-demo
```

**Note:** `.env` 파일은 `.gitignore`에 포함되어 있으므로 git에 커밋되지 않습니다.

### 3. S3 Bucket 생성

Terraform으로 S3 bucket을 먼저 생성합니다:

```bash
cd ../infra
terraform apply -target=module.storage
```

출력에서 bucket name을 확인하여 `docker/.env`의 `S3_BUCKET_NAME`에 설정합니다.

## Quick Start

### 1. 환경 시작

```bash
cd docker

# Build and start all services
docker-compose up -d

# Check logs
docker-compose logs -f

# Check service health
docker-compose ps
```

**초기 시작 시간:** ~2-3분 (Kafka Connect가 S3 Sink Connector를 다운로드)

### 2. Kafka UI 접속

브라우저에서 http://localhost:8080 접속

- Topics 확인
- Consumer groups 모니터링
- Kafka Connect 상태 확인

### 3. S3 Sink Connector 생성

```bash
# Create connector for customer-events topic
curl -X POST http://localhost:8083/connectors \
  -H "Content-Type: application/json" \
  -d @connectors/s3-sink-customer-events.json

# Create connector for orders topic
curl -X POST http://localhost:8083/connectors \
  -H "Content-Type: application/json" \
  -d @connectors/s3-sink-orders.json

# Check connector status
curl http://localhost:8083/connectors/s3-sink-customer-events/status | jq

# List all connectors
curl http://localhost:8083/connectors | jq
```

### 4. Test Producer

```bash
# Test with kafka-console-producer
docker-compose exec kafka kafka-console-producer \
  --bootstrap-server kafka:29092 \
  --topic customer-events

# Type a message and press Enter
{"customer_id": "CUST-001", "name": "John Doe"}

# Check S3 (should appear within 1 minute)
aws s3 ls s3://YOUR_BUCKET/stream/customer-events/ --recursive
```

## Connector Configuration

S3 Sink Connector는 다음과 같이 설정됩니다:

| 설정 | 값 | 설명 |
|------|-----|------|
| `topics.regex` | `customer-events\|orders` | 대상 topics |
| `s3.bucket.name` | `ecommerce-pipeline-landing-*` | S3 bucket |
| `format.class` | `AvroFormat` | Avro 형식으로 저장 |
| `flush.size` | 1000 | 1000개 메시지마다 파일 생성 |
| `rotate.schedule.interval.ms` | 60000 | 1분마다 파일 rotation |
| `partitioner.class` | `TimeBasedPartitioner` | 시간 기반 파티셔닝 |
| `path.format` | `'stream/'YYYY-MM-dd` | `stream/2024-10-29/` |
| `schema.compatibility` | `NONE` | Schema Registry 사용 안 함 (개발용) |

**파일 경로 예시:**
```
s3://ecommerce-pipeline-landing-123456789-demo/
  stream/customer-events/2024-10-29/customer-events+0+0000000000.avro
  stream/orders/2024-10-29/orders+0+0000000000.avro
```

## 개발 워크플로우

### 1. 로컬 개발 단계

```bash
# Start local Kafka
cd docker
docker-compose up -d

# Develop producer
cd ../producers
python customer_registration_producer.py --local

# Check S3
aws s3 ls s3://YOUR_BUCKET/stream/customer-events/ --recursive
```

### 2. AWS Demo 단계 (당일만)

```bash
# Deploy MSK
cd ../infra
terraform apply -target=module.kafka

# Switch producer to MSK
cd ../producers
python customer_registration_producer.py --aws

# Demo 완료 후 삭제
cd ../infra
terraform destroy -target=module.kafka
```

**동일한 producer 코드가 로컬/AWS 모두에서 동작**하도록 구현합니다 (bootstrap servers만 변경).

## Troubleshooting

### Kafka Connect가 시작되지 않음

**증상:** `ecommerce-kafka-connect` 컨테이너가 계속 재시작

**해결:**
```bash
# Check logs
docker-compose logs kafka-connect

# Common issue: AWS credentials not set
# Make sure docker/.env file exists and has valid credentials
```

### S3에 파일이 생성되지 않음

**증상:** Connector는 RUNNING이지만 S3에 파일이 없음

**해결:**
```bash
# 1. Check connector status
curl http://localhost:8083/connectors/s3-sink-customer-events/status | jq

# 2. Check connector tasks
# Make sure "state": "RUNNING"

# 3. Send test messages
docker-compose exec kafka kafka-console-producer \
  --bootstrap-server kafka:29092 \
  --topic customer-events

# 4. Wait 1 minute (flush interval)
# Files should appear in S3

# 5. Check S3 bucket permissions
aws s3 ls s3://YOUR_BUCKET/stream/
```

### Schema Registry 연결 오류

**증상:** `Schema registry not reachable`

**해결:**
```bash
# Check schema registry health
curl http://localhost:8081/subjects

# Should return empty list [] initially

# Check if schema registry is running
docker-compose ps schema-registry
```

### 포트 충돌

**증상:** `Error starting userland proxy: listen tcp4 0.0.0.0:9092: bind: address already in use`

**해결:**
```bash
# Check what's using the port
lsof -i :9092

# Option 1: Stop local Kafka
brew services stop kafka

# Option 2: Change port in docker-compose.yml
# ports:
#   - "19092:9092"  # Use different local port
```

## Commands

```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# View logs
docker-compose logs -f [service_name]

# Restart a service
docker-compose restart kafka-connect

# Delete all data (clean start)
docker-compose down -v

# Access Kafka container
docker-compose exec kafka bash

# List topics
docker-compose exec kafka kafka-topics \
  --bootstrap-server kafka:29092 --list

# Describe topic
docker-compose exec kafka kafka-topics \
  --bootstrap-server kafka:29092 \
  --describe --topic customer-events

# Consumer (read messages)
docker-compose exec kafka kafka-console-consumer \
  --bootstrap-server kafka:29092 \
  --topic customer-events \
  --from-beginning
```

## Cost Comparison

| 환경 | 월 비용 | 일 비용 |
|------|---------|---------|
| 로컬 Kafka (Docker) | $0 | $0 |
| AWS MSK (kafka.t3.small × 2) | ~$90 | ~$3 |
| S3 Storage (동일) | ~$0.10 | ~$0.003 |

**절감액:** ~$90/month (개발 단계에서 MSK 사용하지 않음)

## Next Steps

1. ✅ 로컬 Kafka 환경 구축
2. [ ] Customer registration producer 개발 (`producers/customer_registration_producer.py`)
3. [ ] Order producer 개발 (`producers/order_producer.py`)
4. [ ] Avro schema를 Schema Registry에 등록
5. [ ] S3 → Databricks Bronze 파이프라인 테스트
6. [ ] Demo 당일: MSK 배포 및 전환

## References

- [Confluent Kafka Docker Images](https://hub.docker.com/u/confluentinc)
- [Kafka Connect S3 Sink Connector](https://docs.confluent.io/kafka-connectors/s3-sink/current/overview.html)
- [Schema Registry Documentation](https://docs.confluent.io/platform/current/schema-registry/index.html)
- [Kafka UI](https://github.com/provectus/kafka-ui)
