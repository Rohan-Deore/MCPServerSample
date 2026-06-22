import os
from pathlib import Path
from mcp.server.fastmcp import FastMCP
from langchain_ollama import OllamaLLM

# 1. Initialize the FastMCP server
mcp = FastMCP("MarkdownNotesServer")

# 2. Define the base directory where your markdown notes live
NOTES_DIR = "D:/Data/OneDrive/Documents/Obsidian Vaults/KnowledgeBase"

# Ensure the base directory exists
os.makedirs(NOTES_DIR, exist_ok=True)

@mcp.tool()
def answer_from_notes(question: str) -> str:
    """Answers a question by referencing your local markdown notes, including all subdirectories."""
    
    notes_content = ""
    base_path = Path(NOTES_DIR)
    
    # 3. Read all markdown files recursively
    # .rglob("*.md") searches the base directory AND all subfolders
    for filepath in base_path.rglob("*.md"):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                # Use the relative path so the LLM knows which folder the note came from
                relative_path = filepath.relative_to(base_path)
                notes_content += f"\n--- {relative_path} ---\n"
                notes_content += f.read()
        except Exception as e:
            # Silently skip files that can't be read (e.g., permission issues)
            pass
            
    if not notes_content.strip():
        return "No markdown notes found in the directory or subdirectories."

    # 4. Construct the prompt for Ollama
    prompt = (
        f"You are a helpful assistant. Use the following markdown notes to "
        f"answer the user's question. If the answer isn't in the notes, say so.\n\n"
        f"NOTES:\n{notes_content}\n\n"
        f"QUESTION: {question}"
    )
    
    # 5. Call Ollama locally
    # Ensure the model name matches what you pulled in the terminal
    llm = OllamaLLM(model="llama3.2") 
    #llm = OllamaLLM(model="gemma3:4b") 
    
    try:
        response = llm.invoke(prompt)
        return response
    except Exception as e:
        return f"Error communicating with Ollama: {str(e)}"

if __name__ == "__main__":
    # Start the MCP server using standard input/output (stdio)
    mcp.run()