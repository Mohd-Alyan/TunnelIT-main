import pytest
from typer.testing import CliRunner
from tunnel_it.cli import app, get_http_url
from unittest.mock import patch, AsyncMock
import httpx
import sys

runner = CliRunner()

def test_cli_invalid_port():
    result = runner.invoke(app, ["expose", "70000"])
    assert result.exit_code != 0

def test_cli_invalid_arg():
    result = runner.invoke(app, ["expose", "abc"])
    assert result.exit_code != 0

def test_url_derivation():
    assert get_http_url("wss://example.com/ws") == "https://example.com"
    assert get_http_url("wss://example.com/ws/") == "https://example.com"
    assert get_http_url("ws://example.com/ws") == "http://example.com"
    assert get_http_url("https://example.com/ws") == "https://example.com"
    assert get_http_url("http://example.com") == "http://example.com"

@patch("tunnel_it.cli.httpx.AsyncClient.get", new_callable=AsyncMock)
def test_wakeup_healthy_immediately(mock_get):
    mock_response = httpx.Response(200, json={"status": "healthy"})
    mock_response.request = httpx.Request("GET", "http://example.com/health")
    mock_get.return_value = mock_response
    
    result = runner.invoke(app, ["wakeup"])
    assert result.exit_code == 0
    assert "Attempt 1" in result.stdout
    assert "Tunnel It relay is up." in result.stdout
    assert "healthy" in result.stdout

@patch("tunnel_it.cli.asyncio.sleep", new_callable=AsyncMock)
@patch("tunnel_it.cli.httpx.AsyncClient.get", new_callable=AsyncMock)
def test_wakeup_cold_start_behavior(mock_get, mock_sleep):
    mock_resp_503 = httpx.Response(503)
    mock_resp_503.request = httpx.Request("GET", "http://example.com/health")
    mock_resp_200 = httpx.Response(200, json={"status": "healthy"})
    mock_resp_200.request = httpx.Request("GET", "http://example.com/health")
    
    mock_responses = [
        httpx.RequestError("Connection failure"),
        httpx.TimeoutException("Timeout"),
        mock_resp_503,
        mock_resp_200
    ]
    
    # Keep track of calls to return different responses
    call_count = 0
    def mock_get_side_effect(*args, **kwargs):
        nonlocal call_count
        response = mock_responses[call_count]
        call_count += 1
        if isinstance(response, Exception):
            raise response
        return response
        
    mock_get.side_effect = mock_get_side_effect
    
    result = runner.invoke(app, ["wakeup"])
    assert result.exit_code == 0
    assert "Attempt 1" in result.stdout
    assert "Attempt 2" in result.stdout
    assert "Attempt 3" in result.stdout
    assert "Attempt 4" in result.stdout
    assert "Tunnel It relay is up." in result.stdout

@patch("tunnel_it.cli.time.time")
@patch("tunnel_it.cli.asyncio.sleep", new_callable=AsyncMock)
@patch("tunnel_it.cli.httpx.AsyncClient.get", new_callable=AsyncMock)
def test_wakeup_timeout(mock_get, mock_sleep, mock_time):
    mock_get.side_effect = httpx.RequestError("Failure")
    
    # time.time() is called once before the loop and once inside each iteration
    # Start time = 0, elapsed = 0, 100
    mock_time.side_effect = [0, 0, 100]
    
    result = runner.invoke(app, ["wakeup"])
    assert result.exit_code == 1
    assert "Unable to wake relay within 90 seconds." in result.stdout

