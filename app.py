import streamlit as st
import os
import pandas as pd
from dotenv import load_dotenv

from utils import file_loader, web_loader, summarizer, qa_agent, recommender

# Load environment variables
load_dotenv()

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

def main():
    # Helper to clean session
    if "data_loaded" not in st.session_state:
        st.session_state.data_loaded = False
        st.session_state.text_data_list = []
        st.session_state.summary = ""
        st.session_state.full_context = None
        st.session_state.recommendations = []
        st.session_state.messages = []

    # Sidebar: Settings & Inputs
    with st.sidebar:
        st.title("🧠 AI資料まとめくん")
        
        # API Key
        # API Key
        env_api_key = os.getenv("GOOGLE_API_KEY", "")
        api_key = st.text_input("Google Gemini API Key", value=env_api_key, type="password", help="Google AI Studioで作成したキーを入力")
        if api_key:
            os.environ["GOOGLE_API_KEY"] = api_key
        
        st.divider()

        # Category
        render_chapter_header("1. カテゴリ選択", "📂")
        category = st.text_input("カテゴリ / トピック", "統合資料まとめ", help="資料を保存・管理するフォルダ名")

        st.divider()

        # Input Sources
        render_chapter_header("2. データ取り込み", "📥")
        source_type = st.radio("入力ソース", ["ファイル (PDF/TXT)", "Web検索 (キーワード)", "URL直接入力", "RSSフィード"])

        uploaded_files = None
        search_query = ""
        direct_url = ""
        rss_url = ""

        if source_type == "ファイル (PDF/TXT)":
            uploaded_files = st.file_uploader("資料をアップロード", type=['pdf', 'txt'], accept_multiple_files=True)
        
        elif source_type == "Web検索 (キーワード)":
            search_query = st.text_input("検索キーワード", "Artificial Intelligence tutorial")
        
        elif source_type == "URL直接入力":
            direct_url = st.text_input("WebページURL", placeholder="https://example.com/lecture")
            
        elif source_type == "RSSフィード":
            rss_url = st.text_input("RSS URL", placeholder="https://news.google.com/rss/...")

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
                st.error("APIキーを入力してください！")
            else:
                with st.spinner("資料を解析中... (要約生成・AI学習)"):
                    # 1. Load Data
                    text_data = [] # List of {content: str, source: str}
                    
                    # Save uploaded files first
                    if uploaded_files:
                        for f in uploaded_files:
                            file_loader.save_uploaded_file(f, category)
                    
                    # LOAD ALL FILES from the category directory (Persistent Storage)
                    import glob
                    saved_files = glob.glob(f"data/{category}/*")
                    
                    for num, path in enumerate(saved_files):
                         # Limit to avoid overloading if too many files (e.g. > 20)
                         # But user wants to add, so we load.
                         filename = os.path.basename(path)
                         if path.endswith('.pdf'):
                             content = file_loader.load_pdf(path)
                         else:
                             content = file_loader.load_text(path)
                         
                         if content and "Error" not in content[:50]:
                             text_data.append({"content": content, "source": filename})

                    # Handle Web/URL inputs (These are not saved as files currently, so we process normally)
                    if search_query:
                        results = web_loader.search_web(search_query)
                        for res in results:
                            content = web_loader.fetch_url_content(res['href'])
                            text_data.append({"content": content, "source": res['href']}) 
                            
                    if direct_url:
                        content = web_loader.fetch_url_content(direct_url)
                        text_data.append({"content": content, "source": direct_url})
                        
                    if rss_url:
                        entries = web_loader.fetch_rss(rss_url)
                        for entry in entries[:5]:
                            text_data.append({"content": entry['title'] + "\n" + entry['summary'], "source": entry['link']})

                    if text_data:
                        st.session_state.text_data_list = text_data
                        
                        # 2. Summarize (Using only Flash Latest to avoid 429)
                        st.session_state.summary = summarizer.generate_summary(text_data, api_key)
                        
                        # 3. Initialize QA Context (Long Context)
                        st.session_state.full_context = qa_agent.initialize_vector_store(text_data, api_key)
                        
                        # 4. Recommend
                        st.session_state.recommendations = recommender.recommend_sources(st.session_state.summary, api_key)
                        
                        st.session_state.data_loaded = True
                        st.success(f"解析完了！ 合計 {len(text_data)} 件の資料を統合しました。")
                    else:
                        st.error("データが読み込めませんでした。")


    # Main Content Area
    st.title(f"📚 {category} - AIナレッジベース")

    if not st.session_state.data_loaded:
        st.info("👈 サイドバーから資料をアップロードまたは指定して、「読み込み」ボタンを押してください。")
        return

    # Feature Tabs (Chapters)
    tab_summary, tab_reco, tab_qa = st.tabs([
        "� 第1章: 統合要約", 
        "� 第2章: 関連資料・参考文献", 
        "🎓 第3章: AIチューター (Q&A)"
    ])

    # --- Chapter 1: Summary ---
    with tab_summary:
        render_chapter_header("統合要約 & ソース一覧", "📝")
        
        st.markdown(st.session_state.summary)
        
        st.divider()
        st.subheader("📚 使用されたソース")
        for item in st.session_state.text_data_list:
            if item['source'].startswith("http"):
                st.markdown(f"- 🌐 [{item['source']}]({item['source']})")
            else:
                st.markdown(f"- 📄 {item['source']} (ローカルファイル)")

    # --- Chapter 2: Recommendations ---
    with tab_reco:
        render_chapter_header("学習におすすめの関連リンク", "🔗")
        st.info("AIが要約内容をもとに、信頼性の高そうな外部リソースをピックアップしました。")
        
        if st.session_state.recommendations:
            for rec in st.session_state.recommendations:
                st.markdown(f"### [{rec['title']}]({rec['href']})")
                st.caption(rec['body'])
                st.markdown("---")
        else:
            st.warning("関連情報が見つかりませんでした。")

    # --- Chapter 3: AI Q&A ---
    with tab_qa:
        render_chapter_header("AIチューターへの質問", "🙋‍♂️")
        st.info("読み込んだ全ての資料に基づいて、AIがあなたの質問に答えます。")

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
