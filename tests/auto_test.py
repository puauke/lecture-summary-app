import os
import sys
import time

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'lecture_summary_app')))

from utils import summarizer, qa_agent
from dotenv import load_dotenv

# Load Env
load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")

if not api_key:
    print("❌ ERROR: API Key not found. Please set GOOGLE_API_KEY in .env or environment.")
    # For testing, we might need to ask user, but let's assume they set it in UI -> processed to env vars? 
    # Actually ui sets it in os.environ. We need to mock that if running standalone.
    # We will ask user to check .env or we'll fail.
    # Let's try to mock it if passed as arg? No, simpler to just start.
    print("Skipping test requiring API key if not present.")
else:
    print(f"✅ API Key found: {api_key[:5]}...")

def test_summary():
    print("\n--- Testing Summary ---")
    dummy_text = [{"content": "AIは人工知能のことです。機械学習はAIの一部です。", "source": "test_doc_1"}]
    try:
        start = time.time()
        summary = summarizer.generate_summary(dummy_text, api_key)
        print(f"✅ Summary generated in {time.time() - start:.2f}s")
        print(f"Sample: {summary[:50]}...")
    except Exception as e:
        print(f"❌ Summary Failed: {e}")

def test_qa_agent_initialization():
    print("\n--- Testing QA Agent (Vector Store) ---")
    # Generate enough text to force batching if batch size is small
    dummy_text = [{"content": f"これはテスト用の文章です。{i}行目。重要な情報はここにあります。", "source": f"doc_{i}"} for i in range(10)]
    
    try:
        start = time.time()
        vector_store = qa_agent.initialize_vector_store(dummy_text, api_key)
        print(f"✅ Vector Store initialized in {time.time() - start:.2f}s")
        return vector_store
    except Exception as e:
        print(f"❌ Initialization Failed: {e}")
        return None

def test_qa_answering(vector_store):
    print("\n--- Testing QA Answering ---")
    if not vector_store:
        print("Skipping QA test (No vector store)")
        return
    
    try:
        start = time.time()
        ans, sources = qa_agent.get_answer("重要な情報はどこ？", vector_store, api_key)
        print(f"✅ Answer generated in {time.time() - start:.2f}s")
        print(f"Answer: {ans}")
        print(f"Sources: {sources}")
    except Exception as e:
        print(f"❌ Answering Failed: {e}")

if __name__ == "__main__":
    if api_key:
        test_summary()
        vs = test_qa_agent_initialization()
        test_qa_answering(vs)
    else:
        print("Please provide API Key to run tests.")
