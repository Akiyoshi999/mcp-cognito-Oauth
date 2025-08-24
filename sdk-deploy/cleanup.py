#!/usr/bin/env python3
"""
Cleanup script for Bedrock AgentCore Gateway resources

This script provides comprehensive cleanup functionality for all resources
created by the MCP Cognito OAuth implementation.
"""

import boto3
import json
import logging
import sys
import time
from typing import List, Dict, Any, Optional
from gateway_manager import BedrockAgentCoreGatewayManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ResourceCleanup:
    """Cleanup manager for all MCP-related AWS resources"""
    
    def __init__(self, region: str = "us-west-2", stack_name: str = "McpCognitoOauthStack", profile_name: str = None):
        self.region = region
        self.stack_name = stack_name
        self.profile_name = profile_name
        
        # Create session with profile if specified
        if profile_name:
            session = boto3.Session(profile_name=profile_name)
            self.cloudformation = session.client('cloudformation', region_name=region)
            self.cognito = session.client('cognito-idp', region_name=region)
            self.lambda_client = session.client('lambda', region_name=region)
            self.s3 = session.client('s3', region_name=region)
        else:
            self.cloudformation = boto3.client('cloudformation', region_name=region)
            self.cognito = boto3.client('cognito-idp', region_name=region)
            self.lambda_client = boto3.client('lambda', region_name=region)
            self.s3 = boto3.client('s3', region_name=region)
        
        self.gateway_manager = BedrockAgentCoreGatewayManager(region, profile_name)
    
    def cleanup_all(self, force: bool = False) -> Dict[str, Any]:
        """Clean up all resources in the correct order"""
        cleanup_results = {
            "gateways": [],
            "lambda_functions": [],
            "cognito_resources": [],
            "s3_buckets": [],
            "cloudformation_stack": None,
            "errors": []
        }
        
        try:
            # 1. Clean up Bedrock AgentCore Gateways
            logger.info("Cleaning up Bedrock AgentCore Gateways...")
            gateway_results = self.cleanup_gateways(force)
            cleanup_results["gateways"] = gateway_results
            
            # 2. Clean up S3 data (if any)
            logger.info("Cleaning up S3 data...")
            s3_results = self.cleanup_s3_data()
            cleanup_results["s3_buckets"] = s3_results
            
            # 3. Delete CloudFormation stack (this will handle Lambda and Cognito)
            if force or self._confirm_action("Delete CloudFormation stack?"):
                logger.info("Deleting CloudFormation stack...")
                stack_result = self.delete_cloudformation_stack()
                cleanup_results["cloudformation_stack"] = stack_result
            
            logger.info("Cleanup completed successfully")
            return cleanup_results
            
        except Exception as e:
            error_msg = f"Cleanup failed: {str(e)}"
            logger.error(error_msg)
            cleanup_results["errors"].append(error_msg)
            return cleanup_results
    
    def cleanup_gateways(self, force: bool = False) -> List[Dict[str, Any]]:
        """Clean up all Bedrock AgentCore Gateways"""
        results = []
        
        try:
            gateways = self.gateway_manager.list_gateways()
            
            for gateway in gateways:
                gateway_id = gateway['gatewayId']
                gateway_name = gateway.get('gatewayName', 'Unknown')
                
                # Check if this is our gateway
                if 'mcp' in gateway_name.lower() or 'bedrock' in gateway_name.lower():
                    if force or self._confirm_action(f"Delete gateway {gateway_name} ({gateway_id})?"):
                        try:
                            logger.info(f"Deleting gateway: {gateway_name}")
                            self.gateway_manager.delete_gateway(gateway_id)
                            results.append({
                                "gateway_id": gateway_id,
                                "gateway_name": gateway_name,
                                "status": "deleted"
                            })
                        except Exception as e:
                            error_msg = f"Failed to delete gateway {gateway_id}: {str(e)}"
                            logger.error(error_msg)
                            results.append({
                                "gateway_id": gateway_id,
                                "gateway_name": gateway_name,
                                "status": "error",
                                "error": error_msg
                            })
                
        except Exception as e:
            logger.error(f"Failed to list gateways: {str(e)}")
            results.append({
                "status": "error",
                "error": f"Failed to list gateways: {str(e)}"
            })
        
        return results
    
    def cleanup_s3_data(self) -> List[Dict[str, Any]]:
        """Clean up S3 data created by MCP tools"""
        results = []
        
        try:
            # List all buckets and find potential MCP data buckets
            buckets_response = self.s3.list_buckets()
            
            for bucket in buckets_response.get('Buckets', []):
                bucket_name = bucket['Name']
                
                # Check if bucket might contain MCP data
                if 'mcp' in bucket_name.lower() or self._bucket_has_mcp_data(bucket_name):
                    try:
                        # List objects in mcp-data/ prefix
                        objects_response = self.s3.list_objects_v2(
                            Bucket=bucket_name,
                            Prefix='mcp-data/'
                        )
                        
                        objects_to_delete = []
                        for obj in objects_response.get('Contents', []):
                            objects_to_delete.append({'Key': obj['Key']})
                        
                        if objects_to_delete:
                            logger.info(f"Deleting {len(objects_to_delete)} MCP objects from bucket {bucket_name}")
                            self.s3.delete_objects(
                                Bucket=bucket_name,
                                Delete={'Objects': objects_to_delete}
                            )
                            
                            results.append({
                                "bucket_name": bucket_name,
                                "objects_deleted": len(objects_to_delete),
                                "status": "cleaned"
                            })
                    
                    except Exception as e:
                        if "NoSuchBucket" not in str(e):
                            logger.error(f"Failed to clean bucket {bucket_name}: {str(e)}")
                            results.append({
                                "bucket_name": bucket_name,
                                "status": "error",
                                "error": str(e)
                            })
        
        except Exception as e:
            logger.error(f"Failed to list S3 buckets: {str(e)}")
            results.append({
                "status": "error",
                "error": f"Failed to list S3 buckets: {str(e)}"
            })
        
        return results
    
    def delete_cloudformation_stack(self) -> Dict[str, Any]:
        """Delete the CloudFormation stack"""
        try:
            # Check if stack exists
            try:
                self.cloudformation.describe_stacks(StackName=self.stack_name)
            except Exception as e:
                if "does not exist" in str(e):
                    return {
                        "stack_name": self.stack_name,
                        "status": "not_found",
                        "message": "Stack does not exist"
                    }
                raise
            
            # Delete the stack
            logger.info(f"Deleting CloudFormation stack: {self.stack_name}")
            self.cloudformation.delete_stack(StackName=self.stack_name)
            
            # Wait for deletion to complete
            logger.info("Waiting for stack deletion to complete...")
            waiter = self.cloudformation.get_waiter('stack_delete_complete')
            waiter.wait(
                StackName=self.stack_name,
                WaiterConfig={'Delay': 30, 'MaxAttempts': 60}
            )
            
            return {
                "stack_name": self.stack_name,
                "status": "deleted",
                "message": "Stack deleted successfully"
            }
            
        except Exception as e:
            error_msg = f"Failed to delete stack {self.stack_name}: {str(e)}"
            logger.error(error_msg)
            return {
                "stack_name": self.stack_name,
                "status": "error",
                "error": error_msg
            }
    
    def _bucket_has_mcp_data(self, bucket_name: str) -> bool:
        """Check if bucket contains MCP data"""
        try:
            response = self.s3.list_objects_v2(
                Bucket=bucket_name,
                Prefix='mcp-data/',
                MaxKeys=1
            )
            return response.get('KeyCount', 0) > 0
        except:
            return False
    
    def _confirm_action(self, message: str) -> bool:
        """Prompt user for confirmation"""
        response = input(f"{message} (y/N): ").strip().lower()
        return response in ['y', 'yes']
    
    def list_resources(self) -> Dict[str, Any]:
        """List all MCP-related resources"""
        resources = {
            "gateways": [],
            "lambda_functions": [],
            "cognito_resources": [],
            "s3_data": [],
            "cloudformation_stack": None
        }
        
        # List gateways
        try:
            gateways = self.gateway_manager.list_gateways()
            resources["gateways"] = [
                {
                    "id": gw['gatewayId'],
                    "name": gw.get('gatewayName', 'Unknown'),
                    "status": gw.get('gatewayStatus', 'Unknown')
                }
                for gw in gateways
                if 'mcp' in gw.get('gatewayName', '').lower()
            ]
        except Exception as e:
            logger.error(f"Failed to list gateways: {str(e)}")
        
        # Check CloudFormation stack
        try:
            stack_response = self.cloudformation.describe_stacks(StackName=self.stack_name)
            if stack_response['Stacks']:
                stack = stack_response['Stacks'][0]
                resources["cloudformation_stack"] = {
                    "name": stack['StackName'],
                    "status": stack['StackStatus'],
                    "creation_time": stack['CreationTime'].isoformat() if stack.get('CreationTime') else None
                }
        except Exception as e:
            if "does not exist" not in str(e):
                logger.error(f"Failed to describe stack: {str(e)}")
        
        return resources

def main():
    """Main function for command-line usage"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Cleanup MCP Cognito OAuth resources')
    parser.add_argument('--action', choices=['list', 'cleanup-gateways', 'cleanup-all'], 
                       required=True, help='Action to perform')
    parser.add_argument('--stack-name', default='McpCognitoOauthStack', 
                       help='CloudFormation stack name')
    parser.add_argument('--region', default='us-west-2', help='AWS region')
    parser.add_argument('--force', action='store_true', 
                       help='Skip confirmation prompts')
    parser.add_argument('--profile', help='AWS profile to use')
    
    args = parser.parse_args()
    
    cleanup = ResourceCleanup(region=args.region, stack_name=args.stack_name, profile_name=args.profile)
    
    try:
        if args.action == 'list':
            resources = cleanup.list_resources()
            print(json.dumps(resources, indent=2, default=str))
        
        elif args.action == 'cleanup-gateways':
            results = cleanup.cleanup_gateways(force=args.force)
            print(json.dumps(results, indent=2))
        
        elif args.action == 'cleanup-all':
            results = cleanup.cleanup_all(force=args.force)
            print(json.dumps(results, indent=2, default=str))
    
    except Exception as e:
        logger.error(f"Operation failed: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main()