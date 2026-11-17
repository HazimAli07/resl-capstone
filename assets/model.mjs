// Browser inference for the same verified synthetic JSON forest used by Python.
export const FEATURES = ['credit_score','dti','ltv','original_balance','original_rate','original_term','loan_purpose','occupancy','property_type'];
const NUMERIC = FEATURES.slice(0,6), CATEGORICAL = FEATURES.slice(6);
const CATEGORIES = {loan_purpose:['purchase','cash_out','refinance'],occupancy:['primary','second_home','investment'],property_type:['single_family','condo','cooperative','manufactured','pud']};
const BOUNDS = {credit_score:[300,850],dti:[0,998],ltv:[0,998],original_balance:[0,Infinity],original_rate:[0,100],original_term:[1,600]};
const SENTINELS = {credit_score:[9999],dti:[999],ltv:[999]};
const same = (a,b) => JSON.stringify(a)===JSON.stringify(b);
const keysEqual = (value,expected) => value && typeof value==='object' && !Array.isArray(value) && same(Object.keys(value).sort(),[...expected].sort());
const fail = message => {throw new Error(message);};

function numericValue(field,value) {
  if(value===null || value===undefined || (typeof value==='string' && !value.trim())) return null;
  if(typeof value==='boolean' || !['string','number'].includes(typeof value)) fail(`${field}: expected a number`);
  if(typeof value==='string' && !/^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$/.test(value.trim())) fail(`${field}: expected a decimal number`);
  const number=Number(value);
  if(!Number.isFinite(number)) fail(`${field}: nonfinite value`);
  if((SENTINELS[field]||[]).includes(number)) return null;
  const [low,high]=BOUNDS[field];
  if(number<low || number>high) fail(`${field}: outside normalized interface bounds`);
  if(field==='original_balance' && number===0) fail('original_balance must be positive');
  if(['credit_score','original_term'].includes(field) && !Number.isInteger(number)) fail(`${field}: expected an integer`);
  return number;
}

export function validateApplication(values) {
  if(!keysEqual(values,FEATURES)) fail('Application must contain exactly the nine eligible inputs');
  const clean={};
  for(const field of NUMERIC) clean[field]=numericValue(field,values[field]);
  for(const field of CATEGORICAL) {
    const value=values[field]===null || values[field]===undefined ? null : String(values[field]).trim() || null;
    if(value!==null && !CATEGORIES[field].includes(value)) fail(`${field}: unreviewed category code`);
    clean[field]=value;
  }
  return clean;
}

function validateModel(model) {
  if(!model || model.format!=='resl-forest-json-v1' || model.contract!=='hazim-input-contract-v1' || model.synthetic!==true || model.bands!==null || !same(model.features,FEATURES)) fail('Expected the synthetic development model');
  const prep=model.preprocessing;
  if(!prep || prep.version!=='mannan-preprocessing-v1' || prep.fit_split!=='train' || !Number.isInteger(prep.training_count) || prep.training_count<2 || !keysEqual(prep.numeric,NUMERIC) || !keysEqual(prep.categories,CATEGORICAL)) fail('Invalid saved preprocessing');
  const names=[];
  for(const field of NUMERIC) {
    const stat=prep.numeric[field];
    if(!keysEqual(stat,['median','mean','scale']) || !Object.values(stat).every(Number.isFinite) || stat.scale<=0) fail('Invalid numeric preprocessing');
    names.push(`${field}:scaled`,`${field}:missing`);
  }
  for(const field of CATEGORICAL) {
    const values=prep.categories[field];
    if(!Array.isArray(values) || values.some(v=>typeof v!=='string'||!v) || new Set(values).size!==values.length) fail('Invalid category vocabulary');
    for(const value of values) names.push(`${field}:value:${[...value].length}:${value}`);
    names.push(`${field}:missing`,`${field}:unknown`);
  }
  if(!same(names,prep.feature_names)) fail('Saved feature order differs');
  if(!Array.isArray(model.trees) || !model.trees.length || model.trees.length>128) fail('Invalid forest size');
  for(const tree of model.trees) {
    if(!keysEqual(tree,['left','right','feature','threshold','positive'])) fail('Invalid tree fields');
    const n=tree.left.length;
    if(!n || n>1023 || !Object.values(tree).every(array=>Array.isArray(array)&&array.length===n)) fail('Invalid tree dimensions');
    for(let i=0;i<n;i++) {
      const left=tree.left[i],right=tree.right[i],feature=tree.feature[i],probability=tree.positive[i];
      if(![left,right,feature].every(Number.isInteger) || !Number.isFinite(tree.threshold[i]) || !Number.isFinite(probability) || probability<0 || probability>1) fail('Invalid tree values');
      if(left===-1 && right===-1) continue;
      if(!(i<left && left<n && i<right && right<n && left!==right && feature>=0 && feature<names.length)) fail('Cyclic or invalid tree');
    }
  }
}

