def generate_summary(text_data_list, api_key, output_language="ja"):
    """
    Generates a summary from a list of text data.
    text_data_list: List of dicts with 'content' and 'source'.
    output_language: 'ja' for Japanese, 'en' for English, etc.
    """
    # Lazy imports to prevent startup errors
    from langchain_google_genai import ChatGoogleGenerativeAI
    
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

    llm = ChatGoogleGenerativeAI(model="gemini-flash-latest", google_api_key=api_key)

    # 1. Generate Summary
    summary_prompt = f"""
    {language_instruction}
    
    あなたは「講義資料の統合マスター」です。
    提供された複数の資料（レジュメ、Web記事など）の内容を完全に統合し、
    「重複を整理」して「体系的」にまとめた、レポート作成に最適な学習ノートを作成してください。
    
    【重要事項】
    1. **情報の統合**: ファイルAとファイルBで同じトピックを扱っている場合は、内容を統合して一つの項目にまとめること。バラバラに要約してはいけません。
    2. **共通カテゴリで整理**: 資料内で繰り返されるカテゴリやテーマがあれば、それを使って見出しを作り、関連情報をまとめること。
    3. **全情報を表示**: 情報の取捨選択をしてはいけません。すべての詳細、定義、例を漏らさず含めること。
    4. **ソース明記**: 各セクションの末尾に `[出典: ファイル名]` を明記すること。
    5. **構造化**: 大見出し・小見出しを使い、論理的な構成にすること。
    6. **自己完結**: 元の資料を見なくても、このノートだけで学習が完結するように詳しく書くこと。
    
    【数式・特殊文字の扱い】
    - **数式の保持**: 数学・物理の数式は LaTeX形式で記述すること（例: $E = mc^2$、$\\\\frac{{d}}{{dx}}$）
    - **数式の説明**: 資料内に数式の説明がある場合のみ、その説明を数式の後に記載すること。資料内に説明がない場合は数式のみを記載する。
    - **特殊記号**: ギリシャ文字や数学記号も正確に表記すること（α, β, ∫, ∑ など）
    
    【用語辞書の作成】
    最後に「## 📚 重要用語集」セクションを追加し、以下を含めること：
    - 専門用語とその定義
    - 数式記号の意味（例: σ = 標準偏差）
    - 略語の展開（例: AI = Artificial Intelligence）
    
    【索引の作成】
    最後に「## 🔍 キーワード索引」セクションを追加し、重要なキーワードがどの出典に含まれているかを記載すること。
    
    【絶対に守ること】
    - **自然な日本語で記述**: プログラムコードやマークダウン記法以外の記号を使わない。
    - **読みやすい文章**: 学生が理解しやすいように、丁寧に解説する。
    - **文字化け禁止**: UTF-8で正しく表示される日本語を使う。
    
    【出力フォーマット】
    # [統合タイトル]
    
    ## 1. [トピック名/カテゴリ名]
    - 【詳細解説】
    - 【具体例】
    - 【重要ポイント】
    
    `[出典: ファイル名1, ファイル名2]`
    
    ## 2. [次のトピック]
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
    {language_instruction}
    
    あなたは優秀なまとめの専門家です。
    以下の複数の資料から、最も重要なポイントと全体の流れをまとめてください。
    
    【ルール】
    1. **全情報表示**: 取捨選択せず、すべての重要な情報を含めること。
    2. **カテゴリ整理**: 資料内に共通のカテゴリやテーマがあれば、それを使って整理すること。
    3. **要点抽出**: 全体を通じて最も大切な3~5つのポイントを明確にすること。
    4. **全体像**: 各資料の関係性や流れを示すこと。
    5. **実践的**: 学んだ内容をどう活かすかまで言及すること。
    6. **ソース明記**: 情報の出典を `[出典: ファイル名]` の形式で明記すること。
    
    【絶対に守ること】
    - **自然な日本語で記述**: プログラムコードや特殊記号を使わない。
    - **読みやすい文章**: 学生が理解しやすいように、丁寧に解説する。
    - **文字化け禁止**: UTF-8で正しく表示される日本語を使う。
    
    【出力フォーマット】
    # 📌 全体まとめ
    
    ## 【最重要ポイント】
    - ポイント1 `[出典: ファイル名]`
    - ポイント2 `[出典: ファイル名]`
    - ...
    
    ## 【全体の流れ】
    [ストーリー形式で資料全体の流れを説明]
    `[出典: ファイル名]`
    
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

