import os
import sys
import datetime
import time
import traceback
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, PageBreak
)
from reportlab.lib import colors

# Cấu hình lọc file
VALID_EXTENSIONS = ['.cs', '.cshtml', '.dart']
EXCLUDED_PATTERNS = [
    '.g.dart', '.freezed.dart', '.mocks.dart', '.config.dart', 'main.dart', 
    '.env', 'appcontroller.cs',
    '.min.js', '.mini.js', '.bundle.js', '.packed.js',  # Minified files
    '.designer.cs', '.generated.cs', '.g.cs',  # Generated C# files
    'jquery', 'bootstrap', 'popper', 'Program.cs', 'BHYTController.cs', 'enum.cs' # Common libraries
]
EXCLUDED_DIRS = [
    'build', '.dart_tool', 'android', 'ios', 'web', 'windows', 'macos', 'linux', 
    'node_modules', 'bin', 'obj', '.git', '.vscode', '.idea', 'generated', 'gen',
    'wwwroot', 'vendor', 'vendors', 'vendor_plugins', 'lib', 'libs', 'libraries',  # Library folders
    'packages', 'bower_components', 'dist', 'public', 'static',  # Build/dist folders
    'migrations', 'logs', 'temp', 'tmp', 'cache', 'Firebase' , 'VietinBank', 'VNPTSmartCA', 'eSignCloud', 'BIDV', 'BHXH','.config', '.vscode' # Temp folders
]
# Thư mục ưu tiên (chỉ scan trong này nếu người dùng chọn)
PRIORITY_DIRS = ['src', 'app', 'source', 'lib', 'components', 'controllers', 'models', 'views', 'services', 'api']
MAX_LINES_PER_FILE = 10000
MAX_FILES_TO_PROCESS = 500  # Giới hạn số file tối đa
PAGES_PER_SECTION = 25  # Số trang mỗi phần (đầu, giữa, cuối)

# Màu sắc cho console output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def log_info(message, indent=0):
    """Log thông tin thường"""
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    prefix = "  " * indent
    print(f"{Colors.OKCYAN}[{timestamp}]{Colors.ENDC} {prefix}ℹ️  {message}")

def log_success(message, indent=0):
    """Log thành công"""
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    prefix = "  " * indent
    print(f"{Colors.OKGREEN}[{timestamp}]{Colors.ENDC} {prefix}✅ {message}")

def log_warning(message, indent=0):
    """Log cảnh báo"""
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    prefix = "  " * indent
    print(f"{Colors.WARNING}[{timestamp}]{Colors.ENDC} {prefix}⚠️  {message}")

def log_error(message, indent=0):
    """Log lỗi"""
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    prefix = "  " * indent
    print(f"{Colors.FAIL}[{timestamp}]{Colors.ENDC} {prefix}❌ {message}")

