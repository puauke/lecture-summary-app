def generate_summary(text_data_list, api_key):
    """
    Generates a summary from a list of text data.
    text_data_list: List of dicts with 'content' and 'source'.
    """
    # Lazy imports to prevent startup errors
    from langchain_google_genai import ChatGoogleGenerativeAI
    
    if not text_data_list:
        return {"summary": "No content to summarize.", "integration": "No content available."}

    # Combine all text content
    full_text = ""
    for item in text_data_list:
        full_text += f"\n\n--- Source: {item['source']} ---\n"
        full_text += item['content']

    llm = ChatGoogleGenerativeAI(model="gemini-flash-latest", google_api_key=api_key)

    # 1. Generate Summary
    summary_prompt = f"""
    あなたは「講義資料の統合マスター」です。
    提供された複数の資料（レジュメ、Web記事など）の内容を完全に統合し、
    「重複を整理」して「体系的」にまとめた、最強の学習ノートを作成してください。
    
    【重要事項】
    1. **情報の統合**: ファイルAとファイルBで同じトピックを扱っている場合は、内容を統合して一つの項目にまとめること。バラバラに要約してはいけません。
    2. **構造化**: 大見出し・小見出しを使い、論理的な構成にすること。
    3. **網羅性**: どの資料に載っていた重要な定義や例も漏らさないこと。
    4. **自己完結**: 元の資料を見なくても、このノートだけで学習が完結するように詳しく書くこと。
    
    【出力フォーマット】
    # [統合タイトル]
    ## 1. [トピック名]
    - [詳細解説]
    - [詳細解説]
    ...
    
    【統合する入力資料】
    {full_text}
    """
    
    import time
    max_retries = 5
    retry_delay = 30  # 30秒待機
    
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
            if "RESOURCE_EXHAUSTED" in str(e) or "429" in str(e) or "TOO_MANY_REQUESTS" in str(e):
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (attempt + 1)
                    print(f"⏳ レート制限: {wait_time}秒待機中... (試行 {attempt+1}/{max_retries})")
                    time.sleep(wait_time)
                    continue
                else:
                    summary_result = f"⚠️ 要約生成エラー: API のレート制限に達しました。30秒待ってからお試しください。"
            else:
                summary_result = f"⚠️ 要約生成エラー: {type(e).__name__}"
            break
    
    if not summary_result:
        summary_result = "⚠️ 要約生成エラーが発生しました"
    
    # 要約完了後、少し待機してからまとめを生成
    time.sleep(5)
    
    # 2. Generate Integration Summary (まとめ)
    integration_prompt = f"""
    あなたは優秀なまとめの専門家です。
    以下の複数の資料から、最も重要なポイントと全体の流れをまとめてください。
    
    【ルール】
    1. **要点抽出**: 全体を通じて最も大切な3~5つのポイントを明確にすること。
    2. **全体像**: 各資料の関係性や流れを示すこと。
    3. **実践的**: 学んだ内容をどう活かすかまで言及すること。
    4. **簡潔性**: 長くなりすぎず、5~10分で読める長さに。
    
    【出力フォーマット】
    # 📌 全体まとめ
    
    ## 【最重要ポイント】
    - ポイント1
    - ポイント2
    - ...
    
    ## 【全体の流れ】
    [ストーリー形式で資料全体の流れを説明]
    
    ## 【実践的応用】
    [学んだことをどう使うか]
    
    【統合する入力資料】
    {full_text[:3000]}
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
            if "RESOURCE_EXHAUSTED" in str(e) or "429" in str(e) or "TOO_MANY_REQUESTS" in str(e):
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (attempt + 1)
                    print(f"⏳ レート制限: {wait_time}秒待機中... (試行 {attempt+1}/{max_retries})")
                    time.sleep(wait_time)
                    continue
                else:
                    integration_result = f"⚠️ まとめ生成エラー: API のレート制限に達しました。"
            else:
                integration_result = f"⚠️ まとめ生成エラー: {type(e).__name__}"
            break
    
    if not integration_result:
        integration_result = "⚠️ まとめ生成エラーが発生しました"
    
    return {
        "summary": summary_result or "エラーが発生しました",
        "integration": integration_result or "エラーが発生しました"
    }

