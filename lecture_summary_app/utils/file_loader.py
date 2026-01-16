import os
import fitz  # PyMuPDF
from pathlib import Path
import hashlib
import re

# Maximum file size: 100MB (より多くのファイルに対応)
MAX_FILE_SIZE = 100 * 1024 * 1024

# 許可される拡張子
ALLOWED_EXTENSIONS = {'.pdf', '.txt'}

def extract_lecture_number(filename: str, content: str = "") -> int:
    """
    ファイル名または内容から講義番号を抽出
    
    Args:
        filename: ファイル名
        content: ファイル内容（オプション）
    
    Returns:
        講義番号（見つからない場合は999を返して最後にソート）
    """
    # ファイル名から検索するパターン
    patterns = [
        r'第(\d+)回',           # 第1回、第2回
        r'第(\d+)講',           # 第1講、第2講
        r'lecture[\s_-]*(\d+)',  # lecture1, lecture_1, lecture-1
        r'lec[\s_-]*(\d+)',      # lec1, lec_1
        r'class[\s_-]*(\d+)',    # class1, class_1
        r'week[\s_-]*(\d+)',     # week1, week_1
        r'(\d+)回目',           # 1回目、2回目
        r'(\d+)[\s_-]*(?:st|nd|rd|th)',  # 1st, 2nd, 3rd, 4th
        r'^(\d+)[\s_\-\.]',     # 先頭の数字: "01.pdf", "1_lecture.pdf"
    ]
    
    # ファイル名から検索
    filename_lower = filename.lower()
    for pattern in patterns:
        match = re.search(pattern, filename_lower)
        if match:
            try:
                return int(match.group(1))
            except (ValueError, IndexError):
                pass
    
    # 内容から検索（最初の500文字のみ）
    if content:
        content_head = content[:500]
        for pattern in patterns:
            match = re.search(pattern, content_head)
            if match:
                try:
                    return int(match.group(1))
                except (ValueError, IndexError):
                    pass
    
    # 見つからない場合は999を返す（最後にソート）
    return 999

def sanitize_filename(filename: str) -> str:
    """
    ファイル名から危険な文字を除去（セキュリティ対策）
    
    Args:
        filename: サニタイズするファイル名
    
    Returns:
        安全なファイル名（最大255文字）
    """
    # パストラバーサル対策: ベース名のみを取得
    filename = os.path.basename(filename)
    
    # 許可する文字のみを残す（英数字、空白、ハイフン、アンダースコア、ドット）
    filename = re.sub(r'[^\w\s.-]', '', filename, flags=re.UNICODE)
    
    return filename[:255]  # ファイルシステムの最大長を制限

def validate_file(uploaded_file, category):
    """
    ファイルのセキュリティ検証
    """
    # ファイル名の検証
    if not uploaded_file.name:
        raise ValueError("❌ ファイル名が空です")
    
    # 拡張子の検証
    file_ext = Path(uploaded_file.name).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"❌ 許可されたファイル形式は .pdf または .txt のみです（アップロード: {file_ext}）")
    
    # ファイルサイズの検証
    if uploaded_file.size > MAX_FILE_SIZE:
        raise ValueError(f"❌ ファイルサイズが大きすぎます ({uploaded_file.size / 1024 / 1024:.1f}MB > 100MB)")
    
    return True

def save_uploaded_file(uploaded_file, category):
    """
    Saves an uploaded file to the data/{category} directory.
    Returns the absolute path of the saved file.
    """
    try:
        # セキュリティ検証
        validate_file(uploaded_file, category)
        
        # ファイル名をサニタイズ
        safe_filename = sanitize_filename(uploaded_file.name)
        
        # カテゴリ名もサニタイズ
        safe_category = sanitize_filename(category)
        
        # Create directory if not exists
        save_dir = Path(f"data/{safe_category}")
        save_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = save_dir / safe_filename
        
        # ファイル重複チェック（同じ内容のファイルを防ぐ）
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        return str(file_path.absolute())
    
    except ValueError as e:
        raise e
    except Exception as e:
        raise ValueError(f"❌ ファイル保存エラー: {str(e)}")

def load_pdf(file_path):
    """
    Extracts text from a PDF file using PyMuPDF.
    Handles large files by limiting pages.
    Optimized for speed.
    """
    text_content = ""
    try:
        # Check file size first
        file_size = os.path.getsize(file_path)
        if file_size > MAX_FILE_SIZE:
            return f"⚠️ ファイルサイズが大きすぎます ({file_size / 1024 / 1024:.1f}MB > 100MB)。最初の100ページのみを処理します。"
        
        doc = fitz.open(file_path)
        total_pages = len(doc)  # doc.close()前に取得
        max_pages = min(total_pages, 100)  # Limit to first 100 pages
        
        # 高速化: テキスト抽出を並列化せず、シンプルに高速モードで実行
        for page_num in range(max_pages):
            page = doc[page_num]
            # 高速化: "text"モードのみ使用（レイアウト情報不要）
            text_content += page.get_text("text") + "\n"
        
        doc.close()  # メモリ解放（高速化）
        
        if total_pages > 100:
            text_content += f"\n\n[注記: {total_pages - 100}ページ以降は処理されていません。]"
        
        return text_content
    except Exception as e:
        return f"Error reading PDF: {str(e)}"

def load_text(file_path):
    """
    Reads text from a text file.
    Automatically detects encoding (UTF-8, Shift-JIS, etc.)
    Handles large files by limiting size.
    """
    try:
        file_size = os.path.getsize(file_path)
        
        # Try UTF-8 first
        def try_read_with_encoding(encoding):
            try:
                if file_size > MAX_FILE_SIZE:
                    with open(file_path, "r", encoding=encoding) as f:
                        content = f.read(MAX_FILE_SIZE)
                    return f"⚠️ ファイルサイズが大きすぎます ({file_size / 1024 / 1024:.1f}MB)。最初の{MAX_FILE_SIZE / 1024 / 1024:.0f}MBのみを処理します。\n\n{content}"
                else:
                    with open(file_path, "r", encoding=encoding) as f:
                        return f.read()
            except (UnicodeDecodeError, LookupError):
                return None
        
        # 複数のエンコーディングを優先度順に試行（日本語ファイル対応）
        encodings = ['utf-8', 'shift-jis', 'cp932', 'euc-jp', 'iso-8859-1', 'latin-1']
        for enc in encodings:
            result = try_read_with_encoding(enc)
            if result is not None:
                return result  # 成功したエンコーディングで読み込み完了
        
        # If all fail, use UTF-8 with error handling
        if file_size > MAX_FILE_SIZE:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read(MAX_FILE_SIZE)
            return f"⚠️ ファイルサイズが大きすぎます ({file_size / 1024 / 1024:.1f}MB)。最初の{MAX_FILE_SIZE / 1024 / 1024:.0f}MBのみを処理します。\n\n{content}"
        else:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
    except Exception as e:
        return f"Error reading text file: {str(e)}"
