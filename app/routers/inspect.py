from fastapi import APIRouter, Request, UploadFile, File, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from typing import List, Optional
from app.services.ocr import perform_ocr
from app.services.search import find_marking_documents
from app.services.datasheet import fetch_and_extract_marking_sections
from app.services.parser import build_marking_spec_from_sections
from app.services.comparator import compare_marking_to_spec

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@router.post("/inspect", response_class=HTMLResponse)
async def inspect(
    request: Request,
    files: List[UploadFile] = File(...),
    part_number: str = Form(...),
    preferred_url: Optional[str] = Form(None),
):
    ocr_texts = []
    for f in files:
        image_bytes = await f.read()
        ocr_result = perform_ocr(image_bytes)
        ocr_texts.append({
            "filename": f.filename,
            "text": ocr_result.text,
            "engine": ocr_result.engine,
            "preprocessing": ocr_result.preprocessing_variant,
        })

    consolidated_text = "\n".join([o["text"] for o in ocr_texts])

    search_results = await find_marking_documents(part_number, preferred_url)
    sections = await fetch_and_extract_marking_sections(search_results)

    marking_spec = build_marking_spec_from_sections(part_number, sections)

    comparison = compare_marking_to_spec(consolidated_text, marking_spec)

    return templates.TemplateResponse(
        "result.html",
        {
            "request": request,
            "part_number": part_number,
            "ocr_texts": ocr_texts,
            "search_results": search_results,
            "sections": sections,
            "marking_spec": marking_spec,
            "comparison": comparison,
        },
    )
