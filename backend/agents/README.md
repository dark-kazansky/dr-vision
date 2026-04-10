# Dr.Vision Agents

This directory contains the agent system for Dr.Vision. Agents are responsible for communicating with AI models (LLMs, VLMs, OCR models) through standardized interfaces.

## Architecture

```
Base Classes (Abstract)
├── BaseLLMAgent (Text-based language models)
├── BaseVLMAgent (Vision-language models)
└── BaseOCRAgent (Specialized OCR models)

Implementations
├── LLM Agents
│   ├── POELLMAgent (POE API)
│   ├── LMStudioLLMAgent (Local LM Studio)
│   └── OllamaLLMAgent (Local Ollama)
│
├── VLM Agents
│   ├── POEVLMAgent (POE API)
│   ├── LMStudioVLMAgent (Local LM Studio)
│   └── OllamaVLMAgent (Local Ollama)
│
└── OCR Agents
    ├── LMStudioOCRAgent (Local LM Studio)
    └── VLLMOCRAgent (Remote vLLM server)
```

## Base Classes

### BaseLLMAgent

Abstract base class for text-based language models.

**Methods:**
- `generate(prompt, system_prompt, timeout)` - Generate text from prompt
- `chat(messages, timeout)` - Chat completion with message history
- `validate_config()` - Validate agent configuration
- `get_config()` - Get agent configuration

**Response:**
```python
@dataclass
class LLMResponse:
    success: bool
    content: Optional[str] = None
    error: Optional[str] = None
    error_type: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
```

### BaseVLMAgent

Abstract base class for vision-language models.

**Methods:**
- `generate_from_image(image_path, prompt, system_prompt, timeout)` - Generate from single image
- `generate_from_images(image_paths, prompt, system_prompt, timeout)` - Generate from multiple images
- `generate_from_base64(image_base64, prompt, media_type, system_prompt, timeout)` - Generate from base64 image
- `validate_config()` - Validate agent configuration
- `get_config()` - Get agent configuration

**Response:**
```python
@dataclass
class VLMResponse:
    success: bool
    content: Optional[str] = None
    error: Optional[str] = None
    error_type: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
```

### BaseOCRAgent

Abstract base class for specialized OCR models.

**Methods:**
- `process_image(image_path, timeout)` - Process OCR on image
- `process_pdf_page(pdf_path, page_number, render_dpi, timeout)` - Process single PDF page
- `process_pdf_all_pages(pdf_path, render_dpi, timeout)` - Process all PDF pages
- `validate_config()` - Validate agent configuration
- `get_config()` - Get agent configuration
- `check_server_status()` - Check if OCR server is running

**Response:**
```python
@dataclass
class OCRResponse:
    success: bool
    text: Optional[str] = None
    pages: Optional[int] = None
    error: Optional[str] = None
    error_type: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
```

## LLM Agents

### POELLMAgent

POE API implementation for text-based language models.

**Supported Models:**
- `assistant` - POE Assistant
- `qwen3-max` - Qwen3 Max
- `gemini-3-pro` - Gemini 3 Pro
- `claude-opus-4.5` - Claude Opus 4.5
- And more POE models

**Configuration:**
```python
from agents import POELLMAgent

agent = POELLMAgent(
    model_id="qwen3-max",
    api_key="your-poe-api-key",  # or set POE_API_KEY env var
    temperature=0.2,
    max_tokens=4096,
    top_p=0.9
)
```

**Usage:**
```python
# Simple generation
response = agent.generate("What is AI?")

# With system prompt
response = agent.generate(
    prompt="Explain quantum computing",
    system_prompt="You are a physics expert"
)

# Chat with history
messages = [
    {"role": "system", "content": "You are a helpful assistant"},
    {"role": "user", "content": "Hello"},
    {"role": "assistant", "content": "Hi! How can I help?"},
    {"role": "user", "content": "Tell me about Python"}
]
response = agent.chat(messages)
```

### LMStudioLLMAgent

LM Studio implementation for local language models.

**Supported Models:**
- Any model loaded in LM Studio with OpenAI-compatible API

**Configuration:**
```python
from agents import LMStudioLLMAgent

agent = LMStudioLLMAgent(
    model_id="llama-3-8b",
    base_url="http://localhost:1234",
    temperature=0.2,
    max_tokens=4096
)
```

**Usage:**
```python
response = agent.generate("Explain machine learning")

if response.success:
    print(response.content)
else:
    print(f"Error: {response.error}")
```

### OllamaLLMAgent

Ollama implementation for local language models.

**Supported Models:**
- `llama3` - Llama 3
- `mistral` - Mistral
- `qwen` - Qwen
- `phi` - Phi
- And more Ollama models

