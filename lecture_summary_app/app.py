import streamlit as st
import os
import pandas as pd
from dotenv import load_dotenv
import logging

# 遅延インポート（高速化：必要な時だけインポート）
# from utils import file_loader, web_loader, summarizer, qa_agent, recommender

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
        st.session_state.ai_provider = "gemini"  # デフォルトAIプロバイダー
        st.session_state.user_email = ""  # ユーザーメール
        st.session_state.user_api_key = ""  # ユーザーAPIキー
        st.session_state.is_logged_in = False  # ログイン状態
    
    # 個別の初期化（languageとai_providerは常に更新される可能性がある）
    if "language" not in st.session_state:
        st.session_state.language = "ja"
    if "ai_provider" not in st.session_state:
        st.session_state.ai_provider = "gemini"
    if "user_email" not in st.session_state:
        st.session_state.user_email = ""
    if "user_api_key" not in st.session_state:
        st.session_state.user_api_key = ""
    if "is_logged_in" not in st.session_state:
        st.session_state.is_logged_in = False
    
    # Save category to session
    if "current_category" not in st.session_state:
        st.session_state.current_category = None
    
    # キャンセルフラグの初期化
    if "cancel_processing" not in st.session_state:
        st.session_state.cancel_processing = False
    if "is_processing" not in st.session_state:
        st.session_state.is_processing = False

    # Sidebar: Settings & Inputs
    with st.sidebar:
        st.title("🧠 AI資料まとめくん")
        
        # 初回ログイン機能（共有版向け）
        if not st.session_state.is_logged_in:
            st.markdown("### 👤 初回利用者登録")
            st.info("**このアプリを使うには、あなた自身のAIアカウント情報が必要です。**\n\n" +
                   "他の人のAPIキーは使えません。無料で取得できます！")
            
            st.markdown("---")
            st.caption("💡 **初めての方へ:** 下のフォームで登録すると、すぐにアプリを使い始められます。")
            
            with st.form("login_form"):
                user_email = st.text_input(
                    "📧 メールアドレス（識別用）",
                    placeholder="your.email@example.com",
                    help="ログイン識別用です。実際のメール送信はありません。"
                )
                
                st.markdown("---")
                st.markdown("**あなた自身のAPIキーを取得してください:**")
                
                ai_provider_choice = st.selectbox(
                    "使用するAI",
                    ["gemini", "openai"],
                    format_func=lambda x: "🔷 Google Gemini（完全無料・推奨）" if x == "gemini" else "🟢 OpenAI ChatGPT（有料）"
                )
                
                with st.expander("📝 APIキーの取得方法", expanded=True):
                    if ai_provider_choice == "gemini":
                        st.markdown("""
                        ### 🔷 Google Gemini APIキーの取得手順（無料・推奨）
                        
                        **所要時間:** 約3分  
                        **費用:** 完全無料（月間1.5M tokens、1日1500リクエストまで）
                        
                        #### 📋 詳細手順：
                        
                        **ステップ 1:** 下のリンクをクリック  
                        👉 [Google AI Studio](https://ai.google.dev/)
                        
                        **ステップ 2:** 画面右上の **「Get API Key」** ボタンをクリック
                        - Googleアカウントでログインを求められたらログイン
                        - まだGoogleアカウントがない場合は無料で作成できます
                        
                        **ステップ 3:** **「Create API Key」** ボタンをクリック
                        - 新しいプロジェクトを作成するか、既存のプロジェクトを選択
                        - 初めての場合は **「Create API key in new project」** を選択
                        
                        **ステップ 4:** APIキーが表示されます
                        - `AIzaSy...` で始まる長い文字列（約39文字）
                        - 右側の **📋 コピーアイコン** をクリックしてコピー
                        
                        **ステップ 5:** 下の入力欄に貼り付け
                        - `Ctrl + V`（Windows）または `Cmd + V`（Mac）で貼り付け
                        
                        ✅ **完了！** これでこのアプリで使えます
                        
                        ⚠️ **注意事項:**
                        - APIキーは他人と共有しないでください
                        - このアプリはブラウザ内でのみキーを保存します（サーバーには送信されません）
                        - 無料枠を超えた場合も自動的に課金されることはありません
                        """)
                    else:
                        st.markdown("""
                        ### 🟢 OpenAI APIキーの取得手順（有料）
                        
                        **所要時間:** 約5分  
                        **費用:** 従量課金制（最初に$5-$10のクレジット購入が必要）
                        
                        #### 📋 詳細手順：
                        
                        **ステップ 1:** 下のリンクをクリック  
                        👉 [OpenAI Platform](https://platform.openai.com/)
                        
                        **ステップ 2:** アカウント作成/ログイン
                        - **「Sign up」** をクリックしてアカウント作成
                        - メールアドレスと電話番号による認証が必要
                        
                        **ステップ 3:** 支払い情報を登録
                        - 左メニューの **「Billing」** をクリック
                        - クレジットカード情報を登録
                        - 最低$5のクレジット購入が必要
                        
                        **ステップ 4:** APIキーを作成
                        - 左メニューの **「API Keys」** をクリック
                        - **「+ Create new secret key」** ボタンをクリック
                        - 任意の名前を入力（例：「AI資料まとめくん用」）
                        - **「Create secret key」** をクリック
                        
                        **ステップ 5:** APIキーが表示されます
                        - `sk-...` で始まる長い文字列（約50文字以上）
                        - ⚠️ **この画面でしかコピーできません**
                        - 右側の **📋 コピーアイコン** をクリックしてコピー
                        
                        **ステップ 6:** 下の入力欄に貼り付け
                        - `Ctrl + V`（Windows）または `Cmd + V`（Mac）で貼り付け
                        
                        ✅ **完了！** これでこのアプリで使えます
                        
                        ⚠️ **注意事項:**
                        - APIキーは一度しか表示されません（必ず保存してください）
                        - APIキーは他人と共有しないでください
                        - 使用量に応じて課金されます（目安：1000回の要約で約$5-$10）
                        """)
                    
                    st.divider()
                    st.success("💡 **困ったら:** 上記の手順通りに進めば必ず取得できます。ゆっくり1ステップずつ進めてください。")
                
                user_api_key = st.text_input(
                    f"🔑 あなたの{ai_provider_choice.upper()} APIキー",
                    type="password",
                    placeholder="AIza... または sk-... で始まるキー",
                    help="このAPIキーはブラウザにのみ保存され、サーバーには送信されません。"
                )
                
                submitted = st.form_submit_button("✅ 登録して始める", use_container_width=True, type="primary")
                
                if submitted:
                    if not user_email or not user_api_key:
                        st.error("❌ メールアドレスとAPIキーを両方入力してください。")
                    elif len(user_api_key.strip()) < 20:
                        st.error("❌ APIキーが短すぎます。正しいキーを入力してください。")
                    else:
                        # APIキーの前後の空白を削除
                        user_api_key = user_api_key.strip()
                        st.session_state.user_email = user_email.strip()
                        st.session_state.user_api_key = user_api_key
                        st.session_state.ai_provider = ai_provider_choice
                        st.session_state.is_logged_in = True
                        st.success(f"✅ ようこそ {user_email} さん！")
                        st.rerun()
            
            st.divider()
            st.caption("💡 **Google Geminiなら完全無料で使えます！** OpenAIは有料オプションです。")
            st.stop()  # ログインしていない場合は処理を停止
        
        # ログイン済みの場合：ユーザー情報表示
        st.success(f"👤 ログイン中: {st.session_state.user_email}")
        col1, col2 = st.columns([3, 1])
        with col2:
            if st.button("🚪", help="ログアウト"):
                st.session_state.is_logged_in = False
                st.session_state.user_email = ""
                st.session_state.user_api_key = ""
                st.rerun()
        
        st.divider()
        # 言語選択
        language = st.selectbox(
            "🌍 Language / 言語",
            ["ja", "en"],
            format_func=lambda x: "🇯🇵 日本語" if x == "ja" else "🇬🇧 English",
            key="language_selector"
        )
        st.session_state.language = language
        
        # モード選択（ログイン時の選択を反映）
        provider_options = ["extract_only", "gemini", "openai"]
        # ログイン時に選択したプロバイダーをデフォルトにする
        default_index = 0
        if st.session_state.ai_provider in provider_options:
            default_index = provider_options.index(st.session_state.ai_provider)
        
        ai_provider = st.selectbox(
            "⚙️ 機能モードを選択してください",
            provider_options,
            index=default_index,
            format_func=lambda x: "📝 テキスト抽出のみ（AIアカウント不要）" if x == "extract_only" else ("🔷 Google Gemini アカウントで自動要約" if x == "gemini" else "🟢 ChatGPT アカウントで自動要約"),
            key="ai_provider_selector",
            help="• テキスト抽出: PDFを文字に変換するだけ\n• AIアカウント: 個人的なGemini/ChatGPTアカウントを登録して自動要約を生成"
        )
        st.session_state.ai_provider = ai_provider
        
        # 言語別テキスト定数
        TEXTS = {
            "ja": {
                "api_info_local": "✅ AIアカウント登録済み（環境変数から読み込み）",
                "api_info_shared_gemini": "ℹ️ **Google Gemini AIアカウントと接続**: あなたの個人的なAPIキーを入力してください。",
                "api_info_shared_openai": "ℹ️ **OpenAI (ChatGPT) アカウントと接続**: あなたの個人的なAPIキーを入力してください。",
                "api_key_label_gemini": "🔑 Google Gemini APIキー（あなた個人のアカウント）",
                "api_key_label_openai": "🔑 OpenAI APIキー（あなた個人のアカウント）",
                "api_key_help_gemini": "無料で取得可能: Google AI Studio (https://ai.google.dev/)",
                "api_key_help_openai": "OpenAI Platform (https://platform.openai.com/api-keys) で取得",
                "api_key_placeholder_gemini": "AIza... で始まるキーを入力",
                "api_key_placeholder_openai": "sk-... で始まるキーを入力",
                "api_key_link_gemini": "🆓 [登録方法] Google AI Studioで無料登録 → APIキーをコピー → 上の欄に貼り付け",
                "api_key_link_openai": "🆓 [登録方法] OpenAI Platformで登録 → API Keys → キーをコピー → 上の欄に貼り付け",
                "api_short_warning": "⚠️ APIキーが短すぎる可能性があります。正しいキーを入力してください。",
                "api_success": "✅ AIアカウント登録完了",
                "api_warning": "⚠️ AIアカウントを登録してください。APIキーを入力しないとAI機能は使えません。",
                "local_mode": "ℹ️ ローカル環境: .envファイルから自動登録"
            },
            "en": {
                "api_info_local": "✅ AI Account Registered (loaded from environment variables)",
                "api_info_shared_gemini": "ℹ️ **Connect Your Google Gemini Account**: Enter your personal API Key.",
                "api_info_shared_openai": "ℹ️ **Connect Your OpenAI (ChatGPT) Account**: Enter your personal API Key.",
                "api_key_label_gemini": "🔑 Google Gemini API Key (Your Personal Account)",
                "api_key_label_openai": "🔑 OpenAI API Key (Your Personal Account)",
                "api_key_help_gemini": "Free: Get it at Google AI Studio (https://ai.google.dev/)",
                "api_key_help_openai": "Get it at OpenAI Platform (https://platform.openai.com/api-keys)",
                "api_key_placeholder_gemini": "Enter key starting with AIza...",
                "api_key_placeholder_openai": "Enter key starting with sk-...",
                "api_key_link_gemini": "🆓 [How to Register] Sign up at Google AI Studio → Copy API Key → Paste above",
                "api_key_link_openai": "🆓 [How to Register] Sign up at OpenAI Platform → API Keys → Copy → Paste above",
                "api_short_warning": "⚠️ API key may be too short. Please enter correct key.",
                "api_success": "✅ AI Account Registered Successfully",
                "api_warning": "⚠️ Please register your AI account. AI features won't work without API Key.",
                "local_mode": "ℹ️ Local environment: Auto-registered from .env file"
            }
        }
        
        t = TEXTS[language]
        
        st.divider()
        
        # AIアカウント登録 (テキスト抽出モードの場合はスキップ)
        if ai_provider == "extract_only":
            st.info("📝 **テキスト抽出モード**: PDF/TXTファイルから文字を抽出し、コピー可能な形式で表示します。\n\nAIアカウントの登録は不要です。")
            api_key = "dummy_key_not_used"  # テキスト抽出モード用のダミー
        else:
            # ログイン済みユーザーのAPIキーを使用
            api_key = st.session_state.user_api_key
            ai_name = "Google Gemini" if st.session_state.ai_provider == "gemini" else "OpenAI ChatGPT"
            
            # 環境変数に確実に設定（AI処理で使用）
            if st.session_state.ai_provider == "gemini":
                os.environ["GOOGLE_API_KEY"] = api_key
            else:
                os.environ["OPENAI_API_KEY"] = api_key
            
            # APIキーの確認
            masked_key = mask_api_key(api_key)
            st.success(f"✅ **{ai_name}アカウント登録済み**")
            st.caption(f"🔒 登録キー: {masked_key}")
            
            # APIキーの変更オプション
            with st.expander("🔄 APIキーを変更する", expanded=False):
                st.warning("新しいAPIキーに変更すると、再度ログインが必要になります。")
                if st.button("ログアウトして再登録", use_container_width=True):
                    st.session_state.is_logged_in = False
                    st.session_state.user_email = ""
                    st.session_state.user_api_key = ""
                    st.rerun()
            
            with st.expander("⏱️ 処理時間について", expanded=False):
                st.markdown("""
                **処理に時間がかかる理由:**
                
                1. **複数回のAI処理** 🤖
                   - 要約生成（1回目）
                   - まとめ生成（2回目）
                   - 各処理で20～60秒程度
                
                2. **ネットワーク通信** 🌐
                   - GoogleサーバーとのAPI通信
                   - インターネット速度に依存
                
                3. **大量テキスト処理** 📄
                   - 複数ファイルの統合
                   - 1万文字あたり30～60秒
                
                **💡 高速化のヒント:**
                - ファイル数を減らす（1～3ファイル推奨）
                - 各ファイルのサイズを小さくする
                - 不要なページを削除してからアップロード
                """)
        
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
        
        # カテゴリ削除機能（確認付き）
        st.subheader("🗑️ カテゴリ削除")
        
        # 削除済みフォルダから30日以上経過したものを自動削除
        def cleanup_old_deleted_folders():
            """30日以上経過した削除済みフォルダを完全削除"""
            import time
            deleted_base = Path("data/deleted")
            if deleted_base.exists():
                current_time = time.time()
                for folder in deleted_base.iterdir():
                    if folder.is_dir():
                        # フォルダの更新日時をチェック
                        folder_time = folder.stat().st_mtime
                        days_old = (current_time - folder_time) / (24 * 3600)
                        if days_old > 30:
                            try:
                                shutil.rmtree(folder, onerror=lambda func, path, _: (os.chmod(path, stat.S_IWRITE), func(path)))
                            except:
                                pass
        
        cleanup_old_deleted_folders()
        
        # 削除確認のチェックボックス
        delete_confirm = st.checkbox(
            f"⚠️ カテゴリ '{category}' のすべてのデータを削除します（30日間は復元可能）",
            key=f"delete_confirm_{category}"
        )
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🗑️ カテゴリを削除", use_container_width=True, disabled=not delete_confirm, type="secondary"):
                import shutil
                import stat
                from pathlib import Path
                from datetime import datetime
                
                data_dir = Path(f"data/{category}")
                if data_dir.exists():
                    try:
                        # 削除フォルダに移動（完全削除ではない）
                        deleted_base = Path("data/deleted")
                        deleted_base.mkdir(parents=True, exist_ok=True)
                        
                        # タイムスタンプ付きのフォルダ名
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        deleted_dir = deleted_base / f"{category}_{timestamp}"
                        
                        # フォルダを移動
                        shutil.move(str(data_dir), str(deleted_dir))
                        
                        st.success(f"✅ カテゴリ '{category}' を削除しました。\\n\\n📦 30日以内であれば復元できます。")
                        st.rerun()
                    except PermissionError as e:
                        st.error(f"❌ アクセス拒否エラー: ファイルが使用中の可能性があります。\\n\\n{str(e)}\\n\\n💡 解決方法:\\n1. このアプリを一度閉じて再起動してください\\n2. エクスプローラーでフォルダを開いている場合は閉じてください")
                    except Exception as e:
                        st.error(f"❌ 削除エラー: {str(e)}")
                else:
                    st.warning("削除するデータがありません。")
        
        with col2:
            # 復元機能
            deleted_base = Path("data/deleted")
            if deleted_base.exists():
                deleted_folders = [f for f in deleted_base.iterdir() if f.is_dir() and f.name.startswith(category + "_")]
                if deleted_folders:
                    # 最新の削除フォルダを取得
                    latest_deleted = max(deleted_folders, key=lambda f: f.stat().st_mtime)
                    
                    if st.button("♻️ 削除を取り消して復元", use_container_width=True, type="primary"):
                        try:
                            restore_dir = Path(f"data/{category}")
                            if restore_dir.exists():
                                st.error(f"❌ カテゴリ '{category}' は既に存在します。先に削除してから復元してください。")
                            else:
                                shutil.move(str(latest_deleted), str(restore_dir))
                                st.success(f"✅ カテゴリ '{category}' を復元しました！")
                                st.rerun()
                        except Exception as e:
                            st.error(f"❌ 復元エラー: {str(e)}")

        st.divider()
        
        # Action Button
        col_btn1, col_btn2 = st.columns([3, 1])
        with col_btn1:
            start_button = st.button("🚀 読み込み & 解析開始", use_container_width=True, type="primary", disabled=st.session_state.is_processing)
        with col_btn2:
            if st.session_state.is_processing:
                if st.button("⏹️ キャンセル", use_container_width=True, type="secondary"):
                    st.session_state.cancel_processing = True
                    st.session_state.is_processing = False
                    st.warning("⚠️ 処理をキャンセルしました")
                    st.rerun()
        
        if start_button:
            # キャンセルフラグをリセット
            st.session_state.cancel_processing = False
            st.session_state.is_processing = True
            
            # APIキーの確認と環境変数への設定
            if ai_provider != "extract_only":
                if not api_key or len(api_key.strip()) < 20:
                    ai_name_btn = "Google Gemini" if ai_provider == "gemini" else "ChatGPT"
                    st.error(f"❌ {ai_name_btn}アカウントを登録してください！\n\n上のセクションで、{ai_name_btn}アカウントの接続情報が正しく入力されているか確認してください。")
                    st.session_state.is_processing = False
                else:
                    # 環境変数に確実に設定
                    if ai_provider == "gemini":
                        os.environ["GOOGLE_API_KEY"] = api_key.strip()
                    else:
                        os.environ["OPENAI_API_KEY"] = api_key.strip()
            
            if ai_provider != "extract_only" and not api_key:
                ai_name_btn = "Google Gemini" if ai_provider == "gemini" else "ChatGPT"
                # エラーメッセージは上で表示済み
                pass
            else:
                # 遅延インポート（使用時のみ） - 全モジュール一括インポート
                from utils import file_loader, web_loader, summarizer, qa_agent, recommender
                import glob
                import shutil
                
                # プログレスバー追加
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                try:
                    # 1. Load Data
                    status_text.text("📂 データを読み込み中...")
                    progress_bar.progress(10)
                    
                    # キャンセルチェック
                    if st.session_state.cancel_processing:
                        st.session_state.is_processing = False
                        status_text.text("⏹️ キャンセルされました")
                        progress_bar.empty()
                        st.stop()
                    
                    text_data = [] # List of {content: str, source: str}
                    upload_errors = []  # エラーを記録
                    
                    # Save uploaded files first
                    if uploaded_files:
                        for idx, f in enumerate(uploaded_files):
                            # キャンセルチェック
                            if st.session_state.cancel_processing:
                                st.session_state.is_processing = False
                                status_text.text("⏹️ キャンセルされました")
                                progress_bar.empty()
                                st.stop()
                            
                            try:
                                # ファイルサイズを事前にチェックして表示
                                file_size_mb = f.size / 1024 / 1024
                                status_text.text(f"💾 ファイル保存中: {f.name} ({file_size_mb:.1f}MB)")
                                
                                file_loader.save_uploaded_file(f, category)
                                progress_bar.progress(10 + (idx + 1) * 5)
                            except ValueError as ve:
                                error_msg = str(ve)
                                st.error(f"{error_msg} - ファイル: {f.name}")
                                upload_errors.append(f"{f.name}: {error_msg}")
                                continue
                            except Exception as e:
                                st.error(f"❌ ファイル処理エラー: {f.name} - {str(e)}")
                                upload_errors.append(f"{f.name}: {str(e)}")
                                continue
                    
                    # LOAD ALL FILES from the category directory (Persistent Storage)
                    status_text.text("📄 保存済みファイルを読み込み中...")
                    progress_bar.progress(25)
                    
                    # キャンセルチェック
                    if st.session_state.cancel_processing:
                        st.session_state.is_processing = False
                        status_text.text("⏹️ キャンセルされました")
                        progress_bar.empty()
                        st.stop()
                    
                    import glob
                    saved_files = glob.glob(f"data/{category}/*")
                    status_text.text(f"📄 {len(saved_files)}個のファイルを発見...")
                    
                    # ファイルを講義番号順にソート
                    file_data_with_order = []
                    successful_count = 0
                    failed_count = 0
                    
                    for num, path in enumerate(saved_files):
                        filename = os.path.basename(path)
                        status_text.text(f"📖 読み込み中 ({num+1}/{len(saved_files)}): {filename}")
                        
                        try:
                            if path.endswith('.pdf'):
                                content = file_loader.load_pdf(path)
                            else:
                                content = file_loader.load_text(path)
                            
                            if not content:
                                st.warning(f"⚠️ ファイルが空です: {filename}")
                                upload_errors.append(f"{filename}: 内容が空")
                                failed_count += 1
                                continue
                            
                            if "Error" in content[:50]:
                                st.error(f"❌ 読み込みエラー: {filename} - {content[:100]}")
                                upload_errors.append(f"{filename}: {content[:100]}")
                                failed_count += 1
                                continue
                            
                            # 講義番号を抽出
                            lecture_num = file_loader.extract_lecture_number(filename, content[:500])
                            file_data_with_order.append({
                                "content": content,
                                "source": filename,
                                "order": lecture_num,
                                "original_order": num
                            })
                            successful_count += 1
                            st.success(f"✅ 成功: {filename} (第{lecture_num}回)" if lecture_num != 999 else f"✅ 成功: {filename}")
                            
                        except Exception as e:
                            st.error(f"❌ 読み込みエラー: {filename} - {str(e)}")
                            upload_errors.append(f"{filename}: {str(e)}")
                            failed_count += 1
                            continue
                    
                    # 読み込み結果のサマリー
                    st.info(f"📊 読み込み完了: 成功 {successful_count}個 / 失敗 {failed_count}個 / 合計 {len(saved_files)}個")
                    
                    # 講義番号でソート（番号が同じ場合は元の順序を維持）
                    file_data_with_order.sort(key=lambda x: (x["order"], x["original_order"]))
                    
                    # text_dataに追加（ソート済み）
                    for item in file_data_with_order:
                        text_data.append({"content": item["content"], "source": item["source"]})
                    
                    # ソート結果をログ出力（デバッグ用）
                    if file_data_with_order:
                        status_text.text(f"✅ {len(file_data_with_order)}個のファイルを順序付けしました")
                        print("📋 ファイル順序:")
                        for idx, item in enumerate(file_data_with_order, 1):
                            order_text = f"第{item['order']}回" if item['order'] != 999 else "順序不明"
                            print(f"  {idx}. {item['source']} ({order_text})")

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
                        error_details = "\n\n**考えられる原因:**\n"
                        if upload_errors:
                            error_details += "\n⚠️ **ファイルアップロードエラー:**\n"
                            for err in upload_errors:
                                error_details += f"- {err}\n"
                        if uploaded_files:
                            error_details += f"\n📤 アップロードされたファイル数: {len(uploaded_files)}個\n"
                        if not uploaded_files and not search_query and not direct_url and not rss_url:
                            error_details += "\n- ファイルまたはURLが入力されていません\n"
                        error_details += "\n💡 **解決方法:**\n"
                        error_details += "- 1ファイルは100MB以下にしてください\n"
                        error_details += "- PDFファイルの場合は100ページ以内にしてください\n"
                        error_details += "- ファイル形式は .pdf または .txt のみ対応しています\n"
                        
                        st.error(f"❌ データが読み込まれませんでした。{error_details}")
                        progress_bar.empty()
                        status_text.empty()
                    else:
                        st.session_state.text_data_list = text_data
                        
                        # 2. Summarize (テキスト抽出モードはスキップ)
                        if ai_provider == "extract_only":
                            status_text.text("📝 テキスト抽出完了！「抽出テキスト」タブで確認できます。")
                            st.session_state.summary = "⚠️ テキスト抽出モード: AI連携を選択すると、このアプリ内で自動的に要約を生成できます。"
                            st.session_state.integration = "⚠️ テキスト抽出モード: 抽出されたテキストは「抽出テキスト」タブで確認できます。"
                            progress_bar.progress(100)
                        else:
                            ai_name_processing = "Google Gemini" if ai_provider == "gemini" else "ChatGPT"
                            status_text.text(f"🔗 {ai_name_processing}アカウントに接続中...")
                            progress_bar.progress(45)
                            import time
                            import threading
                            time.sleep(0.5)
                            
                            # 推定処理時間の計算（文字数に基づく）
                            total_chars = sum(len(item['content']) for item in text_data)
                            # 1万文字あたり約30秒と推定
                            estimated_seconds = max(30, int(total_chars / 10000 * 30))
                            
                            start_time = time.time()
                            result_container = {"result": None, "error": None, "done": False}
                            
                            # スレッドで使用する変数をローカルに保存（session_stateはスレッドからアクセス不可）
                            output_language = st.session_state.language
                            current_ai_provider = st.session_state.ai_provider
                            
                            # 別スレッドで要約生成
                            def generate_in_background():
                                try:
                                    summary_result = summarizer.generate_summary(
                                        text_data, 
                                        api_key, 
                                        output_language=output_language,
                                        ai_provider=current_ai_provider
                                    )
                                    result_container["result"] = summary_result
                                except Exception as e:
                                    result_container["error"] = e
                                finally:
                                    result_container["done"] = True
                            
                            # バックグラウンドスレッド開始
                            thread = threading.Thread(target=generate_in_background)
                            thread.start()
                            
                            # 動的な時間推定（10秒ごとに更新、1分ごとに再計算）
                            progress_bar.progress(50)
                            last_recalc_time = start_time
                            recalc_interval = 60  # 1分ごとに再計算
                            
                            while not result_container["done"]:
                                # キャンセルチェック
                                if st.session_state.cancel_processing:
                                    st.session_state.is_processing = False
                                    status_text.text("⏹️ 処理をキャンセルしました")
                                    progress_bar.empty()
                                    # バックグラウンドスレッドは継続するが、結果は無視
                                    st.stop()
                                
                                elapsed = int(time.time() - start_time)
                                
                                # 1分ごとに推定時間を再計算（実測データから）
                                if elapsed - (last_recalc_time - start_time) >= recalc_interval and elapsed > 30:
                                    # 現在の進捗から残り時間を再推定
                                    # 処理は「要約生成」と「まとめ生成」の2段階
                                    # 前半60%が経過していると仮定して、残り40%の時間を推定
                                    if elapsed > 0:
                                        # 実測ベースの推定: 現在までの速度から全体時間を予測
                                        estimated_total = int(elapsed * 1.8)  # 現在の位置から全体を推定
                                        estimated_seconds = max(estimated_seconds, estimated_total)
                                        last_recalc_time = time.time()
                                
                                remaining = max(0, estimated_seconds - elapsed)
                                
                                # 進捗率の計算（50%～90%の範囲で更新）
                                if estimated_seconds > 0:
                                    progress_percent = min(90, 50 + int((elapsed / estimated_seconds) * 40))
                                else:
                                    progress_percent = 70
                                
                                # 詳細な状態表示
                                status_text.text(f"🤖 {ai_name_processing}で処理中... (経過: {elapsed}秒 / 推定残り: 約{remaining}秒) - 再計算: {int(time.time() - last_recalc_time)}秒前")
                                progress_bar.progress(progress_percent)
                                
                                # 10秒待機（または完了を確認）
                                for _ in range(100):  # 0.1秒×100回 = 10秒
                                    if result_container["done"] or st.session_state.cancel_processing:
                                        break
                                    time.sleep(0.1)
                            
                            # スレッドの終了を待つ
                            thread.join()
                            
                            # 結果の処理
                            try:
                                if result_container["error"]:
                                    raise result_container["error"]
                                
                                st.session_state.summary = result_container["result"].get("summary", "")
                                st.session_state.integration = result_container["result"].get("integration", "")
                                elapsed = int(time.time() - start_time)
                                status_text.text(f"✅ 完了！(処理時間: {elapsed}秒)")
                                progress_bar.progress(70)
                                st.session_state.is_processing = False
                            except Exception as e:
                                st.session_state.is_processing = False
                                st.error(f"❌ 要約生成エラー: {str(e)} - APIキーを確認してください")
                                raise
                        
                        # 3. Initialize QA Context
                        status_text.text("💬 Q&A機能初期化中...")
                        progress_bar.progress(80)
                        
                        # キャンセルチェック
                        if st.session_state.cancel_processing:
                            st.session_state.is_processing = False
                            status_text.text("⏹️ キャンセルされました")
                            progress_bar.empty()
                            st.stop()
                        
                        try:
                            from utils import qa_agent
                            st.session_state.full_context = qa_agent.initialize_vector_store(text_data, api_key)
                        except Exception as e:
                            st.error(f"❌ Q&A初期化エラー: {str(e)}")
                        
                        # 4. Recommend (オプション: 見つからなければスキップ)
                        status_text.text("🔗 関連資料を検索中...")
                        progress_bar.progress(90)
                        
                        # キャンセルチェック
                        if st.session_state.cancel_processing:
                            st.session_state.is_processing = False
                            status_text.text("⏹️ キャンセルされました")
                            progress_bar.empty()
                            st.stop()
                        
                        try:
                            from utils import recommender
                            st.session_state.recommendations = recommender.recommend_sources(
                                st.session_state.summary, 
                                api_key, 
                                skip_if_not_found=True,
                                ai_provider=st.session_state.ai_provider
                            )
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
                        st.session_state.is_processing = False
                        progress_bar.progress(100)
                        status_text.text("✅ 解析完了！")
                        st.success("✅ 解析完了！各タブで結果を確認できます。")
                        
                        # メモリクリア（セキュリティ強化）
                        import gc
                        gc.collect()
                        
                except Exception as e:
                    st.session_state.is_processing = False
                    st.error(f"❌ 処理中にエラーが発生しました: {str(e)}")
                    progress_bar.empty()
                    status_text.empty()
                finally:
                    st.session_state.is_processing = False
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

    # Feature Tabs (Chapters) - テキスト抽出モードの場合は簡略表示
    if st.session_state.ai_provider == "extract_only":
        tab_extracted, tab_summary, tab_integration = st.tabs([
            "📝 抽出テキスト（コピペ用）", 
            "📝 統合要約", 
            "📝 全体まとめ"
        ])
        
        # --- 抽出テキストタブ（テキスト抽出モード専用） ---
        with tab_extracted:
            render_chapter_header("抽出テキスト（コピペ用）", "📝")
            
            st.info("💡 **使い方**: 下のテキストをすべてコピーして、自分のChatGPTやGeminiに貼り付けて「要約して」と指示してください。\n\nまたは、サイドバーで**AI連携モード**を選び、AIアカウントを登録すると、このアプリ内で直接要約を生成できます。")
            
            # 全テキストを結合
            full_extracted_text = ""
            for idx, item in enumerate(st.session_state.text_data_list, 1):
                full_extracted_text += f"\n\n{'='*50}\n"
                full_extracted_text += f"📄 ファイル {idx}: {item['source']}\n"
                full_extracted_text += f"{'='*50}\n\n"
                full_extracted_text += item['content']
            
            # テキストエリアに表示（コピペ可能）
            st.text_area(
                "抽出されたテキスト（全選択してコピーしてください）",
                value=full_extracted_text,
                height=600,
                key="extracted_text_area"
            )
            
            # ファイル情報（順序付き）
            st.divider()
            st.subheader("📚 処理されたファイル（自動順序付け）")
            st.caption("💡 ファイル名や内容から「第1回」「第2回」などを判断して自動的に順序付けしています")
            
            # 遅延インポート
            from utils import file_loader
            
            for idx, item in enumerate(st.session_state.text_data_list, 1):
                # 講義番号を再抽出して表示
                lecture_num = file_loader.extract_lecture_number(item['source'], item['content'][:500])
                order_info = f"（第{lecture_num}回）" if lecture_num != 999 else "（順序不明）"
                st.markdown(f"{idx}. **{item['source']}** {order_info} - {len(item['content'])}文字")
            
            # ダウンロードボタン
            st.divider()
            st.download_button(
                label="📥 テキストファイルとしてダウンロード",
                data=full_extracted_text,
                file_name=f"extracted_text_{pd.Timestamp.now().strftime('%Y%m%d_%H%M')}.txt",
                mime="text/plain",
                use_container_width=True,
                key="download_extracted_text"
            )
        
        # 統合要約タブ（テキスト抽出モードでは説明のみ）
        with tab_summary:
            render_chapter_header("統合要約", "📝")
            st.warning("⚠️ **テキスト抽出モード**: 要約は生成されません。\n\n🔗 **AI連携で自動要約**: サイドバーで**AI連携モード**を選び、あなたのAIアカウント（Google GeminiまたはOpenAI）を登録すると、このアプリ内で直接要約を生成できます。")
        
        # 全体まとめタブ（テキスト抽出モードでは説明のみ）
        with tab_integration:
            render_chapter_header("全体まとめ", "📝")
            st.warning("⚠️ **テキスト抽出モード**: まとめは生成されません。\n\n🔗 **AI連携で自動まとめ**: サイドバーで**AI連携モード**を選び、あなたのAIアカウント（Google GeminiまたはOpenAI）を登録すると、このアプリ内で直接まとめを生成できます。")
    
    else:
        # 通常モード（AI使用）
        tab_integration, tab_summary, tab_reco, tab_qa = st.tabs([
            "📋 第1章: 統合まとめ（全ファイル統合）", 
            "📝 第2章: 要約（簡潔版）", 
            "🔗 第3章: 関連資料・参考文献", 
            "🎓 第4章: AIチューター (Q&A)"
        ])

    # --- Chapter 1: Integration Summary (統合まとめ - integration) ---
    with tab_integration:
        render_chapter_header("統合まとめ（全ファイル統合）", "📋")
        st.caption("💡 すべてのファイルの内容を統合した詳細なまとめです")
        
        # キーワード検索機能
        search_col1, search_col2 = st.columns([3, 1])
        with search_col1:
            search_keyword = st.text_input(
                "🔍 キーワード検索", 
                value=st.session_state.search_keyword, 
                placeholder="検索したいキーワードを入力", 
                key="search_integration"
            )
        with search_col2:
            if st.button("検索", key="search_btn_integration"):
                st.session_state.search_keyword = search_keyword
        
        # ハイライト表示
        displayed_text = highlight_keywords(
            st.session_state.integration, 
            [search_keyword] if search_keyword else []
        )
        
        st.markdown(displayed_text)
        
        # エクスポート機能
        st.divider()
        export_md = export_to_markdown(st.session_state.summary, st.session_state.integration, st.session_state.text_data_list)
        st.download_button(
            label="📥 Markdownでエクスポート",
            data=export_md,
            file_name=f"{st.session_state.category}_summary_{pd.Timestamp.now().strftime('%Y%m%d_%H%M')}.md",
            mime="text/markdown",
            use_container_width=True,
            key="export_integration"
        )

    # --- Chapter 2: Summary (要約 - summary) ---
    with tab_summary:
        render_chapter_header("要約（簡潔版）& ソース一覧", "📝")
        st.caption("💡 統合まとめをさらに簡潔にした要約版です")
        
        # キーワード検索機能
        search_col1, search_col2 = st.columns([3, 1])
        with search_col1:
            search_keyword_summary = st.text_input(
                "🔍 キーワード検索", 
                placeholder="検索したいキーワードを入力", 
                key="search_summary"
            )
        with search_col2:
            if st.button("検索", key="search_btn_summary"):
                st.session_state.search_keyword = search_keyword_summary
        
        # ハイライト表示
        displayed_summary = highlight_keywords(
            st.session_state.summary, 
            [st.session_state.search_keyword] if st.session_state.search_keyword else []
        )
        
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
            use_container_width=True,
            key="export_summary"
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
                                explanation = qa_agent.get_answer(
                                    explanation_prompt, 
                                    st.session_state.full_context,
                                    api_key,
                                    st.session_state.ai_provider
                                )
                                
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
                                explanation = qa_agent.get_answer(
                                    formula_prompt,
                                    st.session_state.full_context,
                                    api_key,
                                    st.session_state.ai_provider
                                )
                                
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
                            explanation = qa_agent.get_answer(
                                explanation_prompt,
                                st.session_state.full_context,
                                api_key,
                                st.session_state.ai_provider
                            )
                            
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
                            explanation = qa_agent.get_answer(
                                formula_prompt,
                                st.session_state.full_context,
                                api_key,
                                st.session_state.ai_provider
                            )
                            
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
                                api_key,
                                st.session_state.ai_provider
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
