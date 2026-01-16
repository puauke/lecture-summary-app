import os
import fitz  # PyMuPDF
from pathlib import Path
import hashlib
import re

# Maximum file size: 50MB (14 files × 3MB対応)
MAX_FILE_SIZE = 50 * 1024 * 1024

# 許可される拡張子
ALLOWED_EXTENSIONS = {'.pdf', '.txt'}

def sanitize_filename(filename: str) -> str:
    """
    ファイル名から危険な文字を除去
    """
    # パストラバーサル対策
    filename = os.path.basename(filename)
    
    # 許可する文字のみを残す（英数字、ハイフン、アンダースコア、ドット）
    filename = re.sub(r'[^\w\s.-]', '', filename, flags=re.UNICODE)
    
    return filename[:255]  # ファイル名の最大長を制限

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
        raise ValueError(f"❌ ファイルサイズが大きすぎます ({uploaded_file.size / 1024 / 1024:.1f}MB > 50MB)")
    
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
    """
    text_content = ""
    try:
        # Check file size first
        file_size = os.path.getsize(file_path)
        if file_size > MAX_FILE_SIZE:
            return f"⚠️ ファイルサイズが大きすぎます ({file_size / 1024 / 1024:.1f}MB > 50MB)。最初の50ページのみを処理します。"
        
        doc = fitz.open(file_path)
        max_pages = min(len(doc), 50)  # Limit to first 50 pages
        
        for page_num in range(max_pages):
            page = doc[page_num]
            text_content += page.get_text() + "\n"
        
        if len(doc) > 50:
            text_content += f"\n\n[注記: {len(doc) - 50}ページ以降は処理されていません。]"
        
        return text_content
    except Exception as e:
        return f"Error reading PDF: {str(e)}"

def load_text(file_path):
    """
    Reads text from a text file.
    Handles large files by limiting size.
    """
    try:
        file_size = os.path.getsize(file_path)
        if file_size > MAX_FILE_SIZE:
            # Read only first 5MB of text
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read(MAX_FILE_SIZE)
            return f"⚠️ ファイルサイズが大きすぎます ({file_size / 1024 / 1024:.1f}MB)。最初の5MBのみを処理します。\n\n{content}"
        else:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
    except Exception as e:
        return f"Error reading text file: {str(e)}"
