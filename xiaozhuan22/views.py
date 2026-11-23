import os,re,ast,json

from django.db.models import Max
from io import BytesIO
from docx.oxml.ns import qn
from django.http import JsonResponse,FileResponse
from django.shortcuts import render, redirect
from fontTools.ttLib import TTFont
from pypinyin import pinyin, Style
from django.templatetags.static import static
from utils.word_desp import get_word_des, get_clean_description
from webapp_2 import settings
from xiaozhuan22.models import History
from docx import Document
from docx.shared import Cm, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from PIL import Image, ImageDraw, ImageFont
from django.utils import timezone



# Create your views here.
_font_cmap_cache = {}

def get_font_cmap(font_path):
    if font_path not in _font_cmap_cache:
        try:
            font = TTFont(font_path)
            cmap = set()
            for table in font['cmap'].tables:
                if table.isUnicode():
                    cmap.update(table.cmap.keys())
            _font_cmap_cache[font_path] = cmap
        except Exception as e:
            print(f"解析字体失败: {font_path}", e)
            return set()
    return _font_cmap_cache[font_path]

def UI(request):
    return render(request, 'xiaozhuanUI.html')

def convert(request):
    char = request.GET.get("char", "").strip()
    action = request.GET.get("action", "")
    if not char:
        return JsonResponse({"code": 400, "msg": "请输入汉字"})
    if not request.session.session_key:
        request.session.create()
    current_session = request.session.session_key
    # ==== 基于历史记录计算“上一个 / 下一个” ====
    switched = False
    if action in ("prev", "next"):
        # 每个字按“最近一次查询时间”排序去重（最旧 -> 最新）
        rows = (
            History.objects
            .filter(session_key=current_session)  # <--- 加上这行
            .values("char")
            .annotate(last_time=Max("create_time"))
            .order_by("last_time")
            .values_list("char", flat=True)
        )
        history_chars = list(rows)

        if len(history_chars) > 1:
            if char in history_chars:
                idx = history_chars.index(char)
                idx = (idx + 1) % len(history_chars) if action == "next" \
                    else (idx - 1) % len(history_chars)
                char = history_chars[idx]
            else:
                # 兜底：当前字不在历史里，按方向取端点
                char = history_chars[0] if action == "next" else history_chars[-1]
            switched = True

    py_list = pinyin(char, style=Style.TONE)
    pinyin_str = py_list[0][0] if py_list else "无"
    unicode_code = f"U+{ord(char):04X}"

    word_data = get_word_des(char)
    stroke_raw = str(word_data.get("strokes", "")).strip()
    if not stroke_raw or stroke_raw == "—" or stroke_raw == "None":
        stroke = "暂无笔画信息，该字信息待完善"
    else:
        stroke = stroke_raw
    radical_raw = str(word_data.get("radicals", "")).strip()
    if not radical_raw or radical_raw == "—" or radical_raw == "None":
        radical = "暂无部首信息，该字信息待完善"
    else:
        radical = radical_raw
    description = get_clean_description(word_data)

    font_dir = os.path.join(settings.BASE_DIR, 'static', 'font')
    if not os.path.exists(font_dir):
        return JsonResponse({"code": 500, "msg": "找不到字体文件夹"})

    matched_fonts = []
    for filename in os.listdir(font_dir):
        if filename.lower().endswith(('.ttf', '.otf')):
            abs_path = os.path.join(font_dir, filename)
            cmap = get_font_cmap(abs_path)
            if ord(char) in cmap:
                font_name = os.path.splitext(filename)[0]
                matched_fonts.append({
                    "name": font_name,
                    "url": static(f"font/{filename}")
                })

    if not matched_fonts:
        return JsonResponse({"code": 404, "msg": f"所有字库中暂未收录【{char}】"})

    info = {
        "char": char,
        "pinyin": pinyin_str,
        "stroke": stroke,
        "radical": radical,
        "unicode": unicode_code,
        "description": description,
    }

    # ==== 只有主动查询才写历史，翻页不写 ====
    if action not in ("prev", "next"):
        History.objects.create(
            char=char,
            info=json.dumps(info, ensure_ascii=False),
            session_key = current_session
        )

    return JsonResponse({
        "code": 200,
        "char": char,
        "info": info,
        "fonts": matched_fonts,
        "switched": switched,   # 前端用来判断是否需要提示
    })

