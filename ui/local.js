const portParam = new URLSearchParams(location.search).get('port');
const backendPort = portParam && /^\d{1,5}$/.test(portParam) && Number(portParam) > 0 && Number(portParam) <= 65535 ? Number(portParam) : 8765;
const API_BASE = `http://127.0.0.1:${backendPort}`;
const form = document.querySelector('#prediction-form');
const inputs = [...form.querySelectorAll('input[data-feature]')];
const result = document.querySelector('#result-content');
const predictButton = document.querySelector('#predict-button');
const backendStatus = document.querySelector('#backend-status');

function setFieldError(input, message) {
  input.setAttribute('aria-invalid', message ? 'true' : 'false');
  document.querySelector(`#${input.id}-error`).textContent = message;
}

function showMessage(kind, kicker, name, detail) {
  result.className = `result-content ${kind}`;
  result.replaceChildren();
  const symbol = document.createElement('div');
  symbol.className = 'result-symbol';
  symbol.setAttribute('aria-hidden', 'true');
  symbol.textContent = kind === 'error' ? '!' : kind === 'success' ? '✓' : '…';
  const label = document.createElement('p');
  label.className = 'result-kicker';
  label.textContent = kicker;
  const heading = document.createElement('p');
  heading.className = 'result-name';
  heading.textContent = name;
  const note = document.createElement('p');
  note.className = 'result-detail';
  note.textContent = detail;
  result.append(symbol, label, heading, note);
}

function readMeasurements() {
  let firstInvalid = null;
  const values = inputs.map((input) => {
    const raw = input.value.trim();
    const value = Number(raw);
    const error = !raw ? 'Enter a measurement.' : !Number.isFinite(value) || value <= 0 ? 'Enter a positive number.' : '';
    setFieldError(input, error);
    if (error && !firstInvalid) firstInvalid = input;
    return value;
  });
  if (firstInvalid) {
    firstInvalid.focus();
    return null;
  }
  return values;
}

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  const values = readMeasurements();
  if (!values) {
    showMessage('error', 'Check the form', 'Four measurements are needed.', 'Use positive numbers in centimeters for every field.');
    return;
  }
  predictButton.disabled = true;
  showMessage('loading', 'Calculating', 'Comparing nearby flowers…', 'The Python model on this laptop is checking the measurements.');
  try {
    const response = await fetch(`${API_BASE}/api/predict`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ measurements: values }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Prediction failed.');
    const label = data.species.replace(/^Iris-/, 'Iris ');
    const votes = Math.round(data.vote_share * data.neighbors);
    showMessage('success', 'Predicted species', label, `${votes} of ${data.neighbors} nearest flowers voted for this species. This is a vote share, not a probability.`);
  } catch (error) {
    const serviceMissing = error instanceof TypeError;
    showMessage('error', 'Could not predict', serviceMissing ? 'Start the model service.' : 'Check the model.',
      serviceMissing ? 'Double-click Launch_Iris_Local.cmd, then try again.' : error.message);
    backendStatus.textContent = serviceMissing ? 'Model service is not running. Open Launch_Iris_Local.cmd.' : 'The local model returned an error.';
    backendStatus.classList.add('is-error');
  } finally {
    predictButton.disabled = false;
  }
});

inputs.forEach((input) => input.addEventListener('input', () => setFieldError(input, '')));

document.querySelector('#example-button').addEventListener('click', () => {
  [5.1, 3.5, 1.4, 0.2].forEach((value, index) => {
    inputs[index].value = value;
    setFieldError(inputs[index], '');
  });
  inputs[0].focus();
});

document.querySelector('#clear-button').addEventListener('click', () => {
  form.reset();
  inputs.forEach((input) => setFieldError(input, ''));
  showMessage('idle', 'Ready when you are', 'Enter four values to see a species.', 'The classifier uses the saved model; no retraining is needed.');
  inputs[0].focus();
});

fetch(`${API_BASE}/api/info`)
  .then((response) => {
    if (!response.ok) throw new Error('Model details unavailable');
    return response.json();
  })
  .then((info) => {
    const correct = Math.round(info.test_accuracy * info.test_rows);
    document.querySelector('#model-k').textContent = info.k;
    document.querySelector('#model-samples').textContent = info.training_rows;
    document.querySelector('#test-accuracy').textContent = `${(info.test_accuracy * 100).toFixed(1)}% (${correct}/${info.test_rows})`;
    document.querySelector('#fact-k').textContent = info.k;
    document.querySelector('#fact-accuracy').textContent = `${correct}/${info.test_rows}`;
    document.querySelector('#fact-note').textContent = `The model learned from ${info.training_rows} training flowers. It returns one of three species: Iris-setosa, Iris-versicolor, or Iris-virginica. It classified ${correct} of ${info.test_rows} test flowers correctly. A new result can still be wrong.`;
    backendStatus.textContent = 'Python model ready on this laptop.';
    backendStatus.classList.remove('is-error');
  })
  .catch(() => {
    backendStatus.textContent = 'Model service is not running. Open Launch_Iris_Local.cmd.';
    backendStatus.classList.add('is-error');
  });
