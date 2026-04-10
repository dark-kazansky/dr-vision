"""
FastAPI route handlers for Dr.Vision.

New agent-based architecture:
Input → Backend API → Functions + Config → Agents → Output → Frontend
"""

from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from fastapi.responses import JSONResponse
from typing import Optional, List
import os
import json

from core import Config, ConfigurationError
from core.utils import allowed_file, secure_save_file
from core.agent_factory import AgentFactory
from core import (
    OCRResponse, HealthResponse, ClassifyResponse,
    SplitResponse, ChunkModel, ChunkCategoryModel,
    ExtractionConfig, SchemaField, FieldType, ExtractionTarget
)
from functions.parser import Parser
from functions.extractor import Extractor
from functions.classifier import Classifier, ClassificationRule
from functions.schema_generator import SchemaGenerator
from functions.splitter import Splitter
from functions.text_parser import TextParser
from functions.condition_evaluator import ConditionEvaluator, Condition, ConditionOperator


# Create API router
router = APIRouter()


# Dependency injection for configuration
def get_config() -> Config:
    """Get configuration instance."""
    try:
        return Config.load()
    except ConfigurationError as e:
        raise HTTPException(status_code=500, detail=f"Configuration error: {str(e)}")


@router.post("/ocr")
@router.post("/parse")
async def parse_document(
    file: UploadFile = File(...),
    model_id: str = Form(...),
    force_ocr: bool = Form(False),
    parse_formatting: bool = Form(True),
    process_all_pages: bool = Form(True),
    tier: str = Form("Normal"),
    extraction_enabled: bool = Form(False),
    extraction_target: Optional[str] = Form(None),
    extraction_schema: Optional[str] = Form(None),
    extractor_model: Optional[str] = Form("qwen3-max"),
    config: Config = Depends(get_config)
) -> JSONResponse:
    """
    Parse document and extract text (with optional structured extraction).
    
    This endpoint supports both /ocr (legacy) and /parse paths.
    
    Args:
        file: Uploaded file
        model_id: OCR model ID
        force_ocr: Force OCR even for text-based PDFs
        parse_formatting: Parse markdown/HTML to plain text
        process_all_pages: Process all pages (for PDFs)
        tier: Processing tier (Rapid, Normal, Advance)
        extraction_enabled: Enable structured data extraction
        extraction_target: Extraction scope (document, page, table_row)
        extraction_schema: JSON string with extraction schema
        extractor_model: LLM model for extraction
        config: Configuration instance
        
    Returns:
        JSON response with parsed text, metadata, and optional structured data
    """
    # Validate file
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file selected")
    
    upload_config = config.upload_config
    allowed_extensions = set(upload_config.get('allowed_extensions', []))
    
    if not allowed_file(file.filename, allowed_extensions):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(allowed_extensions)}"
        )
    
    # Save file
    upload_folder = upload_config.get('folder', 'uploads')
    try:
        file_path = await secure_save_file(file, upload_folder)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")
    
    try:
        # Create OCR agent
        ocr_agent = AgentFactory.create_from_config(config, model_id)
        
        # Create parser
        parser = Parser(ocr_agent=ocr_agent)
        
        # Parse file
        result = parser.parse(file_path, force_ocr)
        
        if not result.success:
            raise HTTPException(status_code=500, detail=result.error)
        
        # Parse formatting if requested
        text = result.text
        if parse_formatting:
            text = TextParser.auto_parse(text)
        
        # Save raw OCR result and create DOCX
        data_dir = os.path.join(os.path.dirname(__file__), 'data')
        raw_ocr_dir = os.path.join(data_dir, 'raw_ocr')
        parsed_dir = os.path.join(data_dir, 'parsed')
        os.makedirs(raw_ocr_dir, exist_ok=True)
        os.makedirs(parsed_dir, exist_ok=True)
        
        # Generate base filename (without extension)
        base_filename = os.path.splitext(file.filename)[0]
        
        # Save raw OCR result as text file
        raw_ocr_path = os.path.join(raw_ocr_dir, f"{base_filename}.txt")
        try:
            with open(raw_ocr_path, 'w', encoding='utf-8') as f:
                f.write(result.text)
            print(f"Raw OCR saved: {raw_ocr_path}")
        except Exception as e:
            print(f"Warning: Failed to save raw OCR: {str(e)}")
        
        # Convert to DOCX and save
        docx_path = os.path.join(parsed_dir, f"{base_filename}.docx")
        try:
            from docx import Document
            from docx.shared import Pt, RGBColor
            from docx.enum.text import WD_ALIGN_PARAGRAPH
            import re
            
            # Helper function to add inline formatting
            def _add_inline_formatting(para, text):
                """Add text with inline markdown formatting to paragraph."""
                patterns = [
                    (r'\*\*(.+?)\*\*', 'bold'),           # **bold**
                    (r'\*(.+?)\*', 'italic'),             # *italic*
                    (r'`(.+?)`', 'code'),                 # `code`
                    (r'\[(.+?)\]\((.+?)\)', 'link'),      # [text](url)
                ]
                
                remaining_text = text
                while remaining_text:
                    earliest_match = None
                    earliest_pos = len(remaining_text)
                    earliest_pattern = None
                    
                    for pattern, ptype in patterns:
                        match = re.search(pattern, remaining_text)
                        if match and match.start() < earliest_pos:
                            earliest_match = match
                            earliest_pos = match.start()
                            earliest_pattern = ptype
                    
                    if earliest_match:
                        if earliest_pos > 0:
                            run = para.add_run(remaining_text[:earliest_pos])
                            run.font.size = Pt(11)
                        
                        if earliest_pattern == 'bold':
                            run = para.add_run(earliest_match.group(1))
                            run.bold = True
                            run.font.size = Pt(11)
                        elif earliest_pattern == 'italic':
                            run = para.add_run(earliest_match.group(1))
                            run.italic = True
                            run.font.size = Pt(11)
                        elif earliest_pattern == 'code':
                            run = para.add_run(earliest_match.group(1))
                            run.font.name = 'Courier New'
                            run.font.size = Pt(10)
                            run.font.color.rgb = RGBColor(220, 50, 47)
                        elif earliest_pattern == 'link':
                            link_text = earliest_match.group(1)
                            link_url = earliest_match.group(2)
                            run = para.add_run(f"{link_text} ({link_url})")
                            run.font.color.rgb = RGBColor(0, 102, 204)
                            run.font.size = Pt(11)
                        
                        remaining_text = remaining_text[earliest_match.end():]
                    else:
                        run = para.add_run(remaining_text)
                        run.font.size = Pt(11)
                        break
            
            # Create new document
            doc = Document()
            
            # Add title
            title = doc.add_heading(file.filename, level=1)
            
            # Add metadata
            doc.add_paragraph(f"Model: {model_id}")
            doc.add_paragraph(f"Pages: {result.pages if result.pages else 1}")
            doc.add_paragraph(f"File Type: {result.file_type}")
            doc.add_paragraph("")  # Empty line
            
            # Parse and add content with markdown/HTML formatting
            lines = text.split('\n') if text else []
            i = 0
            while i < len(lines):
                line = lines[i].strip()
                
                if not line:
                    # Empty line - add spacing
                    doc.add_paragraph("")
                    i += 1
                    continue
                
                # Check for markdown headers
                if line.startswith('# '):
                    # H1 - Heading 1
                    doc.add_heading(line[2:].strip(), level=1)
                elif line.startswith('## '):
                    # H2 - Heading 2
                    doc.add_heading(line[3:].strip(), level=2)
                elif line.startswith('### '):
                    # H3 - Heading 3
                    doc.add_heading(line[4:].strip(), level=3)
                elif line.startswith('#### '):
                    # H4 - Heading 4
                    doc.add_heading(line[5:].strip(), level=4)
                elif line.startswith('- ') or line.startswith('* '):
                    # Bullet list with inline formatting
                    list_text = line[2:].strip()
                    para = doc.add_paragraph(style='List Bullet')
                    para.paragraph_format.left_indent = Pt(18)
                    _add_inline_formatting(para, list_text)
                elif re.match(r'^\d+\.\s', line):
                    # Numbered list with inline formatting
                    text_content = re.sub(r'^\d+\.\s', '', line)
                    para = doc.add_paragraph(style='List Number')
                    para.paragraph_format.left_indent = Pt(18)
                    _add_inline_formatting(para, text_content)
                elif line.startswith('> '):
                    # Blockquote with inline formatting
                    quote_text = line[2:].strip()
                    para = doc.add_paragraph()
                    para.paragraph_format.left_indent = Pt(36)
                    para.paragraph_format.right_indent = Pt(36)
                    _add_inline_formatting(para, quote_text)
                    # Apply italic and gray color to all runs
                    for run in para.runs:
                        run.font.italic = True
                        run.font.color.rgb = RGBColor(96, 96, 96)
                elif line.startswith('---') or line.startswith('***'):
                    # Horizontal rule - add empty paragraph with bottom border
                    para = doc.add_paragraph()
                    para.paragraph_format.space_after = Pt(12)
                else:
                    # Regular paragraph - parse inline formatting
                    para = doc.add_paragraph()
                    _add_inline_formatting(para, line)
                
                i += 1
            
            # Save document
            doc.save(docx_path)
            print(f"DOCX saved: {docx_path}")
        except Exception as e:
            print(f"Warning: Failed to create DOCX: {str(e)}")
            import traceback
            traceback.print_exc()
        
        response_data = {
            "success": True,
            "text": text,
            "parsed_text": text if parse_formatting else None,
            "file_type": result.file_type,
            "is_scanned": result.is_scanned,
            "pages": result.pages,
            "filename": file.filename,
            "model": model_id
        }
        
        # Perform extraction if enabled
        if extraction_enabled and extraction_schema:
            try:
                # Parse schema
                schema_data = json.loads(extraction_schema)
                fields = [
                    SchemaField(
                        name=field['name'],
                        type=FieldType(field['type']),
                        description=field.get('description', ''),
                        required=field.get('required', False)
                    )
                    for field in schema_data
                ]
                
                # Create extraction config
                extraction_config = ExtractionConfig(
                    fields=fields,
                    target=ExtractionTarget(extraction_target or "document")
                )
                
                # Extract data
                llm_agent = AgentFactory.create_llm_agent(extractor_model)
                extractor = Extractor(agent=llm_agent)
                extract_result = extractor.extract(text, extraction_config)
                
                if extract_result.success:
                    # Save extraction result to file
                    extracted_dir = os.path.join(data_dir, 'extracted')
                    os.makedirs(extracted_dir, exist_ok=True)
                    
                    # Generate filename (without extension)
                    base_filename = os.path.splitext(file.filename)[0]
                    extracted_file_path = os.path.join(extracted_dir, f"{base_filename}.json")
                    
                    try:
                        extraction_output = {
                            "filename": file.filename,
                            "model": extractor_model,
                            "extraction_target": extraction_target or "document",
                            "schema": schema_data,
                            "structured_data": extract_result.structured_data,
                            "field_errors": extract_result.field_errors,
                            "timestamp": os.path.getctime(file_path) if os.path.exists(file_path) else None
                        }
                        
                        with open(extracted_file_path, 'w', encoding='utf-8') as f:
                            json.dump(extraction_output, f, indent=2, ensure_ascii=False)
                        
                        print(f"Extraction result saved: {extracted_file_path}")
                    except Exception as e:
                        print(f"Warning: Failed to save extraction result: {str(e)}")
                    
                    response_data["extraction"] = {
                        "success": True,
                        "structured_data": extract_result.structured_data,
                        "field_errors": extract_result.field_errors
                    }
                else:
                    response_data["extraction"] = {
                        "success": False,
                        "error": extract_result.error
                    }
            except Exception as e:
                response_data["extraction"] = {
                    "success": False,
                    "error": f"Extraction failed: {str(e)}"
                }
        
        return JSONResponse(response_data)
        
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)


