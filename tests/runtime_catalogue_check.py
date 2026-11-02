#!/usr/bin/env python3
"""Execute JS catalogue generation and verify v4 stage alignment."""
from pathlib import Path
import re, subprocess, json, tempfile
ROOT=Path(__file__).resolve().parents[1]
html=(ROOT/'index.html').read_text(encoding='utf-8')
scripts=re.findall(r'<script[^>]*>(.*?)</script>',html,re.S)
assert len(scripts)==1,f'expected one inline script, got {len(scripts)}'
js=scripts[0]
with tempfile.TemporaryDirectory() as td:
    js_path=Path(td)/'game.js'; js_path.write_text(js,encoding='utf-8')
    subprocess.run(['node','--check',str(js_path)],check=True)
    marker='// Robust, version-tolerant progress state.'
    assert marker in js
    prefix=js[:js.index(marker)]
    test_path=Path(td)/'catalogue-check.js'
    test_path.write_text('global.Image=class {set src(v){this._src=v}};\n'+prefix+
      '\nconst cases=Object.values(stagesData).filter(s=>s.kind===\'case\');\n'+
      'const modes=cases.reduce((a,s)=>(a[s.stageMode]=(a[s.stageMode]||0)+1,a),{});\n'+
      'const refs=AUTHORED_STAGE_SCENE_CATALOGUE.records.filter(r=>[\'single-pattern\',\'pattern-only\'].includes(r.stageMode)).map(r=>r.patternRefs[0]);\n'+
      'const composites=cases.filter(s=>[\'two-pattern-combo\',\'cross-conflict-combo\',\'multi-pattern-boss\'].includes(s.stageMode));\n'+
      'const assistChecks=composites.every(s=>s.patterns.every(p=>stagePatternSummary(s).includes(p.p))&&s.conflictMasterIds.every(id=>stageConflictSummary(s).includes(GAME_CONFLICT_MASTER.find(c=>c.id===id).name)));\n'+
      'const stageChoiceChecks=cases.every(s=>{const n=s.objects.find(o=>o.kind===\'npc\');return n&&n.choices&&n.choices.length===3&&n.choices.filter(c=>c.ok).length===1});\n'+
      'console.log(JSON.stringify({totalStages:Object.keys(stagesData).length,conflicts:CONFLICT_MAP.length,uniquePatterns:GAME_PATTERN_MASTER.patterns.length,caseStages:cases.length,specials:Object.values(stagesData).filter(s=>s.kind===\'special\').length,patternStageDuplicates:refs.length-new Set(refs).size,uniqueSinglePatternRefs:new Set(refs).size,modes,assistChecks,stageChoiceChecks,choiceFailures:cases.filter(s=>{const n=s.objects.find(o=>o.kind===\'npc\');return !n||!n.choices||n.choices.length!==3||n.choices.filter(c=>c.ok).length!==1}).map(s=>({id:s.id,objects:s.objects.map(o=>o.kind),npc:s.objects.find(o=>o.kind===\'npc\')})).slice(0,12),authored:AUTHORED_SCENE_DIAGNOSTICS,lastLocation:stagesData[TOTAL_STAGES].locationName,finaleKey:stagesData[TOTAL_STAGES].specialKey}));\n',encoding='utf-8')
    res=subprocess.run(['node',str(test_path)],capture_output=True,text=True)
    if res.returncode: raise RuntimeError('Node runtime failed: '+res.stderr+'\n'+res.stdout)
    out=json.loads(res.stdout.strip().splitlines()[-1])
assert out['totalStages']==389 and out['conflicts']==22 and out['uniquePatterns']==259
assert out['caseStages']==383 and out['specials']==6
assert out['patternStageDuplicates']==0 and out['uniqueSinglePatternRefs']==259
print(json.dumps(out,ensure_ascii=False,indent=2))
assert out['assistChecks'] is True and out['stageChoiceChecks'] is True
assert out['modes']=={'single-pattern':190,'pattern-only':69,'conflict-focus':22,'two-pattern-combo':61,'cross-conflict-combo':18,'multi-pattern-boss':23}
assert out['authored']['catalogueVersion']==5
assert out['authored']['expected']==389 and out['authored']['applied']==389
assert out['authored']['cases']==383 and out['authored']['specials']==6
assert out['authored']['mismatchCount']==0,out['authored']['mismatches']
assert out['authored']['compositeStages']==102 and out['authored']['uniqueCompositeSignatures']==102
assert out['lastLocation'] and out['finaleKey']=='finale'
print('RUNTIME_CATALOGUE_CHECK_OK')
print(json.dumps(out,ensure_ascii=False,indent=2))
print('Note: content-generation layer only; not a full graphical browser playtest.')
