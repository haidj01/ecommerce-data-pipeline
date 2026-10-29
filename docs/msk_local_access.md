# MSK 로컬 접근 가이드

Session Manager + SSH Tunnel을 통해 로컬 머신에서 Private Subnet의 MSK (Kafka) 클러스터에 안전하게 접근하는 방법입니다.

## 📋 아키텍처

```
로컬 머신 (localhost:9092, 9093, ...)
    ↓ (SSH Tunnel via Session Manager)
Bastion Host (EC2 t3.micro, Private Subnet)
    ↓ (Security Group 허용)
MSK Cluster (Multiple Brokers, Private Subnet)
```

## 🔧 작동 원리

MSK는 여러 broker로 구성되어 있고 각 broker는 별도의 호스트명과 포트를 사용합니다. 로컬에서 접근하려면:

1. **Session Manager를 SSH ProxyCommand로 사용** - SSH 키 없이 bastion에 연결
2. **SSH 터널을 통해 각 broker에 대한 포트 포워딩** - localhost의 여러 포트를 각 broker에 매핑
3. **Kafka 클라이언트는 localhost bootstrap servers 사용** - 예: `localhost:9092,localhost:9093`

## 🚀 사용 방법

### Step 1: MSK 배포 확인

```bash
cd infra

# MSK 클러스터 배포 (아직 배포하지 않은 경우)
terraform apply -target=module.kafka

# 또는 전체 인프라 배포
terraform apply
```

### Step 2: SSH Tunnel 시작

```bash
cd infra
./scripts/connect-msk.sh
```

스크립트는 자동으로:
- Bastion 인스턴스 ID를 가져옵니다
- MSK broker 엔드포인트를 가져옵니다
- 각 broker에 대한 SSH 터널을 생성합니다
- localhost 포트를 출력합니다

**출력 예시:**
```
===================================================================
  SSH Tunnel Configuration
===================================================================

This script will create SSH tunnels for each MSK broker.
You can then connect Kafka clients to localhost with the following
bootstrap servers:

  localhost:9092 -> b-1.demo-cluster.xxx.kafka.us-east-1.amazonaws.com:9094
  localhost:9093 -> b-2.demo-cluster.xxx.kafka.us-east-1.amazonaws.com:9094

Bootstrap servers for your Kafka client:
  localhost:9092,localhost:9093

===================================================================

Starting SSH tunnels (press Ctrl+C to stop)...
```

### Step 3: Kafka 클라이언트 연결

**kafka-console-producer 사용:**
```bash
# 별도 터미널에서
kafka-console-producer \
  --bootstrap-server localhost:9092,localhost:9093 \
  --topic customer-events \
  --producer-property security.protocol=PLAINTEXT
```

**Note:** 로컬 연결이므로 `security.protocol=PLAINTEXT` 사용. SSH 터널 내부에서는 이미 암호화됨.

**kafka-console-consumer 사용:**
```bash
kafka-console-consumer \
  --bootstrap-server localhost:9092,localhost:9093 \
  --topic customer-events \
  --from-beginning
```

**Python (confluent-kafka) 사용:**
```python
from confluent_kafka import Producer, Consumer

# Producer 설정
producer_conf = {
    'bootstrap.servers': 'localhost:9092,localhost:9093',
    'client.id': 'my-producer'
}

producer = Producer(producer_conf)

# Consumer 설정
consumer_conf = {
    'bootstrap.servers': 'localhost:9092,localhost:9093',
    'group.id': 'my-consumer-group',
    'auto.offset.reset': 'earliest'
}

consumer = Consumer(consumer_conf)
consumer.subscribe(['customer-events'])
```

**kcat (kafkacat) 사용:**
```bash
# Topic 리스트 확인
kcat -b localhost:9092,localhost:9093 -L

# 메시지 produce
echo '{"customer_id": "CUST-001", "name": "John Doe"}' | \
  kcat -b localhost:9092,localhost:9093 -t customer-events -P

# 메시지 consume
kcat -b localhost:9092,localhost:9093 -t customer-events -C
```

### Step 4: 연결 종료

SSH 터널을 종료하려면:
- 터미널에서 `Ctrl+C` 입력

## 💡 장점

✅ **SSH 키 불필요** - Session Manager를 ProxyCommand로 사용
✅ **보안** - SSH 포트(22) 외부 노출 없음, MSK는 private subnet에 유지
✅ **감사 추적** - CloudTrail에 모든 Session Manager 접근 기록
✅ **간편함** - 단일 스크립트로 모든 broker 터널 자동 설정
✅ **무료** - Session Manager 사용료 없음, bastion EC2만 과금

## 🔐 보안 고려사항

### IAM 인증 (AWS MSK에서)