@router.post("/classify", response_model=ClassifyResponse)
async def classify_document(
    file: UploadFile = File(...),
    parser_model_id: str = Form(...),
    classifier_model_id: str = Form(None),  # Make optional, will use tier config if not provided
    classification_rules: str = Form(...),
    tier: str = Form("Normal"),
    max_pages: int = Form(5),
    is_multimodal: bool = Form(False),
    config: Config = Depends(get_config)
) -> ClassifyResponse:
    """
    Classify document based on rules.
    
    Args:
        file: Uploaded file
        parser_model_id: OCR model ID
        classifier_model_id: LLM model ID for classification (optional, uses tier config if not provided)
        classification_rules: JSON string with classification rules
        tier: Processing tier (Rapid, Normal, Advance, Multimodal)
        max_pages: Maximum number of pages to process
        is_multimodal: Whether to use multimodal processing
        config: Configuration instance
        
    Returns:
        ClassifyResponse with classification results
    """
    try:
        print(f"\n=== CLASSIFY REQUEST ===")
        print(f"File: {file.filename if file else 'None'}")
        print(f"Parser Model: {parser_model_id}")
        print(f"Classifier Model: {classifier_model_id}")
        print(f"Tier: {tier}")
        print(f"Rules: {classification_rules[:100]}..." if len(classification_rules) > 100 else f"Rules: {classification_rules}")
        print(f"========================\n")
    except Exception as e:
        print(f"Error logging request: {e}")
    
    # Use tier config if classifier_model_id not provided
    if not classifier_model_id:
        from config import TierConfig
        classifier_model_id = TierConfig.get_classifier_llm_model(tier)
        print(f"Using classifier model from tier config: {classifier_model_id} for tier: {tier}")
    else:
        print(f"Using provided classifier model: {classifier_model_id}")
    
    # Validate file
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file selected")
    
    print(f"Processing file: {file.filename}")
    
    # Parse classification rules
    try:
        rules_data = json.loads(classification_rules)
        if not rules_data or len(rules_data) == 0:
            raise HTTPException(status_code=400, detail="Classification rules cannot be empty. Please add rules in node settings.")
        
        rules = [
            ClassificationRule(
                doc_type=rule.get('type', rule.get('doc_type', '')),
                description=rule.get('description', '')
            )
            for rule in rules_data
        ]
        
        # Validate that rules have doc_type
        for i, rule in enumerate(rules):
            if not rule.doc_type:
                raise HTTPException(status_code=400, detail=f"Rule {i+1} is missing doc_type. Please fill in all rule fields.")
        
        print(f"Loaded {len(rules)} classification rules: {[r.doc_type for r in rules]}")
        
    except json.JSONDecodeError as e:
        print(f"JSON decode error: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Invalid classification rules JSON: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error parsing rules: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=f"Invalid classification rules: {str(e)}")
    
    # Setup directories
    data_dir = os.path.join(os.path.dirname(__file__), 'data')
    uploaded_dir = os.path.join(data_dir, 'uploaded')
    classified_dir = os.path.join(data_dir, 'classified')
    os.makedirs(uploaded_dir, exist_ok=True)
    os.makedirs(classified_dir, exist_ok=True)
    
    # Read file content
    file_content = await file.read()
    
    # Calculate file hash for duplicate detection
    import hashlib
    file_hash = hashlib.sha256(file_content).hexdigest()
    
    # Check for duplicate file
    saved_file_path = os.path.join(uploaded_dir, file.filename)
    is_duplicate = False
    
    if os.path.exists(saved_file_path):
        # File with same name exists, check content hash
        with open(saved_file_path, 'rb') as existing_file:
            existing_hash = hashlib.sha256(existing_file.read()).hexdigest()
            if existing_hash == file_hash:
                is_duplicate = True
                print(f"Duplicate file detected: {file.filename} (hash: {file_hash[:8]}...)")
    
    # Save file only if not duplicate
    if not is_duplicate:
        try:
            with open(saved_file_path, 'wb') as f:
                f.write(file_content)
            print(f"File saved: {saved_file_path}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")
    else:
        print(f"Skipping duplicate file: {file.filename}")
    
    # Save to temp folder for processing (using already-read content)
    upload_config = config.upload_config
    upload_folder = upload_config.get('folder', 'uploads')
    try:
        # Create upload folder if it doesn't exist
        os.makedirs(upload_folder, exist_ok=True)
        
        # Generate secure temp filename
        import secrets
        random_hex = secrets.token_hex(16)
        safe_filename = file.filename.replace('/', '_').replace('\\', '_')
        temp_filename = f"{random_hex}_{safe_filename}"
        file_path = os.path.join(upload_folder, temp_filename)
        
        # Write the already-read content to temp file
        with open(file_path, 'wb') as f:
            f.write(file_content)
        
        print(f"Temp file created for processing: {file_path}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save temp file: {str(e)}")
    
    try:
        # Step 1: Parse document
        print(f"Parsing document with model: {parser_model_id}")
        
        # Check if model exists
        if parser_model_id not in config.models:
            raise HTTPException(
                status_code=400, 
                detail=f"Parser model '{parser_model_id}' not found in configuration. Available models: {', '.join(config.models.keys())}"
            )
        
        ocr_agent = AgentFactory.create_from_config(config, parser_model_id)
        parser = Parser(ocr_agent=ocr_agent)
        parse_result = parser.parse(file_path)
        
        if not parse_result.success:
            raise HTTPException(status_code=500, detail=f"Parse failed: {parse_result.error}")
        
        print(f"Parse successful, text length: {len(parse_result.text)}")
        
        # Step 2: Classify
        print(f"Classifying with model: {classifier_model_id}, rules: {len(rules)}")
        
        # Check if model exists
        if classifier_model_id not in config.models:
            raise HTTPException(
                status_code=400,
                detail=f"Classifier model '{classifier_model_id}' not found in configuration. Available models: {', '.join(config.models.keys())}"
            )
        
        llm_agent = AgentFactory.create_llm_agent(classifier_model_id)
        classifier = Classifier(agent=llm_agent)
        classify_result = classifier.classify(parse_result.text, rules)
        
        if not classify_result.success:
            raise HTTPException(status_code=500, detail=f"Classification failed: {classify_result.error}")
        
        print(f"Classification successful: {classify_result.document_type}")
        
        # Import ClassificationResult from core.schemas
        from core.schemas import ClassificationResult
        
        # Create classification result
        classification_result = ClassificationResult(
            fileName=file.filename,
            documentType=classify_result.document_type,
            confidence=classify_result.confidence,
            reasoning=classify_result.reasoning
        )
        
        # Save result to classified/result.json
        result_file_path = os.path.join(classified_dir, 'result.json')
        try:
            # Load existing results
            if os.path.exists(result_file_path):
                with open(result_file_path, 'r', encoding='utf-8') as f:
                    results_data = json.load(f)
            else:
                results_data = {}
            
            # Add new result (or update if duplicate)
            results_data[file.filename] = classify_result.document_type
            
            # Save updated results
            with open(result_file_path, 'w', encoding='utf-8') as f:
                json.dump(results_data, f, indent=2, ensure_ascii=False)
            
            print(f"Result saved to: {result_file_path}")
        except Exception as e:
            print(f"Warning: Failed to save result to result.json: {str(e)}")
        
        return ClassifyResponse(
            success=True,
            results=[classification_result],
            error=None,
            error_type=None
        )
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Classification error: {str(e)}")
        
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)


