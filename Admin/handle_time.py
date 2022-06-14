import re
import pymysql


class Mysql():
    def __init__(self) -> None:
        self.db=pymysql.connect(host="192.168.1.196",user="root",password="12345678",database="autotest")
        self.cursor=self.db.cursor()

    def getData(self,sql):
        self.cursor.execute(sql)
        data = self.cursor.fetchall()
        self.Close()
        return data

    def Commit(self,sql):
        try:
            self.cursor.execute(sql)
            self.db.commit()
        except:
            self.db.rollback()
            print("执行失败")
        self.Close()

    def Close(self):
        self.cursor.close()
        self.db.close()



def getData():
    sql="SELECT  SplitResult.loadtime ,Result.title,SplitResult.createTime , SplitResult.id FROM SplitResult left join Result on Result.id=SplitResult.resultId WHERE Result.taskId in (31,32) and SplitResult.handle_time=0 and Result.status=30;"
    datas=Mysql().getData(sql)
    return datas

def handleDate():
    datas=getData()
    if datas:
        for data in datas:
            title=re.compile(r'[^-]+$')
            result = re.compile(r"(?<=完成': ')\d+\.?\d")
            rest=re.compile(r'{.*?}')
            dat=re.compile(r'\d+\.?\d')
            pageName=title.findall(data[1])
            date=str(data)
            Times=result.findall(date)
            Times=handleTime(Times)
            if Times:
                for i in range(len(Times)):
                    sql="INSERT INTO Product_tasktime( title,pageName, last_titleid,single_time,createTime) VALUES ( '"+data[1]+"','"+pageName[0]+"','"+str(Times[i][0])+"','"+Times[i][1]+"' ,'"+str(data[2])+"');"
                    Mysql().Commit(sql)
                rest=rest.findall(date)
                performance=dat.findall(rest[0])
                sql1="INSERT INTO Product_performance(title,first_contentful_paint,httpRequestTime,DOMtime,createTime) VALUES('"+data[1]+"','"+performance[0]+"','"+performance[1]+"','"+performance[2]+"','"+str(data[2])+"')"
                Mysql().Commit(sql1)
                sql2="update SplitResult set handle_time=1 where id="+str(data[3])+";"
                Mysql().Commit(sql2)
            continue
    return "执行完成"

def handleTime(list):
    ls=[]
    if list:
        for i in range(len(list)):
            s=(i+1,list[i])
            ls.append(s)
        return ls
    else:
        return

if __name__=="__main__":
    status=handleDate()
    print(status)



