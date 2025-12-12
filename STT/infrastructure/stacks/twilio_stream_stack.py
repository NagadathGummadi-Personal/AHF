"""
CDK Stack for Twilio Real-Time Audio Streaming Infrastructure.
"""

from aws_cdk import (
    Stack,
    Duration,
    RemovalPolicy,
    CfnOutput,
    aws_lambda as lambda_,
    aws_apigatewayv2 as apigwv2,
    aws_apigatewayv2_integrations as integrations,
    aws_apigateway as apigw,
    aws_dynamodb as dynamodb,
    aws_s3 as s3,
    aws_iam as iam,
    aws_logs as logs,
)
from constructs import Construct


class TwilioStreamStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # ElevenLabs API Key (set via environment or CDK context)
        elevenlabs_api_key = self.node.try_get_context("elevenlabs_api_key") or ""

        # ============================================
        # DynamoDB Table for Connection Tracking
        # ============================================
        connections_table = dynamodb.Table(
            self,
            "ConnectionsTable",
            table_name="twilio-stream-connections",
            partition_key=dynamodb.Attribute(
                name="connectionId",
                type=dynamodb.AttributeType.STRING,
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,  # Change for production
        )

        # ============================================
        # DynamoDB Table for Transcripts
        # ============================================
        transcripts_table = dynamodb.Table(
            self,
            "TranscriptsTable",
            table_name="twilio-stream-transcripts",
            partition_key=dynamodb.Attribute(
                name="streamSid",
                type=dynamodb.AttributeType.STRING,
            ),
            sort_key=dynamodb.Attribute(
                name="timestamp",
                type=dynamodb.AttributeType.STRING,
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,  # Change for production
        )

        # ============================================
        # S3 Bucket for Audio Storage (Optional)
        # ============================================
        audio_bucket = s3.Bucket(
            self,
            "AudioBucket",
            bucket_name=None,  # Auto-generate unique name
            removal_policy=RemovalPolicy.DESTROY,  # Change for production
            auto_delete_objects=True,  # Change for production
        )

        # ============================================
        # WebSocket Handler Lambda (with dependencies)
        # ============================================
        websocket_handler = lambda_.Function(
            self,
            "WebSocketHandler",
            function_name="twilio-stream-websocket-handler",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="lambda_handler.lambda_handler",
            code=lambda_.Code.from_asset("../twilio_stream"),
            timeout=Duration.seconds(60),  # Increased for WebSocket transcription
            memory_size=512,  # Increased for async processing
            environment={
                "CONNECTIONS_TABLE": connections_table.table_name,
                "AUDIO_BUCKET": audio_bucket.bucket_name,
                "TRANSCRIPTS_TABLE": transcripts_table.table_name,
                "ELEVENLABS_API_KEY": elevenlabs_api_key,
            },
            log_retention=logs.RetentionDays.ONE_WEEK,
        )

        # Grant permissions
        connections_table.grant_read_write_data(websocket_handler)
        transcripts_table.grant_read_write_data(websocket_handler)
        audio_bucket.grant_read_write(websocket_handler)

        # ============================================
        # API Gateway WebSocket API
        # ============================================
        websocket_api = apigwv2.WebSocketApi(
            self,
            "TwilioStreamWebSocketApi",
            api_name="twilio-stream-websocket",
            description="WebSocket API for Twilio Media Stream",
            connect_route_options=apigwv2.WebSocketRouteOptions(
                integration=integrations.WebSocketLambdaIntegration(
                    "ConnectIntegration",
                    websocket_handler,
                ),
            ),
            disconnect_route_options=apigwv2.WebSocketRouteOptions(
                integration=integrations.WebSocketLambdaIntegration(
                    "DisconnectIntegration",
                    websocket_handler,
                ),
            ),
            default_route_options=apigwv2.WebSocketRouteOptions(
                integration=integrations.WebSocketLambdaIntegration(
                    "DefaultIntegration",
                    websocket_handler,
                ),
            ),
        )

        # WebSocket Stage
        websocket_stage = apigwv2.WebSocketStage(
            self,
            "WebSocketStage",
            web_socket_api=websocket_api,
            stage_name="prod",
            auto_deploy=True,
        )

        # Grant permission to manage WebSocket connections
        websocket_handler.add_to_role_policy(
            iam.PolicyStatement(
                actions=["execute-api:ManageConnections"],
                resources=[
                    f"arn:aws:execute-api:{self.region}:{self.account}:{websocket_api.api_id}/*"
                ],
            )
        )

        # ============================================
        # TwiML Handler Lambda
        # ============================================
        twiml_handler = lambda_.Function(
            self,
            "TwiMLHandler",
            function_name="twilio-stream-twiml-handler",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="twiml_handler.lambda_handler",
            code=lambda_.Code.from_asset("../twilio_stream"),
            timeout=Duration.seconds(10),
            memory_size=128,
            environment={
                "WEBSOCKET_URL": websocket_stage.url,
            },
            log_retention=logs.RetentionDays.ONE_WEEK,
        )

        # ============================================
        # REST API for TwiML Webhook
        # ============================================
        rest_api = apigw.RestApi(
            self,
            "TwiMLRestApi",
            rest_api_name="twilio-stream-twiml",
            description="REST API for Twilio TwiML Webhook",
            deploy_options=apigw.StageOptions(
                stage_name="prod",
            ),
        )

        # Add /twiml endpoint
        twiml_resource = rest_api.root.add_resource("twiml")
        twiml_resource.add_method(
            "POST",
            apigw.LambdaIntegration(twiml_handler),
        )
        # Also allow GET for testing
        twiml_resource.add_method(
            "GET",
            apigw.LambdaIntegration(twiml_handler),
        )

        # ============================================
        # Outputs
        # ============================================
        CfnOutput(
            self,
            "WebSocketURL",
            value=websocket_stage.url,
            description="WebSocket URL for Twilio Media Stream",
            export_name="TwilioStreamWebSocketURL",
        )

        CfnOutput(
            self,
            "TwiMLWebhookURL",
            value=f"{rest_api.url}twiml",
            description="TwiML Webhook URL - Configure this in Twilio",
            export_name="TwilioStreamTwiMLURL",
        )

        CfnOutput(
            self,
            "ConnectionsTableName",
            value=connections_table.table_name,
            description="DynamoDB table for connection tracking",
        )

        CfnOutput(
            self,
            "AudioBucketName",
            value=audio_bucket.bucket_name,
            description="S3 bucket for audio storage",
        )

        CfnOutput(
            self,
            "TranscriptsTableName",
            value=transcripts_table.table_name,
            description="DynamoDB table for transcripts",
        )

