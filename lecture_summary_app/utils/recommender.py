def recommend_sources(summary_text, api_key):
    """
    Analyzes the summary to find key topics and searches for high-quality external resources.
    """
    from langchain_google_genai import ChatGoogleGenerativeAI
    from .web_loader import search_web
    llm = ChatGoogleGenerativeAI(model="gemini-flash-latest", google_api_key=api_key)
    
    # 1. Extract Keywords
    prompt = f"Extract 3 main technical topics or keywords from this text for searching academic or documentation resources. Return only the keywords separated by spaces. Text: {summary_text[:1000]}"
    try:
        keywords = llm.invoke(prompt).content
    except Exception as e:
        print(f"Error extracting keywords: {e}")
        keywords = "General Science"

    # 2. Search Web
    # Add 'tutorial', 'documentation', 'university' to favor good sources
    search_query = f"{keywords} tutorial documentation OR site:.ac.jp OR site:.edu"
    results = search_web(search_query, max_results=5)
    
    return results
