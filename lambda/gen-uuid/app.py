import uuid


def generate_uuid() -> str:
    return str(uuid.uuid4())


def handler(event, context):
    return generate_uuid()
