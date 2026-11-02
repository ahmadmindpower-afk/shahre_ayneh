#!/usr/bin/env python3
"""Static integrity audit for Shahr-e Ayeneh v5."""
from pathlib import Path
from collections import Counter
import hashlib, json, re, xml.etree.ElementTree as ET, unicodedata
ROOT=Path(__file__).resolve().parents[1]
html=(ROOT/'index.html').read_text(encoding='utf-8')
assert '<html' in html and '</html>' in html
assert re.search(r'const TOTAL_STAGES\s*=\s*389\s*;',html)
assert 'GAME_CATALOGUE_VERSION=4' in html
assert 'function renderReferenceLibrary()' in html and 'referenceLibraryOverlay' in html
assert 'const GAME_CONFLICT_MASTER =' in html and 'const GAME_PATTERN_MASTER =' in html
assert 'const V4_ADDITIONAL_PATTERN_DEFS =' in html and 'const V4_ADDED_STAGE_SCHEDULE=' in html
assert "priorCatalogueVersion==='2'" in html and "priorCatalogueVersion==='3'" in html, 'legacy save migrations missing'
for token in ['dailyOverlay','achievementsOverlay','settingsOverlay','marketOverlay','companionOverlay','rivalOverlay','endingsGuideOverlay','differenceOverlay','dreamOverlay','function openDifferencePuzzle()','function openDreamPuzzle()']:
    assert token in html, f'missing integrated feature: {token}'
mapping=json.loads((ROOT/'data/city-conflict-mapping.json').read_text(encoding='utf-8'))
source=json.loads((ROOT/'data/source-conflict-patterns.json').read_text(encoding='utf-8'))['conflicts']
master=json.loads((ROOT/'data/conflict-master-catalogue.json').read_text(encoding='utf-8'))
patterns=json.loads((ROOT/'data/pattern-catalogue.json').read_text(encoding='utf-8'))
cat_doc=json.loads((ROOT/'data/stage-scene-catalogue.json').read_text(encoding='utf-8'))
records=cat_doc['records']
assert len(mapping['cities'])==18 and len(mapping['all_conflicts'])==22 and len(mapping['realms'])==3
assert len(source)==22 and len(master['conflicts'])==22 and len(master['mergeCrosswalk'])==30
assert {x['submittedId'] for x in master['mergeCrosswalk']}==set(range(1,31))
assert {x['canonicalId'] for x in master['mergeCrosswalk']}==set(range(1,23))
merge={x['submittedId']:x['canonicalId'] for x in master['mergeCrosswalk']}
for a,b in [(15,9),(19,9),(17,12),(26,12),(22,4),(29,4),(23,3),(30,7)]: assert merge[a]==b
assert patterns['uniquePatternCount']==259 and len(patterns['patterns'])==259
pids=[x['id'] for x in patterns['patterns']]
assert len(pids)==len(set(pids)) and pids==[f'P{i:03d}' for i in range(1,260)]
names=[unicodedata.normalize('NFKC',x['name']).replace('\u200c',' ').strip().casefold() for x in patterns['patterns']]
assert len(names)==len(set(names))==259
assert sum(x['primaryConflictId'] is not None for x in patterns['patterns'])==190
assert sum(x['primaryConflictId'] is None for x in patterns['patterns'])==69
for p in patterns['patterns']:
    assert all(1<=x<=22 for x in p['relatedConflictIds']),p['id']
    if p['primaryConflictId'] is not None: assert p['primaryConflictId'] in p['relatedConflictIds'],p['id']
new_ids=[f'P{i:03d}' for i in range(243,260)]
assert all(x in pids for x in new_ids)
for p in patterns['patterns'][-17:]:
    assert p.get('description') and p.get('example') and p.get('distinction')
    assert p.get('reviewStatus')=='بازبینی و تأیید برای ورود به بازی'
