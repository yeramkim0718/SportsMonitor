from enum import IntEnum,Enum

class SportsElem(Enum) :
    BASEBALL = 'BASEBALL'
    FOOTBALL = 'FOOTBALL'
    AMERICANFOOTBALL = 'AMERICAN FOOTBALL'
    BASKETBALL = 'BASKETBALL'
    ICEHOCKEY = 'ICEHOCKEY'
    CRICKET = 'CRICKET'

class PushElem(IntEnum) :
    ID = 0
    START_TIME = 1
    LEAGUE = 2
    SPORT_ID = 3
    HOME = 4
    AWAY = 5
    LOG_TIME = 6
    
    STATUS = 7
    STATE = 8
    SCORES = 9
    EXT_SCORE_FLAG = 10
    EXT_SCORE_INFO = 11

class ChartHeadElem(IntEnum) : 
    NUM = 0
    ID = 1
    START_TIME = 2
    LEAGUE = 3
    SPORT = 4
    HOME = 5
    AWAY = 6
    LOG_TIME = 7
    IS_ERR = 8
    ERR_PUSH = 9
    ERR_TYPE = 10

class DBElem(IntEnum) :
    ID = 0
    TIME = 1
    STATUS = 2
    HOME = 3
    HOME_SCORE = 4
    AWAY = 5
    AWAY_SCORE = 6
    LEAGUE = 7
    SPORT = 8

class WEBElem(IntEnum) :
    TIME = 0
    HOME = 1
    AWAY = 2
    HOME_SCORE = 3
    AWAY_SCORE = 4