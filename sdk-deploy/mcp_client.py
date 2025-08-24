#!/usr/bin/env python3
"""
MCP Client for Bedrock AgentCore Gateway

This script provides a client interface to interact with the MCP server
through the Bedrock AgentCore Gateway using OAuth authentication.
"""

import asyncio
import json
import logging
import base64
import requests
from typing import Dict, Any, List, Optional
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class CognitoOAuthClient:
    """OAuth client for Cognito authentication"""
    
    def __init__(self, client_id: str, client_secret: str, cognito_domain: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.cognito_domain = cognito_domain
        self.access_token: Optional[str] = None
    
    def get_access_token(self) -> str:
        """Get OAuth access token using client credentials flow"""
        credentials = base64.b64encode(f"{self.client_id}:{self.client_secret}".encode()).decode()
        
        response = requests.post(
            f"https://{self.cognito_domain}/oauth2/token",
            headers={
                "Authorization": f"Basic {credentials}",
                "Content-Type": "application/x-www-form-urlencoded"
            },
            data={"grant_type": "client_credentials"}
        )
        
        if response.status_code == 200:
            token_data = response.json()
            self.access_token = token_data["access_token"]
            logger.info("Successfully obtained access token")
            return self.access_token
        else:
            logger.error(f"Failed to get access token: {response.status_code} - {response.text}")
            raise Exception(f"OAuth authentication failed: {response.status_code}")

class BedrockAgentCoreMCPClient:
    """MCP Client for Bedrock AgentCore Gateway"""
    
    def __init__(self, gateway_url: str, oauth_client: CognitoOAuthClient):
        self.gateway_url = gateway_url
        self.oauth_client = oauth_client
        self.mcp_url = f"{gateway_url}/mcp"
    
    async def list_tools(self) -> List[Dict[str, Any]]:
        """List all available MCP tools"""
        access_token = self.oauth_client.get_access_token()
        headers = {"Authorization": f"Bearer {access_token}"}
        
        async with streamablehttp_client(self.mcp_url, headers=headers) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tool_result = await session.list_tools()
                return tool_result.tools
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call a specific MCP tool"""
        access_token = self.oauth_client.get_access_token()
        headers = {"Authorization": f"Bearer {access_token}"}
        
        async with streamablehttp_client(self.mcp_url, headers=headers) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, arguments=arguments)
                
                # Extract content from the result
                content_list = []
                for content in result.content:
                    if hasattr(content, 'text'):
                        try:
                            # Try to parse as JSON first
                            content_data = json.loads(content.text)
                            content_list.append(content_data)
                        except json.JSONDecodeError:
                            # If not JSON, return as text
                            content_list.append(content.text)
                    else:
                        content_list.append(str(content))
                
                return {
                    "tool_name": tool_name,
                    "arguments": arguments,
                    "content": content_list,
                    "is_error": result.isError if hasattr(result, 'isError') else False
                }
    
    async def search_tools(self, query: str) -> List[Dict[str, Any]]:
        """Search for relevant tools using semantic search"""
        try:
            result = await self.call_tool(
                "x_amz_bedrock_agentcore_search",
                {"query": query}
            )
            
            # Parse search results
            search_results = []
            for content in result.get("content", []):
                if isinstance(content, list):
                    search_results.extend(content)
                elif isinstance(content, dict):
                    search_results.append(content)
            
            return search_results
        except Exception as e:
            logger.warning(f"Semantic search not available: {str(e)}")
            return []
    
    async def get_server_info(self) -> Dict[str, Any]:
        """Get information about the MCP server"""
        access_token = self.oauth_client.get_access_token()
        headers = {"Authorization": f"Bearer {access_token}"}
        
        async with streamablehttp_client(self.mcp_url, headers=headers) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                return {
                    "server_name": session.server_info.name if session.server_info else "Unknown",
                    "server_version": session.server_info.version if session.server_info else "Unknown",
                    "protocol_version": session.protocol_version if hasattr(session, 'protocol_version') else "Unknown"
                }

async def demo_mcp_client(gateway_url: str, client_id: str, client_secret: str, cognito_domain: str):
    """Demonstration of MCP client functionality"""
    logger.info("Starting MCP client demonstration")
    
    # Initialize OAuth client
    oauth_client = CognitoOAuthClient(client_id, client_secret, cognito_domain)
    
    # Initialize MCP client
    mcp_client = BedrockAgentCoreMCPClient(gateway_url, oauth_client)
    
    try:
        # Get server info
        logger.info("Getting server information...")
        server_info = await mcp_client.get_server_info()
        print(f"Server Info: {json.dumps(server_info, indent=2)}")
        
        # List available tools
        logger.info("Listing available tools...")
        tools = await mcp_client.list_tools()
        print(f"Available Tools: {json.dumps([tool.name for tool in tools], indent=2)}")
        
        # Demonstrate tool calls
        logger.info("Demonstrating tool calls...")
        
        # Generate UUID
        uuid_result = await mcp_client.call_tool("generate_uuid", {})
        print(f"Generated UUID: {json.dumps(uuid_result, indent=2)}")
        
        # Get system info
        system_info_result = await mcp_client.call_tool("get_system_info", {})
        print(f"System Info: {json.dumps(system_info_result, indent=2)}")
        
        # Store and retrieve data
        store_result = await mcp_client.call_tool("store_data", {
            "key": "test-key",
            "data": "Hello from MCP client!"
        })
        print(f"Store Result: {json.dumps(store_result, indent=2)}")
        
        retrieve_result = await mcp_client.call_tool("retrieve_data", {
            "key": "test-key"
        })
        print(f"Retrieve Result: {json.dumps(retrieve_result, indent=2)}")
        
        # Process text with Bedrock
        bedrock_result = await mcp_client.call_tool("process_text_with_bedrock", {
            "text": "Analyze this sample text for sentiment and key topics"
        })
        print(f"Bedrock Processing: {json.dumps(bedrock_result, indent=2)}")
        
        # Search for tools
        logger.info("Searching for tools...")
        search_results = await mcp_client.search_tools("data storage")
        if search_results:
            print(f"Search Results: {json.dumps(search_results, indent=2)}")
        
    except Exception as e:
        logger.error(f"Demo failed: {str(e)}")
        raise

def main():
    """Main function for command-line usage"""
    import argparse
    
    parser = argparse.ArgumentParser(description='MCP Client for Bedrock AgentCore Gateway')
    parser.add_argument('--gateway-url', required=True, help='Gateway URL')
    parser.add_argument('--client-id', required=True, help='Cognito Client ID')
    parser.add_argument('--client-secret', required=True, help='Cognito Client Secret')
    parser.add_argument('--cognito-domain', required=True, help='Cognito Domain')
    parser.add_argument('--demo', action='store_true', help='Run demonstration')
    parser.add_argument('--profile', help='AWS profile to use')
    
    args = parser.parse_args()
    
    if args.demo:
        asyncio.run(demo_mcp_client(
            args.gateway_url,
            args.client_id,
            args.client_secret,
            args.cognito_domain
        ))
    else:
        print("Use --demo to run the demonstration")

if __name__ == '__main__':
    main()