assert patterns.get('mergedConceptsV4')
assert cat_doc['version']==5 and cat_doc['count']==389 and cat_doc['cityCount']==18 and cat_doc['realmCount']==3
assert len(records)==389 and [r['id'] for r in records]==list(range(1,390))
assert Counter(r['kind'] for r in records)=={'case':383,'special':6}
assert records[-1]['specialKey']=='finale' and records[-1]['id']==389
modes=Counter(r.get('stageMode','special') for r in records if r['kind']=='case')
assert modes=={'single-pattern':190,'pattern-only':69,'conflict-focus':22,'two-pattern-combo':61,'cross-conflict-combo':18,'multi-pattern-boss':23},modes
single=[r for r in records if r.get('stageMode') in ('single-pattern','pattern-only')]
single_refs=[r['patternRefs'][0] for r in single]
assert len(single_refs)==len(set(single_refs))==259
assert set(single_refs)==set(pids)
assert all(r.get('locationName') and r.get('sceneObject') and r.get('sceneSetup') and r.get('question') and r.get('clue1') and r.get('clue2') for r in records)
assert all(r.get('patternRefs') for r in records if r['kind']=='case' and r.get('stageMode') not in ('conflict-focus',))
for field in ('sceneTitle','locationName'):
    vals=[r[field] for r in records if r['kind']=='case']
    assert len(vals)==len(set(vals))==383,field
combo=[r for r in records if r.get('stageMode') in ('two-pattern-combo','cross-conflict-combo','multi-pattern-boss')]
sigs=[(r['stageMode'],tuple(r['conflictIds']),tuple(sorted(r['patternRefs']))) for r in combo]
assert len(sigs)==len(set(sigs))==102
assert all(len(r['patternRefs'])==2 for r in combo if r['stageMode'] in ('two-pattern-combo','cross-conflict-combo'))
assert all(len(r['patternRefs'])==3 for r in combo if r['stageMode']=='multi-pattern-boss')
assert all(r.get('puzzleType') in {'evidence','sequence','maze','clarify','plan','match','boss'} for r in records if r['kind']=='case')
assert all(len(r.get('choices',[]))==3 and sum(1 for c in r['choices'] if c.get('ok'))==1 for r in records if r['kind']=='case')
assert all(len(r.get('hintLevels',[]))>=2 and r.get('accessibilityText') for r in records if r['kind']=='case')
assert all(r['conflictIndices']==[] for r in records if r.get('stageMode')=='pattern-only')
assert all(r['patternRefs']==[] for r in records if r.get('stageMode')=='conflict-focus')
pattern_by_id={p['id']:p for p in patterns['patterns']}
conflict_by_id={c['id']:c for c in master['conflicts']}
for r in records:
    if r['kind']!='case': continue
    assert all(ref in pattern_by_id for ref in r.get('patternRefs',[])),r['id']
    assert all(cid in conflict_by_id for cid in r.get('conflictIds',[])),r['id']
    if r.get('stageMode')=='two-pattern-combo':
        cid=r['conflictIds'][0]
        assert len(r['patternRefs'])==2 and all(cid in pattern_by_id[ref]['relatedConflictIds'] for ref in r['patternRefs']),r['id']
    if r.get('stageMode') in ('cross-conflict-combo','multi-pattern-boss'):
        related=set().union(*(set(pattern_by_id[ref]['relatedConflictIds']) for ref in r['patternRefs']))
        assert set(r['conflictIds'])<=related,r['id']
    if r.get('stageMode') in ('two-pattern-combo','cross-conflict-combo','multi-pattern-boss'):
        assert all(pattern_by_id[ref]['name'] in r['clue1'] for ref in r['patternRefs']),r['id']
        assert all(conflict_by_id[cid]['name'] in r['clue2'] for cid in r['conflictIds']),r['id']
expansion=json.loads((ROOT/'data/stage-expansion-catalogue.json').read_text(encoding='utf-8'))
assert len(expansion['newRecords'])==45
assert len({r['id'] for r in expansion['newRecords']})==45
assert cat_doc['uniquePatternStages']==259 and cat_doc['compositeStages']==102
assert 'جایگزین بازی‌آزمایی انسانی نیست' in cat_doc['reviewSummary']
# Embedded JSON must match the shipped data exactly.
def embedded(var, terminator):
    m=re.search(re.escape(var)+r'\s*=\s*(\{.*?\}|\[.*?\])'+re.escape(terminator),html,re.S)
    assert m,var
    return json.loads(m.group(1))
