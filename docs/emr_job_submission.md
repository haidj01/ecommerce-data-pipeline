# EMR Spark Job Submission Guide

EMR에 Spark job을 submit하는 AWS CLI 명령어 가이드

## 1. 실행 중인 클러스터에 Step 추가 (가장 일반적)

```bash
# PySpark job 제출
aws emr add-steps \
  --cluster-id j-XXXXXXXXXXXXX \
  --steps Type=Spark,Name="Streaming Job",ActionOnFailure=CONTINUE,Args=[--deploy-mode,cluster,--master,yarn,--conf,spark.streaming.backpressure.enabled=true,s3://bucket-name/scripts/streaming_job.py,--broker,b-1.xxx:9098,--topic,orders]

# Spark JAR job 제출
aws emr add-steps \
  --cluster-id j-XXXXXXXXXXXXX \
  --steps Type=Spark,Name="My Spark Job",ActionOnFailure=TERMINATE_CLUSTER,Args=[--class,com.example.MainClass,--master,yarn,--deploy-mode,cluster,s3://bucket-name/jars/my-app.jar,arg1,arg2]
```

## 2. 프로젝트에 맞는 실제 예시 (Structured Streaming)

```bash
# Order 스트림 처리 → OpenSearch
aws emr add-steps \
  --cluster-id j-XXXXXXXXXXXXX \
  --region us-east-1 \
  --steps Type=Spark,Name="Order Streaming to OpenSearch",ActionOnFailure=CONTINUE,Args=[\
--deploy-mode,cluster,\
--master,yarn,\
--conf,spark.streaming.kafka.maxRatePerPartition=1000,\
--conf,spark.sql.streaming.checkpointLocation=s3://ecommerce-pipeline-landing-xxx/checkpoints/orders/,\
--packages,org.apache.spark:spark-sql-kafka-0-10_2.12:3.4.0,org.opensearch.client:opensearch-spark-30_2.12:1.0.1,\
s3://ecommerce-pipeline-landing-xxx/scripts/order_streaming.py,\
--bootstrap-servers,b-1.ecommerce-msk.xxx.kafka.us-east-1.amazonaws.com:9098,\
--topic,orders,\
--opensearch-host,vpc-ecommerce-pipeline-demo-os-xxx.us-east-1.es.amazonaws.com,\
--opensearch-port,443]
```

## 3. Step 상태 확인

```bash
# Step 목록 조회
aws emr list-steps --cluster-id j-XXXXXXXXXXXXX

# 특정 Step 상세 정보
aws emr describe-step \
  --cluster-id j-XXXXXXXXXXXXX \
  --step-id s-XXXXXXXXXXXXX
```

## 4. 클러스터 생성 시 Step 포함

```bash
aws emr create-cluster \
  --name "Streaming Cluster" \
  --release-label emr-6.14.0 \
  --applications Name=Spark Name=Hadoop \
  --ec2-attributes KeyName=my-key,SubnetId=subnet-xxx \
  --instance-type m5.xlarge \
  --instance-count 3 \
  --use-default-roles \
  --steps Type=Spark,Name="Initial Job",ActionOnFailure=CONTINUE,Args=[...] \
  --auto-terminate
```

## 5. SSH로 직접 spark-submit (개발/테스트용)

```bash
# EMR 마스터 노드에 SSH 접속 후
spark-submit \
  --master yarn \
  --deploy-mode cluster \
  --num-executors 2 \
  --executor-memory 4g \
  --executor-cores 2 \
  --conf spark.streaming.kafka.maxRatePerPartition=1000 \
  --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.4.0 \
  s3://bucket/scripts/streaming_job.py \
  --bootstrap-servers b-1.xxx:9098 \
  --topic orders
```

## 6. JSON 파일로 Step 정의 (복잡한 설정)

`step-config.json`:
```json
[
  {
    "Name": "Order Streaming Job",
    "ActionOnFailure": "CONTINUE",
    "Type": "Spark",
    "Args": [
      "--deploy-mode", "cluster",
      "--master", "yarn",
      "--conf", "spark.streaming.backpressure.enabled=true",
      "--packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.4.0",
      "s3://bucket/scripts/streaming_job.py",
      "--bootstrap-servers", "b-1.xxx:9098",
      "--topic", "orders"
    ]
  }
]
```

```bash
aws emr add-steps \
  --cluster-id j-XXXXXXXXXXXXX \
  --steps file://step-config.json
```

## 주요 파라미터 설명

| 파라미터 | 설명 |
|---|---|
| `--cluster-id` | EMR 클러스터 ID (j-로 시작) |
| `Type=Spark` | Step 타입 (Spark, Hive, Pig 등) |
| `ActionOnFailure` | 실패 시 동작: CONTINUE, TERMINATE_CLUSTER, CANCEL_AND_WAIT |
| `--deploy-mode` | cluster (YARN에서 실행) 또는 client |
| `--master` | yarn, local[*] 등 |
| `--packages` | Maven 좌표로 의존성 자동 다운로드 |
| `--jars` | 추가 JAR 파일 경로 (콤마 구분) |

## 프로젝트 적용 계획

이 프로젝트에서는 **MWAA DAG에서 `add-steps` 명령을 사용**하여 EMR 스트리밍 job을 시작하고, 별도 health-check DAG에서 step 상태를 모니터링하는 방식을 사용할 예정입니다.

### MWAA DAG 예시

```python
from airflow.providers.amazon.aws.operators.emr import EmrAddStepsOperator
from airflow.providers.amazon.aws.sensors.emr import EmrStepSensor

# Step 추가
add_streaming_step = EmrAddStepsOperator(
    task_id='add_streaming_step',
    job_flow_id='{{ var.value.emr_cluster_id }}',
    aws_conn_id='aws_default',
    steps=[{
        'Name': 'Order Streaming to OpenSearch',
        'ActionOnFailure': 'CONTINUE',
        'HadoopJarStep': {
            'Jar': 'command-runner.jar',
            'Args': [
                'spark-submit',
                '--deploy-mode', 'cluster',
                '--master', 'yarn',
                's3://bucket/scripts/order_streaming.py',
                '--bootstrap-servers', '{{ var.value.msk_bootstrap_brokers }}',
                '--topic', 'orders'
            ]
        }
    }]
)

# Step 상태 모니터링
watch_step = EmrStepSensor(
    task_id='watch_streaming_step',
    job_flow_id='{{ var.value.emr_cluster_id }}',
    step_id='{{ task_instance.xcom_pull(task_ids="add_streaming_step")[0] }}',
    aws_conn_id='aws_default',
    poke_interval=60
)

add_streaming_step >> watch_step
```
