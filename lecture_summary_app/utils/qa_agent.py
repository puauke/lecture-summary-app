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

def get_answer(query, context_text, api_key, ai_provider="gemini"):
    """
    長いコンテキストを使用してユーザーの質問に回答（RAG不要）
    
    Args:
        query: ユーザーの質問
        context_text: 講義資料の全コンテキスト
        api_key: Google Gemini APIキー or OpenAI APIキー
        ai_provider: 'gemini' or 'openai'
    
    Returns:
        (回答テキスト, ソースリスト) のタプル
    """
    import os
    
    if not context_text:
        return "❌ 資料が読み込まれていません。サイドバーから資料をアップロードしてください。", []

    # 環境変数に確実にAPIキーを設定
    if ai_provider == "openai":
        os.environ["OPENAI_API_KEY"] = api_key
    else:
        os.environ["GOOGLE_API_KEY"] = api_key

    # Initialize Chat Model with optimized settings
    if ai_provider == "openai":
        from langchain_openai import ChatOpenAI
        llm = ChatOpenAI(model="gpt-3.5-turbo", openai_api_key=api_key, temperature=0.1)
    else:
        from langchain_google_genai import ChatGoogleGenerativeAI
        # 環境変数から自動的にAPIキーを読み取る
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash", 
            temperature=0.1
        )
    
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
        # Long Context モードでは、ソースの引用はテキスト内で行う
        return response.content, [] 
    except Exception as e:
        error_message = f"❌ 回答生成エラー: {type(e).__name__}"
        if "RESOURCE_EXHAUSTED" in str(e) or "429" in str(e):
            error_message += " - APIのレート制限に達しました。少し待ってから再試行してください。"
        else:
            error_message += f" - {str(e)[:100]}"
        return error_message, []