embedded_scene=embedded('const AUTHORED_STAGE_SCENE_CATALOGUE',';\nfunction applyAuthoredStageSceneCatalogue')
embedded_conf=embedded('const GAME_CONFLICT_MASTER',';\nconst GAME_PATTERN_MASTER')
embedded_pat=embedded('const GAME_PATTERN_MASTER',';\nconst GAME_CITY_MASTER')
embedded_city=embedded('const GAME_CITY_MASTER',';\nconst GAME_ADDED_CHOICE_SETS')
assert embedded_scene==cat_doc
assert embedded_conf==master['conflicts'] and embedded_pat==patterns
assert len(embedded_city)==18 and all(embedded_city[i]['id']==mapping['cities'][i]['id'] and embedded_city[i]['name']==mapping['cities'][i]['name'] and embedded_city[i]['stageCount']==mapping['cities'][i]['stageCount'] for i in range(18))
for f in (ROOT/'assets/cities').glob('*.svg'): ET.parse(f)
assert len(list((ROOT/'assets/cities').glob('*.svg')))==18
html_ids=re.findall(r'\bid=["\']([^"\']+)["\']',html)
assert not [k for k,v in Counter(html_ids).items() if v>1]
refs=set(re.findall(r"\bel\(['\"]([^'\"]+)['\"]\)",html))
assert not (refs-set(html_ids)), sorted(refs-set(html_ids))[:20]
ideas=(ROOT/'docs/IDEAS_78.md').read_text(encoding='utf-8')
assert len(re.findall(r'^\|\s*\d+\s*\|',ideas,re.M))==78
status=json.loads((ROOT/'data/feature-status-50.json').read_text(encoding='utf-8'))
assert len(status)==50 and [x['id'] for x in status]==list(range(1,51))
for f in ['source/conflict-pattern-mapping-reference.pdf','source/risk-patterns-reference.pdf']: assert (ROOT/f).is_file()
# Verify the release manifest (it lists every project file except itself).
manifest=json.loads((ROOT/'MANIFEST.json').read_text(encoding='utf-8'))
assert manifest['version']=='7.0.0' and manifest['cities']==18 and manifest['realms']==3
# V7 mobile-first WebGL renderer, offline assets and graceful fallback.
assert 'id="world3d"' in html and 'function createShahr3D()' in html
assert 'lowpoly-webgl1-mobile-v1' in html and 'window.__SHAHR_E_AYENEH_3D_QUALITY__' in html
assert 'shahr_ayeneh_3d_quality_v1' in html and 'pointerdown' in html and 'cameraResetBtn' in html
assert html.count('data:image/jpeg;base64,')==18
assert len(list((ROOT/'assets/3d-cities').glob('city-*.jpg')))==18
assert (ROOT/'server/public/index.html').read_bytes()==(ROOT/'index.html').read_bytes()
assert 'docs/3D_MOBILE_RENDERING_V7.md' in {x.relative_to(ROOT).as_posix() for x in ROOT.rglob('*') if x.is_file()}
manifest_items=manifest['files']
manifest_paths={item['path'] for item in manifest_items}
actual_paths={x.relative_to(ROOT).as_posix() for x in ROOT.rglob('*') if x.is_file() and x.name!='MANIFEST.json'}
assert manifest_paths==actual_paths, (sorted(actual_paths-manifest_paths)[:10],sorted(manifest_paths-actual_paths)[:10])
assert manifest['fileCount']==len(manifest_items)
for item in manifest_items:
    file_path=ROOT/item['path']
    raw=file_path.read_bytes()
    assert len(raw)==item['size_bytes'],item['path']
    assert hashlib.sha256(raw).hexdigest()==item['sha256'],item['path']
print('MANIFEST_CHECKS_OK')
print('STATIC_CHECKS_OK')
print('cities=18 realms=3 conflicts=22 unique_patterns=259 single_pattern_stages=259 conflict_focus=22 composites=102 cases=383 specials=6 total=389')
