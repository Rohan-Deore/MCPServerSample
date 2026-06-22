import pytest
from unittest.mock import MagicMock
from mcp.client.session import ClientSession
from mcp.shared.memory import create_connected_server_and_client_session

# Import your actual server script
# (Ensures your file is named 'server.py')
import MCPServer

# ---------------------------------------------------------
# Fixtures Setup
# ---------------------------------------------------------

@pytest.fixture
def anyio_backend():
    """Tells the testing framework to use the standard asyncio event loop."""
    return "asyncio"

@pytest.fixture
def mock_notes_dir(tmp_path, monkeypatch):
    """
    Creates a temporary directory with a dummy markdown file 
    and forces the server to use it instead of your real notes.
    """
    # Create a temporary directory structure mimicking your notes
    notes_dir = tmp_path / "my_notes"
    notes_dir.mkdir()
    
    sub_dir = notes_dir / "work"
    sub_dir.mkdir()
    
    test_note = sub_dir / "project_x.md"
    test_note.write_text("The secret project code is 'Apollo'.")
    
    # Safely override the NOTES_DIR constant in your server script
    monkeypatch.setattr(MCPServer, "NOTES_DIR", str(notes_dir))
    return str(notes_dir)

@pytest.fixture
async def mcp_client():
    """Spins up an in-memory MCP client/server session for lightning-fast testing."""
    async with create_connected_server_and_client_session(MCPServer.mcp) as session:
        yield session

# ---------------------------------------------------------
# Unit Tests
# ---------------------------------------------------------

@pytest.mark.anyio
async def test_answer_from_notes(mock_notes_dir, mcp_client, mocker):
    """Tests the tool execution end-to-end with mocked files and LLM."""
    
    # 1. Mock the OllamaLLM class to prevent actual network/local calls
    mock_llm_class = mocker.patch("MCPServer.OllamaLLM")
    mock_llm_instance = mock_llm_class.return_value
    mock_llm_instance.invoke.return_value = "The secret project code is Apollo."
    
    # 2. Call the tool exactly as a real MCP Client would
    result = await mcp_client.call_tool(
        "answer_from_notes", 
        arguments={"question": "What is the code for the project?"}
    )
    
    # 3. Assert the MCP Server responded correctly
    assert len(result.content) > 0
    assert result.content[0].text == "The secret project code is Apollo."
    
    # 4. Assert the tool read the mocked files and formatted the prompt correctly
    mock_llm_instance.invoke.assert_called_once()
    called_prompt = mock_llm_instance.invoke.call_args[0][0]
    
    #assert "--- work/project_x.md ---" in called_prompt
    assert "The secret project code is 'Apollo'." in called_prompt
    assert "QUESTION: What is the code for the project?" in called_prompt

@pytest.mark.anyio
async def test_empty_notes_directory(tmp_path, monkeypatch, mcp_client):
    """Tests how the tool handles a directory with no markdown files."""
    
    # Point the server to a completely empty temporary directory
    empty_dir = tmp_path / "empty_notes"
    empty_dir.mkdir()
    monkeypatch.setattr(MCPServer, "NOTES_DIR", str(empty_dir))
    
    result = await mcp_client.call_tool(
        "answer_from_notes", 
        arguments={"question": "Are there any notes?"}
    )
    
    # Assert the graceful fallback triggered successfully
    assert result.content[0].text == "No markdown notes found in the directory or subdirectories."