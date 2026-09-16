from typing import Dict, Optional, Any
from pydantic import BaseModel, Field

class RegisterMessage(BaseModel):
    type: str
    port: int

class RegisteredMessage(BaseModel):
    type: str = "registered"
    tunnel_id: str
    public_url: str

class RequestMessage(BaseModel):
    type: str = "request"
    request_id: str
    method: str
    path: str
    query: str
    headers: Dict[str, str]
    body_encoding: str = "base64"
    body: str = ""

class ResponseMessage(BaseModel):
    type: str
    request_id: str
    status: int
    headers: Dict[str, str]
    body_encoding: str = "base64"
    body: str = ""