@router.post("/classify-text", response_model=ClassifyResponse)
async def classify_text(
    text: str = Form(...),
    classification_rules: str = Form(...),
    classifier_model_id: str = Form(None),  # Make optional
    tier: str = Form("Normal"),  # Add tier parameter
    config: Config = Depends(get_config)
) -> ClassifyResponse:
    """
    Classify text directly without OCR (for reusing OCR results).
    
    Args:
        text: Text content to classify
        classification_rules: JSON string with classification rules
        classifier_model_id: LLM model ID for classification (optional, uses tier config if not provided)
        tier: Processing tier (Rapid, Normal, Advance)
        config: Configuration instance
        
    Returns:
        ClassifyResponse with classification results
    """
    # Use tier config if classifier_model_id not provided
    if not classifier_model_id:
        from config import TierConfig
        classifier_model_id = TierConfig.get_classifier_llm_model(tier)
        print(f"Using classifier model from tier config: {classifier_model_id}")
    
    # Parse classification rules
    try:
        rules_data = json.loads(classification_rules)
        rules = [
            ClassificationRule(
                doc_type=rule.get('type', rule.get('doc_type', '')),
                description=rule.get('description', '')
            )
            for rule in rules_data
        ]
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid classification rules: {str(e)}")
    
    try:
        # Classify text directly
        llm_agent = AgentFactory.create_llm_agent(classifier_model_id)
        classifier = Classifier(agent=llm_agent)
        classify_result = classifier.classify(text, rules)
        
        if not classify_result.success:
            raise HTTPException(status_code=500, detail=classify_result.error)
        
        # Import ClassificationResult from core.schemas
        from core.schemas import ClassificationResult
        
        # Create classification result
        classification_result = ClassificationResult(
            fileName="text_input",
            documentType=classify_result.document_type,
            confidence=classify_result.confidence,
            reasoning=classify_result.reasoning
        )
        
        return ClassifyResponse(
            success=True,
            results=[classification_result],
            error=None,
            error_type=None
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Classification failed: {str(e)}")


@router.post("/generate-schema")
async def generate_schema(
    prompt: str = Form(...),
    file: Optional[UploadFile] = File(None),
    tier: str = Form("Normal"),
    config: Config = Depends(get_config)
) -> JSONResponse:
    """
    Generate extraction schema using AI.
    
    Args:
        prompt: Description of what to extract
        file: Optional sample document
        tier: Processing tier (Rapid, Normal, Advance) - uses extractor tier config
        config: Configuration instance
        
    Returns:
        JSON response with generated schema
    """
    sample_text = None
    file_path = None
    
    try:
        # If file provided, extract text
        if file and file.filename:
            upload_config = config.upload_config
            upload_folder = upload_config.get('folder', 'uploads')
            file_path = await secure_save_file(file, upload_folder)
            
            # Parse file to get sample text
            ocr_model_id = config.get_available_models()[0] if config.get_available_models() else None
            if ocr_model_id:
                ocr_agent = AgentFactory.create_from_config(config, ocr_model_id)
                parser = Parser(ocr_agent=ocr_agent)
                parse_result = parser.parse(file_path)
                
                if parse_result.success:
                    sample_text = parse_result.text[:2000]  # Limit to 2000 chars
        
        # Get model from extractor tier configuration
        from config import TierConfig
        model_id = TierConfig.get_extractor_model(tier)
        
        # Generate schema
        llm_agent = AgentFactory.create_llm_agent(model_id)
        schema_gen = SchemaGenerator(agent=llm_agent)
        result = schema_gen.generate(sample_text or "", prompt)
        
        if not result.success:
            raise HTTPException(status_code=500, detail=result.error)
        
        # Convert to dict
        schema_dicts = [
            {
                "name": field.name,
                "type": field.type.value,
                "description": field.description,
                "required": field.required
            }
            for field in result.fields
        ]
        
        return JSONResponse({
            "success": True,
            "schema": schema_dicts
        })
        
    finally:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)


