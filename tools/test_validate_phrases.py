import copy,importlib.util,json,pathlib,tempfile,unittest
spec=importlib.util.spec_from_file_location('validator',pathlib.Path(__file__).with_name('validate-phrases.py'));v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)
class Cases(unittest.TestCase):
 def test_valid(self):self.assertEqual(v.validate(json.loads((v.ROOT/'data/phrases.json').read_text())),[])
 def test_errors(self):
  source=json.loads((v.ROOT/'data/phrases.json').read_text())
  for key,value in [('id','goat'),('image','../x.svg'),('image','missing.svg'),('english',''),('audio','missing.mp3'),('category',None),('id',{}),('english','This sentence has too many words.'),('audio','/tmp/out.mp3')]:
   rows=copy.deepcopy(source);rows[0][key]=value
   with self.subTest(key=key,value=value):self.assertTrue(v.validate(rows))
  self.assertTrue(v.validate(source+source));self.assertTrue(v.validate({}));self.assertTrue(v.validate([None]))
 def test_invalid_svg(self):
  source=json.loads((v.ROOT/'data/phrases.json').read_text())[0]
  with tempfile.TemporaryDirectory() as tmp:
   root=pathlib.Path(tmp);source['image']='bad.svg'
   for svg in ('broken', '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 300"/>'):
    (root/'bad.svg').write_text(svg)
    with self.subTest(svg=svg):self.assertTrue(v.validate([source],root))
 def test_missing_voice_line(self):
  source=json.loads((v.ROOT/'data/phrases.json').read_text())
  rows=copy.deepcopy(source);rows[0]['id']='phrase_no_voice'
  self.assertTrue(any('missing zh.phrase_no_voice' in e for e in v.validate(rows)))
if __name__=='__main__':unittest.main()
