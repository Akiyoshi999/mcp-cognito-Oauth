import uuid
from awslabs.mcp_lambda_handler import MCPLambdaHandler

mcp_server = MCPLambdaHandler(
    name="sample-uuid-tools",
    version="1.0.0",)


@mcp_server.tool()
def generate_uuid():
    return str(uuid.uuid4())


def handler(event, context):
    return mcp_server.handle_request(event, context)
