# Terraform Targeted Apply Guide

Terraform에서 특정 모듈만 선택적으로 apply하는 방법

## 기본 사용법

```bash
# networking과 iam 모듈만 apply
terraform apply -target=module.networking -target=module.iam

# 또는 plan을 먼저 확인하고 싶다면
terraform plan -target=module.networking -target=module.iam

# plan 확인 후 apply
terraform apply -target=module.networking -target=module.iam
```

## 단계별 적용 순서 (의존성 고려)

프로젝트 구조상 추천하는 순서:

```bash
# 1단계: networking과 iam
terraform apply -target=module.networking -target=module.iam

# 2단계: storage (S3 버킷)
terraform apply -target=module.storage

# 3단계: kafka (MSK - networking에 의존)
terraform apply -target=module.kafka

# 4단계: database (RDS - networking에 의존)
terraform apply -target=module.database

# 5단계: orchestration (MWAA - networking, storage, iam에 의존)
terraform apply -target=module.orchestration

# 6단계: streaming (EMR, OpenSearch - networking, iam, kafka에 의존)
terraform apply -target=module.streaming

# 7단계 (선택): databricks (storage, iam에 의존)
terraform apply -target=module.databricks

# 마지막: 전체 적용하여 누락된 부분 확인
terraform apply
```

## 모듈 의존성 맵

```
module.networking (기반)
├── module.kafka (MSK)
├── module.database (RDS)
├── module.orchestration (MWAA)
└── module.streaming (EMR, OpenSearch)

module.iam (기반)
├── module.kafka (MSK Connect)
├── module.orchestration (MWAA)
├── module.streaming (EMR)
└── module.databricks (Unity Catalog)

module.storage (기반)
├── module.orchestration (MWAA)
├── module.kafka (MSK Connect)
└── module.databricks (External Volume)

module.kafka
└── module.streaming (EMR에서 MSK 접속)
```

## 자동 승인 옵션

```bash
# 확인 없이 바로 적용 (위험할 수 있으므로 신중히 사용)
terraform apply -target=module.networking -target=module.iam -auto-approve
```

## 특정 모듈 Destroy

```bash
# 특정 모듈만 삭제
terraform destroy -target=module.streaming -target=module.orchestration

# 역순으로 삭제 (의존성 고려)
terraform destroy -target=module.databricks
terraform destroy -target=module.streaming
terraform destroy -target=module.orchestration
terraform destroy -target=module.database
terraform destroy -target=module.kafka
terraform destroy -target=module.storage
terraform destroy -target=module.iam
terraform destroy -target=module.networking
```

## 특정 리소스만 타겟팅

```bash
# 모듈 전체가 아닌 특정 리소스만
terraform apply -target=module.networking.aws_vpc.main

# 여러 리소스
terraform apply \
  -target=module.networking.aws_vpc.main \
  -target=module.networking.aws_subnet.private[0] \
  -target=module.networking.aws_subnet.private[1]
```

## 유용한 명령어

```bash
# 현재 state 확인
terraform state list

# 특정 모듈의 리소스 목록
terraform state list | grep module.networking

# 특정 리소스 상세 정보
terraform state show module.networking.aws_vpc.main

# Plan 결과를 파일로 저장
terraform plan -target=module.networking -out=networking.tfplan

# 저장된 plan 적용
terraform apply networking.tfplan
```

## 주의사항

⚠️ **`-target` 사용 시 주의점:**

1. **의존성 불완전성**
   - Terraform은 의존성을 자동으로 포함하지만, 완벽하지 않을 수 있습니다
   - 부분 적용 후에는 반드시 `terraform apply`로 전체 상태를 확인하세요

2. **순서 중요**
   - 의존성이 있는 리소스는 반드시 순서대로 적용해야 합니다
   - 예: `module.kafka`는 `module.networking`의 security group을 참조하므로, networking을 먼저 apply

3. **State 불일치 가능성**
   - 부분 적용을 자주 사용하면 state 파일과 실제 인프라가 불일치할 수 있습니다
   - 정기적으로 `terraform plan`으로 drift를 확인하세요

4. **프로덕션 환경 주의**
   - 프로덕션 환경에서는 `-target` 사용을 최소화하세요
   - 전체 `terraform plan` → `terraform apply` 워크플로우를 권장합니다

## 데모 환경 빠른 구축 예시

```bash
# 1. 기본 인프라만 먼저 구축 (저렴함)
terraform apply \
  -target=module.networking \
  -target=module.iam \
  -target=module.storage

# 2. 개발/테스트 시작 전에 나머지 추가
terraform apply \
  -target=module.database \
  -target=module.kafka

# 3. 데모 당일에 비용이 큰 서비스 추가
terraform apply \
  -target=module.orchestration \
  -target=module.streaming

# 4. 전체 확인
terraform apply

# 5. 데모 종료 후 비용 절감 (역순 삭제)
terraform destroy -target=module.streaming
terraform destroy -target=module.orchestration
```

## 비용 최적화 팁

프로젝트의 1-day 데모 특성상:

```bash
# 평소: 기본 인프라만 유지 (VPC, S3, IAM - 거의 무료)
terraform apply -target=module.networking -target=module.iam -target=module.storage

# 데모 당일: 전체 인프라 구축
terraform apply

# 데모 후: 비용 발생 서비스만 제거
terraform destroy -target=module.streaming      # EMR, OpenSearch
terraform destroy -target=module.orchestration  # MWAA
terraform destroy -target=module.kafka          # MSK
terraform destroy -target=module.database       # RDS
```
