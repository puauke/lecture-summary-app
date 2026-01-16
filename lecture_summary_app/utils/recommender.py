def recommend_sources(summary_text, api_key, skip_if_not_found=True, ai_provider="gemini"):
    """
    Analyzes the summary to find key topics and searches for high-quality external resources.
    skip_if_not_found: Trueの場合、見つからなければ空リストを返す（無理に探さない）
    ai_provider: 'gemini' or 'openai'
    """
    from .web_loader import search_web
    
    if ai_provider == "openai":
        from langchain_openai import ChatOpenAI
        llm = ChatOpenAI(model="gpt-3.5-turbo", openai_api_key=api_key, temperature=0.7)
    else:
        from langchain_google_genai import ChatGoogleGenerativeAI
        llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=api_key)
    
    # 1. Extract Keywords
    prompt = f"""
    以下のテキストから、学術的な資料やドキュメントを検索するための重要なキーワード3つを抽出してください。
    キーワードのみをスペース区切りで返してください。
    
    テキスト: {summary_text[:1000]}
    """
    
    try:
        response = llm.invoke(prompt)
        keywords = response.content.strip()
        print(f"🔍 抽出されたキーワード: {keywords}")
    except Exception as e:
        print(f"⚠️ キーワード抽出エラー: {e}")
        if skip_if_not_found:
            return []  # エラー時は空リストを返す
        keywords = summary_text[:100] if summary_text else "学習 資料 チュートリアル"

    # 2. Search Web (1回のみ)
    try:
        # 高品質なソースを優先する検索クエリ
        search_query = f"{keywords} tutorial documentation OR site:.ac.jp OR site:.edu OR site:wikipedia"
        print(f"🌐 Web検索中: {search_query}")
        results = search_web(search_query, max_results=5)
        
        if results and len(results) > 0:
            print(f"✅ {len(results)}件の関連資料を発見")
            return results
        else:
            print("ℹ️ 関連資料が見つかりませんでした")
            if skip_if_not_found:
                return []  # 見つからなければ空リストを返す
            else:
                return [{
                    "title": "📚 関連資料が見つかりませんでした",
                    "href": "https://www.google.com/search?q=" + keywords.replace(" ", "+"),
                    "body": f"「{keywords}」でGoogle検索してみてください。"
                }]
    except Exception as e:
        print(f"❌ Web検索エラー: {e}")
        return []  # エラー時は空リスト

def manual_search(query, max_results=5):
    """
    ユーザーが手動で関連資料を検索する機能
    """
    from .web_loader import search_web
    
    try:
        print(f"🔍 手動検索: {query}")
        # 安全な検索クエリに変換
        safe_query = query + " site:.ac.jp OR site:.edu OR site:wikipedia OR tutorial"
        results = search_web(safe_query, max_results=max_results)
        
        if results and len(results) > 0:
            print(f"✅ {len(results)}件の資料を発見")
            return results
        else:
            return [{
                "title": "検索結果なし",
                "href": f"https://www.google.com/search?q={query.replace(' ', '+')}",
                "body": f"「{query}」の検索結果が見つかりませんでした。Googleで検索してみてください。"
            }]
    except Exception as e:
        print(f"❌ 検索エラー: {e}")
        return [{
            "title": "検索エラー",
            "href": "https://www.google.com",
            "body": f"エラーが発生しました: {str(e)}"
        }]