export function createPredictor(model) {
  validateModel(model);
  return values => {
    const clean=validateApplication(values),vector=[],prep=model.preprocessing;
    for(const field of NUMERIC) {
      const value=clean[field],stat=prep.numeric[field],imputed=value===null?stat.median:value;
      vector.push((imputed-stat.mean)/stat.scale,value===null?1:0);
    }
    for(const field of CATEGORICAL) {
      const value=clean[field],known=prep.categories[field];
      for(const category of known) vector.push(value===category?1:0);
      vector.push(value===null?1:0,value!==null && !known.includes(value)?1:0);
    }
    // Match sklearn/Python's float32 input rounding at every tree threshold.
    const x=vector.map(Math.fround);
    if(!x.every(Number.isFinite)) fail('Input overflows model precision');
    let total=0;
    for(const tree of model.trees) {
      let node=0;
      while(tree.left[node]!==-1) node=x[tree.feature[node]]<=tree.threshold[node]?tree.left[node]:tree.right[node];
      total+=tree.positive[node];
    }
    return {mode:'fictional application / synthetic-trained model',inputs:clean,
            demo_score:total/model.trees.length*100,
            missing_fields:FEATURES.filter(field=>clean[field]===null),
            real_mortgage_probability:null,lending_decision:null};
  };
}

export async function verifyModelBytes(bytes,manifest) {
  if(!manifest || manifest.format!=='resl-browser-demo-v1' || manifest.synthetic!==true || !/^[0-9a-f]{64}$/.test(manifest.model_file_sha256||'')) fail('Invalid browser-model manifest');
  const digest=await globalThis.crypto.subtle.digest('SHA-256',bytes);
  const actual=Array.from(new Uint8Array(digest),b=>b.toString(16).padStart(2,'0')).join('');
  if(actual!==manifest.model_file_sha256) fail('Saved model checksum mismatch');
  const model=JSON.parse(new TextDecoder().decode(bytes));
  validateModel(model);
  return model;
}

export async function loadBrowserDemo() {
  const root=new URL('../',import.meta.url);
  const responses=await Promise.all(['manifest.json','demo.json','model.json'].map(name=>fetch(new URL(name,root),{cache:'no-store'})));
  if(responses.some(response=>!response.ok)) fail('The hosted demo files could not be loaded. Refresh the page and try again.');
  const [manifest,configuration,bytes]=await Promise.all([responses[0].json(),responses[1].json(),responses[2].arrayBuffer()]);
  const model=await verifyModelBytes(bytes,manifest),predict=createPredictor(model);
  configuration.comparison=configuration.scenario_order.map(name=>{
    const values=configuration.scenarios[name],result=predict(values);
    return {'Fictional example':name,'Demo score / 100':Math.round(result.demo_score*10)/10,
            'Credit score':values.credit_score===''?'Missing':String(values.credit_score),
            'DTI (%)':values.dti,'LTV (%)':values.ltv,'Missing inputs':result.missing_fields.length};
  });
  configuration.model_info={family:'Random forest',tree_count:model.trees.length,
                            training_rows:model.preprocessing.training_count,input_count:FEATURES.length};
  return {configuration,predict};
}
