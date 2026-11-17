"""Build the GitHub Pages demo from explicit public assets and synthetic data."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

from .mini_demo import WEB_ROOT, SCENARIOS, LABELS, CATEGORIES, CHOICES, load_demo_bundle


def browser_files(bundle):
    if bundle.payload.get('synthetic') is not True:
        raise ValueError('Only the synthetic demonstration model can be published')
    model=(json.dumps(bundle.payload,sort_keys=True,allow_nan=False)+'\n').encode('utf-8')
    manifest={'format':'resl-browser-demo-v1','synthetic':True,
              'model_file_sha256':hashlib.sha256(model).hexdigest()}
    config={'scenarios':SCENARIOS,'scenario_order':list(SCENARIOS),'labels':LABELS,
            'options':CATEGORIES,'option_labels':CHOICES,
            'model_status':'verified synthetic fixture'}
    return {'model.json':model,
            'manifest.json':(json.dumps(manifest,indent=2)+'\n').encode(),
            'demo.json':(json.dumps(config,indent=2)+'\n').encode()}


def build_site(output):
    output=Path(output)
    bundle=load_demo_bundle()
    output.mkdir(parents=True,exist_ok=True)
    assets=output/'assets';assets.mkdir(exist_ok=True)
    shutil.copy2(WEB_ROOT/'index.html',output/'index.html')
    for name in ('app.css','app.js','model.mjs'):
        shutil.copy2(WEB_ROOT/name,assets/name)
    for name,body in browser_files(bundle).items():
        (output/name).write_bytes(body)
    (output/'.nojekyll').write_text('')
    return ['index.html','assets/app.css','assets/app.js','assets/model.mjs',
            'model.json','manifest.json','demo.json','.nojekyll']


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,default=Path('_site'))
    args=parser.parse_args()
    files=build_site(args.out)
    print(json.dumps({'public_assets':files,'synthetic_model':True,'loan_records_published':False}))


if __name__=='__main__':
    main()
