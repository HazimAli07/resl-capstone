import {loadBrowserDemo} from './model.mjs';
const $ = (selector) => document.querySelector(selector);
const form = $('#application-form');
let configuration, predict, currentScenario = 'Purchase example', lastResult = null, inputRevision = 0;
const cases = ['Purchase example','Refinance example','Missing credit score'];
const escapeHtml = (value) => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

function clearResult(message = 'Awaiting review') {
  lastResult = null;
  $('#score').textContent = '—';
  $('#score-fill').style.width = '0%';
  $('#checked-count').textContent = '—';
  $('#missing-count').textContent = '—';
  $('#result-state').textContent = message;
  $('#result-state').classList.remove('ready');
  $('#missing-note').hidden = true;
  $('#download-result').disabled = true;
}

function selectScenario(name) {
  currentScenario = name;
  const values = configuration.scenarios[name];
  Object.entries(values).forEach(([field,value]) => {form.elements[field].value = value ?? '';});
  document.querySelectorAll('[data-scenario]').forEach(button => {
    const active = button.dataset.scenario === name;
    button.classList.toggle('active',active);
    button.setAttribute('aria-pressed',String(active));
  });
  $('#case-label').textContent = `CASE ${String(cases.indexOf(name)+1).padStart(2,'0')} · FICTIONAL`;
  $('#form-error').hidden = true;
  inputRevision++;
  clearResult();
}

function showView(view) {
  const titles = {application:'Application',comparison:'Compare examples',progress:'Project progress',model:'How the model works'};
  document.querySelectorAll('.view').forEach(section => {section.hidden = section.id !== `${view}-view`;});
  document.querySelectorAll('[data-view]').forEach(button => {
    const active = button.dataset.view === view;
    button.classList.toggle('active',active);
    if(active) button.setAttribute('aria-current','page'); else button.removeAttribute('aria-current');
  });
  $('#breadcrumb-current').textContent = titles[view];
  window.scrollTo({top:0,behavior:'instant'});
}

function renderComparison(rows) {
  $('#comparison-body').innerHTML = rows.map((row,index) => `<tr>
    <td><span class="case-index">0${index+1}</span>${escapeHtml(row['Fictional example'])}</td>
    <td>${escapeHtml(row['Credit score'])}</td><td>${escapeHtml(row['DTI (%)'])}%</td><td>${escapeHtml(row['LTV (%)'])}%</td>
    <td><div class="table-score"><span><i data-width="${Number(row['Demo score / 100'])}"></i></span><strong>${Number(row['Demo score / 100']).toFixed(1)}</strong></div></td>
    <td><button class="open-case" data-open-case="${index}">Open case ↗</button></td></tr>`).join('');
  document.querySelectorAll('[data-width]').forEach(bar => {bar.style.width = `${bar.dataset.width}%`;});
  document.querySelectorAll('[data-open-case]').forEach(button => button.addEventListener('click',() => {
    selectScenario(cases[Number(button.dataset.openCase)]); showView('application');
  }));
}

form.addEventListener('input',() => {inputRevision++;clearResult('Inputs changed');$('#form-error').hidden=true;});
form.addEventListener('change',() => {inputRevision++;clearResult('Inputs changed');});
form.addEventListener('submit',async event => {
  event.preventDefault();
  const revision = inputRevision;
  clearResult('Reviewing…');
  const button = $('#run-button'); button.disabled = true;
  $('#form-error').hidden = true;
  try {
    const inputs = Object.fromEntries(new FormData(form).entries());
    const data = predict(inputs);
    if (revision !== inputRevision) return;
    lastResult = data;
    $('#score').textContent = data.demo_score.toFixed(1);
    $('#score-fill').style.width = `${data.demo_score}%`;
    $('#checked-count').textContent = String(Object.keys(data.inputs).length);
    $('#missing-count').textContent = String(data.missing_fields.length);
    $('#result-state').textContent = 'Review complete';
    $('#result-state').classList.add('ready');
    $('#download-result').disabled = false;
    if(data.missing_fields.length) {
      const names = data.missing_fields.map(field => configuration.labels[field]).join(', ');
      $('#missing-note').textContent = `${names} missing. The saved training median is used, with a missingness flag.`;
      $('#missing-note').hidden = false;
    }
  } catch(error) {
    if(revision !== inputRevision) return;
    clearResult('Input needs attention');
    let message=error.message;
    Object.entries(configuration.labels).forEach(([field,label])=>{message=message.replaceAll(field,label);});
    $('#form-error').textContent = message;
    $('#form-error').hidden = false;
  } finally {button.disabled = false;}
});

$('#download-result').addEventListener('click',() => {
  if(!lastResult) return;
  const url = URL.createObjectURL(new Blob([JSON.stringify(lastResult,null,2)],{type:'application/json'}));
  const link = document.createElement('a'); link.href = url;link.download='resl-fictional-demo.json';link.click();
  setTimeout(() => URL.revokeObjectURL(url),1000);
});
document.querySelectorAll('[data-view]').forEach(button => button.addEventListener('click',() => showView(button.dataset.view)));
document.querySelectorAll('[data-scenario]').forEach(button => button.addEventListener('click',() => configuration && selectScenario(button.dataset.scenario)));
$('.brand').addEventListener('click',event => {event.preventDefault();showView('application');});
$('#reset-inputs').addEventListener('click',() => configuration && selectScenario(currentScenario));

async function start() {
  $('#run-button').disabled = true;
  try {
    ({configuration,predict}=await loadBrowserDemo());
    Object.entries(configuration.options).forEach(([field,options]) => {
      const select = form.elements[field];
      options.forEach(value => {const option = document.createElement('option');option.value=value;option.textContent=configuration.option_labels[value];select.appendChild(option);});
    });
    selectScenario(currentScenario);
    renderComparison(configuration.comparison);
    $('#model-tree-count').textContent=String(configuration.model_info.tree_count);
    $('#model-training-count').textContent=String(configuration.model_info.training_rows);
    const example=predict(configuration.scenarios['Purchase example']);
    $('#model-math').textContent=`Purchase example: average tree output ≈ ${(example.demo_score/100).toFixed(3)} × 100 = ${example.demo_score.toFixed(1)} / 100.`;
    $('#run-button').disabled = false;
  } catch(error) {$('#form-error').textContent=error.message;$('#form-error').hidden=false;clearResult('Demo unavailable');}
}
start();
