from django.db import models

# Create your models here.
class History(models.Model):
    input = models.CharField(max_length=200, verbose_name="输入内容")
    output = models.CharField(max_length=200, verbose_name="输出内容")
    mode = models.CharField(max_length=10, default='s2t')
    create_time = models.DateTimeField(auto_now_add=True, verbose_name="查询时间")

    class Meta:
        verbose_name = "简繁转换记录"