def historyUI(request):
    current_session = request.session.session_key
    if current_session:
        datas = History.objects.filter(session_key=current_session).order_by('-create_time')
    else:
        datas = []

    font_dir = os.path.join(settings.BASE_DIR, 'static', 'font')
    # 遍历每一条记录，解析字典，并查找字体
    for data in datas:
        # 1. 把字符串形式的字典转回真正的字典
        try:
            data.parsed_info = ast.literal_eval(data.info)
        except:
            data.parsed_info = {}
        # 2. 给这个字找一套字体
        char = data.char
        data.matched_font_url = None
        data.font_name = None

        if os.path.exists(font_dir):
            for filename in os.listdir(font_dir):
                if filename.lower().endswith(('.ttf', '.otf')):
                    abs_path = os.path.join(font_dir, filename)
                    cmap = get_font_cmap(abs_path)  # 复用查字的缓存函数
                    if ord(char) in cmap:
                        data.matched_font_url = static(f"font/{filename}")
                        data.font_name = os.path.splitext(filename)[0]
                        break  # 在历史页，找到一个字体展示就行
    context = {'datas': datas}
    return render(request, 'xiaozhuanHistoryList.html', context=context)

def delete_history(request):
    if request.method == "POST":
        current_session = request.session.session_key
        if current_session:
            # 只删自己的
            History.objects.filter(session_key=current_session).delete()
    return redirect("xiaozhuan22:historyUI")

# 批量导出小篆字形到 Word 文档
# 小篆字形的红色（较醒目、打印也清晰）
_XZ_RED = (200, 40, 40, 255)

def _render_char_png(char, font_path, size=240, color=_XZ_RED):
    """把单个汉字用小篆字体渲染成 PNG 图片，返回 BytesIO"""
    try:
        font = ImageFont.truetype(font_path, int(size * 0.82))
    except Exception as e:
        print(f"加载字体失败: {font_path}", e)
        return None

    # 白底 —— 在 Word 中显示、打印都稳定
    img = Image.new('RGB', (size, size), (255, 255, 255))
    draw = ImageDraw.Draw(img)

    try:
        bbox = draw.textbbox((0, 0), char, font=font)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        x = (size - w) / 2 - bbox[0]
        y = (size - h) / 2 - bbox[1]
    except Exception:
        x, y = 0, 0

    draw.text((x, y), char, font=font, fill=color)

    buf = BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return buf


def _parse_color(value, default=_XZ_RED):
    """把 #RRGGBB 形式的颜色值转成 RGBA 元组，非法时使用默认色"""
    value = (value or "").strip().lstrip('#')
    if len(value) == 6:
        try:
            return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4)) + (255,)
        except ValueError:
            pass
    return default


def _normalize_text(raw, keep_punct=True):
    """去掉空白字符；keep_punct 为 False 时只保留汉字"""
    text = re.sub(r'\s+', '', raw)
    if not keep_punct:
        text = ''.join(c for c in text if '\u4e00' <= c <= '\u9fff')
    return text


def export_word(request):
    """
    批量导出小篆字形为 Word 文档
    GET 参数：chars —— 待导出的文本
              punct —— 是否保留标点符号（1 保留 / 0 不保留）
              color —— 字形颜色（#RRGGBB，默认朱红）
    """
    raw = request.GET.get("chars", "").strip()
    if not raw:
        return JsonResponse({"code": 400, "msg": "请输入要导出的文本"})

    keep_punct = request.GET.get("punct", "1") != "0"
    color = _parse_color(request.GET.get("color"))

    # 过滤掉所有空白字符，按需保留标点符号
    text = _normalize_text(raw, keep_punct)
    if not text:
        msg = "未识别到有效字符" if keep_punct else "未识别到汉字（已关闭标点符号）"
        return JsonResponse({"code": 400, "msg": msg})
    if len(text) > 1000:
        return JsonResponse({"code": 400, "msg": "单次最多导出 1000 个字符，请分批处理"})

    buf = _build_xiaozhuan_docx(list(text), keep_punct=keep_punct, color=color)
    if buf is None:
        return JsonResponse({"code": 500, "msg": "字体文件夹为空或不存在"})

    filename = f'小篆字形导出_{timezone.now().strftime("%Y%m%d_%H%M%S")}.docx'

    return FileResponse(
        buf,
        as_attachment=True,
        filename=filename,
        content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    )


