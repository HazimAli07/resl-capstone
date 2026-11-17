"""Cross-language inference parity and synthetic-only GitHub Pages builds."""
import base64
import copy
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from urllib.parse import urljoin, urlsplit
from unittest.mock import patch

from resl.build_demo_site import browser_files, build_site
from resl.hazim_training import synthetic_cohort
from resl.mini_demo import SCENARIOS, evaluate_application, load_demo_bundle
from resl.hazim_contract import validate_application

ROOT = Path(__file__).resolve().parents[1]
NODE = os.environ.get('RESL_NODE') or shutil.which('node')


@unittest.skipUnless(NODE, 'Node is required for browser inference checks')
class BrowserInferenceTests(unittest.TestCase):
    def setUp(self):
        self.bundle = load_demo_bundle()

    def run_js(self, script, data):
        uri = (ROOT/'resl/demo_web/model.mjs').as_uri()
        prefix = ('import * as engine from '+json.dumps(uri)+';'
                  'import {readFileSync} from "node:fs";'
                  'const input=JSON.parse(readFileSync(0,"utf8"));')
        result = subprocess.run([NODE, '--input-type=module', '-e', prefix+script],
                                input=json.dumps(data,allow_nan=False),text=True,
                                capture_output=True,check=True)
        return json.loads(result.stdout)

    def compare(self, cases):
        actual=self.run_js('const predict=engine.createPredictor(input.model);'
                           'console.log(JSON.stringify(input.cases.map(predict)));',
                           {'model':self.bundle.payload,'cases':cases})
        for values, result in zip(cases, actual):
            expected=evaluate_application(self.bundle,values)
            self.assertAlmostEqual(result['demo_score'],expected['demo_score'],places=12)
            self.assertEqual(result['inputs'],expected['inputs'])
            self.assertEqual(result['missing_fields'],expected['missing_fields'])
            self.assertIsNone(result['real_mortgage_probability'])
            self.assertIsNone(result['lending_decision'])

    def test_browser_matches_python_on_presets_and_generated_cohort(self):
        train, validation, _=synthetic_cohort()
        fields=self.bundle.payload['features']
        cases=list(SCENARIOS.values())+[{f:row[f] for f in fields} for row in train+validation]
        self.compare(cases)

    def test_missing_sentinels_unseen_categories_and_float32_boundaries_match(self):
        base=SCENARIOS['Purchase example']
        cases=[base|{'credit_score':9999,'dti':999,'ltv':999},
               base|{'loan_purpose':None,'occupancy':'investment','property_type':'pud'},
               base|{'credit_score':300,'dti':0,'ltv':998,'original_term':600,'original_rate':100},
               base|{'original_balance':'1e6','original_term':'3.6e2','credit_score':''}]
        numeric=self.bundle.payload['features'][:6]
        for tree in self.bundle.payload['trees']:
            for feature,threshold,left in zip(tree['feature'],tree['threshold'],tree['left']):
                if left!=-1 and feature in (2,4,6,8):
                    field=numeric[feature//2]
                    stat=self.bundle.payload['preprocessing']['numeric'][field]
                    raw=threshold*stat['scale']+stat['mean']
                    for epsilon in (-1e-7,0,1e-7):
                        row=base|{field:raw+epsilon}
                        try:validate_application(row)
                        except ValueError:continue
                        cases.append(row)
                    break
            if len(cases)>15:break
        self.assertGreater(len(cases),4)
        self.compare(cases)

    def test_invalid_inputs_never_produce_a_browser_prediction(self):
        base=SCENARIOS['Purchase example']
        cases=[base|{'credit_score':True},base|{'credit_score':1000},base|{'original_balance':0},
               base|{'dti':'NaN'},base|{'original_rate':'inf'},base|{'loan_id':'unwanted'},
               base|{'property_type':'unknown'}, {k:v for k,v in base.items() if k!='dti'}]
        for row in cases:
            with self.assertRaises(ValueError):validate_application(row)
        results=self.run_js('const predict=engine.createPredictor(input.model);'
            'console.log(JSON.stringify(input.cases.map(row=>{try{predict(row);return false;}catch{return true;}})));',
            {'model':self.bundle.payload,'cases':cases})
        self.assertTrue(all(results))

    def test_checksum_actual_model_and_corrupt_tree_are_rejected(self):
        files=browser_files(self.bundle)
        data={'bytes':base64.b64encode(files['model.json']).decode(),
              'manifest':json.loads(files['manifest.json']), 'model':self.bundle.payload}
        result=self.run_js('''const bytes=Uint8Array.from(Buffer.from(input.bytes,'base64'));
          const good=await engine.verifyModelBytes(bytes,input.manifest);
          const outcomes=[good.synthetic===true];bytes[10]^=1;
          try{await engine.verifyModelBytes(bytes,input.manifest);outcomes.push(false);}catch{outcomes.push(true);}
          for(const change of ['actual','cycle','scale']){const model=structuredClone(input.model);
            if(change==='actual')model.synthetic=false;
            if(change==='cycle')model.trees[0].left[0]=0;
            if(change==='scale')model.preprocessing.numeric.dti.scale=0;
            try{engine.createPredictor(model);outcomes.push(false);}catch{outcomes.push(true);}}
          console.log(JSON.stringify(outcomes));''',data)
        self.assertEqual(result,[True]*5)


class PagesBuildTests(unittest.TestCase):
    def test_build_contains_only_explicit_site_files_and_synthetic_model(self):
        with tempfile.TemporaryDirectory() as folder:
            output=Path(folder);paths=build_site(output)
            self.assertEqual(len(paths),8)
            self.assertEqual({p.relative_to(output).as_posix() for p in output.rglob('*') if p.is_file()},set(paths))
            self.assertTrue(json.loads((output/'model.json').read_text())['synthetic'])
            self.assertNotIn('api/predict',(output/'assets/app.js').read_text())
            self.assertNotIn('localhost',(output/'index.html').read_text())

    def test_assets_resolve_under_a_github_project_subpath(self):
        class Assets(HTMLParser):
            def __init__(self):super().__init__();self.paths=[]
            def handle_starttag(self,tag,attrs):
                attrs=dict(attrs)
                if tag=='script' and 'src' in attrs:self.paths.append(attrs['src'])
                if tag=='link' and attrs.get('rel')=='stylesheet':self.paths.append(attrs['href'])
        with tempfile.TemporaryDirectory() as folder:
            output=Path(folder);build_site(output)
            parser=Assets();parser.feed((output/'index.html').read_text())
            self.assertEqual(len(parser.paths),2)
            for path in parser.paths:
                resolved=urlsplit(urljoin('https://example.test/resl-capstone/',path)).path
                self.assertTrue(resolved.startswith('/resl-capstone/'))
                self.assertTrue((output/path).is_file())

    def test_build_rejects_an_actual_data_package(self):
        model=load_demo_bundle();model.payload=copy.deepcopy(model.payload);model.payload['synthetic']=False
        with tempfile.TemporaryDirectory() as folder,patch('resl.build_demo_site.load_demo_bundle',return_value=model):
            with self.assertRaisesRegex(ValueError,'synthetic'):
                build_site(Path(folder)/'site')


if __name__=='__main__':unittest.main()