이 데모는 간단함을 위해 로컬 SSH 터널에서는 PLAINTEXT를 사용하지만, **실제 프로덕션 환경**에서는 MSK IAM 인증을 사용해야 합니다:

**MSK IAM 인증 사용 시:**
```python
from confluent_kafka import Producer

producer_conf = {
    'bootstrap.servers': 'localhost:9092,localhost:9093',
    'security.protocol': 'SASL_SSL',
    'sasl.mechanism': 'AWS_MSK_IAM',
    'sasl.jaas.config': 'software.amazon.msk.auth.iam.IAMLoginModule required;',
    'ssl.ca.location': '/path/to/ca-cert'
}
```

현재 MSK 설정:
- **IAM 인증 활성화**: `client_authentication.sasl.iam = true`
- **TLS 암호화**: `encryption_in_transit.client_broker = "TLS"`
- **비인증 접근 차단**: `client_authentication.unauthenticated = false`

### 필요한 IAM 권한

로컬 머신에서 MSK에 접근하려면 다음 IAM 권한이 필요합니다:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "kafka-cluster:Connect",
        "kafka-cluster:DescribeCluster"
      ],
      "Resource": "arn:aws:kafka:*:*:cluster/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "kafka-cluster:*Topic*",
        "kafka-cluster:WriteData",
        "kafka-cluster:ReadData"
      ],
      "Resource": "arn:aws:kafka:*:*:topic/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "kafka-cluster:AlterGroup",
        "kafka-cluster:DescribeGroup"
      ],
      "Resource": "arn:aws:kafka:*:*:group/*"
    }
  ]
}
```

## 🔧 트러블슈팅

### 1. Session Manager 연결 실패

**에러:** `TargetNotConnected`

**해결:**
- Bastion EC2 인스턴스가 실행 중인지 확인
- SSM Agent가 실행 중인지 확인 (인스턴스 시작 후 1-2분 소요)
- IAM 권한 확인: `AmazonSSMManagedInstanceCore` 정책 확인

### 2. SSH 터널 연결 실패

**에러:** `ssh: Could not resolve hostname`

**해결:**
- AWS CLI가 설치되어 있는지 확인
- AWS 프로파일이 올바르게 설정되어 있는지 확인
- Session Manager 플러그인이 설치되어 있는지 확인

### 3. Kafka 연결 실패

**에러:** `Connection refused` 또는 `Timeout`

**해결:**
- SSH 터널이 실행 중인지 확인
- Bootstrap servers가 올바른지 확인 (스크립트 출력 확인)
- Security Group 규칙 확인: Bastion SG → MSK SG 9092-9098 포트 허용

### 4. AWS CLI Session Manager Plugin 미설치

**에러:** `SessionManagerPlugin is not found`

**해결:**
```bash
# macOS
brew install --cask session-manager-plugin

# Ubuntu/Debian
curl "https://s3.amazonaws.com/session-manager-downloads/plugin/latest/ubuntu_64bit/session-manager-plugin.deb" -o "session-manager-plugin.deb"
sudo dpkg -i session-manager-plugin.deb

# Verify installation
session-manager-plugin
```

### 5. Kafka Tools 미설치

**필수 도구:**

```bash
# macOS - Kafka CLI tools
brew install kafka

# macOS - kcat (kafkacat)
brew install kcat

# Ubuntu/Debian - Kafka CLI tools
wget https://downloads.apache.org/kafka/3.6.0/kafka_2.13-3.6.0.tgz
tar -xzf kafka_2.13-3.6.0.tgz
cd kafka_2.13-3.6.0

# Python - confluent-kafka
pip install confluent-kafka
```

## 📚 참고 자료

- [AWS Systems Manager Session Manager](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager.html)
- [SSH over Session Manager](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-getting-started-enable-ssh-connections.html)
- [MSK IAM Authentication](https://docs.aws.amazon.com/msk/latest/developerguide/iam-access-control.html)
- [Apache Kafka Documentation](https://kafka.apache.org/documentation/)

## 🗑️ 정리 (Teardown)

데모 종료 후 비용 절감을 위해 Bastion 비활성화:

```bash
# terraform.tfvars 수정
enable_rds_bastion = false

# 재배포
terraform apply -target=module.database
```

또는 전체 인프라 삭제:
```bash
terraform destroy
```

## 🎯 다음 단계

1. **Producer 개발**: Kafka producer 개발하여 customer-events, orders 토픽에 메시지 전송
2. **Schema Registry 사용**: Glue Schema Registry를 사용하여 Avro 스키마 관리
3. **MSK Connect 설정**: S3 Sink Connector 설정하여 Kafka → S3 데이터 파이프라인 구축
4. **Databricks 연동**: Auto Loader를 사용하여 S3 → Bronze 레이어 수집
