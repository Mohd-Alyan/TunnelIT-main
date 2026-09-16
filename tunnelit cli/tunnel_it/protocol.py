from typing import Dict
from pydantic import BaseModel

class RegisterMessage(BaseModel):
    type: str = "register"
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
    type: str = "response"
    request_id: str
    status: int
    headers: Dict[str, str]
    body_encoding: str = "base64"
    body: str = ""