@router.post("/extract")
async def extract_data(
    file: UploadFile = File(...),
    parser_model_id: str = Form(...),
    extractor_model_id: str = Form("qwen3-max"),
    extraction_schema: str = Form(...),
    extraction_target: str = Form("document"),
    generate_schema: bool = Form(False),
    schema_prompt: Optional[str] = Form(None),
    config: Config = Depends(get_config)
) -> JSONResponse:
    """
    Extract structured data from document.
    
    Args:
        file: Uploaded file
        parser_model_id: OCR model ID
        extractor_model_id: LLM model ID for extraction
        extraction_schema: JSON string with schema
        extraction_target: Target scope (document, page, table_row)
        generate_schema: Whether to generate schema first
        schema_prompt: Prompt for schema generation
        config: Configuration instance
        
    Returns:
        JSON response with extracted data
    """
    # Validate file
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file selected")
    
    # Save file
    upload_config = config.upload_config
    upload_folder = upload_config.get('folder', 'uploads')
    try:
        file_path = await secure_save_file(file, upload_folder)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")
    
    try:
        # Step 1: Parse document
        ocr_agent = AgentFactory.create_from_config(config, parser_model_id)
        parser = Parser(ocr_agent=ocr_agent)
        parse_result = parser.parse(file_path)
        
        if not parse_result.success:
            raise HTTPException(status_code=500, detail=parse_result.error)
        
        llm_agent = AgentFactory.create_llm_agent(extractor_model_id)
        
        # Step 2: Generate schema if requested
        if generate_schema and schema_prompt:
            schema_gen = SchemaGenerator(agent=llm_agent)
            schema_result = schema_gen.generate(parse_result.text, schema_prompt)
            
            if not schema_result.success:
                raise HTTPException(status_code=500, detail=schema_result.error)
            
            fields = schema_result.fields
        else:
            # Parse provided schema
            try:
                schema_data = json.loads(extraction_schema)
                fields = [
                    SchemaField(
                        name=field['name'],
                        type=FieldType(field['type']),
                        description=field.get('description', ''),
                        required=field.get('required', False)
                    )
                    for field in schema_data
                ]
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Invalid schema: {str(e)}")
        
        # Step 3: Extract data
        extraction_config = ExtractionConfig(
            fields=fields,
            target=ExtractionTarget(extraction_target)
        )
        
        extractor = Extractor(agent=llm_agent)
        extract_result = extractor.extract(parse_result.text, extraction_config)
        
        if not extract_result.success:
            raise HTTPException(status_code=500, detail=extract_result.error)
        
        return JSONResponse({
            "success": True,
            "structured_data": extract_result.structured_data,
            "field_errors": extract_result.field_errors,
            "filename": file.filename
        })
        
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)


