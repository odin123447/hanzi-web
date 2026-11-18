import json
import re
from pathlib import Path

# 1. 定义两个数据文件的路径
_BASE_PATH = Path(__file__).resolve().parent.parent / "static" / "data" / "char_base.json"
_DETAIL_PATH = Path(__file__).resolve().parent.parent / "static" / "data" / "char_detail.json"


def _load():
    if not _BASE_PATH.exists() or not _DETAIL_PATH.exists():
        print("⚠️ 警告: char_base.json 或 char_detail.json 不存在，请检查路径")
        return {}

    # === 第一步：加载 base 基本信息 ===
    with open(_BASE_PATH, encoding="utf-8") as f:
        base_data = json.load(f)

    base_dict = {}
    for item in base_data:
        word = item.get("char")
        if word:
            # 拼音可能是数组，转成字符串
            pinyin_list = item.get("pinyin", [])
            pinyin_str = ", ".join(pinyin_list) if isinstance(pinyin_list, list) else str(pinyin_list)

            base_dict[word] = {
                "char": word,
                "strokes": item.get("strokes", "—"),
                "radicals": item.get("radicals", "—"),
                "pinyin": pinyin_str,
                "explanations": []
            }
    # === 第二步：加载 detail 详细释义，并合并进去 ===
    with open(_DETAIL_PATH, encoding="utf-8") as f:
        detail_data = json.load(f)

    for item in detail_data:
        word = item.get("char")
        if word in base_dict:
            # 遍历所有读音、所有解释，把 content 提取出来
            explanations = []
            for pron in item.get("pronunciations", []):
                for exp in pron.get("explanations", []):
                    content = exp.get("content", "").strip()
                    if content:
                        explanations.append(content)
            base_dict[word]["explanations"] = explanations

    return base_dict


# 全局加载字典
WORD_DES = _load()

def get_word_des(char):
    """获取汉字详细简介信息"""
    return WORD_DES.get(char, {})


def get_clean_description(word_data):
    "极简简介提取：提取本义，去除词典冗余排版"
    if not word_data:
        return "暂无简介。"

    explanations = word_data.get("explanations", [])
    if not explanations:
        return "暂无简介。"
    # 核心提取：遍历所有释义，优先找包含“本义”的句子
    for raw in explanations:
        if not raw:
            continue
        match = re.search(r'本义[：:]?\s*([^。；\n]+)', raw)
        if match:
            core_text = match.group(1).strip()
            core_text = core_text.strip('。，,；;()（） ')
            return f"本义：{core_text}。"
    # 如果所有解释都没写“本义”，那就取第一条释义来清洗
    raw = explanations[0]
    raw = re.sub(r'[\(（].*?[\)）]', '', raw).strip()
    raw = raw.replace('(', '').replace(')', '').replace('（', '').replace('）', '')
    # 按标点切分，取第一句
    first_sentence = re.split(r'[。；;]', raw)[0].strip()
    if first_sentence:
        if not first_sentence.endswith('。'):
            first_sentence += '。'
        return first_sentence

    return "暂无简介。"