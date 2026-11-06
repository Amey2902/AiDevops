from django.core.management.base import BaseCommand
from core.rag.knowledge_manager import get_knowledge_manager
from core.rag.supabase_vector_store import SupabaseVectorStore

class Command(BaseCommand):
    help = "Syncs runbooks and embeddings into Supabase pgvector database"

    def handle(self, *args, **options):
        self.stdout.write("Connecting to Supabase Vector Store...")
        supabase = SupabaseVectorStore()

        if not supabase.is_configured():
            self.stdout.write(self.style.ERROR("Supabase credentials not configured in .env"))
            return

        km = get_knowledge_manager()
        km.ingest_all()

        chunks = km.vector_store.chunks
        embeddings = km.vector_store.embeddings

        self.stdout.write(f"Preparing {len(chunks)} runbook chunks for upload to Supabase...")
        uploaded = supabase.upload_chunks(chunks, embeddings)

        if uploaded > 0:
            self.stdout.write(self.style.SUCCESS(f"Successfully uploaded {uploaded} chunks to Supabase!"))
            # Test search
            q_emb = km.embedding_provider.embed_query("container terminated exit code 137 oom")
            res = supabase.semantic_search(q_emb, top_k=2)
            self.stdout.write(f"Supabase RPC Semantic Search Results: {len(res)} matches found")
            for r in res:
                self.stdout.write(f" - [{r.get('similarity_score')}] {r.get('title')}")
        else:
            self.stdout.write(self.style.WARNING("Upload returned 0. Ensure table 'runbook_embeddings' is created in Supabase."))

