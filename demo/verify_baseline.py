"""Re-score committed historical outputs; does NOT run a live model."""
import json
import re
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'validation'/'scripts'))
import qa
import rules

def main():
    import contextlib, io, runpy
    with contextlib.redirect_stdout(io.StringIO()):
        privacy=runpy.run_path(str(ROOT/'validation'/'scripts'/'test_privacy.py'))
    assert privacy['n_secrets']==266 and not privacy['leaks'] and not privacy['damaged']
    holiday=json.loads((ROOT/'validation/docs_holiday/ground_truth.json').read_text())
    rule_count=0
    for d in holiday:
        actual=[o.to_dict() for w in d['workers'] for o in rules.compute(d['doc_type'],w)]
        assert actual==d['obligations']
        rule_count+=len(actual)
    questions=[]
    for i,(question,facts,cite) in enumerate(qa.QH,1):
        saved=json.loads((ROOT/f'validation/runs/qa_holdout/rag2s_haiku/q{i:02d}.json').read_text())
        answer=saved['answer']
        hit=all(any(v in answer for v in alternatives) for alternatives in facts)
        cited=any(v in answer for v in (f"第{cite['no']}條",f"第 {cite['no']} 條"))
        questions.append({'id':i,'facts':hit,'citation':cited})
    truth=json.loads((ROOT/'validation/penalty/truth.json').read_text())
    detected=total=0
    for row in truth:
        saved=json.loads((ROOT/f"validation/runs/penalty/haiku/{row['id']}.json").read_text())['parsed']
        for c in row['defects']:
            total+=1;detected+=saved[c]['ok'] is False
    result={'mode':'historical_output_replay_not_live','legacy_holiday':{'passed':rule_count,'total':33},
            'qa_holdout':{'passed':sum(x['facts'] for x in questions),'total':10,'items':questions},
            'penalty':{'detected':detected,'total_defects':total,'drafts':30},
            'privacy':{'checked':privacy['n_secrets'],'leaks':len(privacy['leaks']),'damaged_lines':len(privacy['damaged'])},
            'live_model_verified':False,'privacy_scope':'pure text only; excludes scanned images'}
    assert rule_count==33 and sum(x['facts'] for x in questions)==10 and detected>=29
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
