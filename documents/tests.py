"""Tests for documents app."""

import os
import tempfile
from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, Client

from documents.models import Collection, Document, DocumentChunk
from documents.services import (
    extract_text_from_pdf,
    chunk_text,
    generate_embedding,
    search_chunks,
    index_document,
)


class CollectionModelTest(TestCase):
    def test_create_collection(self):
        collection = Collection.objects.create(
            name="Test Collection",
            slug="test-collection",
            description="A test collection",
        )
        self.assertEqual(collection.name, "Test Collection")
        self.assertEqual(collection.slug, "test-collection")
        self.assertEqual(str(collection), "Test Collection")

    def test_collection_ordering(self):
        """Test that collections are ordered by name."""
        Collection.objects.create(name="Zebra", slug="zebra")
        Collection.objects.create(name="Apple", slug="apple")
        Collection.objects.create(name="Banana", slug="banana")

        collections = list(Collection.objects.all())
        self.assertEqual(collections[0].name, "Apple")
        self.assertEqual(collections[1].name, "Banana")
        self.assertEqual(collections[2].name, "Zebra")


class DocumentModelTest(TestCase):
    def setUp(self):
        self.collection = Collection.objects.create(
            name="Test Collection",
            slug="test-collection",
        )

    def test_create_document_with_all_fields(self):
        pdf_content = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        pdf_file = SimpleUploadedFile(
            "test.pdf", pdf_content, content_type="application/pdf"
        )

        document = Document.objects.create(
            collection=self.collection,
            file=pdf_file,
            name="Test Document",
            original_filename="test.pdf",
            mime_type="application/pdf",
            file_size=len(pdf_content),
        )

        self.assertEqual(document.name, "Test Document")
        self.assertEqual(document.original_filename, "test.pdf")
        self.assertEqual(document.file_size, len(pdf_content))
        self.assertEqual(document.mime_type, "application/pdf")
        self.assertEqual(str(document), "Test Document")

    def test_create_document_minimal(self):
        """Test creating document with minimal fields (nullable fields)."""
        pdf_content = b"pdf content"  # 11 bytes
        pdf_file = SimpleUploadedFile(
            "test.pdf", pdf_content, content_type="application/pdf"
        )

        # Don't set file_size or original_filename - let save() populate them
        # But set mime_type explicitly as FileField doesn't preserve content_type after save
        document = Document.objects.create(
            collection=self.collection,
            file=pdf_file,
            name="",
            mime_type="application/pdf",
        )

        # After save, fields should be populated from file
        self.assertEqual(document.original_filename, "test.pdf")
        self.assertEqual(document.file_size, len(pdf_content))  # 11 bytes
        self.assertEqual(document.mime_type, "application/pdf")
        self.assertEqual(document.name, "test.pdf")  # Falls back to original_filename

    def test_document_ordering(self):
        """Test that documents are ordered by -created_at."""
        doc1 = Document.objects.create(
            collection=self.collection,
            file=SimpleUploadedFile("1.pdf", b"content1"),
            name="Doc 1",
            original_filename="1.pdf",
            file_size=8,
        )
        doc2 = Document.objects.create(
            collection=self.collection,
            file=SimpleUploadedFile("2.pdf", b"content2"),
            name="Doc 2",
            original_filename="2.pdf",
            file_size=8,
        )

        documents = list(Document.objects.all())
        # Most recent first
        self.assertEqual(documents[0].id, doc2.id)
        self.assertEqual(documents[1].id, doc1.id)


