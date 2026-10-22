const story = document.querySelector('#scroll-story');
const video = document.querySelector('#iris-video');
const beats = [...document.querySelectorAll('.story-beat')];
const stageShade = document.querySelector('.stage-shade');
const videoStatus = document.querySelector('#video-status');
const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
const beatStarts = [0.24, 0.38, 0.52, 0.65, 0.78, 0.92];
const openingTime = 0.1;

let pendingFrame = false;
let targetTime = 0;
let activeBeat = -2;

function clamp(value, low, high) {
  return Math.min(high, Math.max(low, value));
}

function showBeat(index) {
  if (index === activeBeat) return;
  activeBeat = index;
  beats.forEach((beat, beatIndex) => {
    beat.classList.toggle('is-active', beatIndex === index);
    beat.setAttribute('aria-hidden', beatIndex === index ? 'false' : 'true');
    const link = beat.querySelector('a');
    if (link) link.tabIndex = beatIndex === index ? 0 : -1;
  });
}

function seekToTarget() {
  if (!Number.isFinite(video.duration) || video.duration <= 0 || video.seeking) return;
  if (Math.abs(video.currentTime - targetTime) > 0.08) {
    video.currentTime = targetTime;
  }
}

function updateStory() {
  pendingFrame = false;
  if (reducedMotion.matches) {
    showBeat(beats.length - 1);
    stageShade.style.opacity = '1';
    return;
  }
  const rect = story.getBoundingClientRect();
  const travel = Math.max(story.offsetHeight - window.innerHeight, 1);
  const progress = clamp(-rect.top / travel, 0, 1);
  const beatIndex = beatStarts.reduce((index, start, position) => progress >= start ? position : index, -1);
  showBeat(beatIndex);
  stageShade.style.opacity = String(clamp((progress - 0.20) / 0.16, 0, 1));
  if (Number.isFinite(video.duration) && video.duration > 0) {
    // The supplied video ends with a black frame. Keep the last visible flower on screen.
    const lastVisibleTime = Math.max(video.duration - 0.3, 0);
    const firstVisibleTime = Math.min(openingTime, lastVisibleTime);
    targetTime = firstVisibleTime + progress * (lastVisibleTime - firstVisibleTime);
    seekToTarget();
  }
}

function requestUpdate() {
  if (pendingFrame) return;
  pendingFrame = true;
  requestAnimationFrame(updateStory);
}

video.addEventListener('loadedmetadata', () => {
  video.pause();
  requestUpdate();
});
video.addEventListener('seeked', () => {
  video.classList.add('is-ready');
  seekToTarget();
});
video.addEventListener('error', () => {
  videoStatus.hidden = false;
});
reducedMotion.addEventListener('change', requestUpdate);
window.addEventListener('scroll', requestUpdate, { passive: true });
window.addEventListener('resize', requestUpdate);
requestUpdate();

fetch('/api/info')
  .then((response) => {
    if (!response.ok) throw new Error('Model details unavailable');
    return response.json();
  })
  .then((info) => {
    const correct = Math.round(info.test_accuracy * info.test_rows);
    document.querySelector('#fact-k').textContent = info.k;
    document.querySelector('#fact-accuracy').textContent = `${correct}/${info.test_rows}`;
    document.querySelector('#fact-note').textContent = `The model learned from ${info.training_rows} training flowers. It returns one of three species: Iris-setosa, Iris-versicolor, or Iris-virginica. It classified ${correct} of ${info.test_rows} test flowers correctly. A new result can still be wrong.`;
  })
  .catch(() => {
    document.querySelector('#fact-note').textContent = 'The saved model is unavailable. Run training before you use the classifier.';
  });
