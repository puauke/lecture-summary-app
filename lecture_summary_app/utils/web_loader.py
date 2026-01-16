from duckduckgo_search import DDGS
from langchain_community.document_loaders import WebBaseLoader
import feedparser
from urllib.parse import urlparse
import re

# タイムアウト設定（秒）
REQUEST_TIMEOUT = 10

# コンテンツサイズ上限: 2MB
MAX_CONTENT_SIZE = 2 * 1024 * 1024

def validate_url(url: str) -> bool:
    """
    URLの検証（SSRF対策）
    """
    try:
        parsed = urlparse(url)
        
        # プロトコルが http または https のみを許可
        if parsed.scheme not in ['http', 'https']:
            return False
        
        # localhost や内部ネットワークへのアクセスを防ぐ
        hostname = parsed.hostname
        if not hostname:
            return False
        
        # ローカルホスト、プライベートIP、メタデータサーバーを除外
        blocked_patterns = [
            r'^localhost$',
            r'^127\.',
            r'^192\.168\.',
            r'^10\.',
            r'^172\.(1[6-9]|2[0-9]|3[01])\.',
            r'^169\.254\.',  # Link-local
            r'^0\.0\.0\.0$',
            r'^169\.254\.169\.254$',  # AWS metadata
        ]
        
        for pattern in blocked_patterns:
            if re.match(pattern, hostname):
                return False
        
        # 危険なドメインのブラックリスト
        dangerous_domains = [
            '.tk', '.ml', '.ga', '.cf', '.gq',  # 無料ドメイン（フィッシング多発）
        ]
        
        hostname_lower = hostname.lower()
        for domain in dangerous_domains:
            if hostname_lower.endswith(domain):
                print(f"⚠️ 危険な可能性のあるドメインをブロック: {hostname}")
                return False
        
        # 危険なキーワードを含むURL
        url_lower = url.lower()
        dangerous_keywords = [
            'phishing', 'malware', 'virus', 'hack', 'crack',
            'download-free', 'prize', 'winner', 'claim',
        ]
        
        for keyword in dangerous_keywords:
            if keyword in url_lower:
                print(f"⚠️ 危険なキーワードを含むURLをブロック: {keyword}")
                return False
        
        return True
    except Exception:
        return False

def sanitize_search_query(query: str) -> str:
    """
    検索クエリのサニタイゼーション
    """
    # 最大長を制限
    query = query[:500]
    
    # 危険な文字を除去
    query = re.sub(r'[<>"\']', '', query)
    
    return query.strip()

def search_web(query, max_results=5):
    """
    Searches the web using DuckDuckGo and returns a list of dictionaries with 'title', 'href', 'body'.
    """
    try:
        # クエリをサニタイズ
        safe_query = sanitize_search_query(query)
        
        results = DDGS().text(safe_query, max_results=max_results)
        safe_results = []
        
        # 結果の URL を検証
        for res in results:
            if validate_url(res.get('href', '')):
                safe_results.append(res)
        
        return safe_results
    except Exception as e:
        print(f"⚠️  Web検索エラー: {type(e).__name__}")
        return []

def fetch_url_content(url):
    """
    Fetches content from a single URL using LangChain's WebBaseLoader.
    Returns the text content.
    """
    try:
        # URL 検証
        if not validate_url(url):
            return f"❌ 無効な URL です: アクセスが許可されていません"
        
        loader = WebBaseLoader(url, requests_per_second=1, requests_kwargs={"timeout": REQUEST_TIMEOUT})
        docs = loader.load()
        
        # Combine content from all "pages" (usually just one for a URL)
        content = "\n".join([doc.page_content for doc in docs])
        
        # コンテンツサイズの制限
        if len(content) > MAX_CONTENT_SIZE:
            content = content[:MAX_CONTENT_SIZE] + "\n\n[注記: コンテンツが長すぎるため、最初の部分のみを取得しました]"
        
        return content
    except Exception as e:
        print(f"⚠️  URL取得エラー: {type(e).__name__}")
        return f"❌ URL の内容を取得できませんでした"

def fetch_rss(url):
    """
    Parses an RSS feed and returns a list of entries with title, link, and summary.
    """
    try:
        # RSS URL の検証
        if not validate_url(url):
            return []
        
        # タイムアウト付きでパース
        feed = feedparser.parse(url, timeout=REQUEST_TIMEOUT)
        
        if feed.bozo:  # RSS解析エラーの場合
            print(f"⚠️  RSS解析警告: 無効な RSS フィード形式の可能性")
        
        entries = []
        for entry in feed.entries[:10]:  # 最大10件に制限
            # リンクを検証
            link = entry.get("link", "")
            if link and validate_url(link):
                entries.append({
                    "title": sanitize_search_query(entry.get("title", "No Title")),
                    "link": link,
                    "summary": sanitize_search_query(entry.get("summary", "") or entry.get("description", ""))[:500]
                })
        return entries
    except Exception as e:
        print(f"⚠️  RSS取得エラー: {type(e).__name__}")
        return []
