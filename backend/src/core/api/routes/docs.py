# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query

from src.common.context_vars.user_context import get_user_laui
from src.common.logger.logger import log_info

docs_router = APIRouter()

DOCS_DIR = Path(__file__).resolve().parents[5] / "docs"
AI_PROMPTS_DIR = Path(__file__).resolve().parents[5] / "config" / "AI"


@docs_router.get("/list")
def list_docs() -> dict:
    """List all available documentation and AI prompt files."""
    log_info("api", "docs_router", "list_docs", f"user={get_user_laui()} payload={{}}")
    docs = sorted(str(p.relative_to(DOCS_DIR)) for p in DOCS_DIR.rglob("*.md"))
    ai_prompts = sorted(
        str(p.relative_to(AI_PROMPTS_DIR)) for p in AI_PROMPTS_DIR.iterdir() if p.is_file()
    )
    return {"docs": docs, "ai_prompts": ai_prompts}


@docs_router.get("/get")
def get_doc(
    path: str = Query(..., description="Relative path returned by list_docs"),
    category: str = Query(
        "docs", description="'docs' for platform docs, 'ai_prompts' for /config/AI/ files"
    ),
) -> dict:
    """Read a documentation or AI prompt file by its relative path."""
    log_info(
        "api",
        "docs_router",
        "get_doc",
        f"user={get_user_laui()} payload={{path={path}, category={category}}}",
    )
    base = DOCS_DIR if category == "docs" else AI_PROMPTS_DIR
    resolved = (base / path).resolve()
    if not str(resolved).startswith(str(base.resolve())):
        raise HTTPException(status_code=400, detail="Invalid path")
    if not resolved.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {path}")
    return {"path": path, "content": resolved.read_text(encoding="utf-8")}
