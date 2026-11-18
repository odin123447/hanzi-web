import json
import os

def filter_fonts(json_path):
    with open(json_path, "r", encoding="utf-8") as f:
        font_data = json.load(f)

    # 转为集合，带上名字
    font_list = [
        {"name": k, "chars": set(v), "count": len(v)}
        for k, v in font_data.items()
    ]
    # 按字体总字数从大到小排序，优先保留字多的
    font_list.sort(key=lambda x: x["count"], reverse=True)

    reserved = []       # 最终保留的字体
    covered_chars = set() # 已经覆盖到的汉字
    report = []

    for item in font_list:
        name = item["name"]
        char_set = item["chars"]
        # 这个字体独有的字：当前字体有，但是前面保留的字体里还没有
        new_chars = char_set - covered_chars
        new_count = len(new_chars)
        total = len(char_set)
        overlap_count = total - new_count
        overlap_rate = overlap_count / total if total > 0 else 0

        info = {
            "字体名": name,
            "总字数": total,
            "独有新增字": new_count,
            "和已保留字体重复字": overlap_count,
            "重复占比": f"{overlap_rate:.2%}"
        }
        report.append(info)

        # 判断规则：你可以自己调这个阈值
        # 例子：如果独有新增字很少（比如小于100），说明价值很低，标记为建议删除
        if new_count >= 100:
            reserved.append(name)
            covered_chars.update(new_chars)
            info["建议"] = "✅ 保留"
        else:
            info["建议"] = "❌ 建议删除（新增字太少，重复很高）"

    print("="*70)
    print("筛选报告（优先保留字量大、独有字多的字体）")
    print("="*70)
    for row in report:
        print(f"{row['字体名']:15} | 总:{row['总字数']:5d} | 新增:{row['独有新增字']:4d} | 重复占比:{row['重复占比']:6s} | {row['建议']}")

    print("\n✅ 最终保留字体列表：")
    for n in reserved:
        print(" -", n)
    print(f"\n保留之后，一共能覆盖汉字数量：{len(covered_chars)}")

    # 输出报告json
    out_report = {
        "筛选规则": "按字体字数降序，新增独有字≥100则保留",
        "保留字体": reserved,
        "最终覆盖汉字数": len(covered_chars),
        "详细统计": report
    }
    out_file = os.path.join(os.path.dirname(json_path), "font_filter_report.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(out_report, f, ensure_ascii=False, indent=2)
    print(f"\n报告已保存到：{out_file}")

if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(base_dir, "charlist.json")
    filter_fonts(json_path)
