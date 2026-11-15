"""Guidance from WDA recognition criteria, never a legal determination."""
from datetime import date, timedelta
from pydantic import BaseModel, Field, model_validator
from typing import Literal

SOURCE='https://fw.wda.gov.tw/wda-employer/home/download-file/2c95efb3882b4eb201882d403147023b.pdf'
class WorkDay(BaseModel):
    day: date
    scheduled: bool
    absent: bool | None = None
    justified: bool | None = None

class Guide(BaseModel):
    today: date
    today_scheduled: bool
    last_attendance: date
    work_days: list[WorkDay] = Field(max_length=90)
    contact_attempted: bool
    contact_result: Literal['unreachable','uncertain','recovered']
    location_verified: bool
    accommodation_period_verified: bool
    contact_method_verified: bool
    sought_1955: bool = False
    relationship_active: bool = True
    special_period: bool = False
    @model_validator(mode='after')
    def valid(self):
        if self.last_attendance>self.today or (self.today-self.last_attendance).days>90:
            raise ValueError('最後出勤日須在今天之前90日內；更早請直接向主管機關確認')
        dates=[d.day for d in self.work_days]
        if len(set(dates))!=len(dates) or any(d<=self.last_attendance or d>self.today for d in dates):
            raise ValueError('每日紀錄不得重複，且須介於最後出勤翌日與今天之間')
        return self

def guide(body):
    missing=[]
    days={d.day:d for d in body.work_days}
    cur=body.last_attendance+timedelta(days=1)
    consecutive=0
    while cur<=body.today:
        d=days.get(cur)
        if not d: missing.append(cur.isoformat()+' 是否應工作及出勤狀況')
        elif d.scheduled:
            if d.absent is None or d.justified is None:
                missing.append(cur.isoformat()+' 有無到工及正當理由')
            elif d.absent and not d.justified: consecutive+=1
            else: consecutive=0
        cur+=timedelta(days=1)
    if body.today not in days or days[body.today].scheduled!=body.today_scheduled:
        missing.append('今天是否應工作，與每日紀錄須一致')
    if not body.contact_attempted: missing.append('聯絡嘗試與可核對的結果')
    verified=body.location_verified and body.accommodation_period_verified and body.contact_method_verified
    status='先聯繫及確認'
    if body.special_period or not body.relationship_active:
        status='需盡速向主管機關確認'
        missing.append('入國、許可餘期、轉換或終止等特殊期間，應由主管機關核對認定基準第六點')
    elif not missing and consecutive>=3 and body.contact_result!='recovered' and not verified:
        status='可能符合要件，請核對'
    if body.sought_1955 and not verified:
        missing.append('曾向1955求助仍需核實住宿地點、住宿期間及聯絡方式，不自動排除失去聯繫')
    if verified: explanation='已有可核實的住宿與聯絡資訊，請保留紀錄並向主管機關確認；不自動宣告行蹤不明。'
    elif body.contact_result=='recovered': explanation='聯絡已恢復，請確認本人、住宿及出勤狀況，保留紀錄。'
    else: explanation='依實際應工作日檢視連續不到工紀錄，休息日不計、週末值班要計。符合全部要件與否仍由主管機關核對。'
    return {'status':status,'missing_facts':missing,'consecutive_work_days':consecutive,'explanation':explanation,
            'next_step':'請先聯繫本人或受委任機構，整理每日出勤與聯繫紀錄，再洽新竹市政府勞工及青年處／1955 勞工諮詢申訴專線。不得扣留護照或居留證。',
            'law_ref':'就業服務法第56條、第57條第8款；受聘僱外國人連續曠職三日失去聯繫認定基準第二至六點',
            'official_url':SOURCE,'report_url':'https://fwapply.wda.gov.tw/','synthetic':True}
