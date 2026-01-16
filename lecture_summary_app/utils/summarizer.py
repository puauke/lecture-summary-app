def generate_summary(text_data_list, api_key, output_language="ja", ai_provider="gemini"):
    """
    Generates a summary from a list of text data.
    text_data_list: List of dicts with 'content' and 'source'.
    output_language: 'ja' for Japanese, 'en' for English, etc.
    ai_provider: 'gemini' or 'openai'
    """
    import os
    
    # 環境変数に確実にAPIキーを設定
    if ai_provider == "openai":
        os.environ["OPENAI_API_KEY"] = api_key
    else:
        os.environ["GOOGLE_API_KEY"] = api_key
    
    # Lazy imports to prevent startup errors
    if ai_provider == "openai":
        from langchain_openai import ChatOpenAI
        llm = ChatOpenAI(model="gpt-3.5-turbo", openai_api_key=api_key, temperature=0.7)
    else:
        from langchain_google_genai import ChatGoogleGenerativeAI
        # Geminiの最新モデル名（temperature設定で高速化）
        # APIキーを明示的に渡す
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash-exp",  # 最新の高速モデル
            google_api_key=api_key,  # APIキーを明示的に渡す
            temperature=0.3,  # 低温度で高速化と一貫性向上
            max_tokens=4096   # トークン数制限で高速化
        )
    
    if not text_data_list:
        return {"summary": "No content to summarize.", "integration": "No content available."}

    # 言語設定
    language_instruction = {
        "ja": "すべての出力は日本語で記述してください。",
        "en": "Please write all output in English."
    }.get(output_language, "すべての出力は日本語で記述してください。")

    # Combine all text content
    full_text = ""
    for item in text_data_list:
        full_text += f"\n\n--- Source: {item['source']} ---\n"
        full_text += item['content']

    # LLM is already initialized above based on ai_provider

    # 1. Generate Summary（プロンプト最適化で高速化）
    summary_prompt = f"""
    {language_instruction}
    
    複数の講義資料を統合し、重複を整理して体系的な学習ノートを作成してください。
    
    【必須要件】
    1. 同じトピックは統合して1つにまとめる
    2. 共通テーマで見出しを作成
    3. すべての重要情報を含める
    4. 各セクションに出典を明記: `[出典: ファイル名]`
    5. LaTeX数式を保持: $E=mc^2$, $\\\\frac{{d}}{{dx}}$
    
    【出力形式】
    # [タイトル]
    
    ## 1. [トピック名]
    - 詳細解説
    - 具体例
    `[出典: ファイル名]`
    
    ## 📚 重要用語集
    - 用語: 定義
    
    【資料】
    {full_text}
    """
    
    import time
    max_retries = 3  # リトライ回数削減（高速化）
    retry_delay = 10  # 10秒待機（高速化）
    
    summary_result = None
    
    # Generate Summary
    print("📝 要約を生成中...")
    for attempt in range(max_retries):
        try:
            response = llm.invoke(summary_prompt)
            summary_result = response.content
            print("✅ 要約生成完了")
            break
        except Exception as e:
            error_str = str(e)
            if "RESOURCE_EXHAUSTED" in error_str or "429" in error_str or "TOO_MANY_REQUESTS" in error_str:
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (attempt + 1)
                    print(f"⏳ レート制限: {wait_time}秒待機中... (試行 {attempt+1}/{max_retries})")
                    time.sleep(wait_time)
                    continue
                else:
                    summary_result = f"⚠️ 要約生成エラー: APIのレート制限に達しました。30秒後に再試行してください。"
            else:
                summary_result = f"⚠️ 要約生成エラー: {type(e).__name__} - {str(e)[:100]}"
            break
    
    if not summary_result:
        summary_result = "⚠️ 要約生成エラーが発生しました"
    
    # 2. Generate Integration Summary (まとめ) - 待機時間なし（高速化）
    integration_prompt = f"""
    {language_instruction}
    
    複数の資料から最重要ポイントと全体の流れをまとめてください。
    
    【必須要件】
    1. 最も重要な3~5つのポイントを明確に
    2. 各資料の関係性と流れを示す
    3. 出典を明記: `[出典: ファイル名]`
    
    【出力形式】
    # 📌 全体まとめ
    
    ## 【最重要ポイント】
    - ポイント1 `[出典: ファイル名]`
    - ポイント2 `[出典: ファイル名]`
    
    ## 【全体の流れ】
    [資料全体の流れを簡潔に説明]
    
    ## 【実践的応用】
    [学んだことの活用方法]
    
    【資料】
    {full_text[:5000]}
    """
    
    integration_result = None
    
    # Generate Integration Summary
    print("📋 まとめを生成中...")
    for attempt in range(max_retries):
        try:
            response = llm.invoke(integration_prompt)
            integration_result = response.content
            print("✅ まとめ生成完了")
            break
        except Exception as e:
            error_str = str(e)
            if "RESOURCE_EXHAUSTED" in error_str or "429" in error_str or "TOO_MANY_REQUESTS" in error_str:
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (attempt + 1)
                    print(f"⏳ レート制限: {wait_time}秒待機中... (試行 {attempt+1}/{max_retries})")
                    time.sleep(wait_time)
                    continue
                else:
                    integration_result = f"⚠️ まとめ生成エラー: APIのレート制限に達しました。30秒後に再試行してください。"
            else:
                integration_result = f"⚠️ まとめ生成エラー: {type(e).__name__} - {str(e)[:100]}"
            break
    
    if not integration_result:
        integration_result = "⚠️ まとめ生成エラーが発生しました"
    
    return {
        "summary": summary_result or "エラーが発生しました",
        "integration": integration_result or "エラーが発生しました"
    }

