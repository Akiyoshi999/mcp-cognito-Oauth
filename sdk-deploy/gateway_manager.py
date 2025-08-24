#!/usr/bin/env python3
"""
Amazon Bedrock AgentCore Gateway Manager

This script manages the creation, configuration, and deletion of Bedrock AgentCore Gateway
with Lambda function targets and Cognito OAuth authentication.
"""

import boto3
import json
import time
import logging
import sys
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class GatewayConfig:
    """Configuration for Bedrock AgentCore Gateway"""
    gateway_name: str
    description: str
    cognito_user_pool_id: str
    cognito_client_id: str
    cognito_domain: str
    lambda_function_arn: str
    region: str = "us-west-2"

class BedrockAgentCoreGatewayManager:
    """Manager for Bedrock AgentCore Gateway operations"""
    
    def __init__(self, region: str = "us-west-2", profile_name: str = None):
        self.region = region
        self.profile_name = profile_name
        
        # Create session with profile if specified
        if profile_name:
            session = boto3.Session(profile_name=profile_name)
            self.bedrock_agentcore = session.client('bedrock-agentcore-control', region_name=region)
            self.cognito = session.client('cognito-idp', region_name=region)
            self.lambda_client = session.client('lambda', region_name=region)
        else:
            self.bedrock_agentcore = boto3.client('bedrock-agentcore-control', region_name=region)
            self.cognito = boto3.client('cognito-idp', region_name=region)
            self.lambda_client = boto3.client('lambda', region_name=region)
        
    def create_gateway(self, config: GatewayConfig) -> Dict[str, Any]:
        """Create a new Bedrock AgentCore Gateway"""
        try:
            logger.info(f"Creating gateway: {config.gateway_name}")
            
            # Create the gateway
            gateway_response = self.bedrock_agentcore.create_gateway(
                name=config.gateway_name,
                description=config.description,
                protocolType='MCP',
                authorizerType='CUSTOM_JWT',
                authorizerConfiguration={
                    'customJwt': {
                        'authorizerName': f"{config.gateway_name}-authorizer",
                        'tokenSource': 'authorization',
                        'issuer': f"https://cognito-idp.{config.region}.amazonaws.com/{config.cognito_user_pool_id}",
                        'audience': [config.cognito_client_id]
                    }
                },
                roleArn=f"arn:aws:iam::{self._get_account_id()}:role/BedrockAgentCoreGatewayRole"
            )
            
            gateway_id = gateway_response['gatewayId']
            logger.info(f"Gateway created with ID: {gateway_id}")
            
            # Wait for gateway to be active
            self._wait_for_gateway_active(gateway_id)
            
            return {
                'gateway_id': gateway_id,
                'gateway_arn': gateway_response['gatewayArn'],
                'gateway_url': gateway_response.get('gatewayUrl'),
                'status': 'created'
            }
            
        except Exception as e:
            logger.error(f"Failed to create gateway: {str(e)}")
            raise
    
    def add_lambda_target(self, gateway_id: str, config: GatewayConfig) -> Dict[str, Any]:
        """Add Lambda function as a target to the gateway"""
        try:
            logger.info(f"Adding Lambda target to gateway: {gateway_id}")
            
            # Get Lambda function details
            lambda_response = self.lambda_client.get_function(
                FunctionName=config.lambda_function_arn
            )
            
            # Create target
            target_response = self.bedrock_agentcore.create_gateway_target(
                gatewayId=gateway_id,
                name=f"{config.gateway_name}-lambda-target",
                protocolType='MCP',
                protocolConfiguration={
                    'mcp': {
                        'lambdaConfiguration': {
                            'functionArn': config.lambda_function_arn
                        }
                    }
                }
            )
            
            target_id = target_response['targetId']
            logger.info(f"Lambda target created with ID: {target_id}")
            
            # Wait for target to be active
            self._wait_for_target_active(gateway_id, target_id)
            
            return {
                'target_id': target_id,
                'target_arn': target_response['targetArn'],
                'status': 'created'
            }
            
        except Exception as e:
            logger.error(f"Failed to add Lambda target: {str(e)}")
            raise
    
    def get_gateway_info(self, gateway_id: str) -> Dict[str, Any]:
        """Get gateway information"""
        try:
            response = self.bedrock_agentcore.get_gateway(gatewayId=gateway_id)
            return response
        except Exception as e:
            logger.error(f"Failed to get gateway info: {str(e)}")
            raise
    
    def list_gateways(self) -> List[Dict[str, Any]]:
        """List all gateways"""
        try:
            response = self.bedrock_agentcore.list_gateways()
            return response.get('gatewaySummaries', [])
        except Exception as e:
            logger.error(f"Failed to list gateways: {str(e)}")
            raise
    
    def delete_gateway(self, gateway_id: str) -> Dict[str, Any]:
        """Delete a gateway and all its targets"""
        try:
            logger.info(f"Deleting gateway: {gateway_id}")
            
            # First, list and delete all targets
            targets_response = self.bedrock_agentcore.list_gateway_targets(gatewayId=gateway_id)
            for target in targets_response.get('targetSummaries', []):
                target_id = target['targetId']
                logger.info(f"Deleting target: {target_id}")
                self.bedrock_agentcore.delete_gateway_target(
                    gatewayId=gateway_id,
                    targetId=target_id
                )
                self._wait_for_target_deleted(gateway_id, target_id)
            
            # Then delete the gateway
            self.bedrock_agentcore.delete_gateway(gatewayId=gateway_id)
            self._wait_for_gateway_deleted(gateway_id)
            
            logger.info(f"Gateway {gateway_id} deleted successfully")
            return {'status': 'deleted'}
            
        except Exception as e:
            logger.error(f"Failed to delete gateway: {str(e)}")
            raise
    
    def _wait_for_gateway_active(self, gateway_id: str, max_wait: int = 300):
        """Wait for gateway to become active"""
        start_time = time.time()
        while time.time() - start_time < max_wait:
            try:
                response = self.bedrock_agentcore.get_gateway(gatewayId=gateway_id)
                status = response.get('gatewayStatus')
                if status == 'ACTIVE':
                    logger.info(f"Gateway {gateway_id} is now active")
                    return
                elif status == 'FAILED':
                    raise Exception(f"Gateway {gateway_id} failed to activate")
                
                logger.info(f"Gateway {gateway_id} status: {status}, waiting...")
                time.sleep(10)
                
            except Exception as e:
                if "ResourceNotFound" in str(e):
                    time.sleep(5)
                    continue
                raise
        
        raise TimeoutError(f"Gateway {gateway_id} did not become active within {max_wait} seconds")
    
    def _wait_for_target_active(self, gateway_id: str, target_id: str, max_wait: int = 300):
        """Wait for target to become active"""
        start_time = time.time()
        while time.time() - start_time < max_wait:
            try:
                response = self.bedrock_agentcore.get_gateway_target(
                    gatewayId=gateway_id,
                    targetId=target_id
                )
                status = response.get('targetStatus')
                if status == 'ACTIVE':
                    logger.info(f"Target {target_id} is now active")
                    return
                elif status == 'FAILED':
                    raise Exception(f"Target {target_id} failed to activate")
                
                logger.info(f"Target {target_id} status: {status}, waiting...")
                time.sleep(10)
                
            except Exception as e:
                if "ResourceNotFound" in str(e):
                    time.sleep(5)
                    continue
                raise
        
        raise TimeoutError(f"Target {target_id} did not become active within {max_wait} seconds")
    
    def _wait_for_gateway_deleted(self, gateway_id: str, max_wait: int = 300):
        """Wait for gateway to be deleted"""
        start_time = time.time()
        while time.time() - start_time < max_wait:
            try:
                self.bedrock_agentcore.get_gateway(gatewayId=gateway_id)
                logger.info(f"Gateway {gateway_id} still exists, waiting...")
                time.sleep(10)
            except Exception as e:
                if "ResourceNotFound" in str(e):
                    logger.info(f"Gateway {gateway_id} successfully deleted")
                    return
                raise
        
        raise TimeoutError(f"Gateway {gateway_id} was not deleted within {max_wait} seconds")
    
    def _wait_for_target_deleted(self, gateway_id: str, target_id: str, max_wait: int = 300):
        """Wait for target to be deleted"""
        start_time = time.time()
        while time.time() - start_time < max_wait:
            try:
                self.bedrock_agentcore.get_gateway_target(gatewayId=gateway_id, targetId=target_id)
                logger.info(f"Target {target_id} still exists, waiting...")
                time.sleep(10)
            except Exception as e:
                if "ResourceNotFound" in str(e):
                    logger.info(f"Target {target_id} successfully deleted")
                    return
                raise
        
        raise TimeoutError(f"Target {target_id} was not deleted within {max_wait} seconds")
    
    def _get_account_id(self) -> str:
        """Get the current AWS account ID"""
        try:
            if self.profile_name:
                session = boto3.Session(profile_name=self.profile_name)
                sts_client = session.client('sts', region_name=self.region)
            else:
                sts_client = boto3.client('sts', region_name=self.region)
            
            return sts_client.get_caller_identity()['Account']
        except Exception as e:
            logger.error(f"Failed to get account ID: {str(e)}")
            raise

