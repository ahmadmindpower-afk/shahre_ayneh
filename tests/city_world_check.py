import json, pathlib, re, sys
root=pathlib.Path(__file__).resolve().parents[1]
st=json.loads((root/'data/stage-scene-catalogue.json').read_text(encoding='utf-8'))
cm=json.loads((root/'data/city-conflict-mapping.json').read_text(encoding='utf-8'))
assert st['count']==389 and len(st['records'])==389
assert st['cityCount']==18 and len(cm['cities'])==18 and len(cm['realms'])==3
assert [c['id'] for c in cm['cities']]==list(range(1,19))
assert len({r['id'] for r in st['records']})==389
assert all(1<=r['cityId']<=18 and r['cityName']==cm['cities'][r['cityId']-1]['name'] for r in st['records'])
assert all((root/p).exists() for p in cm['cityArtFiles'])
assert (root/cm['worldAtlas']).exists()
assert sum(c['stageCount'] for c in cm['cities'])==389
assert min(c['stageCount'] for c in cm['cities'])>0
html=(root/'index.html').read_text(encoding='utf-8')
assert 'هجده شهر' in html and html.count('data:image/svg+xml;base64,')>=19
assert 'REALMS_V5' in html and 'function populateStageGrid' in html
assert len(list((root/'assets/3d-cities').glob('city-*.jpg')))==18
assert html.count('data:image/jpeg;base64,')==18
assert 'function createShahr3D()' in html and 'lowpoly-webgl1-mobile-v1' in html
print('CITY_WORLD_V5_PLUS_3D_V7_OK')
print('cities=18 realms=3 stages=389 art=18 min_city_stages='+str(min(c['stageCount'] for c in cm['cities'])))
print('distribution='+json.dumps(cm['cities'],ensure_ascii=False)[:1600])
