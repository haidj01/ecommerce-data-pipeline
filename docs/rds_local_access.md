# RDS 로컬 접근 가이드

Session Manager Port Forwarding을 통해 로컬 머신에서 Private Subnet의 RDS PostgreSQL에 안전하게 접근하는 방법입니다.

## 📋 아키텍처

```
로컬 머신 (localhost:5432)
    ↓ (Session Manager Port Forwarding)
Bastion Host (EC2 t3.micro, Private Subnet)
    ↓ (Security Group 허용)
RDS PostgreSQL (Private Subnet)
```

## 📦 구성 요소

### 1. **Bastion Host (EC2 t3.micro)**
- Private subnet에 배포
- SSM Agent 포함 (Amazon Linux 2)
- PostgreSQL 15 클라이언트 사전 설치
- SSH 키 불필요, 보안 그룹에 SSH 포트 열기 불필요

### 2. **비용**
```
EC2 t3.micro: $0.0104/hour × 24h = $0.25/day
EBS 8GB:      $0.08/GB/month ÷ 30 = $0.003/day
─────────────────────────────────────────
총합:         ~$0.26/day
```

## 🚀 배포 방법

### 1. Bastion 활성화

`infra/terraform.tfvars` 파일에 다음 설정이 추가되어 있는지 확인:
```hcl
enable_rds_bastion = true
```

### 2. 데이터베이스 모듈 배포

```bash
cd infra

# 데이터베이스 + Bastion 배포
terraform apply -target=module.database
```

## 🔌 로컬에서 RDS 접근 방법

### Step 1: RDS 정보 확인

```bash
# Bastion Instance ID 확인
terraform output rds_bastion_instance_id

# RDS 엔드포인트 확인
terraform output -raw rds_endpoint

# 비밀번호 확인
aws secretsmanager get-secret-value \
  --secret-id $(terraform output -raw rds_password_secret_arn) \
  --query SecretString --output text | jq -r .password
```

출력 예시:
```
rds_bastion_instance_id = "i-0123456789abcdef"
rds_endpoint = "ecommerce-pipeline-demo-xxx.us-east-1.rds.amazonaws.com:5432"
password = "Abc123XYZ..."
```

### Step 2: Session Manager Port Forwarding 시작

```bash
# Bastion을 통해 로컬 5432 포트를 RDS로 포워딩
aws ssm start-session \
  --target <BASTION_INSTANCE_ID> \
  --document-name AWS-StartPortForwardingSessionToRemoteHost \
  --parameters "{\"host\":[\"<RDS_ENDPOINT>\"],\"portNumber\":[\"5432\"],\"localPortNumber\":[\"5432\"]}"
```

**실제 예시:**
```bash
aws ssm start-session \
  --target i-0123456789abcdef \
  --document-name AWS-StartPortForwardingSessionToRemoteHost \
  --parameters '{"host":["ecommerce-pipeline-demo-xxx.us-east-1.rds.amazonaws.com"],"portNumber":["5432"],"localPortNumber":["5432"]}'
```

성공하면 다음과 같은 메시지가 표시됩니다:
```
Starting session with SessionId: user-0abc123def456
Port 5432 opened for sessionId user-0abc123def456.
Waiting for connections...
```

### Step 3: 로컬에서 PostgreSQL 연결

**psql 클라이언트 사용:**
```bash
psql -h localhost -p 5432 -U pipeline_admin -d customer_registry
# Password 입력 (Secrets Manager에서 확인한 값)
```

**DBeaver/pgAdmin GUI 도구:**
```
Host:     localhost
Port:     5432
Database: customer_registry
Username: pipeline_admin
Password: <Secrets Manager에서 확인>
SSL:      Prefer (선택)
```

**Python 코드:**
```python
import psycopg2
import boto3
import json

# Secrets Manager에서 비밀번호 가져오기
secrets = boto3.client('secretsmanager')
secret_arn = "arn:aws:secretsmanager:..."  # terraform output에서 확인
response = secrets.get_secret_value(SecretId=secret_arn)
secret = json.loads(response['SecretString'])

# RDS 연결
conn = psycopg2.connect(
    host="localhost",
    port=5432,
    database=secret['dbname'],
    user=secret['username'],
    password=secret['password']
)

cursor = conn.cursor()
cursor.execute("SELECT version();")
print(cursor.fetchone())
cursor.close()
conn.close()
```

### Step 4: 연결 종료

Session Manager 세션을 종료하려면:
- 터미널에서 `Ctrl+C` 입력, 또는
- 터미널에서 `exit` 입력

## 💡 장점