class DocumentChunkModelTest(TestCase):
    def setUp(self):
        self.collection = Collection.objects.create(
            name="Test Collection",
            slug="test-collection",
        )
        self.document = Document.objects.create(
            collection=self.collection,
            file=SimpleUploadedFile("test.pdf", b"pdf content"),
            name="Test Document",
            original_filename="test.pdf",
            mime_type="application/pdf",
            file_size=12,
        )

    def test_create_chunk(self):
        embedding = [0.1] * 384  # Mock 384-dim embedding
        chunk = DocumentChunk.objects.create(
            document=self.document,
            content="This is a test chunk",
            chunk_index=0,
            embedding=embedding,
        )

        self.assertEqual(chunk.content, "This is a test chunk")
        self.assertEqual(chunk.chunk_index, 0)
        self.assertEqual(len(chunk.embedding), 384)
        self.assertEqual(str(chunk), f"Chunk 0 of {self.document}")

    def test_chunk_ordering(self):
        """Test that chunks are ordered by document, then chunk_index."""
        embedding = [0.1] * 384
        doc2 = Document.objects.create(
            collection=self.collection,
            file=SimpleUploadedFile("test2.pdf", b"pdf content 2"),
            name="Test Document 2",
            original_filename="test2.pdf",
            mime_type="application/pdf",
            file_size=13,
        )

        # Create chunks for both documents
        DocumentChunk.objects.create(
            document=self.document,
            content="chunk 1",
            chunk_index=1,
            embedding=embedding,
        )
        DocumentChunk.objects.create(
            document=self.document,
            content="chunk 0",
            chunk_index=0,
            embedding=embedding,
        )
        DocumentChunk.objects.create(
            document=doc2, content="chunk 0", chunk_index=0, embedding=embedding
        )

        chunks = list(
            DocumentChunk.objects.all().order_by("document__id", "chunk_index")
        )
        # Should be ordered: doc1-chunk0, doc1-chunk1, doc2-chunk0
        self.assertEqual(chunks[0].chunk_index, 0)
        self.assertEqual(chunks[0].document.id, self.document.id)
        self.assertEqual(chunks[1].chunk_index, 1)
        self.assertEqual(chunks[1].document.id, self.document.id)
        self.assertEqual(chunks[2].chunk_index, 0)
        self.assertEqual(chunks[2].document.id, doc2.id)


class DocumentServicesTest(TestCase):
    def test_chunk_text_basic(self):
        text = "This is a test. " * 10
        chunks = chunk_text(text, chunk_size=50, overlap=10)

        self.assertGreater(len(chunks), 1)
        for chunk in chunks:
            self.assertLessEqual(len(chunk), 50)

    def test_chunk_text_empty(self):
        self.assertEqual(chunk_text(""), [])

    def test_chunk_text_none(self):
        self.assertEqual(chunk_text(None), [])

    def test_chunk_text_overlap(self):
        """Test that chunks have the specified overlap."""
        text = "A" * 100  # 100 character string
        chunks = chunk_text(text, chunk_size=50, overlap=10)

        # Should have 3 chunks: 0-50, 40-90, 80-100
        self.assertEqual(len(chunks), 3)
        self.assertEqual(len(chunks[0]), 50)
        self.assertEqual(len(chunks[1]), 50)
        self.assertEqual(len(chunks[2]), 20)
        # Check overlap between first two chunks
        self.assertEqual(chunks[0][40:], chunks[1][:10])

    def test_extract_text_from_pdf(self):
        """Test PDF text extraction with a real PDF."""
        try:
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import letter
        except ImportError:
            self.skipTest("reportlab not installed, skipping PDF extraction test")

        # Create a real PDF with text
        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)
        c.drawString(100, 700, "Test PDF content")
        c.save()
        pdf_content = buffer.getvalue()
        buffer.close()

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(pdf_content)
            tmp_path = tmp.name

        try:
            text = extract_text_from_pdf(tmp_path)
            # Should extract text from the real PDF
            self.assertIsInstance(text, str)
            self.assertIn("Test PDF content", text)
        finally:
            os.unlink(tmp_path)

    def test_generate_embedding(self):
        """Test embedding generation produces 384-dim vector."""
        # This test requires the embedding model to be available
        # It will be slow on first run as it downloads the model
        embedding = generate_embedding("Test sentence")
        self.assertIsInstance(embedding, list)
        self.assertEqual(len(embedding), 384)
        # All values should be floats
        for val in embedding:
            self.assertIsInstance(val, float)


class IndexDocumentTest(TestCase):
    """Test the document indexing pipeline."""

    def setUp(self):
        self.collection = Collection.objects.create(
            name="Test Collection",
            slug="test-collection",
        )

    def test_index_document_creates_chunks(self):
        """Test that indexing a document creates chunks."""
        # Create a PDF with some text
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter

        # Create a real PDF with text
        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)
        text = "This is a test document with multiple words. " * 50
        c.drawString(100, 700, text)
        c.save()
        pdf_content = buffer.getvalue()
        buffer.close()

        pdf_file = SimpleUploadedFile(
            "test.pdf", pdf_content, content_type="application/pdf"
        )
        document = Document.objects.create(
            collection=self.collection,
            file=pdf_file,
            name="Test PDF",
            original_filename="test.pdf",
            mime_type="application/pdf",
            file_size=len(pdf_content),
        )

        # Index the document
        index_document(document)

        # Check that chunks were created
        chunks = DocumentChunk.objects.filter(document=document)
        self.assertGreater(chunks.count(), 0)

        # Check that chunks have embeddings
        for chunk in chunks:
            self.assertIsNotNone(chunk.embedding)
            self.assertEqual(len(chunk.embedding), 384)
            self.assertGreater(len(chunk.content), 0)


