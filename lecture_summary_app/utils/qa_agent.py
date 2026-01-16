from langchain_google_genai import ChatGoogleGenerativeAI

def initialize_vector_store(text_data_list, api_key):
    """
    In Long Context mode, this function simply aggregates text data.
    We don't need a vector store anymore, but we keep the name for compatibility
    with app.py (or we can return the list itself).
    Returns: A string containing all context formatted for the LLM.
    """
    if not text_data_list:
        return None
        
    full_context = ""
    for item in text_data_list:
        full_context += f"\n\n--- Source: {item['source']} ---\n"
        full_context += item['content']
    
    return full_context

def get_answer(query, context_text, api_key):
    """
    Answers question using the full context directly (Long Context).
    """
    if not context_text:
        return "資料が読み込まれていません。", []

    # Initialize Chat Model
    llm = ChatGoogleGenerativeAI(model="gemini-flash-latest", google_api_key=api_key, temperature=0.1)
    
    # Prompt Construction
    prompt = f"""
    あなたは優秀なAIチューターです。
    以下の【講義資料・参考情報】の全てを前提知識として、ユーザーの質問に答えてください。
    
    【ルール】
    1. 資料に書かれている内容に基づいて回答すること。
    2. 資料にないことは「資料には記載がありません」と正直に伝えること。
    3. 必要に応じて、参照した資料のソース名（Source: ...）を引用して根拠を示すこと。
    
    【講義資料・参考情報】
    {context_text}
    
    【ユーザーの質問】
    {query}
    """
    
    try:
        response = llm.invoke(prompt)
        # In long context mode, citing specific sources programmatically is harder strictly 
        # without RAG's metadata, but the model can reference them in text.
        # We will return an empty list for sources for now, or parse the text if needed.
        # The prompt asks to cite in text.
        return response.content, [] 
    except Exception as e:
        return f"Error generation answer: {str(e)}", []