@router.post("/extract-text")
async def extract_text(
    text: str = Form(...),
    extraction_schema: str = Form(...),
    extraction_target: str = Form("document"),
    extractor_model_id: str = Form("gemini-2.5-flash"),
    config: Config = Depends(get_config)
) -> JSONResponse:
    """
    Extract structured data from text directly without OCR (for reusing OCR results).
    
    Args:
        text: Text content to extract from
        extraction_schema: JSON string with schema
        extraction_target: Target scope (document, page, table_row)
        extractor_model_id: LLM model ID for extraction
        config: Configuration instance
        
    Returns:
        JSON response with extracted data
    """
    try:
        # Parse schema
        schema_data = json.loads(extraction_schema)
        fields = [
            SchemaField(
                name=field['name'],
                type=FieldType(field['type']),
                description=field.get('description', ''),
                required=field.get('required', False)
            )
            for field in schema_data
        ]
        
        # Create extraction config
        extraction_config = ExtractionConfig(
            fields=fields,
            target=ExtractionTarget(extraction_target)
        )
        
        # Extract data
        llm_agent = AgentFactory.create_llm_agent(extractor_model_id)
        extractor = Extractor(agent=llm_agent)
        extract_result = extractor.extract(text, extraction_config)
        
        if not extract_result.success:
            raise HTTPException(status_code=500, detail=extract_result.error)
        
        return JSONResponse({
            "success": True,
            "extraction": {
                "success": True,
                "structured_data": extract_result.structured_data,
                "field_errors": extract_result.field_errors
            }
        })
        
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid schema JSON: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Extraction failed: {str(e)}")


