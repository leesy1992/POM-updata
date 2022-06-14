from Product.models import Counttime,Count
import re,json,time
from Autotest_platform.PageObject.emails import send_email_reports
from djcelery import models as celery_models
from Autotest_platform.PageObject.logger import Logger
log=Logger("计时").logger

"""判断页面加载时长"""
def assetTime(durtion,case_title,url,assttime=3000):
    url=get_url(url)
    if durtion>assttime:
            Counttimes=get_model(Counttime,url=url)  
            if Counttimes:
                Counttime.counts=Counttime.counts +1
                if Counttime.counts%5==0:
                    Counttime.status +=1
            else:
                Counttime.objects.create(title=case_title,counts=1,status=0,url=url)
                return "Done"        
    else:
            return "Done"    
    if Counttime.counts>=5:
            # send_email_reports(resultId,name=case_title,status=massage)
            massage=case_title+"的"+url+"超时"
            send_dingding(massage)
            Counttime.counts=0
    Counttime.save()

"""用正则截取URL中间段"""
def get_url(url):
    last_url=re.search('(?<=#).*(?=\?)',url)
    return last_url.group()

"""获取数据库对应表的对象"""
def get_model(model, get=True, *args, **kwargs ):
    from django.db.models.base import ModelBase
    if isinstance(model, ModelBase):
        if get:
            try:
                return model.objects.get(*args, **kwargs)
            except:
                return None
        else:
            return model.objects.filter(*args, **kwargs)
    else:
        raise TypeError("model 没有继承 django.db.models.base.ModelBase")

"""获取最大值"""
def get_maxNunber(string):
    if isinstance(string,str):
        string=string.split(',')
        my_list=[]
        for i in string:
            if i:
                my_list.append(float(i))
        return max(my_list)    
    else:
        return max(string)


"""计算首屏时间、DOM解析时间、资源加载最大耗时"""
def get_timing():
    from Autotest_platform.PageObject.Base import PageObject 

    domready = """          // DOM解析时间 
                    let mytiming = window.performance.timing;
                    return mytiming.domComplete   - mytiming.domInteractive ;
              """
    first_contentful_paint="""//首屏时间
                            let mytiming=window.performance.getEntriesByType('paint')
                            return mytiming[1].startTime
                            """
    httpRequestTime= """     //http请求时间
                   let mytiming = window.performance.timing;
                   return mytiming.responseEnd - mytiming.responseStart ;
                   """

    DOM_time=str(int(PageObject().js_execute(domready)))
    FCP=str(int(PageObject().js_execute(first_contentful_paint)))
    load_EventTime=str(int(PageObject().js_execute(httpRequestTime)))
    return {"首屏时间":FCP,"http请求时间": load_EventTime,"DOM解析时间": DOM_time} 

"""钉钉消息推送"""
def send_dingding(massage):
    import json,requests
    '''
        关联钉钉机器人，执行错误会推送消息到钉钉
		access_token: 钉钉的Webhook
		content: 发送的内容
		msgtype : 类型
	'''     
    value={
            "msgtype": "text", 
            "text": {
                "content": massage }
                } 
    access_token = 'https://oapi.dingtalk.com/robot/send?access_token=ed7e3e0483fb6ec66dee3281d58c4983d6e6da5b90c5f8a07fa8aa2efb99ca00'
        
    headers = {'Content-Type': 'application/json; charset=UTF-8'}
    values = json.dumps(value)
    respose=requests.post(access_token,values,headers=headers)  
    print("钉钉消息推送成功：{}".format(respose.text)) if "ok" in respose.text else print ("钉钉消息推送失败：{}".format(respose.text)) 


"""失败发邮件判断"""
def send_email(massage,case_title,resultId):
        if massage=="【失败】":
            count=get_model(Count,title=case_title)  
            if count:
                count.counts=count.counts +1
                if count.counts%5==0:
                    count.status +=1
            else:
                Count.objects.create(title=case_title,counts=1,status=0)
                return "Done"        
        else:
            return "Done"    
        if count.counts>=5:
            send_email_reports(resultId,name=case_title,status=massage)
            count.counts=0
        count.save()

def task_login(**kwargs):
    if kwargs.get("name") is "":
        return '任务名称不可为空'
    if kwargs.get("timing")==2:
        return "该任务为常规任务"
    try:
        crontab_time = kwargs.pop('crontab').split('/')
        if len(crontab_time) > 5:
            return '定时配置参数格式不正确'
        crontab = {
            'day_of_week': crontab_time[-1],
            'month_of_year': crontab_time[3],  # 月份
            'day_of_month': crontab_time[2],  # 日期
            'hour': crontab_time[1],  # 小时
            'minute': crontab_time[0],  # 分钟
        }
    except Exception:
        crontab = {
            'day_of_week': '1-5',
            'month_of_year': '*',  # 月份
            'day_of_month': '*',  # 日期
            'hour': 0,  # 小时
            'minute': 0,  # 分钟
        }
    name=kwargs.get('name')
    kwarg={"name":name}
    return create_task(name, 'Product.tasks.timingRunning', kwarg,  crontab)

def create_task(name, task, task_args, crontab_time,):
    '''
    新增定时任务
    :param name: 定时任务名称
    :param task: 对应tasks里已有的task
    :param task_args: list 参数
    :param crontab_time: 时间配置
    :param desc: 定时任务描述
    :return: ok
    '''
    # task任务， created是否定时创建
    task, created = celery_models.PeriodicTask.objects.get_or_create(name=name, task=task)
    # 获取 crontab
    crontab = celery_models.CrontabSchedule.objects.filter(**crontab_time).first()
    if crontab is None:
        # 如果没有就创建，有的话就继续复用之前的crontab
        crontab = celery_models.CrontabSchedule.objects.create(**crontab_time)
    task.crontab = crontab  # 设置crontab
    task.enabled = True  # 开启task
    task.kwargs = json.dumps(task_args, ensure_ascii=False)  # 传入task参数
    # task.description = desc
    task.save()
    return 'ok'

#新建一个计时装饰器
def get_time(fn):
    """计时装饰器"""
    def swapper(*args,**kwargs):
        start_time=int(round(time.time() * 1000))
        res=fn(*args,**kwargs)
        stop_time=int(round(time.time() * 1000))
        delta=stop_time-start_time
        log.info(str(delta) +"ms")
        # log.info(res)

        return res
    return swapper