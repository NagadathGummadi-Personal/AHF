"""
CDK Stack for Real-time Twilio-ElevenLabs STT using AWS App Runner.
App Runner provides HTTPS/WSS automatically without needing a custom domain.
"""

from aws_cdk import (
    Stack,
    CfnOutput,
    aws_apprunner as apprunner,
    aws_ecr_assets as ecr_assets,
    aws_iam as iam,
)
from constructs import Construct
import os


class RealtimeSTTStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Get ElevenLabs API key from context
        elevenlabs_api_key = self.node.try_get_context("elevenlabs_api_key") or ""

        # ============================================
        # Docker Image Asset
        # ============================================
        
        realtime_server_path = os.path.join(os.path.dirname(__file__), "..", "..", "realtime_server")
        
        image_asset = ecr_assets.DockerImageAsset(
            self,
            "RealtimeImage",
            directory=realtime_server_path,
            platform=ecr_assets.Platform.LINUX_AMD64,
        )

        # ============================================
        # App Runner Access Role (to pull from ECR)
        # ============================================
        
        access_role = iam.Role(
            self,
            "AppRunnerAccessRole",
            assumed_by=iam.ServicePrincipal("build.apprunner.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSAppRunnerServicePolicyForECRAccess"
                )
            ],
        )
        
        # Grant pull access to the ECR repository
        image_asset.repository.grant_pull(access_role)

        # ============================================
        # App Runner Service
        # ============================================
        
        service = apprunner.CfnService(
            self,
            "RealtimeService",
            service_name="realtime-stt-service",
            source_configuration=apprunner.CfnService.SourceConfigurationProperty(
                auto_deployments_enabled=False,
                authentication_configuration=apprunner.CfnService.AuthenticationConfigurationProperty(
                    access_role_arn=access_role.role_arn,
                ),
                image_repository=apprunner.CfnService.ImageRepositoryProperty(
                    image_identifier=image_asset.image_uri,
                    image_repository_type="ECR",
                    image_configuration=apprunner.CfnService.ImageConfigurationProperty(
                        port="8000",
                        runtime_environment_variables=[
                            apprunner.CfnService.KeyValuePairProperty(
                                name="ELEVENLABS_API_KEY",
                                value=elevenlabs_api_key,
                            ),
                        ],
                    ),
                ),
            ),
            instance_configuration=apprunner.CfnService.InstanceConfigurationProperty(
                cpu="1024",  # 1 vCPU
                memory="2048",  # 2 GB
            ),
            health_check_configuration=apprunner.CfnService.HealthCheckConfigurationProperty(
                protocol="HTTP",
                path="/health",
                interval=10,
                timeout=5,
                healthy_threshold=1,
                unhealthy_threshold=5,
            ),
            # Enable HTTP/2 for better performance
            network_configuration=apprunner.CfnService.NetworkConfigurationProperty(
                ingress_configuration=apprunner.CfnService.IngressConfigurationProperty(
                    is_publicly_accessible=True,
                ),
            ),
        )
        
        # Ensure service waits for the role
        service.node.add_dependency(access_role)

        # ============================================
        # Outputs
        # ============================================
        
        CfnOutput(
            self,
            "ServiceURL",
            value=f"https://{service.attr_service_url}",
            description="Service URL (HTTPS)",
        )

        CfnOutput(
            self,
            "TwiMLWebhookURL",
            value=f"https://{service.attr_service_url}/twiml",
            description="Configure this URL in Twilio as your voice webhook",
        )

        CfnOutput(
            self,
            "WebSocketURL",
            value=f"wss://{service.attr_service_url}/media-stream",
            description="WebSocket URL for Twilio Media Stream (WSS)",
        )