def log_progress(current, total, message=""):
    """Hiển thị progress bar"""
    percent = (current / total) * 100 if total > 0 else 0
    bar_length = 40
    filled_length = int(bar_length * current // total) if total > 0 else 0
    bar = '█' * filled_length + '░' * (bar_length - filled_length)
    
    sys.stdout.write(f'\r{Colors.OKBLUE}Progress:{Colors.ENDC} |{bar}| {percent:.1f}% ({current}/{total}) {message}')
    sys.stdout.flush()
    
    if current == total:
        print()  # Xuống dòng khi hoàn thành

def log_section(title):
    """Log phần mới với đường kẻ"""
    print(f"\n{Colors.HEADER}{'='*60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{title.center(60)}{Colors.ENDC}")
    print(f"{Colors.HEADER}{'='*60}{Colors.ENDC}")

def register_fonts():
    """Đăng ký font Times New Roman cho tiếng Việt"""
    log_info("Bắt đầu đăng ký fonts...")
    start_time = time.time()
    
    try:
        font_dir = os.path.join(os.path.dirname(__file__), 'fonts')
        log_info(f"Thư mục font: {font_dir}", 1)
        
        if not os.path.exists(font_dir):
            log_warning(f"Thư mục font không tồn tại: {font_dir}", 1)
            log_info("Sử dụng font mặc định Helvetica", 1)
            return 'Helvetica'
        
        # Kiểm tra các file font
        font_files = {
            'times.ttf': 'TimesNewRoman',
            'timesbd.ttf': 'TimesNewRoman-Bold',
            'timesi.ttf': 'TimesNewRoman-Italic',
            'timesbi.ttf': 'TimesNewRoman-BoldItalic'
        }
        
        for font_file, font_name in font_files.items():
            font_path = os.path.join(font_dir, font_file)
            if os.path.exists(font_path):
                log_info(f"Đang load: {font_file}", 2)
                pdfmetrics.registerFont(TTFont(font_name, font_path))
            else:
                log_warning(f"Không tìm thấy: {font_file}", 2)
        
        # Đăng ký font family
        from reportlab.pdfbase.pdfmetrics import registerFontFamily
        registerFontFamily('TimesNewRoman',
                          normal='TimesNewRoman',
                          bold='TimesNewRoman-Bold',
                          italic='TimesNewRoman-Italic',
                          boldItalic='TimesNewRoman-BoldItalic')
        
        elapsed = time.time() - start_time
        log_success(f"Đã load font Times New Roman thành công ({elapsed:.2f}s)")
        return 'TimesNewRoman'
        
    except Exception as e:
        log_error(f"Không thể load font Times New Roman: {e}")
        log_info("Sử dụng font mặc định Helvetica")
        return 'Helvetica'


def draw_footer(canvas, doc, page_mapping, total_pages, fontName, is_shortened=False):
    """Vẽ footer với số trang"""
    current_page = canvas.getPageNumber()
    
    if is_shortened and page_mapping:
        original_page = page_mapping.get(current_page, current_page)
    else:
        original_page = current_page
    
    canvas.setFont(fontName, 10)
    canvas.setFillColor(colors.black)
    canvas.drawRightString(A4[0] - 15 * mm, 15 * mm, f"{original_page}/{total_pages}")


def get_all_code_files(directory):
    log_info("Bắt đầu tìm kiếm file code...")
    start_time = time.time()
    
    # Kiểm tra xem có thư mục ưu tiên nào tồn tại không
    existing_priority_dirs = []
    for priority_dir in PRIORITY_DIRS:
        check_path = os.path.join(directory, priority_dir)
        if os.path.exists(check_path):
            existing_priority_dirs.append(priority_dir)
    
    if existing_priority_dirs:
        log_info(f"Tìm thấy các thư mục ưu tiên: {', '.join(existing_priority_dirs)}")
        response = input("\n🎯 Bạn có muốn CHỈ scan trong các thư mục này? (y/n): ").strip().lower()
        if response == 'y':
            scan_dirs = [os.path.join(directory, d) for d in existing_priority_dirs]
            log_info(f"Chỉ scan trong: {', '.join(existing_priority_dirs)}")
        else:
            scan_dirs = [directory]
            log_info("Scan toàn bộ project")
    else:
        scan_dirs = [directory]
    
    code_files = []
    total_scanned = 0
    excluded_count = 0
    
    for scan_dir in scan_dirs:
        for root, dirs, files in os.walk(scan_dir):
            # Log thư mục đang scan
            rel_root = os.path.relpath(root, directory)
            if rel_root != '.' and len(code_files) < 50:  # Chỉ log 50 thư mục đầu
                log_info(f"Scanning: {rel_root}", 1)
            
            # Lọc thư mục
            original_dirs = dirs[:]
            dirs[:] = [d for d in dirs if not any(e.lower() in d.lower() for e in EXCLUDED_DIRS)]
            excluded_dirs = len(original_dirs) - len(dirs)
            if excluded_dirs > 0 and len(code_files) < 50:
                log_info(f"Bỏ qua {excluded_dirs} thư mục bị loại trừ", 2)
            
            for file in files:
                total_scanned += 1
                ext = os.path.splitext(file)[1].lower()
                
                if ext in VALID_EXTENSIONS:
                    path = os.path.join(root, file)
                    
                    # Kiểm tra exclusion patterns
                    if any(p.lower() in path.lower() for p in EXCLUDED_DIRS):
                        excluded_count += 1
                        continue
                        
                    if any(p.lower() in file.lower() for p in EXCLUDED_PATTERNS):
                        excluded_count += 1
                        if len(code_files) < 50:  # Chỉ log 50 file đầu
                            log_info(f"Bỏ qua (pattern): {file}", 3)
                        continue
                    
                    try:
                        file_size = os.path.getsize(path)
                        if file_size < 5 * 1024 * 1024:  # < 5MB
                            code_files.append(path)
                            if len(code_files) <= 20:  # Chỉ log chi tiết 20 file đầu
                                log_info(f"✓ {file} ({file_size/1024:.1f} KB)", 3)
                            
                            # Kiểm tra giới hạn số file
                            if len(code_files) >= MAX_FILES_TO_PROCESS:
                                log_warning(f"⚠️ Đã đạt giới hạn {MAX_FILES_TO_PROCESS} files!")
                                log_warning("Dừng tìm kiếm để tránh xử lý quá lâu")
                                break
                        else:
                            if len(code_files) < 20:
                                log_warning(f"File quá lớn (>5MB): {file}", 3)
                            excluded_count += 1
                    except Exception as e:
                        if len(code_files) < 20:
                            log_error(f"Lỗi khi kiểm tra file {file}: {e}", 3)
                        excluded_count += 1
            
            # Break nếu đã đủ file
            if len(code_files) >= MAX_FILES_TO_PROCESS:
                break
    
    elapsed = time.time() - start_time
    log_success(f"Hoàn thành tìm kiếm ({elapsed:.2f}s)")
    log_info(f"Tổng file đã quét: {total_scanned}")
    log_info(f"File code hợp lệ: {len(code_files)}")
    log_info(f"File bị loại trừ: {excluded_count}")
    
    # Cảnh báo nếu có quá nhiều file
    if len(code_files) > 100:
        log_warning(f"⚠️ Có {len(code_files)} files - PDF sẽ rất lớn!")
        log_warning("Nên chỉ chọn các file quan trọng nhất")
        
        # Đề xuất lọc theo folder cấp 1
        folders = {}
        for file in code_files:
            rel_path = os.path.relpath(file, directory)
            parts = rel_path.split(os.sep)
            if len(parts) > 1:
                folder = parts[0]
            else:
                folder = "root"
            
            if folder not in folders:
                folders[folder] = []
            folders[folder].append(file)
        
        log_info("\n📊 Phân bố file theo thư mục:")
        for folder, files in sorted(folders.items(), key=lambda x: len(x[1]), reverse=True)[:10]:
            log_info(f"  • {folder}: {len(files)} files", 1)
        
        response = input("\n🤔 Bạn có muốn lọc bớt files? (y/n): ").strip().lower()
        if response == 'y':
            log_info("\nTùy chọn lọc:")
            log_info("1. Chỉ lấy files trong thư mục cụ thể")
            log_info("2. Loại trừ thư mục cụ thể") 
            log_info("3. Giới hạn số file")
            log_info("4. Giữ nguyên")
            
            choice = input("\nLựa chọn (1/2/3/4): ").strip()
            
            if choice == '1':
                log_info("Các thư mục có sẵn:")
                for i, folder in enumerate(sorted(folders.keys())[:20], 1):
                    log_info(f"  {i}. {folder} ({len(folders[folder])} files)")
                
                selected = input("\nNhập số thư mục muốn giữ (cách nhau bởi dấu phẩy): ").strip()
                selected_indices = [int(x.strip()) - 1 for x in selected.split(',')]
                folder_names = sorted(folders.keys())
                
                filtered_files = []
                for idx in selected_indices:
                    if 0 <= idx < len(folder_names):
                        filtered_files.extend(folders[folder_names[idx]])
                
                code_files = filtered_files[:MAX_FILES_TO_PROCESS]
                log_info(f"Đã lọc còn {len(code_files)} files")
                
            elif choice == '2':
                exclude = input("Nhập tên thư mục muốn loại trừ (cách nhau bởi dấu phẩy): ").strip()
                exclude_folders = [x.strip() for x in exclude.split(',')]
                
                filtered_files = []
                for file in code_files:
                    rel_path = os.path.relpath(file, directory)
                    parts = rel_path.split(os.sep)
                    folder = parts[0] if len(parts) > 1 else "root"
                    
                    if folder not in exclude_folders:
                        filtered_files.append(file)
                
                code_files = filtered_files[:MAX_FILES_TO_PROCESS]
                log_info(f"Đã lọc còn {len(code_files)} files")
                
            elif choice == '3':
                n = int(input("Nhập số file tối đa (khuyến nghị < 100): ").strip())
                code_files = code_files[:n]
                log_info(f"Đã giới hạn xuống {len(code_files)} files")
    
    return code_files


def build_story_element(path, directory, fontName, styles, file_index=None, total_files=None):
    """Tạo story elements cho một file"""
    code_style = styles['code_style']
    file_heading_style = styles['file_heading_style']
    info_style = styles['info_style']
    
    elements = []
    rel_path = os.path.relpath(path, directory)
    
    # Log processing
    if file_index is not None and total_files is not None:
        log_info(f"[{file_index}/{total_files}] Processing: {rel_path}")
    
    elements.append(Paragraph(f"📄 {rel_path}", file_heading_style))

    try:
        start_time = time.time()
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        
        log_info(f"  Đọc {len(lines)} dòng ({time.time() - start_time:.2f}s)", 1)
        
    except Exception as e:
        log_error(f"  Không thể đọc file: {e}", 1)
        elements.append(Paragraph("❌ Không thể đọc file này", code_style))
        return elements

    if len(lines) > MAX_LINES_PER_FILE:
        lines = lines[:MAX_LINES_PER_FILE]
        log_warning(f"  File bị cắt ngắn, chỉ lấy {MAX_LINES_PER_FILE} dòng đầu", 1)
        elements.append(Paragraph(f"⚠️ File bị cắt ngắn, chỉ hiển thị {MAX_LINES_PER_FILE} dòng đầu", info_style))

    batch_size = 20
    total_batches = (len(lines) + batch_size - 1) // batch_size
    
    for batch_num, start in enumerate(range(0, len(lines), batch_size), 1):
        if batch_num % 10 == 0:  # Log mỗi 10 batch
            log_info(f"  Processing batch {batch_num}/{total_batches}", 2)
        
        batch = lines[start:start + batch_size]
        content = ""
        
        for idx, line in enumerate(batch, start=start + 1):
            clean = line.rstrip().replace('\x00', '').replace('\ufffd', '?')
            clean = clean.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            clean = clean.replace('"', '&quot;').replace("'", '&apos;')
            content += f"{idx:03} | {clean}<br/>"
        
        if content:
            try:
                elements.append(Paragraph(content, code_style))
            except Exception as e:
                log_warning(f"  Lỗi render batch {batch_num}: {e}", 2)
                simple_content = f"[Nội dung file có ký tự đặc biệt - dòng {start+1} đến {min(start+batch_size, len(lines))}]"
                elements.append(Paragraph(simple_content, code_style))
    
    log_success(f"  ✓ Hoàn thành xử lý file", 1)
    return elements


def build_story(directory, code_files, fontName, file_indices=None):
    """Build story cho PDF"""
    log_info("Bắt đầu build story...")
    start_time = time.time()
    
    styles = getSampleStyleSheet()

    # Define các styles
    custom_styles = {
        'file_heading_style': ParagraphStyle('FileHeading', 
                                            parent=styles['Heading2'], 
                                            fontName=fontName, 
                                            fontSize=14, 
                                            alignment=TA_LEFT, 
                                            spaceAfter=8, 
                                            spaceBefore=12),
        
        'code_style': ParagraphStyle('Code', 
                                   parent=styles['Normal'], 
                                   fontName=fontName, 
                                   fontSize=12, 
                                   alignment=TA_LEFT, 
                                   spaceAfter=5, 
                                   spaceBefore=0, 
                                   leading=13),
        
        'info_style': ParagraphStyle('Info', 
                                   parent=styles['Normal'], 
                                   fontName=fontName, 
                                   fontSize=11, 
                                   alignment=TA_LEFT, 
                                   spaceAfter=10)
    }

    story = []
    
    # Nội dung các files
    files_to_process = file_indices if file_indices is not None else range(len(code_files))
    total_files = len(files_to_process)
    
    log_info(f"Sẽ xử lý {total_files} files")
    
    for idx, file_idx in enumerate(files_to_process, 1):
        if file_idx < len(code_files):
            try:
                elements = build_story_element(
                    code_files[file_idx], 
                    directory, 
                    fontName, 
                    custom_styles,
                    file_index=idx,
                    total_files=total_files
                )
                story.extend(elements)
                
                # Thêm PageBreak nếu không phải file cuối
                if idx < total_files:
                    story.append(PageBreak())
                
                # Update progress
                log_progress(idx, total_files, f"Files processed")
                
            except Exception as e:
                log_error(f"Lỗi xử lý file {code_files[file_idx]}: {e}")
                log_error(f"Traceback: {traceback.format_exc()}", 1)
                # Tiếp tục với file tiếp theo
                continue
    
    elapsed = time.time() - start_time
    log_success(f"Hoàn thành build story ({elapsed:.2f}s)")
    return story


def count_pages_per_file(directory, code_files, fontName):
    """Đếm số trang cho mỗi file"""
    log_section("PHÂN TÍCH CẤU TRÚC FILE")
    log_info("Đang phân tích số trang cho từng file...")
    
    pages_info = []
    current_page = 1
    total_files = len(code_files)
    
    for i, path in enumerate(code_files, 1):
        try:
            rel_path = os.path.relpath(path, directory)
            log_info(f"[{i}/{total_files}] Analyzing: {rel_path}")
            
            # Tạo story cho file này
            story = build_story(directory, [path], fontName, file_indices=[0])
            
            # Đếm số trang
            dummy_buf = BytesIO()
            dummy_doc = BaseDocTemplate(
                dummy_buf, 
                pagesize=A4,
                leftMargin=15 * mm,
                rightMargin=15 * mm,
                topMargin=25 * mm,
                bottomMargin=25 * mm
            )
            
            frame = Frame(
                dummy_doc.leftMargin, 
                dummy_doc.bottomMargin + 20 * mm,
                dummy_doc.width, 
                dummy_doc.height - 20 * mm, 
                id='normal'
            )
            
            page_count_holder = {'count': 0}
            
            class SingleFilePageCounter(canvas.Canvas):
                def showPage(self):
                    page_count_holder['count'] += 1
                    super().showPage()
            
            dummy_doc.addPageTemplates([PageTemplate(id='dummy', frames=frame)])
            
            dummy_doc.build(story, canvasmaker=SingleFilePageCounter)
            file_pages = page_count_holder['count']
            
            pages_info.append({
                'file_index': i - 1,
                'file_path': path,
                'start_page': current_page,
                'end_page': current_page + file_pages - 1,
                'page_count': file_pages
            })
            
            log_info(f"  → {file_pages} trang (trang {current_page}-{current_page + file_pages - 1})", 1)
            
            current_page += file_pages
            dummy_buf.close()
            
            # Update progress
            log_progress(i, total_files, "Files analyzed")
            
        except Exception as e:
            log_error(f"Lỗi phân tích file {path}: {e}")
            pages_info.append({
                'file_index': i - 1,
                'file_path': path,
                'start_page': current_page,
                'end_page': current_page,
                'page_count': 1
            })
            current_page += 1
    
    log_success(f"Hoàn thành phân tích: Tổng {current_page - 1} trang")
    return pages_info


def select_files_for_shortened(pages_info, total_pages, pages_per_section=25):
    """Chọn các file cần thiết để tạo shortened version"""
    log_section("CHỌN FILE CHO SHORTENED VERSION")
    
    selected_files = set()
    page_mapping = {}
    
    if total_pages <= pages_per_section * 3:
        log_info(f"File gốc chỉ có {total_pages} trang (≤ {pages_per_section * 3})")
        log_info("→ Không cần tạo shortened version")
        for info in pages_info:
            selected_files.add(info['file_index'])
        return list(selected_files), None
    
    # Tính các trang cần lấy
    first_pages = list(range(1, pages_per_section + 1))
    middle_start = (total_pages - pages_per_section) // 2 + 1
    middle_pages = list(range(middle_start, middle_start + pages_per_section))
    last_pages = list(range(total_pages - pages_per_section + 1, total_pages + 1))
    
    needed_pages = set(first_pages + middle_pages + last_pages)
    
    log_info(f"Trang cần giữ lại:")
    log_info(f"  • Đầu: 1-{pages_per_section}", 1)
    log_info(f"  • Giữa: {middle_start}-{middle_start + pages_per_section - 1}", 1)
    log_info(f"  • Cuối: {total_pages - pages_per_section + 1}-{total_pages}", 1)
    
    # Tìm files chứa các trang cần thiết
    shortened_page_num = 1
    
    for info in pages_info:
        file_pages = set(range(info['start_page'], info['end_page'] + 1))
        if file_pages.intersection(needed_pages):
            selected_files.add(info['file_index'])
            log_info(f"✓ Chọn file: {os.path.basename(info['file_path'])}")
            
            # Tạo mapping
            for page in range(info['start_page'], info['end_page'] + 1):
                if page in needed_pages:
                    page_mapping[shortened_page_num] = page
                    shortened_page_num += 1
    
    log_success(f"Đã chọn {len(selected_files)}/{len(pages_info)} files")
    log_info(f"Shortened version sẽ có ~{len(needed_pages)} trang")
    
    return sorted(list(selected_files)), page_mapping


def create_pdf_document(output_path, directory, code_files, is_shortened=False, 
                       file_indices=None, page_mapping=None, total_pages_original=None):
    """Tạo PDF document"""
    version_name = "SHORTENED" if is_shortened else "FULL"
    log_section(f"TẠO {version_name} PDF")
    
    fontName = register_fonts()
    
    def create_story():
        return build_story(directory, code_files, fontName, file_indices)
    
    # Lần 1: Đếm số trang
    log_info("Bước 1: Tính toán số trang...")
    start_time = time.time()
    
    log_info("  Đang tạo story cho việc đếm trang...")
    story_for_counting = create_story()
    log_info(f"  Story đã tạo với {len(story_for_counting)} elements")
    
    total_pages_holder = {}

    class PageCounterCanvas(canvas.Canvas):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._page_count = 0
        
        def showPage(self):
            self._page_count += 1
            if self._page_count % 100 == 0:
                log_info(f"    Đang đếm: {self._page_count} trang...")
            super().showPage()
        
        def save(self):
            total_pages_holder["count"] = self._page_count
            super().save()

    try:
        dummy_buf = BytesIO()
        dummy_doc = BaseDocTemplate(
            dummy_buf, 
            pagesize=A4,
            leftMargin=15 * mm,
            rightMargin=15 * mm,
            topMargin=25 * mm,
            bottomMargin=25 * mm
        )
        
        frame = Frame(
            dummy_doc.leftMargin, 
            dummy_doc.bottomMargin + 20 * mm,
            dummy_doc.width, 
            dummy_doc.height - 20 * mm, 
            id='normal'
        )
        
        dummy_doc.addPageTemplates([PageTemplate(id='dummy', frames=frame)])
        
        log_info("  Bắt đầu build dummy document để đếm trang...")
        build_start = time.time()
        dummy_doc.build(story_for_counting, canvasmaker=PageCounterCanvas)
        log_info(f"  Build dummy document xong ({time.time() - build_start:.2f}s)")
        
        if not is_shortened:
            total_pages = total_pages_holder.get("count", 1)
            total_pages_original = total_pages
        else:
            total_pages = total_pages_original
        
        dummy_buf.close()
        
        elapsed = time.time() - start_time
        log_success(f"Hoàn thành đếm trang ({elapsed:.2f}s)")
        log_info(f"Số trang thực tế: {total_pages_holder.get('count', 1)}")
        log_info(f"Số trang hiển thị: {total_pages}")
        
        # Cảnh báo nếu quá nhiều trang
        if total_pages > 1000:
            log_warning(f"⚠️ PDF sẽ có {total_pages} trang - RẤT LỚN!")
            response = input("\n🤔 Bạn có muốn tiếp tục? (y/n): ").strip().lower()
            if response != 'y':
                log_info("Đã hủy tạo PDF")
                return None
        
    except Exception as e:
        log_error(f"Lỗi khi đếm số trang: {e}")
        log_error(f"Traceback: {traceback.format_exc()}")
        raise

    # Lần 2: Render thật
    log_info("Bước 2: Render PDF...")
    start_time = time.time()
    
    try:
        log_info("  Đang tạo lại story cho render cuối cùng...")
        story_for_final = create_story()
        log_info(f"  Story final có {len(story_for_final)} elements")
        
        final_doc = BaseDocTemplate(
            output_path,
            pagesize=A4,
            leftMargin=15 * mm,
            rightMargin=15 * mm,
            topMargin=25 * mm,
            bottomMargin=25 * mm
        )

        frame_final = Frame(
            final_doc.leftMargin, 
            final_doc.bottomMargin + 20 * mm,
            final_doc.width, 
            final_doc.height - 20 * mm, 
            id='normal'
        )

        def on_page(canvas_obj, doc_obj):
            current = canvas_obj.getPageNumber()
            if current % 100 == 0:
                log_info(f"    Đang render: trang {current}/{total_pages}...")
            draw_footer(canvas_obj, doc_obj, page_mapping, total_pages, fontName, is_shortened)

        final_doc.addPageTemplates([
            PageTemplate(id='real', frames=frame_final, onPage=on_page)
        ])
        
        log_info("  Bắt đầu build PDF final...")
        build_start = time.time()
        final_doc.build(story_for_final)
        log_info(f"  Build PDF final xong ({time.time() - build_start:.2f}s)")
        
        elapsed = time.time() - start_time
        file_size = os.path.getsize(output_path) / (1024 * 1024)  # MB
        
        log_success(f"Hoàn thành render PDF ({elapsed:.2f}s)")
        log_info(f"File size: {file_size:.2f} MB")
        log_info(f"Output: {output_path}")
        
    except Exception as e:
        log_error(f"Lỗi khi render PDF: {e}")
        log_error(f"Traceback: {traceback.format_exc()}")
        raise
    
    return total_pages


def main():
    log_section("SOURCE CODE TO PDF CONVERTER")
    log_info(f"Start time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Kiểm tra thư viện
    try:
        from reportlab.lib.pagesizes import A4
        log_success("Thư viện reportlab đã sẵn sàng")
    except ImportError:
        log_error("Chưa cài đặt reportlab!")
        log_info("Vui lòng cài đặt: pip install reportlab")
        return

    # Nhập đường dẫn
    directory = input("\n📁 Nhập đường dẫn thư mục chứa source code: ").strip()
    
    if not os.path.isdir(directory):
        log_error(f"Thư mục không tồn tại: {directory}")
        return
    
    log_success(f"Thư mục hợp lệ: {directory}")
    
    # Hiển thị cấu hình lọc hiện tại
    log_info("Cấu hình lọc file:")
    log_info(f"  • Extensions hợp lệ: {', '.join(VALID_EXTENSIONS)}", 1)
    log_info(f"  • Giới hạn file: {MAX_FILES_TO_PROCESS}", 1)
    log_info(f"  • Giới hạn dòng/file: {MAX_LINES_PER_FILE}", 1)
    
    # Tìm kiếm files
    log_section("TÌM KIẾM FILE CODE")
    code_files = get_all_code_files(directory)
    
    if not code_files:
        log_error("Không tìm thấy file code nào!")
        return
    
    log_success(f"Tìm thấy {len(code_files)} file code")
    
    # Cảnh báo nếu vẫn còn nhiều file
    if len(code_files) > 200:
        log_warning(f"⚠️ CẢNH BÁO: {len(code_files)} files là RẤT NHIỀU!")
        log_warning("PDF có thể mất rất lâu để tạo và có dung lượng lớn")
        log_info("\nBạn có thể:")
        log_info("1. Tiếp tục với tất cả files (mất nhiều thời gian)")
        log_info("2. Chỉ lấy N files đầu tiên")
        log_info("3. Hủy và lọc lại thủ công")
        
        choice = input("\nLựa chọn (1/2/3): ").strip()
        
        if choice == '2':
            n = int(input("Nhập số file muốn lấy (khuyến nghị < 100): ").strip())
            code_files = code_files[:n]
            log_info(f"Đã giới hạn xuống {len(code_files)} files")
        elif choice == '3':
            log_info("Đã hủy. Vui lòng lọc lại files thủ công")
            return
    
    # Hiển thị danh sách file (giới hạn 10 file đầu)
    log_info("Danh sách file (tối đa 10 file đầu):")
    for i, file in enumerate(code_files[:10], 1):
        rel_path = os.path.relpath(file, directory)
        file_size = os.path.getsize(file) / 1024  # KB
        log_info(f"  {i:2}. {rel_path} ({file_size:.1f} KB)", 1)
    if len(code_files) > 10:
        log_info(f"  ... và {len(code_files) - 10} file khác", 1)
    
    # Ước tính thời gian
    estimated_time = len(code_files) * 0.5  # Ước tính 0.5s mỗi file
    log_info(f"\n⏱️  Ước tính thời gian xử lý: {estimated_time/60:.1f} phút")
    
    response = input("\n🚀 Bắt đầu tạo PDF? (y/n): ").strip().lower()
    if response != 'y':
        log_info("Đã hủy")
        return
    
    try:
        # 1. Tạo PDF FULL
        output_path_full = os.path.join(directory, "SourceCode_Full.pdf")
        
        total_pages = create_pdf_document(output_path_full, directory, code_files)
        
        if total_pages is None:
            log_warning("Đã hủy tạo PDF do file quá lớn")
            return
        
        log_section("KẾT QUẢ FULL VERSION")
        log_success(f"Đã lưu: {output_path_full}")
        log_info(f"Tổng số trang: {total_pages}")
        
        # 2. Tạo PDF SHORTENED nếu cần
        if total_pages > PAGES_PER_SECTION * 3:
            pages_info = count_pages_per_file(directory, code_files, register_fonts())
            selected_files, page_mapping = select_files_for_shortened(
                pages_info, total_pages, PAGES_PER_SECTION
            )
            
            output_path_shortened = os.path.join(directory, "SourceCode_Shortened.pdf")
            
            create_pdf_document(
                output_path_shortened, 
                directory, 
                code_files,
                is_shortened=True,
                file_indices=selected_files,
                page_mapping=page_mapping,
                total_pages_original=total_pages
            )
            
            log_section("KẾT QUẢ SHORTENED VERSION")
            log_success(f"Đã lưu: {output_path_shortened}")
            log_info(f"Giữ lại {PAGES_PER_SECTION} trang đầu, "
                    f"{PAGES_PER_SECTION} trang giữa, {PAGES_PER_SECTION} trang cuối")
        else:
            log_section("SHORTENED VERSION")
            log_info(f"File chỉ có {total_pages} trang (≤ {PAGES_PER_SECTION * 3} trang)")
            log_info("→ Không cần tạo shortened version")
        
        # Tổng kết
        log_section("HOÀN THÀNH")
        log_success("✨ Font: Times New Roman (hỗ trợ tiếng Việt)")
        log_success("📖 Footer: Số trang ở góc phải")
        log_info(f"End time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
    except KeyboardInterrupt:
        log_warning("\n\n⚠️  Người dùng đã dừng chương trình (Ctrl+C)")
        log_info("Đang dọn dẹp...")
        sys.exit(1)
        
    except Exception as e:
        log_error(f"\n\n💥 Lỗi nghiêm trọng: {str(e)}")
        log_error("Traceback đầy đủ:")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{Colors.WARNING}⚠️  Chương trình bị dừng bởi người dùng{Colors.ENDC}")
    except Exception as e:
        print(f"\n{Colors.FAIL}💥 Lỗi không xử lý được: {e}{Colors.ENDC}")
        traceback.print_exc()