@router.post("/split", response_model=SplitResponse)
async def split_document(
    file: UploadFile = File(...),
    categories: str = Form(...),
    allow_uncategorized: bool = Form(True),
    parser_tier: str = Form("Normal"),
    splitter_tier: str = Form("Normal"),
    config: Config = Depends(get_config)
) -> SplitResponse:
    """
    Split document into categorized chunks.
    
    This endpoint uses a two-step process:
    1. Parse document with OCR to extract text
    2. Use LLM to categorize chunks based on text content
    
    Args:
        file: Uploaded file
        categories: JSON string with categories
        allow_uncategorized: Whether to include unknown chunks
        parser_tier: OCR processing tier (Rapid, Normal, Advance)
        splitter_tier: Splitting processing tier (Rapid, Normal, Advance)
        config: Configuration instance
        
    Returns:
        SplitResponse with categorized chunks
    """
    # Validate file
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file selected")
    
    # Parse categories
    try:
        categories_data = json.loads(categories)
        from functions.splitter import ChunkCategory
        chunk_categories = [
            ChunkCategory(
                name=cat['name'],
                description=cat['description'],
                order=cat.get('order', 0)
            )
            for cat in categories_data
        ]
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid categories: {str(e)}")
    
    # Get models from tier configuration
    from config import TierConfig
    parser_model_id = TierConfig.get_parser_model(parser_tier)
    splitter_model_id = TierConfig.get_splitter_model(splitter_tier)
    
    # Save file
    upload_config = config.upload_config
    upload_folder = upload_config.get('folder', 'uploads')
    try:
        file_path = await secure_save_file(file, upload_folder)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")
    
    try:
        # Step 1: Parse document with OCR
        ocr_agent = AgentFactory.create_from_config(config, parser_model_id)
        parser = Parser(ocr_agent=ocr_agent)
        parse_result = parser.parse(file_path)
        
        if not parse_result.success:
            raise HTTPException(status_code=500, detail=f"OCR failed: {parse_result.error}")
        
        # Step 2: Use LLM to categorize text chunks
        # For now, we'll use a simple approach: split by pages and categorize each page
        llm_agent = AgentFactory.create_llm_agent(splitter_model_id)
        
        # Build categorization prompt
        categories_list = "\n".join([
            f"{i+1}. {cat.name}: {cat.description}"
            for i, cat in enumerate(chunk_categories)
        ])
        
        # Split text by pages if available
        text = parse_result.text
        pages = []
        
        if "--- Page" in text:
            # Split by page markers
            page_texts = text.split("--- Page")[1:]  # Skip first empty split
            for i, page_text in enumerate(page_texts):
                # Extract page number and content
                lines = page_text.strip().split('\n', 1)
                if len(lines) > 1:
                    page_num = i + 1
                    content = lines[1].strip()
                    if content:
                        pages.append({"page_number": page_num, "content": content})
        else:
            # Single page document
            pages.append({"page_number": 1, "content": text})
        
        # Categorize each page
        categorized_chunks = []
        unknown_chunks = []
        
        for page in pages:
            prompt = f"""Analyze this page content and assign it to the most appropriate category.

Categories:
{categories_list}

Page content:
{page['content'][:2000]}  # Limit to first 2000 chars

Return ONLY a JSON object with this format:
{{
  "category": "category_name",
  "confidence": 0.95,
  "reasoning": "brief explanation"
}}

Use exact category names from the list above, or "unknown" if it doesn't fit any category."""

            try:
                response = llm_agent.generate(prompt, timeout=60)
                
                if response.success:
                    # Parse response
                    response_text = response.content.strip()
                    
                    # Remove markdown code blocks if present
                    if response_text.startswith('```'):
                        lines = response_text.split('\n')
                        if lines[0].startswith('```'):
                            lines = lines[1:]
                        if lines and lines[-1].strip() == '```':
                            lines = lines[:-1]
                        response_text = '\n'.join(lines).strip()
                    
                    result_data = json.loads(response_text)
                    category = result_data.get('category', 'unknown')
                    confidence = result_data.get('confidence', 0.0)
                    
                    # Check if category matches
                    category_names = {cat.name.lower() for cat in chunk_categories}
                    
                    chunk = {
                        "content": page['content'],
                        "category": category,
                        "page_number": page['page_number'],
                        "confidence": confidence
                    }
                    
                    if category.lower() in category_names:
                        categorized_chunks.append(chunk)
                    else:
                        chunk['category'] = 'unknown'
                        unknown_chunks.append(chunk)
                else:
                    # If categorization fails, mark as unknown
                    unknown_chunks.append({
                        "content": page['content'],
                        "category": 'unknown',
                        "page_number": page['page_number'],
                        "confidence": None
                    })
            except Exception as e:
                print(f"Error categorizing page {page['page_number']}: {str(e)}")
                unknown_chunks.append({
                    "content": page['content'],
                    "category": 'unknown',
                    "page_number": page['page_number'],
                    "confidence": None
                })
        
        # Filter unknown chunks if not allowed
        if not allow_uncategorized:
            unknown_chunks = []
        
        # Convert to response models
        chunk_models = [
            ChunkModel(
                content=chunk['content'],
                category=chunk['category'],
                page_number=chunk['page_number'],
                confidence=chunk['confidence']
            )
            for chunk in categorized_chunks
        ]
        
        unknown_chunk_models = [
            ChunkModel(
                content=chunk['content'],
                category=chunk['category'],
                page_number=chunk['page_number'],
                confidence=chunk['confidence']
            )
            for chunk in unknown_chunks
        ]
        
        # Save split result to file
        data_dir = os.path.join(os.path.dirname(__file__), 'data')
        splited_dir = os.path.join(data_dir, 'splited')
        os.makedirs(splited_dir, exist_ok=True)
        
        # Generate filename (without extension)
        base_filename = os.path.splitext(file.filename)[0]
        split_file_path = os.path.join(splited_dir, f"{base_filename}.json")
        
        try:
            split_output = {
                "filename": file.filename,
                "parser_model": parser_model_id,
                "parser_tier": parser_tier,
                "splitter_model": splitter_model_id,
                "splitter_tier": splitter_tier,
                "categories": categories_data,
                "allow_uncategorized": allow_uncategorized,
                "chunks": categorized_chunks,
                "unknown_chunks": unknown_chunks,
                "timestamp": os.path.getctime(file_path) if os.path.exists(file_path) else None
            }
            
            with open(split_file_path, 'w', encoding='utf-8') as f:
                json.dump(split_output, f, indent=2, ensure_ascii=False)
            
            print(f"Split result saved: {split_file_path}")
        except Exception as e:
            print(f"Warning: Failed to save split result: {str(e)}")
        
        return SplitResponse(
            success=True,
            chunks=chunk_models,
            unknown_chunks=unknown_chunk_models,
            filename=file.filename
        )
        
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)


@router.get("/health", response_model=HealthResponse)
async def health_check(config: Config = Depends(get_config)) -> HealthResponse:
    """
    Health check endpoint.
    
    Returns:
        HealthResponse with status and available models
    """
    available_models = config.get_available_models()
    
    # Check if any server is running
    server_running = False
    providers = config.api_providers
    
    if providers:
        first_provider = list(providers.values())[0]
        base_url = first_provider.get('base_url')
        
        if base_url:
            from core.utils import check_server_status
            status = check_server_status(base_url)
            server_running = status.get('running', False)
    
    # Determine status
    if server_running and available_models:
        status = "healthy"
    elif available_models:
        status = "degraded"
    else:
        status = "unhealthy"
    
    return HealthResponse(
        status=status,
        server_running=server_running,
        available_models=available_models
    )


@router.get("/models/check")
async def check_models(config: Config = Depends(get_config)) -> JSONResponse:
    """
    Check which models are configured and available.
    
    Returns detailed information about model availability and configuration.
    """
    import os
    
    print("\n=== MODEL CHECK REQUEST ===")
    
    models_info = []
    
    # Check each model in config
    for model_id, model_config in config.models.items():
        provider = model_config.get('provider')
        provider_config = config.api_providers.get(provider, {})
        
        # Check if API key is set for this provider
        api_key_set = False
        api_key_name = None
        if provider == 'google_studio':
            api_key_name = 'GOOGLE_STUDIO_API_KEY'
            api_key_set = bool(os.getenv('GOOGLE_STUDIO_API_KEY'))
        elif provider == 'poe_api':
            api_key_name = 'POE_API_KEY'
            api_key_set = bool(os.getenv('POE_API_KEY'))
        elif provider == 'lm_studio':
            api_key_name = 'N/A (local)'
            api_key_set = True  # Local, no API key needed
        
        models_info.append({
            'model_id': model_id,
            'name': model_config.get('name', model_id),
            'provider': provider,
            'base_url': provider_config.get('base_url'),
            'api_key_name': api_key_name,
            'api_key_set': api_key_set,
            'available': api_key_set
        })
        
        print(f"  {model_id}: provider={provider}, api_key={api_key_name}, available={api_key_set}")
    
    # Group by provider
    by_provider = {}
    for model in models_info:
        provider = model['provider']
        if provider not in by_provider:
            by_provider[provider] = []
        by_provider[provider].append(model)
    
    print(f"Total models: {len(models_info)}, Available: {len([m for m in models_info if m['available']])}")
    print("===========================\n")
    
    return JSONResponse({
        'success': True,
        'models': models_info,
        'by_provider': by_provider,
        'total_models': len(models_info),
        'available_models': len([m for m in models_info if m['available']])
    })


