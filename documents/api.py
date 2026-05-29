"""REST API for document collections and documents."""

from django.shortcuts import get_object_or_404
from ninja import NinjaAPI, Schema
from ninja.files import UploadedFile

from documents.models import Collection, Document


api = NinjaAPI(version="1.0.0", urls_namespace="documents_api")


# Schemas


class CollectionOut(Schema):
    id: int
    name: str
    slug: str
    description: str | None = None
    document_count: int
    created_at: str
    updated_at: str


class CollectionIn(Schema):
    name: str
    slug: str | None = None
    description: str | None = None


class DocumentOut(Schema):
    id: int
    collection_id: int
    name: str
    original_filename: str
    mime_type: str | None = None
    file_size: int
    chunk_count: int
    created_at: str
    updated_at: str


class DocumentIn(Schema):
    name: str | None = None
    metadata: dict = {}


# Endpoints


@api.get("/collections/", response=list[CollectionOut])
def list_collections(request):
    """List all document collections."""
    collections = Collection.objects.all().prefetch_related("documents")
    return [
        CollectionOut(
            id=c.id,
            name=c.name,
            slug=c.slug,
            description=c.description if c.description else None,
            document_count=c.documents.count(),
            created_at=c.created_at.isoformat(),
            updated_at=c.updated_at.isoformat(),
        )
        for c in collections
    ]


@api.get("/collections/{collection_slug}/", response=CollectionOut)
def get_collection(request, collection_slug: str):
    """Get details for a specific collection."""
    collection = get_object_or_404(Collection, slug=collection_slug)
    return CollectionOut(
        id=collection.id,
        name=collection.name,
        slug=collection.slug,
        description=collection.description if collection.description else None,
        document_count=collection.documents.count(),
        created_at=collection.created_at.isoformat(),
        updated_at=collection.updated_at.isoformat(),
    )


@api.get("/collections/{collection_slug}/documents/", response=list[DocumentOut])
def list_documents(request, collection_slug: str):
    """List all documents in a collection."""
    collection = get_object_or_404(Collection, slug=collection_slug)
    documents = collection.documents.all().prefetch_related("chunks")
    return [
        DocumentOut(
            id=d.id,
            collection_id=d.collection_id,
            name=d.name,
            original_filename=d.original_filename,
            mime_type=d.mime_type if d.mime_type else None,
            file_size=d.file_size,
            chunk_count=d.chunks.count(),
            created_at=d.created_at.isoformat(),
            updated_at=d.updated_at.isoformat(),
        )
        for d in documents
    ]


@api.get(
    "/collections/{collection_slug}/documents/{document_id}/", response=DocumentOut
)
def get_document(request, collection_slug: str, document_id: int):
    """Get details for a specific document."""
    collection = get_object_or_404(Collection, slug=collection_slug)
    document = get_object_or_404(Document, id=document_id, collection=collection)
    return DocumentOut(
        id=document.id,
        collection_id=document.collection_id,
        name=document.name,
        original_filename=document.original_filename,
        mime_type=document.mime_type if document.mime_type else None,
        file_size=document.file_size,
        chunk_count=document.chunks.count(),
        created_at=document.created_at.isoformat(),
        updated_at=document.updated_at.isoformat(),
    )


@api.post("/collections/{collection_slug}/documents/", response=DocumentOut)
def upload_document(
    request,
    collection_slug: str,
    file: UploadedFile,
    name: str | None = None,
    metadata: dict = {},
):
    """Upload a document to a collection.

    Only accepts PDF files. Returns the created document details.
    """
    from django.http import HttpResponseBadRequest

    collection = get_object_or_404(Collection, slug=collection_slug)

    # Validate file is a PDF
    content_type = getattr(file, "content_type", "").lower()
    file_name = file.name.lower()

    if not (content_type == "application/pdf" or file_name.endswith(".pdf")):
        return HttpResponseBadRequest("Only PDF files are allowed")

    try:
        # Create the document
        document = Document.objects.create(
            collection=collection,
            file=file,
            name=name or "",
            original_filename=file.name,
            mime_type=content_type,
            file_size=file.size,
            metadata=metadata,
        )

        return DocumentOut(
            id=document.id,
            collection_id=document.collection_id,
            name=document.name,
            original_filename=document.original_filename,
            mime_type=document.mime_type if document.mime_type else None,
            file_size=document.file_size if document.file_size else 0,
            chunk_count=document.chunks.count(),  # Fetch from DB
            created_at=document.created_at.isoformat(),
            updated_at=document.updated_at.isoformat(),
        )
    except Exception as e:
        return HttpResponseBadRequest(f"Failed to upload document: {e}")