**Configuration:**
```python
from agents import OllamaLLMAgent

agent = OllamaLLMAgent(
    model_id="llama3",
    base_url="http://localhost:11434",
    temperature=0.2,
    max_tokens=4096
)
```

**Usage:**
```python
# Check if model is available
if not agent.check_model_available():
    # Pull model if not available
    agent.pull_model()

# Generate
response = agent.generate("What is deep learning?")
```

## VLM Agents

### POEVLMAgent

POE API implementation for vision-language models.

**Supported Models:**
- `gemini-3-pro` - Gemini 3 Pro (with vision)
- Other POE models with vision capabilities

**Configuration:**
```python
from agents import POEVLMAgent

agent = POEVLMAgent(
    model_id="gemini-3-pro",
    api_key="your-poe-api-key",
    temperature=0.2,
    max_tokens=4096
)
```

**Usage:**
```python
# Single image
response = agent.generate_from_image(
    image_path="document.png",
    prompt="Extract all text from this image"
)

# Multiple images
response = agent.generate_from_images(
    image_paths=["page1.png", "page2.png"],
    prompt="Summarize these document pages"
)

# Base64 image
response = agent.generate_from_base64(
    image_base64=base64_string,
    prompt="Describe this image",
    media_type="image/png"
)
```

### LMStudioVLMAgent

LM Studio implementation for local vision-language models.

**Supported Models:**
- Any vision model loaded in LM Studio with OpenAI-compatible API

**Configuration:**
```python
from agents import LMStudioVLMAgent

agent = LMStudioVLMAgent(
    model_id="llava-v1.6",
    base_url="http://localhost:1234",
    temperature=0.2,
    max_tokens=4096
)
```

**Usage:**
```python
response = agent.generate_from_image(
    image_path="photo.jpg",
    prompt="What's in this image?"
)
```

### OllamaVLMAgent

Ollama implementation for local vision-language models.

**Supported Models:**
- `llava` - LLaVA
- `bakllava` - BakLLaVA
- Other Ollama vision models

**Configuration:**
```python
from agents import OllamaVLMAgent

agent = OllamaVLMAgent(
    model_id="llava",
    base_url="http://localhost:11434",
    temperature=0.2,
    max_tokens=4096
)
```

**Usage:**
```python
# Check and pull model if needed
if not agent.check_model_available():
    agent.pull_model()

# Process image
response = agent.generate_from_image(
    image_path="document.png",
    prompt="Extract text from this document"
)
```

## OCR Agents

### LMStudioOCRAgent

LM Studio implementation for local OCR models.

**Supported Models:**
- DeepSeek-OCR
- Nanonets-OCR2-3B
- Other OCR models in LM Studio

**Configuration:**
```python
from agents import LMStudioOCRAgent

agent = LMStudioOCRAgent(
    model_id="deepseek-ocr",
    base_url="http://localhost:1234",
    max_tokens=4096,
    temperature=0.2
)
```

**Usage:**
```python
# Process image
response = agent.process_image("receipt.png")

# Process PDF page
response = agent.process_pdf_page("document.pdf", page_number=0)

# Process all PDF pages
response = agent.process_pdf_all_pages("document.pdf")

if response.success:
    print(f"Extracted text: {response.text}")
    print(f"Pages: {response.pages}")
```

### VLLMOCRAgent

vLLM server implementation for remote OCR models.

**Supported Models:**
- LightOnOCR-2-1B (production)

**Configuration:**
```python
from agents import VLLMOCRAgent

agent = VLLMOCRAgent(
    model_id="lightonocr-2-1b",
    base_url="http://aimsb.theworkpc.com:8081",
    max_tokens=4096,
    temperature=0.2
)
```

**Usage:**
```python
# Check server status
if agent.check_server_status():
    response = agent.process_image("invoice.png")
else:
    print("vLLM server is not running")
```

## Error Handling

All agents return consistent error types:

- `connection_error` - Cannot connect to server
- `timeout_error` - Request timed out
- `api_error` - API returned error
- `file_error` - File read/write error
- `validation_error` - Invalid input
- `processing_error` - General processing error
- `dependency_error` - Missing required dependency

**Example:**
```python
response = agent.generate("Hello")

if not response.success:
    if response.error_type == "connection_error":
        print("Server is not running")
    elif response.error_type == "timeout_error":
        print("Request timed out")
    else:
        print(f"Error: {response.error}")
```

## Best Practices

### 1. Always Check Success

```python
response = agent.generate("prompt")

if response.success:
    # Use response.content
    print(response.content)
else:
    # Handle error
    print(f"Error: {response.error}")
```

### 2. Use Appropriate Timeouts

