import csv, json, re
from pathlib import Path
from decimal import Decimal as D
from itertools import combinations
from html.parser import HTMLParser

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / 'source-data' if (ROOT / 'source-data').exists() else ROOT.parent
def read(name):
    with (SOURCE / name).open(encoding='utf-8-sig', newline='') as f:
        rows = list(csv.DictReader(f))
    for row in rows:
        for key, val in row.items():
            try:
                n = float(val)
                row[key] = int(n) if n.is_integer() else n
            except ValueError:
                pass
    return rows
data = {'weekly':read('exhibit1_weekly_ledger.csv'), 'branches':read('exhibit2_branch_week12.csv'), 'peaks':read('exhibit2_peak_week12.csv'), 'survey':read('exhibit3_survey_week12.csv'), 'interventions':read('exhibit4_interventions.csv')}
html = ROOT / 'dist' / 'index.html'
text = html.read_text(encoding='utf-8')
serialized = json.dumps(data,ensure_ascii=False,separators=(',',':'))
text = text.replace('__DATA__',serialized)
text = re.sub(r'(<script id="source-data" type="application/json">).*?(</script>)',lambda m:m[1]+serialized+m[2],text,flags=re.S)
bulletin_source=SOURCE/'bulletin01'
with (bulletin_source/'bulletin_option_update.csv').open(encoding='utf-8-sig',newline='') as f:
    updates=list(csv.DictReader(f))
assert len(updates)==1
update=updates[0]
assert update['option']=='C'
assert D(update['one_time_cost_php_000'])==8
assert D(update['weekly_uplift_lower_php_000'])==1
assert D(update['weekly_uplift_upper_php_000'])==4
assert D(update['new_budget_php_000'])==27
class CanvasText(HTMLParser):
    def __init__(self):
        super().__init__(); self.parts=[]
    def handle_data(self,data):
        if data.strip(): self.parts.append(data.strip())
