import streamlit as st
import os
import pandas as pd
from dotenv import load_dotenv
import logging

from utils import file_loader, web_loader, summarizer, qa_agent, recommender

# Load environment variables
load_dotenv()

# USER_AGENT を設定（Web 検索時の警告を消す）
if not os.getenv("USER_AGENT"):
    os.environ["USER_AGENT"] = "lecture-summary-app/1.0 (security-focused)"

# ログ設定（本番環境用）
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(layout="wide", page_title="AI資料まとめくん", page_icon="🧠")

# --- CSS for "Chapter" look ---
st.markdown("""
<style>
    .chapter-header {
        background-color: #f0f2f6;
        padding: 10px 20px;
        border-radius: 10px;
        border-left: 5px solid #ff4b4b;
        margin-bottom: 20px;
    }
    .chapter-title {
        font-size: 24px;
        font-weight: bold;
        color: #31333F;
        margin: 0;
    }
    .source-link {
        color: #1f77b4;
        text-decoration: none;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

def render_chapter_header(title, icon="📄"):
    st.markdown(f"""
    <div class="chapter-header">
        <p class="chapter-title">{icon} {title}</p>
    </div>
    """, unsafe_allow_html=True)

def mask_api_key(api_key):
    """API キーをマスク表示（セキュリティ強化）"""
    if not api_key or len(api_key) < 10:
        return api_key
    return api_key[:4] + "*" * (len(api_key) - 8) + api_key[-4:]

def highlight_keywords(text, keywords):
    """キーワードをハイライト"""
    if not keywords:
        return text
    for keyword in keywords:
        if keyword.strip():
            text = text.replace(keyword, f"**{keyword}**")
    return text

def export_to_markdown(summary, integration, sources):
    """要約を Markdown 形式でエクスポート"""
    content = f"""# AI資料まとめ

## 📋 全体まとめ

{integration}

---

## 📝 統合要約

{summary}

---

## 📚 使用されたソース

"""
    for item in sources:
        content += f"- {item['source']}\n"
    
    content += f"\n---\n生成日時: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    return content

def main():
    # Helper to clean session
    if "data_loaded" not in st.session_state:
        st.session_state.data_loaded = False
        st.session_state.text_data_list = []
        st.session_state.summary = ""
        st.session_state.integration = ""
        st.session_state.full_context = None
        st.session_state.recommendations = []
        st.session_state.messages = []
        st.session_state.category = "統合資料まとめ"  # Default category
        st.session_state.history = []  # 履歴機能
        st.session_state.search_keyword = ""  # 検索キーワード
        st.session_state.manual_search_results = []  # 手動検索結果
        st.session_state.language = "ja"  # デフォルト言語：日本語
    
    # Save category to session
    if "current_category" not in st.session_state:
        st.session_state.current_category = None

    # Sidebar: Settings & Inputs
    with st.sidebar:
        st.title("🧠 AI資料まとめくん")
        
        # 言語選択
        language = st.selectbox(
            "🌍 Language / 言語",
            ["ja", "en"],
            format_func=lambda x: "🇯🇵 日本語" if x == "ja" else "🇬🇧 English",
            key="language_selector"
        )
        st.session_state.language = language
        
        # 言語別テキスト
        texts = {
            "ja": {
                "api_info_local": "✅ APIキー設定済み（環境変数から読み込み）",
                "api_info_shared": "ℹ️ 共有環境で動作中：各自のGoogle Gemini APIキーを入力してください（無料で取得可能）",
                "api_key_label": "🔑 Google Gemini API Key",
                "api_key_help": "Google AI Studio (https://ai.google.dev/) で無料取得できます",
                "api_key_placeholder": "AIza... で始まるキーを入力",
                "api_key_link": "[📖 APIキーの取得方法](https://ai.google.dev/) - Google AI Studioで無料登録",
                "api_short_warning": "⚠️ APIキーが短すぎる可能性があります",
                "api_success": "✅ APIキー設定完了",
                "api_warning": "⚠️ APIキーを入力してください。入力されていない場合、アプリは動作しません。",
                "local_mode": "ℹ️ ローカル環境で動作中（.envから自動読み込み）"
            },
            "en": {
                "api_info_local": "✅ API Key configured (loaded from environment variables)",
                "api_info_shared": "ℹ️ Shared environment: Please enter your own Google Gemini API Key (free to obtain)",
                "api_key_label": "🔑 Google Gemini API Key",
                "api_key_help": "Get it for free at Google AI Studio (https://ai.google.dev/)",
                "api_key_placeholder": "Enter key starting with AIza...",
                "api_key_link": "[📖 How to get API Key](https://ai.google.dev/) - Free registration at Google AI Studio",
                "api_short_warning": "⚠️ API key may be too short",
                "api_success": "✅ API Key configured successfully",
                "api_warning": "⚠️ Please enter your API Key. The app will not work without it.",
                "local_mode": "ℹ️ Running in local environment (auto-loaded from .env)"
            }
        }
        
        t = texts[language]
        
        st.divider()
        
        # API Key (ローカル環境では.envから自動読み込み、共有環境では手動入力)
        env_api_key = os.getenv("GOOGLE_API_KEY", "")
        
        if env_api_key:
            # ローカル環境（.envからAPIキーが読み込まれている場合）
            api_key = env_api_key
            masked_key = mask_api_key(api_key)
            st.success(f"{t['api_info_local']}: {masked_key}")
            st.caption(t["local_mode"])
        else:
            # 共有環境（Streamlit Cloudなど、各ユーザーが入力）
            st.info(t["api_info_shared"])
            api_key = st.text_input(
                t["api_key_label"], 
                value="", 
                type="password", 
                help=t["api_key_help"],
                placeholder=t["api_key_placeholder"]
            )
            
            # API キー取得リンク
            st.caption(t["api_key_link"])
            
            # API キーのマスク表示（セキュリティ強化）
            if api_key:
                # API キーの長さを検証（通常150文字以上）
                if len(api_key) < 20:
                    st.warning(t["api_short_warning"])
                else:
                    # セッション内でのみ保存（他のユーザーと共有されない）
                    os.environ["GOOGLE_API_KEY"] = api_key
                    masked_key = mask_api_key(api_key)
                    st.success(f"{t['api_success']}: {masked_key}")
            else:
                st.warning(t["api_warning"])
                api_key = ""  # 空文字列を設定
        
        st.divider()

        # Category with Save/Load/Delete
        render_chapter_header("1. カテゴリ管理", "📂")
        
        # Load existing categories
        from pathlib import Path
        data_dir = Path("data")
        existing_categories = []
        if data_dir.exists():
            existing_categories = [d.name for d in data_dir.iterdir() if d.is_dir()]
        
        # Category selection or creation
        if existing_categories:
            category = st.selectbox(
                "既存のカテゴリを選択", 
                ["新規作成"] + existing_categories,
                key="category_select"
            )
            if category == "新規作成":
                category = st.text_input("新しいカテゴリ名", "統合資料まとめ")
        else:
            category = st.text_input("カテゴリ / トピック", "統合資料まとめ", help="資料を保存・管理するフォルダ名")
        
        # Save category to session
        st.session_state.category = category
        st.session_state.current_category = category
        
        # Show category info
        if existing_categories:
            st.caption(f"利用可能なカテゴリ: {len(existing_categories)}")
        
        st.divider()

        # Input Sources
        render_chapter_header("2. データ取り込み", "📥")
        source_type = st.radio("入力ソース", ["ファイル (PDF/TXT)", "Web検索 (キーワード)", "URL直接入力", "RSSフィード"])

        uploaded_files = None
        search_query = ""
        direct_url = ""
        rss_url = ""

        if source_type == "ファイル (PDF/TXT)":
            uploaded_files = st.file_uploader(
                "資料をアップロード", 
                type=['pdf', 'txt'], 
                accept_multiple_files=True,
                help="⚠️ 制限: PDF/TXT形式、各50MB以下（約14ファイル × 3MB対応）、PDF最大50ページ"
            )
        
        elif source_type == "Web検索 (キーワード)":
            search_query = st.text_input("検索キーワード", "Artificial Intelligence tutorial", help="関連するウェブページを自動検索します")
        
        elif source_type == "URL直接入力":
            direct_url = st.text_input("WebページURL", placeholder="https://example.com/lecture", help="⚠️ ローカルホスト・プライベートIPは禁止")
            
        elif source_type == "RSSフィード":
            rss_url = st.text_input("RSS URL", placeholder="https://news.google.com/rss/...", help="RSSフィードから記事を取得します")

        st.divider()
        
        if st.button("🗑️ このカテゴリのデータを全消去", use_container_width=True):
            import shutil
            from pathlib import Path # Assuming file_loader.Path refers to pathlib.Path
            data_dir = Path(f"data/{category}")
            if data_dir.exists():
                shutil.rmtree(data_dir)
                st.success(f"カテゴリ '{category}' のデータを削除しました。")
                st.rerun()

        st.divider()
        
        # Action Button
        if st.button("🚀 読み込み & 解析開始", use_container_width=True, type="primary"):
            if not api_key:
                st.error("❌ APIキーを入力してください！Google AI Studioから取得できます: https://ai.google.dev/")
            else:
                # プログレスバー追加
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                try:
                    # 1. Load Data
                    status_text.text("📂 データを読み込み中...")
                    progress_bar.progress(10)
                    
                    text_data = [] # List of {content: str, source: str}
                    
                    # Save uploaded files first
                    if uploaded_files:
                        for idx, f in enumerate(uploaded_files):
                            try:
                                file_loader.save_uploaded_file(f, category)
                                progress_bar.progress(10 + (idx + 1) * 5)
                            except ValueError as ve:
                                st.error(f"❌ {ve} - ファイル: {f.name}")
                                continue
                            except Exception as e:
                                st.error(f"❌ ファイル処理エラー: {f.name} - {str(e)}")
                                continue
                    
                    # LOAD ALL FILES from the category directory (Persistent Storage)
                    status_text.text("📄 保存済みファイルを読み込み中...")
                    progress_bar.progress(25)
                    
                    import glob
                    saved_files = glob.glob(f"data/{category}/*")
                    
                    for num, path in enumerate(saved_files):
                         filename = os.path.basename(path)
                         try:
                             if path.endswith('.pdf'):
                                 content = file_loader.load_pdf(path)
                             else:
                                 content = file_loader.load_text(path)
                             
                             if content and "Error" not in content[:50]:
                                 text_data.append({"content": content, "source": filename})
                         except Exception as e:
                             st.error(f"❌ 読み込みエラー: {filename} - {str(e)}")
                             continue

                    # Handle Web/URL inputs
                    if search_query:
                        status_text.text("🔍 Web検索中...")
                        progress_bar.progress(35)
                        try:
                            results = web_loader.search_web(search_query)
                            for res in results:
                                content = web_loader.fetch_url_content(res['href'])
                                text_data.append({"content": content, "source": res['href']})
                        except Exception as e:
                            st.error(f"❌ Web検索エラー: {str(e)}")
                            
                    if direct_url:
                        status_text.text("🌐 URLからデータ取得中...")
                        progress_bar.progress(40)
                        try:
                            content = web_loader.fetch_url_content(direct_url)
                            text_data.append({"content": content, "source": direct_url})
                        except Exception as e:
                            st.error(f"❌ URL取得エラー: {str(e)}")
                        
                    if rss_url:
                        status_text.text("📡 RSSフィード取得中...")
                        progress_bar.progress(45)
                        try:
                            entries = web_loader.fetch_rss(rss_url)
                            for entry in entries[:5]:
                                text_data.append({"content": entry['title'] + "\n" + entry['summary'], "source": entry['link']})
                        except Exception as e:
                            st.error(f"❌ RSS取得エラー: {str(e)}")

                    if not text_data:
                        st.error("❌ データが読み込まれませんでした。ファイルをアップロードするか、有効なURLを入力してください。")
                        progress_bar.empty()
                        status_text.empty()
                    else:
                        st.session_state.text_data_list = text_data
                        
                        # 2. Summarize
                        status_text.text("🤖 AI要約生成中... (最大3分)")
                        progress_bar.progress(50)
                        try:
                            summary_result = summarizer.generate_summary(text_data, api_key, output_language=st.session_state.language)
                            st.session_state.summary = summary_result.get("summary", "")
                            st.session_state.integration = summary_result.get("integration", "")
                            progress_bar.progress(70)
                        except Exception as e:
                            st.error(f"❌ 要約生成エラー: {str(e)} - APIキーを確認してください")
                            raise
                        
                        # 3. Initialize QA Context
                        status_text.text("💬 Q&A機能初期化中...")
                        progress_bar.progress(80)
                        try:
                            st.session_state.full_context = qa_agent.initialize_vector_store(text_data, api_key)
                        except Exception as e:
                            st.error(f"❌ Q&A初期化エラー: {str(e)}")
                        
                        # 4. Recommend (オプション: 見つからなければスキップ)
                        status_text.text("🔗 関連資料を検索中...")
                        progress_bar.progress(90)
                        try:
                            st.session_state.recommendations = recommender.recommend_sources(st.session_state.summary, api_key, skip_if_not_found=True)
                        except Exception as e:
                            st.error(f"❌ 推薦エラー: {str(e)}")
                            st.session_state.recommendations = []
                        
                        # 履歴に追加
                        st.session_state.history.append({
                            "timestamp": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"),
                            "category": category,
                            "files": len(text_data),
                            "sources": [d["source"] for d in text_data[:3]]  # 最初の3つのみ
                        })
                        
                        st.session_state.data_loaded = True
                        progress_bar.progress(100)
                        status_text.text("✅ 解析完了！")
                        st.success("✅ 解析完了！各タブで結果を確認できます。")
                        
                        # メモリクリア（セキュリティ強化）
                        import gc
                        gc.collect()
                        
                except Exception as e:
                    st.error(f"❌ 処理中にエラーが発生しました: {str(e)}")
                    progress_bar.empty()
                    status_text.empty()
                finally:
                    progress_bar.empty()
                    status_text.empty()
    
    # 履歴表示（サイドバー）
    if st.session_state.history:
        st.sidebar.divider()
        st.sidebar.subheader("📜 処理履歴")
        for idx, h in enumerate(reversed(st.session_state.history[-5:])):  # 最新5件のみ
            with st.sidebar.expander(f"{h['timestamp']} - {h['category']}", expanded=False):
                st.write(f"📁 ファイル数: {h['files']}")
                st.write(f"📄 ソース: {', '.join(h['sources'])}")


    # Main Content Area
    st.title(f"📚 {st.session_state.category} - AIナレッジベース")

    if not st.session_state.data_loaded:
        st.info("👈 サイドバーから資料をアップロードまたは指定して、「読み込み」ボタンを押してください。")
        return

    # Feature Tabs (Chapters)
    tab_integration, tab_summary, tab_reco, tab_qa = st.tabs([
        "📋 第1章: 全体まとめ", 
        "📝 第2章: 統合要約", 
        "🔗 第3章: 関連資料・参考文献", 
        "🎓 第4章: AIチューター (Q&A)"
    ])

    # --- Chapter 1: Integration Summary (まとめ) ---
    with tab_integration:
        render_chapter_header("全体まとめ", "📋")
        
        # キーワード検索機能
        search_col1, search_col2 = st.columns([3, 1])
        with search_col1:
            search_keyword = st.text_input("🔍 キーワード検索", value=st.session_state.search_keyword, placeholder="検索したいキーワードを入力", key="search_integration")
        with search_col2:
            if st.button("検索", key="search_btn_integration"):
                st.session_state.search_keyword = search_keyword
        
        # ハイライト表示
        displayed_text = st.session_state.integration
        if search_keyword:
            displayed_text = highlight_keywords(displayed_text, [search_keyword])
        
        st.markdown(displayed_text)
        
        # エクスポート機能
        st.divider()
        export_md = export_to_markdown(st.session_state.summary, st.session_state.integration, st.session_state.text_data_list)
        st.download_button(
            label="📥 Markdownでエクスポート",
            data=export_md,
            file_name=f"{st.session_state.category}_summary_{pd.Timestamp.now().strftime('%Y%m%d_%H%M')}.md",
            mime="text/markdown",
            use_container_width=True
        )

    # --- Chapter 2: Summary ---
    with tab_summary:
        render_chapter_header("統合要約 & ソース一覧", "📝")
        
        # キーワード検索機能
        search_col1, search_col2 = st.columns([3, 1])
        with search_col1:
            search_keyword_summary = st.text_input("🔍 キーワード検索", placeholder="検索したいキーワードを入力", key="search_summary")
        with search_col2:
            if st.button("検索", key="search_btn_summary"):
                st.session_state.search_keyword = search_keyword_summary
        
        # ハイライト表示
        displayed_summary = st.session_state.summary
        if st.session_state.search_keyword:
            displayed_summary = highlight_keywords(displayed_summary, [st.session_state.search_keyword])
        
        st.markdown(displayed_summary)
        
        st.divider()
        st.subheader("📚 使用されたソース")
        for item in st.session_state.text_data_list:
            if item['source'].startswith("http"):
                st.markdown(f"- 🌐 [{item['source']}]({item['source']})")
            else:
                st.markdown(f"- 📄 {item['source']} (ローカルファイル)")
        
        # エクスポート機能
        st.divider()
        export_md = export_to_markdown(st.session_state.summary, st.session_state.integration, st.session_state.text_data_list)
        st.download_button(
            label="📥 Markdownでエクスポート",
            data=export_md,
            file_name=f"{st.session_state.category}_summary_{pd.Timestamp.now().strftime('%Y%m%d_%H%M')}.md",
            mime="text/markdown",
            use_container_width=True
        )

    # --- Chapter 3: Recommendations ---
    with tab_reco:
        render_chapter_header("学習におすすめの関連リンク", "🔗")
        st.info("AIが要約内容をもとに、信頼性の高そうな外部リソースをピックアップしました。")
        
        # 手動検索機能
        st.subheader("🔍 手動で関連資料を検索")
        manual_query = st.text_input("検索キーワードを入力", placeholder="例: 機械学習 入門", key="manual_search_query")
        if st.button("検索", key="manual_search_btn"):
            if manual_query:
                with st.spinner("検索中..."):
                    try:
                        from utils import recommender
                        manual_results = recommender.manual_search(manual_query)
                        st.session_state.manual_search_results = manual_results
                        st.success(f"✅ {len(manual_results)}件の結果を取得しました")
                    except Exception as e:
                        st.error(f"❌ 検索エラー: {str(e)}")
            else:
                st.warning("検索キーワードを入力してください")
        
        st.divider()
        
        # 自動検索結果
        if st.session_state.recommendations:
            st.subheader("🤖 AI推薦リンク")
            for rec in st.session_state.recommendations:
                st.markdown(f"### [{rec['title']}]({rec['href']})")
                st.caption(rec['body'])
                st.markdown("---")
        else:
            st.caption("ℹ️ 自動推薦結果なし（手動検索をお試しください）")
        
        # 手動検索結果
        if "manual_search_results" in st.session_state and st.session_state.manual_search_results:
            st.divider()
            st.subheader("📋 手動検索結果")
            for rec in st.session_state.manual_search_results:
                st.markdown(f"### [{rec['title']}]({rec['href']})")
                st.caption(rec['body'])
                st.markdown("---")

    # --- Chapter 4: AI Q&A ---
    with tab_qa:
        render_chapter_header("AIチューター & 用語検索", "🙋‍♂️")
        st.info("読み込んだ全ての資料に基づいて、AIがあなたの質問に答えます。")
        
        # 用語・数式検索機能を追加
        st.subheader("🔍 検索機能")
        search_mode = st.radio(
            "検索モード",
            ["📖 用語・単語検索", "🔢 数式・記号検索", "📚 両方表示"],
            horizontal=True,
            key="search_mode"
        )
        
        st.divider()
        
        if search_mode == "📚 両方表示":
            # 2列表示
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("📖 用語・単語検索")
                term_query = st.text_input("わからない用語や単語を入力", placeholder="例: ニューラルネットワーク", key="term_search")
                if st.button("用語を説明", key="term_explain_btn", use_container_width=True):
                    if term_query:
                        with st.spinner(f"「{term_query}」を検索中..."):
                            try:
                                # 資料内から用語を検索して説明
                                explanation_prompt = f"""
                                以下の資料内から「{term_query}」という用語について説明してください。
                                
                                【説明のルール】
                                1. 資料内に記載がある場合は、その定義や意味を詳しく説明する
                                2. 資料内に記載がない場合は、一般的な定義を簡潔に説明する
                                3. どの資料から引用したかを明記する
                                
                                資料の内容:
                                {st.session_state.full_context[:3000] if st.session_state.full_context else "資料が読み込まれていません"}
                                """
                                
                                from utils import qa_agent
                                explanation = qa_agent.get_answer(explanation_prompt, os.getenv("GOOGLE_API_KEY"))
                                
                                st.success(f"📚 「{term_query}」の説明:")
                                st.markdown(explanation)
                            except Exception as e:
                                st.error(f"❌ 用語検索エラー: {str(e)}")
                    else:
                        st.warning("用語を入力してください")
            
            with col2:
                st.subheader("🔢 数式・記号検索")
                formula_query = st.text_input("数式や記号を入力", placeholder="例: E=mc^2 または σ", key="formula_search")
                if st.button("数式を説明", key="formula_explain_btn", use_container_width=True):
                    if formula_query:
                        with st.spinner(f"「{formula_query}」を検索中..."):
                            try:
                                # 資料内から数式を検索して説明
                                formula_prompt = f"""
                                以下の資料内から「{formula_query}」という数式または記号について説明してください。
                                
                                【重要なルール】
                                1. **資料内に説明がある場合**: その説明をそのまま詳しく記載し、どのファイルから引用したかを明記する。
                                2. **資料内に説明がない場合**: 「資料内にこの数式の説明は見つかりませんでした。一般的な意味は...」と前置きして簡潔に説明する。
                                3. 数学・物理の文脈を考慮し、何を表しているかを明確にする。
                                
                                資料の内容:
                                {st.session_state.full_context[:3000] if st.session_state.full_context else "資料が読み込まれていません"}
                                """
                                
                                from utils import qa_agent
                                explanation = qa_agent.get_answer(formula_prompt, os.getenv("GOOGLE_API_KEY"))
                                
                                st.success(f"🔢 「{formula_query}」の説明:")
                                st.markdown(explanation)
                            except Exception as e:
                                st.error(f"❌ 数式検索エラー: {str(e)}")
                    else:
                        st.warning("数式を入力してください")
        
        elif search_mode == "📖 用語・単語検索":
            # 用語検索のみ表示
            st.subheader("📖 用語・単語検索")
            term_query = st.text_input("わからない用語や単語を入力", placeholder="例: ニューラルネットワーク", key="term_search_only")
            if st.button("用語を説明", key="term_explain_only_btn", use_container_width=True):
                if term_query:
                    with st.spinner(f"「{term_query}」を検索中..."):
                        try:
                            explanation_prompt = f"""
                            以下の資料内から「{term_query}」という用語について説明してください。
                            
                            【説明のルール】
                            1. 資料内に記載がある場合は、その定義や意味を詳しく説明する
                            2. 資料内に記載がない場合は、一般的な定義を簡潔に説明する
                            3. どの資料から引用したかを明記する
                            
                            資料の内容:
                            {st.session_state.full_context[:3000] if st.session_state.full_context else "資料が読み込まれていません"}
                            """
                            
                            from utils import qa_agent
                            explanation = qa_agent.get_answer(explanation_prompt, os.getenv("GOOGLE_API_KEY"))
                            
                            st.success(f"📚 「{term_query}」の説明:")
                            st.markdown(explanation)
                        except Exception as e:
                            st.error(f"❌ 用語検索エラー: {str(e)}")
                else:
                    st.warning("用語を入力してください")
        
        else:  # 数式・記号検索
            st.subheader("🔢 数式・記号検索")
            formula_query = st.text_input("数式や記号を入力", placeholder="例: E=mc^2 または σ", key="formula_search_only")
            if st.button("数式を説明", key="formula_explain_only_btn", use_container_width=True):
                if formula_query:
                    with st.spinner(f"「{formula_query}」を検索中..."):
                        try:
                            formula_prompt = f"""
                            以下の資料内から「{formula_query}」という数式または記号について説明してください。
                            
                            【重要なルール】
                            1. **資料内に説明がある場合**: その説明をそのまま詳しく記載し、どのファイルから引用したかを明記する。
                            2. **資料内に説明がない場合**: 「資料内にこの数式の説明は見つかりませんでした。一般的な意味は...」と前置きして簡潔に説明する。
                            3. 数学・物理の文脈を考慮し、何を表しているかを明確にする。
                            
                            資料の内容:
                            {st.session_state.full_context[:3000] if st.session_state.full_context else "資料が読み込まれていません"}
                            """
                            
                            from utils import qa_agent
                            explanation = qa_agent.get_answer(formula_prompt, os.getenv("GOOGLE_API_KEY"))
                            
                            st.success(f"🔢 「{formula_query}」の説明:")
                            st.markdown(explanation)
                        except Exception as e:
                            st.error(f"❌ 数式検索エラー: {str(e)}")
                else:
                    st.warning("数式を入力してください")
        
        st.divider()

        chat_container = st.container()

        # Input
        if prompt := st.chat_input("例: この講義の要点は何ですか？"):
            st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Display History & Generate Answer
        with chat_container:
            for message in st.session_state.messages:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])
            
            # If last message is user, generate response
            if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
                with st.chat_message("assistant"):
                    with st.spinner("AIが回答を生成中..."):
                        if api_key:
                            response, sources = qa_agent.get_answer(
                                st.session_state.messages[-1]["content"], 
                                st.session_state.full_context,
                                api_key
                            )
                            # Append sources to response
                            full_response = response
                            if sources:
                                full_response += "\n\n**根拠:**\n" + "\n".join([f"- {s}" for s in sources])
                            
                            st.markdown(full_response)
                            st.session_state.messages.append({"role": "assistant", "content": full_response})
                        else:
                            st.error("API Key missing")

if __name__ == "__main__":
    main()