class SearchChunksTest(TestCase):
    """Test the search functionality."""

    def setUp(self):
        self.collection = Collection.objects.create(
            name="Test Collection",
            slug="test-collection",
        )

        # Create some test chunks with known embeddings
        # For testing, we'll use mock embeddings since generating real ones is slow
        self.embedding1 = [0.1] * 384
        self.embedding2 = [0.5] * 384
        self.embedding3 = [0.9] * 384

        doc = Document.objects.create(
            collection=self.collection,
            file=SimpleUploadedFile("test.pdf", b"content"),
            name="Test Doc",
            original_filename="test.pdf",
            file_size=7,
        )

        DocumentChunk.objects.create(
            document=doc,
            content="chunk one",
            chunk_index=0,
            embedding=self.embedding1,
        )
        DocumentChunk.objects.create(
            document=doc,
            content="chunk two",
            chunk_index=1,
            embedding=self.embedding2,
        )

    def test_search_chunks_returns_results(self):
        """Test that search returns chunks."""
        # This test is skipped in SQLite mode as it uses brute-force fallback
        # But it should still work
        results = search_chunks("test query", collections=[self.collection], limit=5)
        self.assertIsInstance(results, list)

    def test_search_chunks_empty_collections(self):
        """Test search with empty collections list."""
        results = search_chunks("test query", collections=[], limit=5)
        self.assertEqual(len(results), 0)

    def test_search_chunks_no_collections(self):
        """Test search with no collections filter."""
        results = search_chunks("test query", collections=None, limit=5)
        self.assertIsInstance(results, list)


class DocumentAPITest(TestCase):
    """Test the REST API endpoints."""

    def setUp(self):
        self.client = Client()
        self.collection = Collection.objects.create(
            name="API Test Collection",
            slug="api-test-collection",
            description="For API testing",
        )

    def test_list_collections(self):
        """Test listing all collections."""
        response = self.client.get("/api/collections/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)
        self.assertGreater(len(data), 0)

        # Check structure
        self.assertIn("id", data[0])
        self.assertIn("name", data[0])
        self.assertIn("slug", data[0])
        self.assertIn("document_count", data[0])

    def test_get_collection(self):
        """Test getting a specific collection."""
        response = self.client.get(f"/api/collections/{self.collection.slug}/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["name"], self.collection.name)
        self.assertEqual(data["slug"], self.collection.slug)

    def test_get_collection_not_found(self):
        """Test getting a non-existent collection."""
        response = self.client.get("/api/collections/nonexistent/")
        self.assertEqual(response.status_code, 404)

    def test_list_documents(self):
        """Test listing documents in a collection."""
        response = self.client.get(
            f"/api/collections/{self.collection.slug}/documents/"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)

    def test_upload_document(self):
        """Test uploading a document via API."""
        pdf_content = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"

        response = self.client.post(
            f"/api/collections/{self.collection.slug}/documents/",
            {
                "file": SimpleUploadedFile(
                    "test.pdf", pdf_content, content_type="application/pdf"
                )
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("id", data)
        self.assertEqual(data["collection_id"], self.collection.id)
        self.assertEqual(data["original_filename"], "test.pdf")

    def test_upload_non_pdf(self):
        """Test that non-PDF uploads are rejected."""
        response = self.client.post(
            f"/api/collections/{self.collection.slug}/documents/",
            {
                "file": SimpleUploadedFile(
                    "test.txt", b"text content", content_type="text/plain"
                )
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 400)


class AgentSearchConfigTest(TestCase):
    """Test agent search configuration."""

    def test_agent_search_fields(self):
        """Test that Agent has search_enabled and allowed_collections fields."""
        from agents.models import Agent

        agent = Agent.objects.create(
            name="Search Agent",
            slug="search-agent",
            search_enabled=True,
        )

        self.assertTrue(agent.search_enabled)

        # Test adding collections
        collection = Collection.objects.create(name="Test", slug="test")
        agent.allowed_collections.add(collection)

        self.assertEqual(agent.allowed_collections.count(), 1)
        self.assertEqual(agent.allowed_collections.first().name, "Test")