canvas=CanvasText()
canvas.feed((bulletin_source/'Canvas_Bulletin.html').read_text(encoding='utf-8-sig'))
bulletin={'kind':'official','title':'BAYANI BITE Board Bulletin 01','text':'\n\n'.join(canvas.parts),'option':update['option'],'budget':float(update['new_budget_php_000']),'lower':float(update['weekly_uplift_lower_php_000']),'upper':float(update['weekly_uplift_upper_php_000']),'cost':float(update['one_time_cost_php_000']),'sources':['BAYANI_BITE_Board_Bulletin_Minute_55.pdf','bulletin_option_update.csv','Canvas_Bulletin.html']}
bulletin_json=json.dumps(bulletin,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c')
text = re.sub(r'(<script id="bulletin-data" type="application/json">).*?(</script>)',lambda m:m[1]+bulletin_json+m[2],text,flags=re.S)
assert '__BULLETIN__' not in text
html.write_text(text,encoding='utf-8')
ledger=data['weekly']; w=ledger[-1]
def dec(r,k): return D(str(r[k]))
def net(r): return dec(r,'gross_sales_php_000')-dec(r,'discounts_php_000')-dec(r,'refunds_php_000')
def profit(r): return net(r)-dec(r,'food_cost_php_000')-dec(r,'operating_cost_php_000')
checks={}
assert net(ledger[0])==D('186') and profit(ledger[0])==D('15')
assert net(w)==D('218.3') and profit(w)==D('-34.7')
for key in ['recorded_entries','completed_orders','gross_sales_php_000','discounts_php_000','refunds_php_000','food_cost_php_000','operating_cost_php_000','stockout_incidents']:
    assert sum(dec(r,key) for r in data['branches'])==dec(w,key),key
for b,p in zip(data['branches'],data['peaks']):
    assert b['location']==p['location']
    assert p['peak_entries']+p['nonpeak_entries']==b['recorded_entries']
    assert p['peak_orders']+p['nonpeak_orders']==b['completed_orders']
by={r['option']:r for r in data['interventions']}
def calc(ids):
    cost=sum((dec(by[i],'one_time_cost_php_000') for i in ids),D(0))
    uplift=sum((dec(by[i],'weekly_uplift_lower_php_000') for i in ids),D(0))*(D('.75') if len(ids)>1 else D(1))
    return {'cost':str(cost),'weekly_uplift':str(uplift),'four_week_impact':str(4*uplift-cost),'failure_impact':str(-cost),'ongoing_weekly_profit':str(profit(w)+uplift)}
checks['before_bulletin']={'C':calc('C'),'A+C':calc('AC')}
assert checks['before_bulletin']['C']['four_week_impact']=='12' and D(checks['before_bulletin']['A+C']['four_week_impact'])==7
by={key:dict(value) for key,value in by.items()}
by['C']['weekly_uplift_lower_php_000']=D(update['weekly_uplift_lower_php_000'])
by['C']['weekly_uplift_upper_php_000']=D(update['weekly_uplift_upper_php_000'])
budget=D(update['new_budget_php_000'])
checks['after_bulletin']={'budget':str(budget),'A':calc('A'),'C':calc('C'),'A+C':calc('AC')}
assert D(checks['after_bulletin']['A']['four_week_impact'])==6
assert D(checks['after_bulletin']['A']['failure_impact'])==-18
assert D(checks['after_bulletin']['A']['ongoing_weekly_profit'])==D('-28.7')
assert D(checks['after_bulletin']['C']['four_week_impact'])==-4
assert D(checks['after_bulletin']['A+C']['weekly_uplift'])==D('5.25')
assert D(checks['after_bulletin']['A+C']['four_week_impact'])==-5
checks['initial_A+C_impact_change']=str(D(checks['after_bulletin']['A+C']['four_week_impact'])-D(checks['before_bulletin']['A+C']['four_week_impact']))
assert D(checks['initial_A+C_impact_change'])==-12
all_packages=[]
for size in range(6):
    for ids in combinations(by,size):
        result=calc(ids)
        all_packages.append({'package':'+'.join(ids) or 'Do nothing',**result,'feasible':D(result['cost'])<=budget})
assert len(all_packages)==32
feasible=[r for r in all_packages if r['feasible']]
best=max(feasible,key=lambda r:D(r['four_week_impact']))
assert best['package']=='A' and D(best['four_week_impact'])==6
checks['all_package_checks']={'subsets_checked':32,'feasible_count':len(feasible),'highest_feasible_impact_package':best['package'],'highest_feasible_impact':best['four_week_impact'],'recommended_package_has_positive_incremental_profit':D(best['four_week_impact'])>0}
checks['all_packages_after_bulletin']=all_packages
checks['authoritative_bulletin_sources']=bulletin['sources']
checks['independent_method']='Python Decimal arithmetic directly from supplied CSVs; not AI agreement'
checks['week1']={'net_revenue':str(net(ledger[0])),'operating_profit':str(profit(ledger[0])),'orders_per_entry_percent':1260/2100*100}
checks['week12']={'net_revenue':str(net(w)),'operating_profit':str(profit(w)),'orders_per_entry_percent':1400/3600*100}
checks['week13_forecast']=sum(r['completed_orders'] for r in ledger[9:12])/3
checks['week12_earlier_only_prediction']=sum(r['completed_orders'] for r in ledger[8:11])/3
checks['week12_absolute_error']=abs(w['completed_orders']-checks['week12_earlier_only_prediction'])
assert checks['week13_forecast']==1430 and checks['week12_earlier_only_prediction']==1450 and checks['week12_absolute_error']==50
checks['branch_totals_match_week12']=True
checks['daypart_partitions_match_branches']=True
(ROOT/'verification.json').write_text(json.dumps(checks,indent=2),encoding='utf-8')
record={'case':'BAYANI BITE','status':'Final recommendation under supplied Bulletin 01','units':'PHP thousands','budget':str(budget),'bulletin':bulletin,'retained_initial':{'package':'A+C',**checks['before_bulletin']['A+C']},'retained_initial_under_bulletin':{'package':'A+C',**calc('AC')},'initial_impact_change':checks['initial_A+C_impact_change'],'chosen':{'package':'A',**calc('A')},'alternative':{'package':'A+C',**calc('AC')},'planning_objective':{'period':'Weeks 13–16','incremental_profit_after_setup':'greater than zero versus doing nothing','budget_cap':27,'choose_highest_feasible_planning_benefit':True,'recommended_plan_meets_financial_criteria':True,'actual_outcomes':'Not yet observed; assess during pilot'},'safeguards':'Keep cash payments, existing budget meals, staff consent; no involuntary overtime. Collect missing access baseline at launch.','forecast_week13_orders':1430,'holdout_week12_absolute_error':50,'future_test_actuals_available':False}
(ROOT/'BAYANI_BITE_Decision_Record.json').write_text(json.dumps(record,indent=2,ensure_ascii=False),encoding='utf-8')
print(json.dumps({k:v for k,v in checks.items() if k!='all_packages_after_bulletin'},indent=2))
