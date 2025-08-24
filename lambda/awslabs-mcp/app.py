import uuid
from awslabs.mcp_lambda_handler import MCPLambdaHandler

mcp_server = MCPLambdaHandler(
    name="bedrock-agentcore-mcp-tools",
    version="1.0.0",
)


@mcp_server.tool()
def generate_uuid() -> str:
    """Generate a random UUID for unique identifiers"""
    return str(uuid.uuid4())


def handler(event, context):
    """Lambda handler for MCP requests"""
    return mcp_server.handle_request(event, context)