```python
# Short timeout for simple tasks
response = agent.generate("Hello", timeout=10)

# Longer timeout for complex tasks
response = agent.generate(long_prompt, timeout=120)
```

### 3. Check Server Status

```python
# For local agents
if agent.check_server_status():
    response = agent.process_image("image.png")
else:
    print("Server is not running")
```

### 4. Handle Model Availability (Ollama)

```python
# Check if model exists
if not agent.check_model_available():
    print("Pulling model...")
    if agent.pull_model():
        print("Model ready")
    else:
        print("Failed to pull model")
```

### 5. Use System Prompts

```python
response = agent.generate(
    prompt="Explain quantum physics",
    system_prompt="You are a physics professor. Explain concepts clearly and simply."
)
```

## Testing

### Test LLM Agent

```python
from agents import POELLMAgent

agent = POELLMAgent(model_id="qwen3-max")

# Test simple generation
response = agent.generate("Say hello")
assert response.success
assert "hello" in response.content.lower()

# Test chat
messages = [
    {"role": "user", "content": "Hello"}
]
response = agent.chat(messages)
assert response.success
```

### Test VLM Agent

```python
from agents import POEVLMAgent

agent = POEVLMAgent(model_id="gemini-3-pro")

# Test image processing
response = agent.generate_from_image(
    "test_image.png",
    "Describe this image"
)
assert response.success
assert len(response.content) > 0
```

### Test OCR Agent

```python
from agents import VLLMOCRAgent

agent = VLLMOCRAgent(
    model_id="lightonocr-2-1b",
    base_url="http://aimsb.theworkpc.com:8081"
)

# Test image OCR
response = agent.process_image("test_document.png")
assert response.success
assert len(response.text) > 0
```

## Configuration Examples

### Environment Variables

```bash
# POE API
export POE_API_KEY=your-poe-api-key

# LM Studio
export LM_STUDIO_BASE_URL=http://localhost:1234

# Ollama
export OLLAMA_BASE_URL=http://localhost:11434

# vLLM
export VLLM_BASE_URL=http://aimsb.theworkpc.com:8081
```

### YAML Configuration

```yaml
agents:
  llm:
    poe:
      model_id: qwen3-max
      api_key: ${POE_API_KEY}
      temperature: 0.2
      max_tokens: 4096
    
    lmstudio:
      model_id: llama-3-8b
      base_url: ${LM_STUDIO_BASE_URL}
      temperature: 0.2
      max_tokens: 4096
    
    ollama:
      model_id: llama3
      base_url: ${OLLAMA_BASE_URL}
      temperature: 0.2
      max_tokens: 4096
  
  vlm:
    poe:
      model_id: gemini-3-pro
      api_key: ${POE_API_KEY}
      temperature: 0.2
      max_tokens: 4096
    
    ollama:
      model_id: llava
      base_url: ${OLLAMA_BASE_URL}
      temperature: 0.2
      max_tokens: 4096
  
  ocr:
    vllm:
      model_id: lightonocr-2-1b
      base_url: ${VLLM_BASE_URL}
      max_tokens: 4096
      temperature: 0.2
    
    lmstudio:
      model_id: deepseek-ocr
      base_url: ${LM_STUDIO_BASE_URL}
      max_tokens: 4096
      temperature: 0.2
```

## Adding New Agents

To add a new agent implementation:

1. **Create agent file** (e.g., `custom_llm_agent.py`)
2. **Inherit from base class** (`BaseLLMAgent`, `BaseVLMAgent`, or `BaseOCRAgent`)
3. **Implement required methods**
4. **Add to `__init__.py`**
5. **Add tests**

**Example:**
```python
from agents.base_llm_agent import BaseLLMAgent, LLMResponse

class CustomLLMAgent(BaseLLMAgent):
    def generate(self, prompt, system_prompt=None, timeout=60):
        # Implementation
        pass
    
    def chat(self, messages, timeout=60):
        # Implementation
        pass
```

## Troubleshooting

### Connection Errors

**Problem:** `connection_error` when calling agent

**Solutions:**
- Check if server is running (LM Studio, Ollama, vLLM)
- Verify base URL is correct
- Check firewall settings
- Test with `curl` or browser

### Timeout Errors

**Problem:** `timeout_error` on requests

**Solutions:**
- Increase timeout parameter
- Check server performance
- Reduce input size
- Use faster model

### Model Not Found (Ollama)

**Problem:** Model not available in Ollama

**Solutions:**
```python
# Check and pull model
if not agent.check_model_available():
    agent.pull_model()
```

### API Key Errors (POE)

**Problem:** Authentication failed

**Solutions:**
- Set `POE_API_KEY` environment variable
- Pass `api_key` parameter to agent
- Verify API key is valid
