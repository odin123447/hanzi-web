import os
import json
from fontTools.ttLib import TTFont

# 缓存，和你之前逻辑一致
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
            print(f"解析失败：{font_path} | {e}")
            return set()
    return _font_cmap_cache[font_path]

def is_chinese_codepoint(codepoint: int) -> bool:
    """
    判断码点是不是汉字（覆盖常用区 + 扩展A~F、兼容汉字）
    """
    return (
        (0x4E00 <= codepoint <= 0x9FFF) or        # CJK 基本汉字
        (0x3400 <= codepoint <= 0x4DBF) or        # 扩展 A
        (0x20000 <= codepoint <= 0x2A6DF) or      # 扩展 B
        (0x2A700 <= codepoint <= 0x2B73F) or      # 扩展 C
        (0x2B740 <= codepoint <= 0x2B81F) or      # 扩展 D
        (0x2B820 <= codepoint <= 0x2CEAF) or      # 扩展 E
        (0x2CEB0 <= codepoint <= 0x2EBEF) or      # 扩展 F
        (0xF900 <= codepoint <= 0xFAFF) or        # CJK 兼容汉字
        (0x3190 <= codepoint <= 0x319F)           # 汉字结构符
    )

def extract_chars_from_font_dir(font_dir: str, out_json: str = "charlist.json"):
    result = {}
    if not os.path.isdir(font_dir):
        print("目录不存在！")
        return

    for filename in os.listdir(font_dir):
        lower_name = filename.lower()
        if not lower_name.endswith((".ttf", ".otf")):
            continue
        full_path = os.path.join(font_dir, filename)
        if not os.path.isfile(full_path):
            continue

        print(f"正在处理：{filename}")
        codepoints = get_font_cmap(full_path)
        char_list = []
        for cp in codepoints:
            if is_chinese_codepoint(cp):
                char_list.append(chr(cp))
        # 排序，方便查看
        char_list.sort()
        result[filename] = char_list

    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"\n完成！已输出到 {out_json}")

if __name__ == "__main__":
    FONT_FOLDER = r"C:\Users\ASUS\Downloads\jianfan22\static\font"
    extract_chars_from_font_dir(FONT_FOLDER, "charlist.json")
