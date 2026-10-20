from aws_cdk import (
    Stack,
    Duration,
    RemovalPolicy,
    CfnOutput,
    aws_dynamodb as ddb,
    aws_lambda as _lambda,
)
from constructs import Construct
import os

class SafeGuardStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # 1. Free-Tier DynamoDB Table for Audit Telemetry (On-Demand / Pay Per Request)
        audit_table = ddb.Table(
            self, "SafeGuardTelemetry",
            partition_key=ddb.Attribute(name="scan_id", type=ddb.AttributeType.STRING),
            billing_mode=ddb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY
        )

        base_dir = os.path.dirname(__file__)
        backend_dir = os.path.join(base_dir, "../backend")
        if not os.path.exists(backend_dir):
            backend_dir = os.path.join(base_dir, "../backend_lambda")

        # 2. Dockerized Lambda Function (2048 MB RAM for fast CPU inference)
        rppg_lambda = _lambda.DockerImageFunction(
            self, "SafeGuardRppgFn",
            code=_lambda.DockerImageCode.from_image_asset(backend_dir),
            memory_size=2048,
            timeout=Duration.seconds(30),
            architecture=_lambda.Architecture.X86_64,
            environment={
                "DDB_TABLE_NAME": audit_table.table_name
            }
        )

        audit_table.grant_write_data(rppg_lambda)

        # 3. Built-in HTTPS Function URL (100% Free, no API Gateway cost)
        fn_url = rppg_lambda.add_function_url(
            auth_type=_lambda.FunctionUrlAuthType.NONE,
            cors=_lambda.FunctionUrlCorsOptions(
                allowed_origins=["*"],
                allowed_methods=[_lambda.HttpMethod.ALL],
                allowed_headers=["*"]
            )
        )

        CfnOutput(self, "AnalyzeEndpointUrl", value=f"{fn_url.url}analyze")
        CfnOutput(self, "FunctionUrl", value=fn_url.url)

PulseGuardStack = SafeGuardStack