def main():
    """Main function for command-line usage"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Manage Bedrock AgentCore Gateway')
    parser.add_argument('--action', choices=['create', 'delete', 'list', 'info'], 
                       required=True, help='Action to perform')
    parser.add_argument('--gateway-id', help='Gateway ID (required for delete/info)')
    parser.add_argument('--config-file', help='JSON config file for creation')
    parser.add_argument('--region', default='us-west-2', help='AWS region')
    parser.add_argument('--profile', help='AWS profile to use')
    
    args = parser.parse_args()
    
    manager = BedrockAgentCoreGatewayManager(region=args.region, profile_name=args.profile)
    
    try:
        if args.action == 'create':
            if not args.config_file:
                logger.error("Config file required for creation")
                sys.exit(1)
            
            with open(args.config_file, 'r') as f:
                config_data = json.load(f)
            
            config = GatewayConfig(**config_data)
            result = manager.create_gateway(config)
            
            # Add Lambda target
            target_result = manager.add_lambda_target(result['gateway_id'], config)
            
            print(json.dumps({
                'gateway': result,
                'target': target_result
            }, indent=2))
        
        elif args.action == 'delete':
            if not args.gateway_id:
                logger.error("Gateway ID required for deletion")
                sys.exit(1)
            
            result = manager.delete_gateway(args.gateway_id)
            print(json.dumps(result, indent=2))
        
        elif args.action == 'list':
            gateways = manager.list_gateways()
            print(json.dumps(gateways, indent=2))
        
        elif args.action == 'info':
            if not args.gateway_id:
                logger.error("Gateway ID required for info")
                sys.exit(1)
            
            info = manager.get_gateway_info(args.gateway_id)
            print(json.dumps(info, indent=2))
    
    except Exception as e:
        logger.error(f"Operation failed: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main()