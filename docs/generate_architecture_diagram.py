"""
Generate architecture diagram for E-commerce Data Pipeline
Requires: pip install diagrams
"""
from diagrams import Diagram, Cluster, Edge
from diagrams.aws.analytics import EMR, ManagedStreamingForKafka, Glue, Opensearch
from diagrams.aws.storage import S3
from diagrams.aws.integration import MQ
from diagrams.aws.compute import ECS
from diagrams.aws.analytics import ManagedWorkflowsApacheiAirflow
from diagrams.custom import Custom
from diagrams.programming.language import Python

# Diagram attributes
graph_attr = {
    "fontsize": "16",
    "bgcolor": "white",
    "pad": "0.5",
    "splines": "ortho",
    "nodesep": "0.8",
    "ranksep": "1.2"
}

with Diagram(
    "E-commerce Data Pipeline Architecture",
    filename="docs/architecture_diagram",
    show=False,
    direction="LR",
    graph_attr=graph_attr,
    outformat="png"
):

    # AWS Cluster
    with Cluster("AWS Platform", graph_attr={"bgcolor": "lightblue"}):

        # Data Generation
        with Cluster("Data Generation"):
            producers = Python("Stream Producers\n(Order/Customer/Inventory)")
            mwaa_batch = ManagedWorkflowsApacheiAirflow("MWAA\n(Batch Generators)")
            postgres = Custom("PostgreSQL\n(Customer Registry)", "./postgresql_icon.png") if False else Python("PostgreSQL")

        # Kafka Streaming
        msk = ManagedStreamingForKafka("Amazon MSK\n(Kafka)")
        schema_registry = Glue("Glue Schema Registry\n(Avro)")

        # Stream Processing Paths
        with Cluster("Real-time Processing"):
            emr = EMR("EMR\n(Spark Structured Streaming)")
            opensearch = Opensearch("OpenSearch\n(Real-time Dashboard)")
            mwaa_health = ManagedWorkflowsApacheiAirflow("MWAA\n(EMR Health Check)")

        # Stream Landing
        msk_connect = MQ("MSK Connect\n(S3 Sink, Avro)")

        # Storage
        s3_landing = S3("S3 / UC External Volume\n(Landing Zone)")

    # Databricks Cluster
    with Cluster("Databricks Platform", graph_attr={"bgcolor": "lightgreen"}):

        with Cluster("Lakehouse (Delta Lake)"):
            autoloader = Python("Auto Loader\n(File-arrival trigger)")

            with Cluster("Medallion Architecture"):
                bronze = Python("Bronze\n(Raw, append-only)")
                silver = Python("Silver\n(Validated, deduplicated)")
                gold = Python("Gold\n(Business metrics)")

        unity_catalog = Python("Unity Catalog\n(Governance)")
        lakeflow = Python("Lakeflow Jobs\n(Orchestration)")
        dashboard = Python("AI/BI Dashboard\n(SQL Warehouse)")

    # Data Flow Connections

    # Stream path: Producers -> Kafka -> MSK Connect -> S3
    producers >> Edge(label="Avro events") >> msk
    msk >> schema_registry
    msk >> Edge(label="consumer group 1") >> msk_connect
    msk_connect >> Edge(label="Avro files") >> s3_landing

    # Stream path: Kafka -> EMR -> OpenSearch (real-time metrics)
    msk >> Edge(label="consumer group 2") >> emr
    emr >> Edge(label="metrics") >> opensearch

    # Batch path: MWAA -> S3
    mwaa_batch >> Edge(label="CSV/JSONL") >> s3_landing

    # Customer hybrid path: Producers -> Kafka + PostgreSQL
    producers >> Edge(label="registration") >> postgres
    postgres >> Edge(label="batch updates") >> mwaa_batch

    # MWAA health check
    mwaa_health >> Edge(label="start/monitor", style="dashed") >> emr

    # Databricks ingestion: S3 -> Bronze -> Silver -> Gold
    s3_landing >> Edge(label="file arrival") >> autoloader
    autoloader >> bronze
    bronze >> silver
    silver >> gold
    gold >> dashboard

    # Governance
    unity_catalog >> Edge(style="dotted") >> bronze
    unity_catalog >> Edge(style="dotted") >> silver
    unity_catalog >> Edge(style="dotted") >> gold

    # Orchestration
    lakeflow >> Edge(label="orchestrate", style="dashed") >> autoloader

print("Architecture diagram generated: docs/architecture_diagram.png")
