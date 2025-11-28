

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from typing import List
from PIL import Image
import io, base64, logging, traceback

from .llm_engine import extract_from_image_b64

logger = logging.getLogger("bajaj_llm_vision")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
logger.addHandler(handler)

app = FastAPI(title="Bajaj Invoice Extractor - LLM Vision")

# Example schema we instruct the LLM to follow exactly.
SCHEMA = {
  "document_id": "string",
  "pages": [
    {
      "page_num": 1,
      "line_items": [
        {"description": "string", "amount": 0.0, "page": 1, "bbox": None, "confidence": 0.0}
      ],
      "sub_totals": [],
      "final_total": 0.0
    }
  ],
  "overall_confidence": 0.0
}

@app.post("/process")
async def process(file: UploadFile = File(...)):
    """
    Accepts single file (image/pdf). For PDFs with multiple pages, PIL will load frames.
    Each page is converted to JPEG then base64 encoded and sent to the LLM.
    """
    contents = await file.read()
    filename = file.filename or "uploaded"

    try:
        pil = Image.open(io.BytesIO(contents))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Cannot open file as image/PIL: {e}")

    # Build list of base64-encoded pages
    pages_b64 = []
    try:
        n_frames = getattr(pil, "n_frames", 1)
        for i in range(n_frames):
            pil.seek(i)
            buf = io.BytesIO()
            pil.convert("RGB").save(buf, format="JPEG", quality=85)
            pages_b64.append(base64.b64encode(buf.getvalue()).decode("utf-8"))
    except Exception:
        # fallback: single image
        buf = io.BytesIO()
        pil.convert("RGB").save(buf, format="JPEG", quality=85)
        pages_b64 = [base64.b64encode(buf.getvalue()).decode("utf-8")]

    # Process each page with the LLM
    document_result = {"document_id": filename, "pages": [], "overall_confidence": 0.0}
    for idx, page_b64 in enumerate(pages_b64, start=1):
        try:
            logger.info("Calling LLM for page %d (approx %d KB)", idx, len(page_b64)//1024)
            schema_for_page = {
                "document_id": filename,
                "pages": [
                    {
                        "page_num": idx,
                        "line_items": [{"description":"string","amount":0.0,"page":idx,"bbox":None,"confidence":0.0}],
                        "sub_totals": [],
                        "final_total": 0.0
                    }
                ],
                "overall_confidence": 0.0
            }
            parsed = extract_from_image_b64(page_b64, schema_for_page, filename)
            # normalized handling: parsed may be a dict containing pages or single-page structure
            if isinstance(parsed, dict) and "pages" in parsed:
                for p in parsed["pages"]:
                    document_result["pages"].append(p)
            else:
                # assume parsed is a page object
                document_result["pages"].append(parsed)
        except Exception as e:
            logger.error("LLM failed for page %d: %s", idx, str(e))
            # append a placeholder page with an error field
            document_result["pages"].append({
                "page_num": idx,
                "line_items": [],
                "sub_totals": [],
                "final_total": None,
                "error": str(e)
            })

    # compute a simple overall confidence if confidences are present
    confs = []
    for p in document_result["pages"]:
        for li in p.get("line_items", []):
            c = li.get("confidence")
            if isinstance(c, (int, float)):
                confs.append(float(c))
    if confs:
        document_result["overall_confidence"] = round(sum(confs)/len(confs), 2)
    else:
        document_result["overall_confidence"] = 0.0

    return JSONResponse(content=document_result)


@app.get("/health")
async def health():
    return {"status": "ok"}
