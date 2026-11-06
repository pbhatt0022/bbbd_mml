# scripts

Command-line wrappers for long runs on Colab (e.g. preprocessing every recording, training DL models across folds), so a notebook does not need to stay open. Each script loads `config.yaml`, writes through `bbbd.runlog`, and is called from a notebook cell, e.g. `!python scripts/preprocess_eeg.py --experiment 2`.

Add scripts here as the pipelines are built (Sat 7 Nov onwards).
