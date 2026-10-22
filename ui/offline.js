const offlineModel = JSON.parse(document.querySelector('#model-data').textContent);
const offlineMetrics = JSON.parse(document.querySelector('#metrics-data').textContent);
const form = document.querySelector('#prediction-form');
const inputs = [...form.querySelectorAll('input[data-feature]')];
const result = document.querySelector('#result-content');
const predictButton = document.querySelector('#predict-button');

function compareLabels(a, b) {
  return a < b ? -1 : a > b ? 1 : 0;
}

function predictOffline(values) {
  const transformed = values.map((value, index) =>
    (value - offlineModel.means[index]) / offlineModel.scales[index]);
  const distances = offlineModel.samples.map((sample) => ({
    label: sample.label,
    distance: transformed.reduce((sum, value, index) =>
      sum + (value - sample.x[index]) ** 2, 0),
  })).sort((a, b) => a.distance - b.distance || compareLabels(a.label, b.label));
  const neighbors = distances.slice(0, offlineModel.k);
  const votes = new Map();
  for (const neighbor of neighbors) {
    const vote = votes.get(neighbor.label) || { label: neighbor.label, count: 0, distanceSum: 0 };
    vote.count += 1;
    vote.distanceSum += neighbor.distance;
    votes.set(neighbor.label, vote);
  }
  const winner = [...votes.values()].sort((a, b) =>
    b.count - a.count || a.distanceSum - b.distanceSum || compareLabels(a.label, b.label))[0];
  return { species: winner.label, vote_share: winner.count / neighbors.length, neighbors: neighbors.length };
}

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

form.addEventListener('submit', (event) => {
  event.preventDefault();
  const values = readMeasurements();
  if (!values) {
    showMessage('error', 'Check the form', 'Four measurements are needed.', 'Use positive numbers in centimeters for every field.');
    return;
  }
  predictButton.disabled = true;
  try {
    const data = predictOffline(values);
    const label = data.species.replace(/^Iris-/, 'Iris ');
    const votes = Math.round(data.vote_share * data.neighbors);
    showMessage('success', 'Predicted species', label, `${votes} of ${data.neighbors} nearest flowers voted for this species. This is a vote share, not a probability.`);
  } catch (error) {
    showMessage('error', 'Could not predict', 'Check the saved model.', 'The model data in this HTML file could not be read.');
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

document.querySelector('#model-k').textContent = offlineModel.k;
document.querySelector('#model-samples').textContent = offlineModel.samples.length;
document.querySelector('#test-accuracy').textContent = `${(offlineMetrics.test.accuracy * 100).toFixed(1)}% (${Math.round(offlineMetrics.test.accuracy * offlineMetrics.test_rows)}/${offlineMetrics.test_rows})`;
document.querySelector('#fact-k').textContent = offlineModel.k;
document.querySelector('#fact-accuracy').textContent = `${Math.round(offlineMetrics.test.accuracy * offlineMetrics.test_rows)}/${offlineMetrics.test_rows}`;
document.querySelector('#fact-note').textContent = `The model learned from ${offlineModel.samples.length} training flowers. It returns one of three species: Iris-setosa, Iris-versicolor, or Iris-virginica. It classified ${Math.round(offlineMetrics.test.accuracy * offlineMetrics.test_rows)} of ${offlineMetrics.test_rows} test flowers correctly. A new result can still be wrong.`;
