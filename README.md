# SportsMonitor

스포츠 알람 모니터링 프로젝트 

각 종목의 특징 및 데이터의 형식이 맞지 않은 DB 내 데이터를 체크하여 매일 E-mail로 확인 메일 보냄. 

[error_msg]
common1 = BEFORE_MATCH(맨 처음으로 오는 push)의 status가 BEFORE_MATCH가 아닙니다.

common2 = BEFORE_MATCH(맨 처음으로 오는 push)의 state이 잘못되었습니다: 1▲(야구), 1HALF(축구, 럭비리그), 1Q(럭비, 농구,오스트리아 풋볼),  1P(아이스하키), Overs 0.0(크리켓)

common3 = BEFORE_MATCH(맨 처음으로 오는 push)의 score가 0:0 또는 0/0 : 0/0 (IPL)이 아닙니다.

common4 = push의 status가 IN_PROGRESS, PAUSE_PLAYING, RESUME_PLAYING가 아닙니다.

common5 = 직전 push와 동일한 score가 push되었습니다.

common6 = COMPLETED_MATCH(맨 마지막으로 오는 push)의 status가COMPLETED가 아닙니다.

common7 = COMPLETED_MATCH(맨 마지막으로 오는 push)의 score가 직전 push의 score와 같지 않습니다.

common8 = PAUSE_PLAYING의 score가 직전 score와 같지 않습니다.

common9 = RESUME_PLAYING의 전 push type이 PAUSE_PLAYING이 아닙니다.

common10 = RESUME_PLAYING의state이 전 state과 같지 않습니다. 

notice1 = score가 감소되었습니다. 

notice3 = 게임이 중단되었습니다. 

baseball1 = HOME턴에 AWAY팀이 득점을 하였습니다.

baseball2 = AWAY턴에 HOME팀이 득점을 하였습니다.

baseball3 = 득점이 4점을 초과하였습니다.

baseball4 = HOME팀의 점수가 AWAY팀보다 크지 않은데 9회 초에 끝났습니다.

notice2 = (야구) 게임이 8회말 이하로 끝났습니다. (우천 가능성 있음.)

football1 = 득점 1점을 초과하였습니다.

football2 = PSO(승부차기)상태에서 ext_score_flag값이 Y가 아닙니다.

rugby1 = state가 잘못되었습니다.

rugby2 = 득점이 잘못되었습니다.(1,2,4점만 가능)

aust1 = state가 잘못되었습니다.

aust2 = 득점이 잘못되었습니다. (1,6점만 가능)

basketball1 = state가 잘못되었습니다.

basketball2 = COMPLETED의 state이 직전 push의 state과 다릅니다. 

amefoot1 = 득점이 잘못되었습니다. (1,2,3,6점만 가능)

cricket1 = push의 스코어가 50간격이 아닙니다. 

cricket2 = 공수 전환 push가 존재 하지 않습니다.

cricket3 = 공수 전환 push의 초기값이 잘못되었습니다.

cricket4 = 공격, 수비의 득점이 일관되지 않습니다. 

cricket5 = 공수전환 push 또는 COMPLETED push의 점수차가 50이상입니다. 

golf1 = 처음 push의 시간차가 약 31분이 아닙니다.
golf2 = 중간 push의 시간차가 약 30분이 아닙니다.
golf3 = 마지막 push의 시간차가 30분 이하가 아닙니다. 
