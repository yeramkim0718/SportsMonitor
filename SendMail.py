import smtplib  
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from email.header import Header
from email.generator import Generator
from email.mime.image     import MIMEImage
from email import charset
import os 
from datetime import datetime,timedelta 
import pandas as pd
import numpy as np
from jinja2 import Environment,FileSystemLoader,Template
from Elem import*
import configparser
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
from operator import itemgetter
"""
self.monitoring = {} #id, pushes
self.checked = {} # checked push (id, pushes)
self.errored = {} # error push (id, pushes)
self.error_type = {} # error message (key : id, value : list of (error type, push num, push) per id)
"""

class SendMail :
    
    @staticmethod
    def send_simple_mail (subject, body) :
        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['To'] = 'yeram.kim@lge.com'
        msg['From'] = 'aws.sports.monitoring@gmail.com'

        server = smtplib.SMTP('lgekrhqmh01.lge.com',25)
        server.connect('lgekrhqmh01.lge.com')

        server.sendmail(msg['From'],msg['To'],msg.as_string())
        server.quit()


    def __init__(self,monitor) :
        self.monitor = monitor
        self.env = Environment(loader = FileSystemLoader('templates'))
        self.msg = MIMEMultipart()
        self.images = []

    def make_err_map_chart(self,type_list) :

        output =""
        map_list = []

        for type in type_list :
            print(type)
            row = {}
            msg = self.monitor.error_msg_mapper.get(str(type).lower())
            row['type'] = str(type).upper()
            row['msg'] = msg
            map_list.append(row)
        #print(map_list)
        map_list = sorted(map_list,key=lambda x:x['type'])

        template = self.env.get_template('err_type.html')
        output = template.render(map_list = map_list)
        self.msg.attach(MIMEText(output,'html'))

    def make_summary (self) :
        summary = {}
        # 모니터링 대상 경기 범위
        start = datetime.strptime(self.monitor.dates[0],'%Y-%m-%d')
        end = datetime.strptime(self.monitor.dates[-1],'%Y-%m-%d')

        summary['start'] = start
        summary['end'] = end

        # 대상 리그 및 리그별 경기수
        leagues = {}
        sports = {}
        total_push = 0

        for pushes in self.monitor.monitoring.values() :
            league = pushes[0][PushElem.LEAGUE]
            total_push = total_push + len(pushes)

            sport_id = pushes[0][PushElem.SPORT_ID]
            sport = self.monitor.sportsmapper.get(sport_id)

            sports[league] = sport
            if leagues.get(league) is None :
                leagues[league] = 0
            leagues[league] = leagues[league] + 1
        
        summary['total_push'] = total_push
        summary['total_game'] = len(self.monitor.monitoring)
        summary['error_game'] = len(self.monitor.errored)
        
        # 대상 총 푸쉬 대비 에러 푸쉬수 & 에러 타입
        error_push = 0
        error_type = {}
        for id,types in self.monitor.error_type.items() :
            error_push = error_push + len(types)
            for type in types :
                key = type[0].upper()
                if error_type.get(key) is None :
                    error_type[key] = 0
                error_type[key] = error_type[key] +1

        if len(error_type) == 0 :
            error_type = None

        summary['error_push'] = error_push

        template = self.env.get_template('summary.html')
        if error_type is not None :
            output = template.render(summary = summary, leagues = leagues,sports = sports,error_type = error_type)
            html = MIMEText(output,'html')
            self.msg.attach(html)
            self.make_err_map_chart(error_type.keys())
        else :
            output = template.render(summary = summary, leagues = leagues,sports = sports,error_type = error_type)
            html = MIMEText(output,'html')
            self.msg.attach(html)

        
        return output

    def make_monitor_chart(self) :

        monitoring = []

        for id,pushes in self.monitor.monitoring.items() :
            game = pushes[-1]
            game = list(game)

            sport = self.monitor.sportsmapper.get(game[PushElem.SPORT_ID])
            game[PushElem.SPORT_ID] = sport

            for i in range(0,5) :
                game.pop()

            if id in self.monitor.checked :
                game.append("정상")
                game.append("0/" + str(len(pushes)))
                game.append("")
            else :
                game.append("에러")
                print(id)
                game.append(str(len(self.monitor.error_type.get(id))) +"/"+ str(len(pushes)))

                type_dic = {}
                for error in self.monitor.error_type.get(id) :
                    type = error[0]
                    if type_dic.get(type) is None :
                        type_dic[type] = 0
                    type_dic[type] = type_dic[type] + 1
                str_types = ""
                for type,num in type_dic.items() :
                    str_types = str_types + type + "(" + str(num) + "), "
                str_types = str_types[:len(str_types)-2]
                game.append(str_types.upper())
            
         
            monitoring.append(game)

        monitoring = sorted(monitoring, key=lambda x: (x[-3],x[PushElem.LEAGUE]))
        
        output =""
        game_list = []
        for i,game in enumerate(monitoring) :
            chart = {}
            game.insert(0,i+1)

            chart['num'] = game[ChartHeadElem.NUM]
            chart['id'] = game[ChartHeadElem.ID]
            chart['s_time'] = game[ChartHeadElem.START_TIME]
            chart['league'] = game[ChartHeadElem.LEAGUE]
            chart['sport'] = game[ChartHeadElem.SPORT]
            chart['home'] = game[ChartHeadElem.HOME]
            chart['away'] = game[ChartHeadElem.AWAY]
            chart['e_time'] = game[ChartHeadElem.LOG_TIME]
            chart['is_err'] = game[ChartHeadElem.IS_ERR]
            chart['err_push'] = game[ChartHeadElem.ERR_PUSH]
            chart['err_type'] = game[ChartHeadElem.ERR_TYPE]

            game_list.append(chart)

        template = self.env.get_template('chart_monitor.html')
        output = template.render(game_list = game_list)
        self.msg.attach(MIMEText(output,'html'))


    def make_err_detail(self) :
        
        err_games = self.monitor.errored.values()
        err_games = sorted(err_games, key=lambda x: (x[0][PushElem.LEAGUE]))

        for num,pushes in enumerate(err_games) :
            t_game = {}
            t_game['league'] = pushes[-1][PushElem.LEAGUE]
            t_game['home'] = pushes[-1][PushElem.HOME]
            t_game['away'] = pushes[-1][PushElem.AWAY]
            t_game['num'] = num +1
            id = pushes[-1][PushElem.ID]
            t_game['id'] = id

            err_pushes = []
            err_push_num = []
            for info in self.monitor.error_type.get(id) :
                err = {}
                type = info[0]
                msg = self.monitor.error_msg_mapper.get(type)
                err['msg']= msg
                err['num'] = info[1]
                err_push_num.append(info[1])
                err_pushes.append(err)
            
            err_pushes = sorted(err_pushes, key=itemgetter('num'))

            push_list = []
            for i,push in enumerate(pushes) :
                t_push = {}
                t_push['id'] = push[PushElem.ID]
                t_push['s_time'] = push[PushElem.START_TIME]
                t_push['league'] = push[PushElem.LEAGUE]
                t_push['sport'] = self.monitor.sportsmapper.get(push[PushElem.SPORT_ID])
                t_push['home'] = push[PushElem.HOME]
                t_push['away'] = push[PushElem.AWAY]
                t_push['log_time'] = push[PushElem.LOG_TIME]
                t_push['status'] = push[PushElem.STATUS]
                t_push['state'] = push[PushElem.STATE]
                t_push['scores'] = push[PushElem.SCORES]
                t_push['extra_score_flag'] = push[PushElem.EXT_SCORE_FLAG]
                t_push['extra_scores'] = push[PushElem.EXT_SCORE_INFO]

                if i+1 in err_push_num :
                    t_push['errPush'] = True
                else :
                    t_push['errPush'] = False
                push_list.append(t_push)
            
            template = self.env.get_template('err_push.html')
            output = template.render(game = t_game, errs =err_pushes , pushes=push_list)
            self.msg.attach(MIMEText(output,'html'))


    # just do the function on Sundays
    def print_plot(self) :
        today = datetime.strptime(self.monitor.dates[0],'%Y-%m-%d')

        path = self.monitor.log_path

        config = configparser.ConfigParser()
        config.optionxform = str
        config.read(path)

        #setting font in the graph
        font_fname = '/home/ibs/Monitoring/sportAlert/Configuration/NanumBarunGothic.ttf'
        fp = fm.FontProperties(fname=font_fname)
        font_family = fm.FontProperties(fname=font_fname).get_name()
        plt.rcParams['font.family'] = 'NanumGothic'
        plt.rcParams['font.size'] = 9
        plt.rcParams['figure.figsize'] = [5, 6]

        #graph 1
        dates = []
        tot_game = []
        err_game = []
        non_err_game = []

        n_date = datetime.strptime(self.monitor.dates[0],"%Y-%m-%d")

        for i in range(0,14) :
            date = n_date - timedelta(days = (13-i))
            key = str(date.month) + "-" + str(date.day)
            dates.append(str(date.day) + "일")
    
            tot_game.append(int(config['tot_game'][key]))
            err_game.append(int(config['err_game'][key]))
            non_err_game.append(int(config['tot_game'][key]) - int(config['err_game'][key]))
        
        headers = ['에러 경기수','정상 경기수']
        df = pd.DataFrame(np.array([err_game,non_err_game]).T.tolist(),index = dates,columns = headers)
        ax1 = df.plot.bar( stacked = True,color=["lightcoral",'palegreen'])

        for p in ax1.patches :
            left, bottom, width, height = p.get_bbox().bounds
            if height >0 :
                ax1.annotate("%d"%(height), (left+width/2, height/2+bottom), ha='center')

        plt.title(self.monitor.log_s_date.strftime("%m월 %d일") + " ~ " + today.strftime("%m월 %d일 경기 모니터링 결과"),fontsize = 13)
        ax1.tick_params (axis = 'x', labelrotation =0)
        ax1.tick_params (axis = 'x', labelsize =8)       
        graph1 =  'graph1' + self.monitor.log_s_date.strftime("%m%d") + today.strftime("%m%d") + '.png'
        plt.savefig(graph1)
        self.images.append(graph1)

        #graph2
        tot_push = []
        err_push = []
        non_err_push = []

        for i in range(0,14) :
            date = n_date - timedelta(days = (13-i))
            key = str(date.month) + "-" + str(date.day)
    
            tot_push.append(int(config['tot_push'][key]))
            err_push.append(int(config['err_push'][key]))
            non_err_push.append(int(config['tot_push'][key]) - int(config['err_push'][key]))
        
        headers = ['에러 푸쉬수','정상 푸쉬수']
        df = pd.DataFrame(np.array([err_push,non_err_push]).T.tolist(),index = dates,columns = headers)
        ax2 = df.plot.bar(stacked = True,color = ['lightcoral','palegreen'])
        ax2.tick_params (axis = 'x', labelrotation =0)
        ax2.tick_params (axis = 'x', labelsize =8)
        for p in ax2.patches :
            left, bottom, width, height = p.get_bbox().bounds
            if height >0 :
                ax2.annotate("%d"%(height), (left+width/2, height/2+bottom), ha='center')
        plt.title(self.monitor.log_s_date.strftime("%m월 %d일") + " ~ " + today.strftime("%m월 %d일 푸쉬 모니터링 결과"),fontsize = 13)
        graph2 = 'graph2' + self.monitor.log_s_date.strftime("%m%d") + today.strftime("%m%d") + '.png'
        plt.savefig(graph2)
        self.images.append(graph2)

        # graph3 
        err_type = []
        tmp = {}
        for i in range(0,14) :
            date = n_date - timedelta(days = (13-i))
            key = str(date.month) + "-" + str(date.day)
            
            errs = config['err_num'][key]
            if errs == "" :
                continue

            errs = errs.split(",")
            for err in errs :
                err_ = err.split("/")[0]
                num_ = int(err.split("/")[1])
                if tmp.get(err_) is None :
                    tmp[err_] = 0
                tmp[err_] = tmp[err_] + num_
    
        for err,num in tmp.items() :
            err_type.append([err.upper(),int(num)])

        headers = ['에러 타입','갯수']
        df = pd.DataFrame(err_type,columns = headers)   
        df = df.sort_values(by='갯수', ascending = False)
        ax3 = df.plot.bar(x = '에러 타입', y = '갯수',color = 'lightcoral')
        ax3.set_xticklabels(df['에러 타입'],rotation=20)
        ax3.tick_params (axis = 'x', labelsize =8)
        for p in ax3.patches :
            left, bottom, width, height = p.get_bbox().bounds
            ax3.annotate("%d"%(height), (left+width/2, height), ha='center')
        plt.title(self.monitor.log_s_date.strftime("%m월 %d일") + " ~ " + today.strftime("%m월 %d일 에러푸쉬 타입 모니터링 결과"),fontsize = 12)
        graph3 = 'graph3' + self.monitor.log_s_date.strftime("%m%d") + today.strftime("%m%d") + '.png'
        plt.savefig(graph3)
        self.images.append(graph3)

        for i in range(1,4) :
            i = str(i)
            path = 'graph' + i +  self.monitor.log_s_date.strftime("%m%d") + today.strftime("%m%d") +  ".png"
            with open(path, 'rb') as fp :
                img = MIMEImage(fp.read())
                img.add_header('Content-ID','<capture>')
                self.msg.attach(img)
        
        types = []
        for row in err_type :
            types.append(row[0])
        self.make_err_map_chart(types)


    def make_body(self) :
        self.make_summary()
        self.make_monitor_chart()
        self.make_err_detail()

        if len(self.monitor.dates)>1 :
            return
        
        self.print_plot()

    def erase_file(self) :        
        for image in self.images :
          
            if os.path.isfile(image):
                os.remove(image)
         

    def send_mail(self) :
   
        self.msg['Subject'] = '스포츠 알람 push 모니터링 결과' + str(self.monitor.dates)
        recipients =  ['yeram.kim@lge.com','joohyun.seo@lge.com','kwon.wookeun@lge.com', 'lorin.jeoung@lge.com','warner.lee@lge.com','kyungmee.lee@lge.com']
        self.msg['To'] = 'yeram.kim@lge.com,joohyun.seo@lge.com,kwon.wookeun@lge.com,warner.lee@lge.com,lorin.jeoung@lge.com'
        self.msg['From'] = 'aws.sports.monitoring@gmail.com'
        self.msg['CC'] = 'kyungmee.lee@lge.com'
        
        server = smtplib.SMTP('lgekrhqmh01.lge.com',25)
        server.connect('lgekrhqmh01.lge.com')

        server.sendmail(self.msg['From'],recipients,self.msg.as_string().encode('utf-8'))
        server.quit()

        self.erase_file()

    def test_send_mail(self) :

        self.msg['Subject'] = '스포츠 알람 push 모니터링 결과 TEST 버전' 
        self.msg['To'] = 'yeram.kim@lge.com'
        self.msg['From'] = 'aws.sports.monitoring@gmail.com'
        
        server = smtplib.SMTP('lgekrhqmh01.lge.com',25)
        server.connect('lgekrhqmh01.lge.com')

        server.sendmail(self.msg['From'],self.msg['To'],self.msg.as_string().encode('utf-8'))
        server.quit()

        self.erase_file()

"""
date = ['2022-01-13']
config_path = './Configuration/config.ini'    
monitor = MiniMonitor2(config_path)
monitor.dates = date
monitor.get_push_list_from_db(date)
monitor.check_db_push()  
email = SendMail(monitor)
email.make_body()
email.test_send_mail()
"""
