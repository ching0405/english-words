#!/usr/bin/env python3
"""Validate extensible phrase records, local assets and namespaced IDs."""
import json,pathlib,re,sys,xml.etree.ElementTree as ET
ROOT=pathlib.Path(__file__).resolve().parents[1]
def validate(rows,root=ROOT):
 errors=[];ids=set();english=set()
 if not isinstance(rows,list) or not rows:return ['phrases must be a nonempty array']
 for p in rows:
  if not isinstance(p,dict):errors.append('record must be object');continue
  bad=False
  for k in ('id','english','chinese','category','image'):
   if not isinstance(p.get(k),str) or not p[k].strip():errors.append('missing '+k);bad=True
  if bad:continue
  if not re.fullmatch(r"[A-Za-z']+(?: [A-Za-z']+){0,3}[.?!]",p['english']):errors.append('unsupported sentence tokens')
  id=p.get('id','');en=str(p.get('english','')).lower()
  if not re.fullmatch(r'phrase_[a-z][a-z0-9_]*',str(id)):errors.append('invalid id')
  if id in ids or en in english:errors.append('duplicate id or english')
  ids.add(id);english.add(en)
  for key in ('image','audio'):
   if key not in p:continue
   value=p[key]
   if not isinstance(value,str) or not value or pathlib.PurePosixPath(value).is_absolute() or '..' in pathlib.PurePosixPath(value).parts:errors.append('unsafe '+key);continue
   f=root/value
   if not f.is_file():errors.append('missing '+key);continue
   if key=='image':
    try:
     svg=ET.parse(f).getroot()
     if svg.tag!='{http://www.w3.org/2000/svg}svg' or svg.get('viewBox')!='0 0 512 512':errors.append('invalid SVG dimensions')
    except ET.ParseError:errors.append('invalid SVG')
 # The Chinese meaning is spoken (recorded, never TTS): every phrase needs its line.
 voice=root/'data/voice-zh.json'
 if voice.is_file():
  lines=json.loads(voice.read_text(encoding='utf-8'))
  for id in sorted(ids):
   if 'zh.'+id not in lines:errors.append('missing zh.'+id+' recording: add it to data/voice-zh.json and run tools/gen-voice.py')
 return errors
if __name__=='__main__':
 errors=validate(json.loads((ROOT/'data/phrases.json').read_text()))
 print('\n'.join(errors) if errors else 'OK: phrases valid');sys.exit(bool(errors))