✅ **SSH 키 불필요** - IAM 권한만으로 접근
✅ **보안** - SSH 포트(22) 열 필요 없음, RDS는 private subnet에 유지
✅ **감사 추적** - CloudTrail에 모든 Session Manager 접근 기록
✅ **무료** - Session Manager 사용료 없음, bastion EC2만 과금
✅ **간편함** - 복잡한 VPN 설정 불필요

## 🛠️ 헬퍼 스크립트

편의를 위해 다음 스크립트를 생성할 수 있습니다:

### `infra/scripts/connect-rds.sh`
```bash
#!/bin/bash
set -e

cd "$(dirname "$0")/.."

BASTION_ID=$(terraform output -raw rds_bastion_instance_id)
RDS_ENDPOINT=$(terraform output -raw rds_endpoint | cut -d: -f1)

echo "Starting Session Manager port forwarding..."
echo "Bastion: $BASTION_ID"
echo "RDS: $RDS_ENDPOINT"
echo ""
echo "Connect with: psql -h localhost -p 5432 -U pipeline_admin -d customer_registry"
echo ""

aws ssm start-session \
  --target "$BASTION_ID" \
  --document-name AWS-StartPortForwardingSessionToRemoteHost \
  --parameters "{\"host\":[\"$RDS_ENDPOINT\"],\"portNumber\":[\"5432\"],\"localPortNumber\":[\"5432\"]}"
```

**사용법:**
```bash
chmod +x infra/scripts/connect-rds.sh
./infra/scripts/connect-rds.sh
```

### `infra/scripts/get-rds-password.sh`
```bash
#!/bin/bash
set -e

cd "$(dirname "$0")/.."

SECRET_ARN=$(terraform output -raw rds_password_secret_arn)

echo "Fetching RDS password from Secrets Manager..."
echo ""

aws secretsmanager get-secret-value \
  --secret-id "$SECRET_ARN" \
  --query SecretString --output text | jq .

echo ""
echo "Password only:"
aws secretsmanager get-secret-value \
  --secret-id "$SECRET_ARN" \
  --query SecretString --output text | jq -r .password
```

**사용법:**
```bash
chmod +x infra/scripts/get-rds-password.sh
./infra/scripts/get-rds-password.sh
```

## 🔧 트러블슈팅

### 1. Session Manager 연결 실패

**에러:** `TargetNotConnected`
```
An error occurred (TargetNotConnected) when calling the StartSession operation
```

**해결:**
- Bastion EC2 인스턴스가 실행 중인지 확인: `aws ec2 describe-instances --instance-ids <INSTANCE_ID>`
- SSM Agent가 실행 중인지 확인 (인스턴스 시작 후 1-2분 소요)
- IAM 권한 확인: `AmazonSSMManagedInstanceCore` 정책이 인스턴스 프로파일에 연결되어 있는지 확인

### 2. RDS 연결 실패

**에러:** `could not connect to server: Connection refused`

**해결:**
- Session Manager 포트 포워딩이 실행 중인지 확인
- RDS 엔드포인트가 정확한지 확인
- Security Group 규칙 확인: Bastion SG → RDS SG 5432 포트 허용

### 3. 비밀번호 인증 실패

**에러:** `FATAL: password authentication failed`

**해결:**
- Secrets Manager에서 올바른 비밀번호를 가져왔는지 확인
- 복사/붙여넣기 시 공백이나 개행 문자가 포함되지 않았는지 확인

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

## 🔐 보안 고려사항

### IAM 권한 요구사항

로컬 머신에서 Session Manager를 사용하려면 다음 IAM 권한이 필요합니다:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ssm:StartSession"
      ],
      "Resource": [
        "arn:aws:ec2:*:*:instance/*"
      ],
      "Condition": {
        "StringLike": {
          "ssm:resourceTag/Name": "*bastion*"
        }
      }
    },
    {
      "Effect": "Allow",
      "Action": [
        "ssm:TerminateSession",
        "ssm:ResumeSession"
      ],
      "Resource": [
        "arn:aws:ssm:*:*:session/${aws:username}-*"
      ]
    }
  ]
}
```

### 감사 및 모니터링

- **CloudTrail:** 모든 Session Manager 접근이 자동으로 기록됨
- **CloudWatch Logs:** Session Manager 세션 로그를 별도로 저장 가능 (옵션)
- **VPC Flow Logs:** 네트워크 트래픽 모니터링 (옵션)

## 📚 참고 자료

- [AWS Systems Manager Session Manager](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager.html)
- [Port Forwarding Using Session Manager](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-working-with-sessions-start.html#sessions-remote-port-forwarding)
- [Installing Session Manager Plugin](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-working-with-install-plugin.html)

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
