from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.text_splitter import CharacterTextSplitter
from langchain.schema import Document

class KnowledgeService:
    def __init__(self):
        # Initialize embeddings (using local model to avoid API costs for embeddings if possible, or use OpenAI)
        # For this example, we use a small local model 'all-MiniLM-L6-v2' (compatible with sentence-transformers 2.2.2)
        try:
            self.embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
            
            # Mock Data for Technical Support
            text_data = [
                "To reset your router, press and hold the reset button for 10 seconds.",
                "Error 404 indicates the page was not found. Check the URL.",
                "The blue light indicates the device is connected to Wi-Fi.",
                "If the screen is black, check the power cable.",
                "Update firmware by going to Settings > General > Software Update."
            ]
            
            documents = [Document(page_content=text) for text in text_data]
            text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
            docs = text_splitter.split_documents(documents)
            
            self.db = FAISS.from_documents(docs, self.embeddings)
        except Exception as e:
            print(f"Failed to init KnowledgeService: {e}")
            self.db = None

    def search_knowledge(self, query: str) -> str:
        if not self.db:
            return "Knowledge base unavailable."
        
        try:
            # Similarity search
            docs = self.db.similarity_search(query, k=1)
            if docs:
                return docs[0].page_content
            return "No relevant information found."
        except Exception as e:
            return f"Error searching knowledge base: {str(e)}"
