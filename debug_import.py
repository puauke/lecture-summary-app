try:
    from langchain.chains.summarize import load_summarize_chain
    print("SUCCESS: from langchain.chains.summarize import load_summarize_chain")
except ImportError as e:
    print(f"FAILED: langchain.chains.summarize -> {e}")

try:
    from langchain.chains import load_summarize_chain
    print("SUCCESS: from langchain.chains import load_summarize_chain")
except ImportError as e:
    print(f"FAILED: langchain.chains -> {e}")

import langchain
print(f"LangChain Version: {langchain.__version__}")
