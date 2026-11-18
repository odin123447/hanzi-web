from django.db import models

# Create your models here.
class History(models.Model):
    char = models.CharField(max_length=10, verbose_name="查询汉字")
    info = models.CharField(max_length=300, verbose_name="字形信息")
    create_time = models.DateTimeField(auto_now_add=True, verbose_name="查询时间")

    class Meta:
        verbose_name = "小篆查询记录"