# Iris flower classifier

A Python k-nearest-neighbors classifier trained on `data/Iris_data_sample.csv`. Enter sepal length, sepal width, petal length, and petal width in centimeters to predict Iris-setosa, Iris-versicolor, or Iris-virginica. The classifier and local server require Python 3.10+ and no third-party packages.

## Live site

**[Open the Iris classifier](https://vercel-site-snowy-three.vercel.app/)** · [Go straight to the input form](https://vercel-site-snowy-three.vercel.app/predict)

![QR code for the deployed Iris classifier](site-qr.png)

The QR code opens the same production site. The page and prediction API are publicly accessible.

## What is in this repository

- `iris_classifier.py` trains and runs the saved k-nearest-neighbors model.
- `data/Iris_data_sample.csv`, `model.json`, and `metrics.json` contain the input data, trained model, and evaluation results.
- `ui/` holds the landing page, prediction form, styles, scripts, flower images, and scroll animation.
- `app.py`, `launch_local.py`, and the launch scripts run the Python-backed UI on a laptop.
- `vercel-site/api/`, `vercel-site/model_service.py`, and `vercel-site/vercel.json` provide the deployed Python API and routing.
- `build_offline.py` and `build_vercel.py` create local single-file pages and the Vercel deployment directory. Generated files are excluded by `.gitignore`.

## Browser page with the Python model on this laptop

First run `python build_offline.py` to create the single-file pages. Then double-click `Launch_Iris_Local.cmd`. It starts the Python model on `127.0.0.1` and opens `Iris_Classifier_Local.html` in your browser. Keep the launcher window open while you use the page; press Ctrl+C or close the window to stop the model. The browser sends the four measurements to the local Python process, which runs the saved model and returns the species. No internet connection is needed.

If the browser does not open automatically, keep the launcher running and double-click `Iris_Classifier_Local.html`. Opening that HTML file alone shows a clear message until the local model service is started.

## Open without a server

After running `python build_offline.py`, double-click `Iris_Classifier_Offline.html` to run the model in browser JavaScript. The animation, saved model, styles, and prediction code are inside that file.

If you retrain the Python model or edit the source UI, rebuild both HTML files with `python build_offline.py`.

## Run

```powershell
python iris_classifier.py train
python iris_classifier.py predict 5.1 3.5 1.4 0.2
```

The prediction arguments are sepal length, sepal width, petal length, and petal width, in that order. Training writes `model.json` and `metrics.json`. You can supply another compatible CSV with `train --data PATH`.

## Local browser UI

From this project folder in PowerShell, run:

```powershell
.\run_ui.ps1
```

Open `http://127.0.0.1:8765` in a browser. This opens the project story. Scroll to move through the supplied iris animation and read how the classifier works. At the end, select **Try now** to open the input page. You can also open the form directly at `http://127.0.0.1:8765/predict`.

The launcher uses the Python runtime already available on this computer, or a working `python` command on another computer. Press Ctrl+C in PowerShell to stop the server. The UI reads the saved `model.json`; train the model first if that file is missing. It is available only on this computer through `127.0.0.1`. The animation is stored locally in `ui/assets/iris-scroll.mp4` and is served with byte-range support for scroll scrubbing.

The prediction form needs exactly four positive measurements in centimeters:

1. Sepal length
2. Sepal width
3. Petal length
4. Petal width

Use **Predict species** to classify the flower. **Use example** fills a sample measurement set, and **Clear** resets the form. The result shows the species and the fraction of nearest neighbors voting for it; this vote share is not a calibrated probability. The model information panel displays the saved neighbor count, training size, and held-out test accuracy.

## Vercel deployment

Run `python build_vercel.py` from this project folder after changing the UI or retraining. It refreshes `vercel-site/` with the landing page, animation, saved model, and Python API. Deploy **`vercel-site/` as the project root**. Vercel serves the browser pages and runs the saved classifier through `/api/info` and `/api/predict`; the laptop does not need to stay on.

For later updates, install the Vercel CLI (`npm install -g vercel`) and sign in (`vercel login`). From `vercel-site/`, run `vercel deploy` for a preview or `vercel deploy --prod` to update production. Link this folder to the existing `iris-classifier-ml` Vercel project if prompted. The `/predict` route opens the form. Do not deploy the local `app.py` server or either standalone HTML file for this version.

Current production deployment: https://vercel-site-snowy-three.vercel.app/ (project `iris-classifier-ml`).

## Method

The supplied CSV has an ID column, empty values, and invalid numeric markers. The ID is ignored; unlabeled rows are excluded. Invalid or missing measurements are replaced with the median from the current training fold. Features are then standardized using the same fold's mean and standard deviation. This preprocessing is fitted separately within each validation fold to prevent leakage.

Rows are split by species into 80% training and 20% held-out test sets with seed 42. Five-fold stratified validation on the training set picks k from 1, 3, 5, 7, and 9. The saved model contains the training rows after preprocessing, so it can make predictions without retraining. `metrics.json` records validation scores, held-out accuracy, macro F1, per-class scores, and the confusion matrix. The neighbor vote share printed for a prediction is not a calibrated probability.