@router.get("/test-logging")
async def test_logging() -> JSONResponse:
    """Test endpoint to verify logging is working."""
    print("\n" + "="*50)
    print("TEST LOGGING ENDPOINT CALLED")
    print("If you can see this in your terminal, logging is working!")
    print("="*50 + "\n")
    
    import sys
    import os
    
    return JSONResponse({
        'success': True,
        'message': 'Check your backend terminal for log output',
        'python_version': sys.version,
        'cwd': os.getcwd(),
        'stdout_isatty': sys.stdout.isatty()
    })


@router.get("/tier-config")
async def get_tier_config() -> JSONResponse:
    """
    Get tier configuration mappings.
    
    Returns tier-to-model mappings for all features.
    This allows the frontend to dynamically use the correct models for each tier.
    
    Returns:
        JSON response with tier configuration
    """
    from config import TierConfig
    
    return JSONResponse({
        "success": True,
        "config": TierConfig.export_to_json()
    })


@router.get("/raw-ocr/{filename}")
async def get_raw_ocr(filename: str) -> JSONResponse:
    """
    Get raw OCR text file.
    
    Args:
        filename: Name of the file (without .txt extension)
        
    Returns:
        JSON response with raw OCR text
    """
    data_dir = os.path.join(os.path.dirname(__file__), 'data')
    raw_ocr_dir = os.path.join(data_dir, 'raw_ocr')
    file_path = os.path.join(raw_ocr_dir, f"{filename}.txt")
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"Raw OCR file not found: {filename}.txt")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return JSONResponse({
            "success": True,
            "filename": f"{filename}.txt",
            "content": content,
            "size": len(content)
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read file: {str(e)}")


@router.get("/parsed/{filename}")
async def get_parsed_docx(filename: str):
    """
    Get parsed DOCX file.
    
    Args:
        filename: Name of the file (without .docx extension)
        
    Returns:
        DOCX file as download
    """
    from fastapi.responses import FileResponse
    
    data_dir = os.path.join(os.path.dirname(__file__), 'data')
    parsed_dir = os.path.join(data_dir, 'parsed')
    file_path = os.path.join(parsed_dir, f"{filename}.docx")
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"Parsed DOCX file not found: {filename}.docx")
    
    return FileResponse(
        path=file_path,
        media_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        filename=f"{filename}.docx"
    )


@router.get("/list-saved-files")
async def list_saved_files() -> JSONResponse:
    """
    List all saved OCR files.
    
    Returns:
        JSON response with list of available files
    """
    data_dir = os.path.join(os.path.dirname(__file__), 'data')
    raw_ocr_dir = os.path.join(data_dir, 'raw_ocr')
    parsed_dir = os.path.join(data_dir, 'parsed')
    
    files = []
    
    # List raw OCR files
    if os.path.exists(raw_ocr_dir):
        for filename in os.listdir(raw_ocr_dir):
            if filename.endswith('.txt') and filename != '.gitkeep':
                base_name = filename[:-4]  # Remove .txt extension
                file_path = os.path.join(raw_ocr_dir, filename)
                docx_path = os.path.join(parsed_dir, f"{base_name}.docx")
                
                file_info = {
                    "filename": base_name,
                    "raw_ocr": {
                        "exists": True,
                        "path": f"/raw-ocr/{base_name}",
                        "size": os.path.getsize(file_path)
                    },
                    "parsed": {
                        "exists": os.path.exists(docx_path),
                        "path": f"/parsed/{base_name}" if os.path.exists(docx_path) else None,
                        "size": os.path.getsize(docx_path) if os.path.exists(docx_path) else 0
                    },
                    "created_at": os.path.getctime(file_path)
                }
                files.append(file_info)
    
    # Sort by creation time (newest first)
    files.sort(key=lambda x: x['created_at'], reverse=True)
    
    return JSONResponse({
        "success": True,
        "count": len(files),
        "files": files
    })


@router.post("/condition/evaluate")
async def evaluate_condition(
    conditions: str = Form(...),
    previous_result: str = Form(...),
    field_name: str = Form("document_type")
) -> JSONResponse:
    """
    Evaluate conditions against previous workflow result.
    
    This endpoint determines which output path to take based on conditions.
    
    Args:
        conditions: JSON string with condition definitions
        previous_result: JSON string with previous node result
        field_name: Field name to evaluate (default: document_type)
        
    Returns:
        JSON response with matched condition index (or null for else)
    """
    try:
        # Parse conditions
        conditions_data = json.loads(conditions)
        condition_list = [
            Condition(
                operator=ConditionOperator(cond['operator']),
                value=cond.get('value'),
                valueMin=cond.get('valueMin'),
                valueMax=cond.get('valueMax')
            )
            for cond in conditions_data
        ]
        
        # Parse previous result
        result_data = json.loads(previous_result)
        
        # Evaluate conditions
        evaluator = ConditionEvaluator()
        eval_result = evaluator.evaluate_from_previous_result(
            result_data,
            condition_list,
            field_name
        )
        
        if not eval_result.success:
            raise HTTPException(status_code=500, detail=eval_result.error)
        
        return JSONResponse({
            "success": True,
            "matched_index": eval_result.matched_index,
            "is_else": eval_result.matched_index is None
        })
        
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Condition evaluation failed: {str(e)}")


@router.post("/workflow/execute")
async def execute_workflow(
    file: UploadFile = File(...),
    workflow: str = Form(...),
    config: Config = Depends(get_config)
) -> JSONResponse:
    """
    Execute a workflow pipeline.
    
    This endpoint processes a file through multiple steps defined in the workflow.
    Each step can be: parse, classify, extract, or split.
    
    Args:
        file: Uploaded file
        workflow: JSON string with workflow definition
        config: Configuration instance
        
    Returns:
        JSON response with results from each workflow step
    """
    # Parse workflow
    try:
        workflow_data = json.loads(workflow)
        steps = workflow_data.get('steps', [])
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid workflow: {str(e)}")
    
    if not steps:
        raise HTTPException(status_code=400, detail="Workflow must have at least one step")
    
    # Validate file
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file selected")
    
    upload_config = config.upload_config
    allowed_extensions = set(upload_config.get('allowed_extensions', []))
    
    if not allowed_file(file.filename, allowed_extensions):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(allowed_extensions)}"
        )
    
    # Save file
    upload_folder = upload_config.get('folder', 'uploads')
    try:
        file_path = await secure_save_file(file, upload_folder)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")
    
    # Execute workflow steps
    results = []
    previous_result = None
    
    try:
        for step in steps:
            step_type = step.get('type')
            step_tier = step.get('tier', 'Normal')
            step_config = step.get('config', {})
            
            if step_type == 'parse':
                result = await execute_parse_step(file_path, step_tier, step_config, config)
            elif step_type == 'classify':
                result = await execute_classify_step(file_path, step_tier, step_config, config)
            elif step_type == 'extract':
                result = await execute_extract_step(file_path, step_tier, step_config, config)
            elif step_type == 'split':
                result = await execute_split_step(file_path, step_tier, step_config, config)
            else:
                raise HTTPException(status_code=400, detail=f"Unknown step type: {step_type}")
            
            results.append({
                'step': step_type,
                'tier': step_tier,
                'result': result
            })
            
            previous_result = result
    
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                'success': False,
                'error': str(e),
                'completed_steps': results
            }
        )
    
    return JSONResponse(content={
        'success': True,
        'results': results,
        'filename': file.filename
    })


