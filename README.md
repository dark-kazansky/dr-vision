# LightOnOCR-2-1B Inference Guide for LM Studio
```source .venv/bin/activate && python app.p
y```
## Model Information

| Property | Value |
|----------|-------|
| **Model** | `staghado/LightOnOCR-2-1B-Q4_K_M-GGUF` |
| **API Identifier** | `lightonocr-2-1b` |
| **Architecture** | Qwen3 (Vision Enabled) |
| **Format** | GGUF Q4_K_M |
| **Size** | 846.15 MB |
| **Capabilities** | OCR, Document Understanding, Table Extraction |

## Quick Start

### 1. Start LM Studio Server

1. Open LM Studio
2. Ensure `lightonocr-2-1b` model is loaded (you can see "READY" status)
3. Toggle **Status: Stopped** to start the server
4. Wait for "Server running" message
5. Default endpoint: `http://localhost:1234`

### 2. Install Dependencies

```bash
pip install requests pillow pypdfium2
```

### 3. Basic Usage

```python
import base64
import requests

# Read and encode image
with open("document.png", "rb") as f:
    image_data = base64.b64encode(f.read()).decode("utf-8")

# Make OCR request
response = requests.post(
    "http://localhost:1234/v1/chat/completions",
    json={
        "model": "lightonocr-2-1b",
        "messages": [{
            "role": "user",
            "content": [{
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{image_data}"
                }
            }]
        }],
        "max_tokens": 4096,
        "temperature": 0.2
    }
)

text = response.json()["choices"][0]["message"]["content"]
print(text)
```

## Files Included

| File | Description |
|------|-------------|
| `lightonocr_inference.py` | Full-featured inference library with PDF support |
| `lightonocr_api_examples.py` | Various API usage patterns (sync, async, streaming) |
| `ocr_quick.py` | Command-line tool for quick OCR |
| `requirements.txt` | Python dependencies |

## API Endpoints

LM Studio provides OpenAI-compatible endpoints:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/v1/models` | GET | List available models |
| `/v1/chat/completions` | POST | Generate OCR response |
| `/v1/completions` | POST | Legacy completions API |

## Usage Examples

### Command Line

```bash
# OCR single image
python ocr_quick.py receipt.png

# OCR PDF (first page)
python ocr_quick.py document.pdf

# OCR specific PDF page
python ocr_quick.py document.pdf --page 2

# Save results to file
python ocr_quick.py *.png --output results.txt
```

### Python Library

```python
from lightonocr_inference import ocr_image, ocr_pdf_page, check_server_status

# Check server
status = check_server_status()
if status["status"] == "running":
    
    # OCR image file
    text = ocr_image("scan.jpg")
    
    # OCR from URL
    text = ocr_image("https://example.com/document.jpg")
    
    # OCR PDF page
    text = ocr_pdf_page("contract.pdf", page_number=0)
```

### Using OpenAI SDK

```python
from openai import OpenAI
import base64

client = OpenAI(
    base_url="http://localhost:1234/v1",
    api_key="not-needed"
)

with open("image.png", "rb") as f:
    image_data = base64.b64encode(f.read()).decode("utf-8")

response = client.chat.completions.create(
    model="lightonocr-2-1b",
    messages=[{
        "role": "user",
        "content": [{
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{image_data}"}
        }]
    }],
    max_tokens=4096
)

print(response.choices[0].message.content)
```

### cURL

```bash
# Encode image to base64
IMAGE_BASE64=$(base64 -i document.png)

# Make request
curl http://localhost:1234/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "lightonocr-2-1b",
    "messages": [{
      "role": "user",
      "content": [{
        "type": "image_url",
        "image_url": {
          "url": "data:image/png;base64,'$IMAGE_BASE64'"
        }
      }]
    }],
    "max_tokens": 4096,
    "temperature": 0.2
  }'
```

## Recommended Parameters

| Parameter | Recommended Value | Description |
|-----------|------------------|-------------|
| `max_tokens` | 4096-8192 | Higher for longer documents |
| `temperature` | 0.2 | Lower for more deterministic output |
| `top_p` | 0.9 | Nucleus sampling |

## Performance Tips

1. **Image Resolution**: Render PDFs at 200 DPI for optimal quality/speed balance
2. **Batch Processing**: Use async client for multiple images
3. **Memory**: Q4_K_M quantization keeps memory usage low (~1.5GB RAM)
4. **GPU**: Model supports Metal (MPS) on Mac, CUDA on Windows/Linux

## Document Types Supported

- 📄 Scanned documents
- 🧾 Receipts and invoices
- 📊 Tables and forms
- 📑 Multi-column layouts
- 🔢 Mathematical notation (LaTeX)
- 🇻🇳 Vietnamese text (well supported)
- 🇫🇷 French text (enhanced in v2)

## Troubleshooting

### Server Not Running
```
Error: LM Studio server is not running!
```
→ Toggle "Status: Stopped" in LM Studio to start the server

### Model Not Loaded
→ Click on model name and ensure it shows "READY"

### Out of Memory
→ Try smaller batch sizes or close other applications

### Slow Response
→ First request may be slow due to model warm-up. Subsequent requests are faster.

## Model Architecture

LightOnOCR-2-1B uses:
- **Vision Encoder**: Pixtral-based (from Mistral-Small-3.1)
- **Language Decoder**: Qwen3-based
- **Training**: RLVR (Reinforcement Learning from Visual Reasoning)
- **Benchmark**: State-of-the-art on OlmOCR-Bench (83.2 score)

## License

LightOnOCR-2-1B is released under Apache 2.0 license.

## Links

- [Model on HuggingFace](https://huggingface.co/lightonai/LightOnOCR-2-1B)
- [Official Blog Post](https://huggingface.co/blog/lightonai/lightonocr-2)
- [Demo](https://huggingface.co/spaces/lightonai/LightOnOCR-2-1B-Demo)
- [LM Studio](https://lmstudio.ai/)
