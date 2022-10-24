import sys
import io
import os
from apscheduler.schedulers.blocking import BlockingScheduler 
import time
from datetime import timedelta,datetime
import matplotlib.font_manager as fm
from DBConnector import*
from Elem import*
import random
from SendMail import*
import traceback

sys.stdout = io.TextIOWrapper(sys.stdout.detach(), encoding = 'utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.detach(), encoding = 'utf-8')

class MiniMonitor :

    def __init__(self, config_path) :

        self.db_results = None
        self.dates = None

        self.config = configparser.ConfigParser()
        self.config.optionxform = str
        self.config.read(config_path,encoding='utf-8-sig')

        self.log_path = None
        self.log_s_date = None

        self.push_days_sql = self.config['sql']['push_days_sql']

        self.sportsmapper = {}
        for sport_id in self.config['sport_ids'] :
            self.sportsmapper[sport_id] = self.config['sport_ids'][sport_id]

        db_info = self.config['db']
        self.db_host = db_info['host']
        self.db_port = int(db_info['port'])
        self.db_user = db_info['user']
        self.db_pw = db_info['pw']
        self.def_db = db_info['db']

        self.monitoring = {} #id, pushes
        self.nonmonitoring = {}
        self.checked = {} # checked push (id, pushes)
        self.errored = {} # error push (id, pushes)
        self.error_type = {} # error message (key : id, value : list of error types)
        self.error_msg_mapper = {} # error message mapper (key: error id, value : error message)
        self.first_state = {} # first state of sport (key: sport, value : first state)
        for type,msg in self.config['error_msg'].items() :
            self.error_msg_mapper[type] = msg

        for sport,state in self.config['first_state'].items() :
            self.first_state[sport] = state.split(",")

    def check_whether_monitoring(self, game_push) :

        if len(game_push) == 0:
            return

        starttime = (game_push[-1][PushElem.START_TIME]).strftime("%Y-%m-%d")
        endtime = (game_push[-1][PushElem.LOG_TIME]).strftime("%Y-%m-%d")
        end_status = game_push[-1][PushElem.STATUS]
        id = game_push[0][PushElem.ID]
        league = game_push[0][PushElem.LEAGUE]


        if 'WGC' in league:
           self.nonmonitoring[id] = game_push
           return

        if starttime < self.dates[0] :
            if endtime < self.dates[-1] and (end_status == 'COMPLETED' or end_status == 'STOP_PLAYING') :
                self.nonmonitoring[id] = game_push
            else :
                self.monitoring[id] = game_push

        elif (starttime == self.dates[-1]) and (end_status != 'COMPLETED' and end_status !='STOP_PLAYING') :
                self.nonmonitoring[id] = game_push
        
        else :
            if endtime  == self.dates[-1] :
                self.monitoring[id] = game_push
            else :
                self.nonmonitoring[id] = game_push

    def split_game_push(self, results) :

        game_push = []

        if len(results) >0 :
            b_id = results[0][PushElem.ID]

        id = -1
        for result in results :
            sport_id = result[PushElem.SPORT_ID]
           
            if self.sportsmapper.get(sport_id) is None :
                continue

            id = result[PushElem.ID]

            if id != b_id :
                if len(game_push) > 0 :                    
                    #n_results[b_id] = game_push
                    self.check_whether_monitoring(game_push)
                    game_push = []

            game_push.append(result)
            b_id = id

        self.check_whether_monitoring(game_push)

    def get_push_list_from_db(self, dates) :

        self.dates = dates
        connec = DBConnector(self.db_host,self.db_port,self.db_user,self.db_pw,self.def_db)
        start = dates[0]
        end = dates[-1]        
        yesterday = (datetime.strptime(start,"%Y-%m-%d") - timedelta(days=1)).strftime('%Y-%m-%d')

        sql = self.push_days_sql

        vars = [yesterday, end]

        results = connec.execute_sql(sql, vars)

        self.db_results = results 
        self.split_game_push(results)

    def put_error_msg(self, id, game_push,type, index, push) :

        if self.error_type.get(id) is None :
            self.error_type[id] = []

        self.error_type[id].append([type,index, push])
        self.errored[id] = game_push
        
        if self.checked.get(id) is not None :
            del self.checked[id]

    def check_default(self, game_push) :                                               
        
        id = game_push[0][PushElem.ID]
        sport_id = game_push[0][PushElem.SPORT_ID]
        sport = self.sportsmapper.get(sport_id)
        ex_h_score = 0
        ex_a_score = 0
        self.checked[id] = game_push

        for i,push in enumerate(game_push) :
            if sport != 'GOLF' :
                scores = push[PushElem.SCORES]
                home_score = scores.split(":")[1].replace(" ","").split("/")[0]
                away_score = scores.split(":")[0].replace(" ","").split("/")[0]
            
            if i == 0 :
                if push[PushElem.STATUS] != 'BEFORE_MATCH' :
                    type = 'common1'
                    self.put_error_msg(id, game_push,type, i+1, push)
                
                state = self.first_state[sport]

                
                if push[PushElem.STATE] not in state and push[PushElem.STATE] != "" :
                    type = 'common2'
                    self.put_error_msg(id, game_push, type,i+1, push)

                if  push[PushElem.SCORES] != "" and ((sport != 'CRICKET' and (home_score != '0' or away_score != '0')) or (sport == 'CRICKET' and (scores != '0/0 : 0/0'))) : 
                    type  = "common3"
                    self.put_error_msg(id,game_push, type, i+1,push)
            
            if i>0 and i< len(game_push) - 1 :
                if (push[PushElem.STATUS] != 'IN_PROGRESS' and push[PushElem.STATUS] != 'PAUSE_PLAYING' and push[PushElem.STATUS] != 'RESUME_PLAYING') :
                    type = "common4"
                    self.put_error_msg(id,game_push, type,i+1, push)

                if sport != 'BASKETBALL' and sport != 'GOLF'  and push[PushElem.STATUS] != 'PAUSE_PLAYING' and push[PushElem.STATUS] != 'RESUME_PLAYING' and push[PushElem.STATE] != 'PSO' and  ((ex_h_score == home_score) and (ex_a_score == away_score)) :
                    type = "common5"
                    self.put_error_msg(id, game_push, type,i+1, push)

                if sport != 'BASKETBALL' and sport != 'CRICKET' and sport != 'GOLF' and push[PushElem.STATUS] == 'PAUSE_PLAYING' and not (ex_h_score == home_score and ex_a_score == away_score) :
                    type = "common8"
                    self.put_error_msg(id, game_push, type, i+1, push)

                if push[PushElem.STATUS] == 'RESUME_PLAYING' :
                    if game_push[i-1][PushElem.STATUS] != 'PAUSE_PLAYING' :
                        type = "common9"
                        self.put_error_msg(id, game_push, type, i+1, push)
                    if sport != 'GOLF' and sport != 'CRICKET' and push[PushElem.STATE] != game_push[i-1][PushElem.STATE] :
                        type = "common10"
                        self.put_error_msg(id, game_push, type, i+1, push)

                if sport != 'GOLF' and (int(home_score) < int(ex_h_score)  or int(away_score)   < int(ex_a_score)) :
                    type = "notice1"
                    self.put_error_msg(id, game_push, type,i+1, push)

            if i == len(game_push) -1 :
                if push[PushElem.STATUS] == 'STOP_PLAYING' :
                    type = 'notice3'
                    self.put_error_msg(id, game_push, type, i+1,push)
                elif push[PushElem.STATUS] != 'COMPLETED' :
                    type = "common6"
                    self.put_error_msg(id,game_push, type,i+1, push)
                elif sport != 'GOLF' and sport != 'CRICKET' and (ex_h_score != home_score or ex_a_score != away_score) :
                    type = "common7"
                    self.put_error_msg(id, game_push,type,i+1,push)

            if sport != 'GOLF' :
                ex_h_score = home_score
                ex_a_score = away_score

    def check_baseball(self, game_push) :

        ex_h_score = 0
        ex_a_score = 0

        for i,push in enumerate(game_push) :

            id = game_push[0][PushElem.ID]
            scores = push[PushElem.SCORES]
            home_score = int(scores.split(":")[1])
            away_score = int(scores.split(":")[0])
            turn = push[PushElem.STATE][-1]

            if turn == '▲' :
                away_turn = True
                home_turn = False
            if turn == '▼'  :
                away_turn = False
                home_turn = True

            # middle push
            if i>0 and i<len(game_push) -1 :
                h_diff = home_score - ex_h_score
                a_diff = away_score - ex_a_score

                if home_turn is True :
                    if (a_diff > 0) :
                        type = "baseball1"
                        self.put_error_msg(id, game_push,type,i+1,push)
                        
                if away_turn is True :
                    if (h_diff > 0) :
                        type = "baseball2"
                        self.put_error_msg(id, game_push,type,i+1,push)

                if (h_diff >4) or( a_diff >4) :
                    type = "baseball3"
                    self.put_error_msg(id, game_push, type,i+1, push)

            #last push
            if i == len(game_push) - 1 :
                order = int(push[PushElem.STATE][0:-1])

                if order == 9 and (away_turn is True) and home_score <= away_score :
                    category = "baseball4"
                    self.put_error_msg(id, game_push,category,i+1,push)      

                if order <= 8 :
                    category = "notice2"
                    self.put_error_msg(id, game_push,category,i+1,push)

            ex_h_score = home_score
            ex_a_score = away_score

    def check_football(self, game_push) :

        ex_h_score = 0
        ex_a_score = 0
        id = game_push[0][PushElem.ID]

        for i,push in enumerate(game_push) :
            
            scores = push[PushElem.SCORES]
            state = push[PushElem.STATE]
            home_score = int(scores.split(":")[1])
            away_score = int(scores.split(":")[0])
            
            if i>0 and push[PushElem.STATUS] == 'IN_PROGRESS':
                h_diff = abs(home_score - ex_h_score)
                a_diff = abs(away_score - ex_a_score)

                if state != 'PSO' : 
                    if not ((h_diff == 1 and a_diff == 0) or (a_diff==1 and h_diff==0)) :
                        type = "football1"
                        self.put_error_msg(id, game_push, type,i+1, push)

                    ex_h_score = home_score
                    ex_a_score = away_score        

                else :
                    ext_flag = push[PushElem.EXT_SCORE_FLAG]      
                    
                    scores = push[PushElem.EXT_SCORE_INFO]
                    home_score = int(scores.split(":")[1])
                    away_score = int(scores.split(":")[0])
                    
                    ex_scores = game_push[i-1][PushElem.EXT_SCORE_INFO] 
                    ex_h_score = 0
                    ex_a_score = 0

                    if not(ex_scores is None) and ex_scores != '' :
                        ex_h_score = int(ex_scores.split(":")[1])
                        ex_a_score = int(ex_scores.split(":")[0])

                    h_diff = home_score - ex_h_score 
                    a_diff = away_score - ex_a_score

                    if ext_flag != 'Y' :
                        type = 'football2'
                        self.put_error_msg(id, game_push, type, i+1,push)

                    if not ((h_diff == 1 and a_diff == 0) or (a_diff==1 and h_diff==0)) :
                        type = "football1"
                        self.put_error_msg(id, game_push, type,i+1, push)
                


    def check_basketball(self, game_push) :

        id = game_push[0][PushElem.ID]

        before_state = '0Q'
        nxt_state = { '0Q' : '1Q', '1Q':'2Q', '2Q' :'3Q', '3Q':'4Q', '4Q':'1OT', '1OT':'2OT', '2OT':'3OT', '3OT':'4OT'}

        for i,push in enumerate(game_push) :
            status = push[PushElem.STATUS]
            state = push[PushElem.STATE]

            if status == 'COMPLETED' :
                if state != before_state :
                   type = 'basketball2'
                   self.put_error_msg(id,game_push,type,i+1,push)
                
            elif status == 'IN_PROGRESS' :

                if state != nxt_state[before_state] :
                    type = "basketball1"
                    self.put_error_msg(id,game_push,type,i+1,push)
                before_state = state
    
    def check_australianfootball(self,game_push) :

        id = game_push[0][PushElem.ID]
        state_value = {'1Q' : 1, '2Q':2, '3Q':3, '4Q' :4, '1OT' :5} 

        for i,push in enumerate(game_push) :
            status = push[PushElem.STATUS]
            state = push[PushElem.STATE]

            scores = push[PushElem.SCORES]            
            home_score = int(scores.split(":")[1])
            away_score = int(scores.split(":")[0])                

                
            if status == 'IN_PROGRESS' and i > 1 :
                ex_state = game_push[i-1][PushElem.STATE]

                if state_value.get(ex_state) > state_value.get(state) :
                    type = "aust1"
                    self.put_error_msg(id,game_push,type,i+1,push)

                ex_scores = game_push[i-1][PushElem.SCORES]
                h_diff = abs(home_score - int(ex_scores.split(":")[1]))
                a_diff = abs(away_score - int(ex_scores.split(":")[0]))

                if not(( h_diff in [1,6] and a_diff==0)  or  ( a_diff in [1,6] and h_diff==0)):
                    type = "aust2"
                    self.put_error_msg(id,game_push,type,i+1,push)

    
    def check_rugbyleague(self,game_push) :

        id = game_push[0][PushElem.ID]
        state_value = {'1HALF' : 1, '2HALF':2, '1OT':3} 

        for i,push in enumerate(game_push) :
            status = push[PushElem.STATUS]
            state = push[PushElem.STATE]

            scores = push[PushElem.SCORES]            
            home_score = int(scores.split(":")[1])
            away_score = int(scores.split(":")[0])                

                
            if status == 'IN_PROGRESS' and i > 1 :
                ex_state = game_push[i-1][PushElem.STATE]

                if state_value.get(ex_state) > state_value.get(state) :
                    type = "rugby1"
                    self.put_error_msg(id,game_push,type,i+1,push)

                ex_scores = game_push[i-1][PushElem.SCORES]
                h_diff = abs(home_score - int(ex_scores.split(":")[1]))
                a_diff = abs(away_score - int(ex_scores.split(":")[0]))

                if not(( h_diff in [1,2,4] and a_diff==0)  or  ( a_diff in [1,2,4] and h_diff==0)):
                    type = "rugby2"
                    self.put_error_msg(id,game_push,type,i+1,push)


    def check_americanfootball(self, game_push) :
        
        id = game_push[0][PushElem.ID]
        ex_h_score = -1
        ex_a_score = -1

        for i, push in enumerate(game_push) :
                
            scores = push[PushElem.SCORES]            
            home_score = int(scores.split(":")[1])
            away_score = int(scores.split(":")[0])                

            if i>0 and i<len(game_push)-1 :
                
                h_diff = home_score - ex_h_score
                a_diff = away_score - ex_a_score

                if (a_diff== 0 and (not h_diff in [1,2,3,6]) and h_diff>0)  or  (h_diff == 0 and (not a_diff in [1,2,3,6]) and a_diff>0) :
                    type = "amefoot1"
                    self.put_error_msg(id,game_push,type,i+1,push)

            ex_h_score = home_score
            ex_a_score = away_score

    def check_cricket (self, game_push) :

        change = len(game_push) # attack, defend change push index
        b_state = 0
        b_away = 0
        b_home = 0
        prior = None
        b_prior = None
        before = None
        later = None

        for i, push in enumerate(game_push) :

            id = game_push[0][PushElem.ID]
            state = push[PushElem.STATE]
            num_state = int(state.replace("Overs","").split(".")[0])
            scores = push[PushElem.SCORES]
            home = int(scores.split(":")[1].split("/")[0])
            away = int(scores.split(":")[0].split("/")[0])

            if before is None :
                if home - b_home > 0 :
                    before = "HOME"

                if away - b_away > 0 :
                    before = "AWAY"

            if before is not None and before == 'HOME' :
                prior = home
                b_prior = b_home
                later = away

            if before is not None and before == 'AWAY' :
                prior = away
                b_prior = b_away
                later = home

            # prior push before change push
            if 0<i and b_state <= num_state and i<change :

                if not (prior >= 50*i  and prior <50*(i+1)):
                    type = "cricket1"
                    self.put_error_msg(id, game_push, type,i+1, push)

                if later != 0 :
                    type = "cricket4" 
                    self.put_error_msg(id, game_push, type,i+1, push)

            # change push
            if b_state > num_state :
                change = i 
                if num_state != 0 or later != 0 :
                    type = "cricket3"
                    self.put_error_msg(id,game_push,type,i+1,push)

                if not(50*(i-1)< prior and prior <50*i) :
                    type = "cricket5"
                    self.put_error_msg(id, game_push, type,i+1, push)

            # after change push
            if i> change :
                if i < len(game_push)-1 and not (later >= (i-change) and later < 50*(i+1-change)) :
                    type = "cricket1"
                    self.put_error_msg(id, game_push, type,i+1, push)
                if prior != b_prior :
                    type = "cricket4" 
                    self.put_error_msg(id, game_push, type,i+1, push)
            
            if i == len(game_push) -1  and not (later>50*(i-1-change) and later< 50*(i-change)) :
                type = "cricket5"
                self.put_error_msg(id, game_push, type,i+1, push)
    
            b_state = num_state
            b_away = away
            b_home = home

        if change == len(game_push) and (later <= 50*(i-1-change) or later >= 50*(i-change)) :
            type = "cricket2"
            self.put_error_msg(id, game_push, type,i+1, push)

    def check_golf(self, game_push) :

        id = game_push[0][PushElem.ID] 
        b_time = game_push[0][PushElem.LOG_TIME]

        for i,push in enumerate(game_push) :
            status = push[PushElem.STATUS]
            time = push[PushElem.LOG_TIME]
            diff = (time - b_time).seconds / 60
            
            if i == 1 and status == 'IN_PROGRESS':
                if not (diff>=30 and diff<=32) :
                    type = "golf1"
                    self.put_error_msg(id, game_push, type,i+1, push)

            if i>1 and i <len(game_push)-1 and  status == 'IN_PROGRESS' :
                pre_push = game_push[i-1]
                if not (diff >=29 and diff <=31) and pre_push[PushElem.STATUS] != 'RESUME_PLAYING':
                    type = "golf2"
                    self.put_error_msg(id, game_push, type,i+1, push)

            if i == len(game_push)-1 and status == 'COMPLETED' :
                if diff >30 :
                    type = "golf3"
                    self.put_error_msg(id, game_push, type,i+1, push)
            b_time = time

    def check_db_push(self) :

        for id,game_push in self.monitoring.items() :      
   
            sport_id = game_push[0][PushElem.SPORT_ID]
            sport = self.sportsmapper.get(sport_id)
            league = game_push[0][PushElem.LEAGUE]
 
            if sport == 'BASEBALL' :
                self.check_default(game_push)
                self.check_baseball(game_push)
            
            elif sport == 'BASKETBALL' :
                self.check_default(game_push)
                self.check_basketball(game_push)        
    
            elif sport == 'FOOTBALL' :
                self.check_default(game_push)
                self.check_football(game_push)

            elif sport == 'AMERICAN FOOTBALL' :
                self.check_default(game_push)
                self.check_americanfootball(game_push)

            elif sport == 'AUSTRALIAN FOOTBALL' :
                self.check_default(game_push)
                self.check_australianfootball(game_push)
            
            elif sport == 'RUGBY LEAGUE' :
                self.check_default(game_push)
                self.check_rugbyleague(game_push)

            elif sport == 'ICEHOCKEY' :
                self.check_default(game_push)
                self.check_football(game_push) 

            elif sport == 'GOLF'  :
                self.check_default(game_push)
                self.check_golf(game_push)
            
            elif sport == 'CRICKET' :
                self.check_default(game_push)                         
                self.check_cricket(game_push)
            
            else :
                print('없는 sport가 존재합니다.')
                for push in game_push :
                    print(push)

    def record_log(self) :

        if len(self.dates) > 1 :
            return
        
        n_date = datetime.strptime(self.dates[0],"%Y-%m-%d")
        self.log_s_date = n_date - timedelta(days = 13)
        
        path = "./Configuration/recordlog.ini"
        self.log_path = path

        config = configparser.ConfigParser()
        config.optionxform = str
                  
        #record log
        config.read(path)                
        with open(path,'w+') as file :
            tot_push = 0
            for pushes in self.monitoring.values() :
                tot_push = tot_push + len(pushes)

            err_push = 0
            for pushes in self.error_type.values() :
                err_push = err_push + len(pushes)
            
            now = str(n_date.month) +"-"+ str(n_date.day)
            config.set('tot_game',now,str(len(self.monitoring)))
            config.set('err_game',now,str(len(self.errored)))
            config.set('tot_push',now,str(tot_push))
            config.set('err_push',now,str(err_push))

            err_type = {}
            for list in self.error_type.values() :
                for info in list :
                    type = info[0]
                    if err_type.get(type) is None :
                        err_type[info[0]] = 0 
                    err_type[info[0]] = err_type[info[0]] + 1
            
            errs = ""
            for type,num in err_type.items() :
                errs = errs + type + "/" + str(num) +","
            errs = errs[:-1]
            config.set('err_num',now,errs)   
            config.write(file)
            

def verify() :

    config_path = './Configuration/config.ini'
    dates = [(datetime.utcnow() - timedelta(days=1)).strftime('%Y-%m-%d')]    
    monitor = MiniMonitor(config_path)
    monitor.get_push_list_from_db(dates)
    monitor.check_db_push()  
    monitor.record_log()  
    email = SendMail(monitor) 
    email.make_body()
    email.send_mail()
    #email.test_send_mail()


def verify_2(dates) :
    config_path = './Configuration/config.ini'    
    monitor = MiniMonitor(config_path)
    monitor.get_push_list_from_db(dates)

    monitor.check_db_push()
    monitor.record_log()  
    email = SendMail(monitor)
    email.make_body()
    email.send_mail()
    #email.test_send_mail()


"""
try : 

    verify_2(['2022-02-11'])
    #verify()

except :
    SendMail.send_simple_mail('에러 로그 메일',traceback.format_exc())
    print(traceback.format_exc())


"""
try : 
    sched = BlockingScheduler()
    sched.add_job(verify, trigger = 'cron', hour = '10', id = "op",misfire_grace_time=300)
    sched.start()
except :
    SendMail.send_simple_mail('에러 로그 메일',traceback.format_exc())
    print(traceback.format_exc())
