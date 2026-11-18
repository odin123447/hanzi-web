import zhconv,opencc
from django.http import JsonResponse
from django.shortcuts import render, redirect
from jianfan22.models import History

# Create your views here.


def UI(request):
    return render(request, 'jianfanUI.html')

CC_CONFIGS = {
    "s2t": opencc.OpenCC("s2t"),
    "s2tw": opencc.OpenCC("s2tw"),  # 台湾正体（带词汇转换）
    "t2s": opencc.OpenCC("t2s"),
}
def convert(request):
    text = request.GET.get("text", "").strip()
    mode = request.GET.get("mode", "s2t")

    if not text:
        return JsonResponse({"code": 400, "msg": "请输入待转换文字", "result": ""})

    is_simp = zhconv.issimp(text)

    if mode in ["s2t", "s2tw"]:
        # 如果是简转繁，且输入包含繁体
        if is_simp is False:
            return JsonResponse({
                "code": 400,
                "msg": "当前为「简体 → 繁体」模式，输入内容包含繁体字，请切换模式或修改输入",
                "result": ""
            })
    elif mode == "t2s":
        # 如果是繁转简，且输入包含简体
        if is_simp is True:
            return JsonResponse({
                "code": 400,
                "msg": "当前为「繁体 → 简体」模式，输入内容包含简体字，请切换模式或修改输入",
                "result": ""
            })
    else:
        return JsonResponse({"code": 400, "msg": "mode参数错误", "result": ""})

    # 执行转换
    try:
        converter = CC_CONFIGS[mode]
        result = converter.convert(text)

        try:
            History.objects.create(input=text, output=result, mode=mode)
        except Exception as db_err:
            print(f"保存历史记录失败: {db_err}")

        return JsonResponse({
            "code": 200,
            "msg": "ok",
            "result": result
        })
    except Exception as e:
        return JsonResponse({"code": 500, "msg": f"服务异常: {str(e)}", "result": ""})

def historyUI(request):
    s2t_datas = History.objects.filter(mode='s2t').order_by('-create_time')
    t2s_datas = History.objects.filter(mode='t2s').order_by('-create_time')
    context = {'s2t_datas': s2t_datas, 't2s_datas': t2s_datas}
    return render(request, 'jianfanHistoryList.html', context=context)

def delete_history(request):
    if request.method == "POST":
        History.objects.all().delete()
    return redirect("jianfan22:historyUI")
