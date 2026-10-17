"""Single public router for the integrated Secure RAG capability.

The application mounts this router at ``/api/v1/rag``. Child modules therefore
declare only paths relative to that stable integration boundary.
"""

from fastapi import APIRouter

from app.rag.api import documents, query, rag


router = APIRouter()
router.include_router(rag.router)
router.include_router(query.router)
router.include_router(documents.router)