def _build_xiaozhuan_docx(char_list, source_label=None, keep_punct=True, color=_XZ_RED):
    """把字符列表渲染成小篆 Word 文档，返回 BytesIO；字体不可用时返回 None"""
    font_dir = os.path.join(settings.BASE_DIR, 'static', 'font')
    if not os.path.exists(font_dir):
        return None

    font_paths = [
        os.path.join(font_dir, f)
        for f in os.listdir(font_dir)
        if f.lower().endswith(('.ttf', '.otf'))
    ]
    if not font_paths:
        return None

    # ---------- 创建 Word 文档 ----------
    doc = Document()
    for section in doc.sections:
        section.left_margin = Cm(1.8)
        section.right_margin = Cm(1.8)
        section.top_margin = Cm(2)
        section.bottom_margin = Cm(2)

    # 标题
    title = doc.add_heading('', level=1)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_title = title.add_run('小篆字形导出')
    _set_run_font(r_title, '黑体', 22, (0x1b, 0x24, 0x30))

    # 副标题
    info = doc.add_paragraph()
    info.alignment = WD_ALIGN_PARAGRAPH.CENTER
    subtitle = f'共 {len(char_list)} 个字符　·　小篆字形{"与标点" if keep_punct else ""}以所选颜色呈现'
    if source_label:
        subtitle += f'　·　来源：{source_label}'
    r = info.add_run(subtitle)
    _set_run_font(r, '宋体', 10.5, (0x7d, 0x87, 0x98))

    doc.add_paragraph()

    # 表格：6 列
    COLS = 6
    rows = (len(char_list) + COLS - 1) // COLS
    table = doc.add_table(rows=rows, cols=COLS)
    table.style = 'Table Grid'
    table.alignment = WD_TABLE_ALIGNMENT.CENTER

    not_found = []

    for idx, char in enumerate(char_list):
        cell = table.cell(idx // COLS, idx % COLS)

        # 第一个段落
        p_img = cell.paragraphs[0]
        p_img.text = ""

        # 判断是不是汉字
        is_hanzi = ('\u4e00' <= char <= '\u9fff')

        if is_hanzi:
            # ================= 处理汉字 =================
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER

            img_buf = None
            for fp in font_paths:
                if ord(char) in get_font_cmap(fp):
                    img_buf = _render_char_png(char, fp, color=color)
                    if img_buf:
                        break

            if img_buf:
                run = p_img.add_run()
                run.add_picture(img_buf, width=Cm(2.1))
            else:
                not_found.append(char)
                run = p_img.add_run('—')
                _set_run_font(run, '宋体', color=(0xcc, 0xcc, 0xcc))

            # 汉字下方的楷书对照
            p_kai = cell.add_paragraph()
            p_kai.alignment = WD_ALIGN_PARAGRAPH.CENTER
            r_kai = p_kai.add_run(char)
            _set_run_font(r_kai, '楷体', 9, (0x88, 0x88, 0x88))

        else:
            # ================= 处理标点符号 =================
            # 1. 单元格内容靠下对齐
            cell.vertical_alignment = WD_ALIGN_VERTICAL.BOTTOM
            # 2. 段落文字靠左对齐
            p_img.alignment = WD_ALIGN_PARAGRAPH.LEFT
            # 3. 左侧稍微缩进一点，不要紧贴边框（模拟正常书写）
            p_img.paragraph_format.left_indent = Cm(0.3)
            # 4. 底部留出一点点空白
            p_img.paragraph_format.space_after = Pt(5)

            # 渲染所选颜色的标点
            run = p_img.add_run(char)
            _set_run_font(run, '楷体', 28, color[:3])

            # 注意：这里刻意不添加下方的汉字对照 p_kai 段落

    # 未收录说明
    if not_found:
        doc.add_paragraph()
        p = doc.add_paragraph()
        preview = "、".join(not_found[:50])
        extra = "" if len(not_found) <= 50 else " 等"
        r = p.add_run(
            f'注：{preview}{extra} 共 {len(not_found)} 个汉字在现有小篆字库中暂未收录，未在表格中渲染字形。'
        )
        _set_run_font(r, '宋体', 9, (0x99, 0x99, 0x99))

    # 页脚说明
    doc.add_paragraph()
    foot = doc.add_paragraph()
    foot.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = foot.add_run('本文件由「汉字字形信息管理系统」自动生成')
    _set_run_font(r, '宋体', 9, (0xbb, 0xbb, 0xbb))

    # ---------- 输出 ----------
    buf = BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf

def _set_run_font(run, font_name='宋体', size=None, color=None):
    """强制设置字体，包括中文字体（eastAsia），防止 Word 中汉字变成方块"""
    run.font.name = font_name
    run._element.rPr.rFonts.set(qn('w:eastAsia'), font_name)
    if size:
        run.font.size = Pt(size)
    if color:
        run.font.color.rgb = RGBColor(*color)


# 上传文档的大小上限：10 MB
_MAX_UPLOAD_SIZE = 10 * 1024 * 1024


def _extract_docx_text(stream):
    """提取 Word 文档中的文字（正文段落 + 表格内容）"""
    doc = Document(stream)
    parts = [p.text for p in doc.paragraphs]
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                parts.extend(p.text for p in cell.paragraphs)
    return "\n".join(parts)


def _extract_pdf_text(stream):
    """提取 PDF 文档中的文字（扫描版 PDF 无文字层，无法提取）"""
    from pypdf import PdfReader
    reader = PdfReader(stream)
    return "\n".join((page.extract_text() or "") for page in reader.pages)


def export_word_upload(request):
    """
    上传 Word / PDF 文档，提取文字后批量生成小篆 Word 文档
    POST 参数：file —— .docx 或 .pdf 文件
              punct —— 是否保留标点符号（1 保留 / 0 不保留）
              color —— 字形颜色（#RRGGBB，默认朱红）
    """
    if request.method != "POST":
        return JsonResponse({"code": 405, "msg": "请使用 POST 上传文档"})

    upload = request.FILES.get("file")
    if not upload:
        return JsonResponse({"code": 400, "msg": "请选择要上传的文档"})
    if upload.size > _MAX_UPLOAD_SIZE:
        return JsonResponse({"code": 400, "msg": "文档大小不能超过 10 MB"})

    ext = os.path.splitext(upload.name)[1].lower()
    if ext not in (".docx", ".pdf"):
        return JsonResponse({"code": 400, "msg": "仅支持 .docx 或 .pdf 格式的文档"})

    try:
        raw = _extract_docx_text(upload) if ext == ".docx" else _extract_pdf_text(upload)
    except Exception as e:
        return JsonResponse({"code": 400, "msg": f"文档解析失败：{e}"})

    keep_punct = request.POST.get("punct", "1") != "0"
    color = _parse_color(request.POST.get("color"))

    text = _normalize_text(raw, keep_punct)
    if not text:
        msg = "文档中未识别到文字，若是扫描版 PDF 请改用 Word 文档" if keep_punct \
            else "文档中未识别到汉字（已关闭标点符号）"
        return JsonResponse({"code": 400, "msg": msg})
    if len(text) > 1000:
        return JsonResponse({"code": 400, "msg": f"共 {len(text)} 个字符，单次最多导出 1000 个字符，请分批处理"})

    buf = _build_xiaozhuan_docx(
        list(text),
        source_label=os.path.basename(upload.name),
        keep_punct=keep_punct,
        color=color,
    )
    if buf is None:
        return JsonResponse({"code": 500, "msg": "字体文件夹为空或不存在"})

    base = os.path.splitext(os.path.basename(upload.name))[0] or "文档"
    filename = f'{base}_小篆_{timezone.now().strftime("%Y%m%d_%H%M%S")}.docx'

    return FileResponse(
        buf,
        as_attachment=True,
        filename=filename,
        content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    )