async def execute_parse_step(file_path: str, tier: str, step_config: dict, config: Config):
    """Execute parse step."""
    from config import TierConfig
    model_id = TierConfig.get_parser_model(tier)
    
    ocr_agent = AgentFactory.create_from_config(config, model_id)
    parser = Parser(ocr_agent=ocr_agent)
    
    parse_result = parser.parse(file_path)
    
    if not parse_result.success:
        raise Exception(f"Parse failed: {parse_result.error}")
    
    return {
        'text': parse_result.text,
        'file_type': parse_result.file_type,
        'pages': parse_result.pages
    }


async def execute_classify_step(file_path: str, tier: str, step_config: dict, config: Config):
    """Execute classify step."""
    from config import TierConfig
    
    # Parse document first
    parser_model_id = TierConfig.get_parser_model(tier)
    ocr_agent = AgentFactory.create_from_config(config, parser_model_id)
    parser = Parser(ocr_agent=ocr_agent)
    parse_result = parser.parse(file_path)
    
    if not parse_result.success:
        raise Exception(f"Parse failed: {parse_result.error}")
    
    # Classify
    classifier_model_id = TierConfig.get_classifier_llm_model(tier)
    llm_agent = AgentFactory.create_llm_agent(classifier_model_id)
    classifier = Classifier(agent=llm_agent)
    
    rules = [
        ClassificationRule(
            doc_type=rule['doc_type'],
            description=rule['description']
        )
        for rule in step_config.get('rules', [])
    ]
    
    classify_result = classifier.classify(parse_result.text, rules)
    
    if not classify_result.success:
        raise Exception(f"Classify failed: {classify_result.error}")
    
    return {
        'document_type': classify_result.document_type,
        'confidence': classify_result.confidence,
        'reasoning': classify_result.reasoning
    }


async def execute_extract_step(file_path: str, tier: str, step_config: dict, config: Config):
    """Execute extract step."""
    from config import TierConfig
    
    # Parse document first
    parser_model_id = TierConfig.get_parser_model(tier)
    ocr_agent = AgentFactory.create_from_config(config, parser_model_id)
    parser = Parser(ocr_agent=ocr_agent)
    parse_result = parser.parse(file_path)
    
    if not parse_result.success:
        raise Exception(f"Parse failed: {parse_result.error}")
    
    # Extract
    extractor_model_id = TierConfig.get_extractor_model(tier)
    llm_agent = AgentFactory.create_llm_agent(extractor_model_id)
    extractor = Extractor(agent=llm_agent)
    
    # Build extraction config
    schema_data = step_config.get('schema', {})
    extraction_config = ExtractionConfig(
        target=ExtractionTarget(step_config.get('target', 'document')),
        fields=[
            SchemaField(
                name=field['name'],
                field_type=FieldType(field['type']),
                description=field.get('description', ''),
                required=field.get('required', False)
            )
            for field in schema_data.get('fields', [])
        ]
    )
    
    extract_result = extractor.extract(parse_result.text, extraction_config)
    
    if not extract_result.success:
        raise Exception(f"Extract failed: {extract_result.error}")
    
    return {
        'structured_data': extract_result.structured_data,
        'field_errors': extract_result.field_errors
    }


async def execute_split_step(file_path: str, tier: str, step_config: dict, config: Config):
    """Execute split step."""
    from config import TierConfig
    from functions.splitter import ChunkCategory
    
    # Get models
    parser_model_id = TierConfig.get_parser_model(tier)
    splitter_model_id = TierConfig.get_splitter_model(tier)
    
    # Parse document
    ocr_agent = AgentFactory.create_from_config(config, parser_model_id)
    parser = Parser(ocr_agent=ocr_agent)
    parse_result = parser.parse(file_path)
    
    if not parse_result.success:
        raise Exception(f"Parse failed: {parse_result.error}")
    
    # Split
    vlm_agent = AgentFactory.create_vlm_agent(splitter_model_id)
    splitter = Splitter(agent=vlm_agent)
    
    categories = [
        ChunkCategory(
            name=cat['name'],
            description=cat['description'],
            order=cat.get('order', 0)
        )
        for cat in step_config.get('categories', [])
    ]
    
    split_result = splitter.split(
        file_path,
        categories,
        allow_uncategorized=step_config.get('allow_uncategorized', True)
    )
    
    if not split_result.success:
        raise Exception(f"Split failed: {split_result.error}")
    
    return {
        'chunks': [
            {
                'content': chunk.content,
                'category': chunk.category,
                'page_number': chunk.page_number,
                'confidence': chunk.confidence
            }
            for chunk in split_result.chunks or []
        ],
        'unknown_chunks': [
            {
                'content': chunk.content,
                'category': chunk.category,
                'page_number': chunk.page_number
            }
            for chunk in split_result.unknown_chunks or []
        ]
    }
