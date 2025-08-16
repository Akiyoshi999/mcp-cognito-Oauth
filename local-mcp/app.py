import uuid
from fastmcp import FastMCP

mcp = FastMCP(name="sample-uuid-tools", version="1.0.0")


@mcp.tool()
def generate_uuid():
    return str(uuid.uuid4())


mcp.run(transport="streamable-http", host="0.0.0.0", port=3333,)
