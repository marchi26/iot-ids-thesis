# Dataset Download Instructions

Dataset name: TON_IoT / UNSW network dataset.

The project expects the network flow CSV commonly named `train_test_network.csv`. It can be downloaded from Kaggle mirrors of the TON_IoT Network Dataset or from the official UNSW TON_IoT dataset pages.

Place the file here:

```text
data/raw/train_test_network.csv
```

Raw datasets must not be committed to Git. The `data/raw/` and `data/processed/` directories are ignored to keep the repository lightweight and reproducible.

If the Kaggle CLI is used on Windows and the default user profile configuration path is not writable, create a local `.kaggle/` directory and place `kaggle.json` inside it. The `.kaggle/` directory and `kaggle.json` are ignored by Git. Set `KAGGLE_CONFIG_DIR` to that local directory before running Kaggle commands.

The helper script `scripts/download_dataset.ps1` uses the Kaggle dataset slug `arnobbhowmik/ton-iot-network-dataset` by default, matching the community mirror cited in the supervisor repository. If a different official or Kaggle source is used, document the source and verify that the CSV schema still contains `label` and `type`.
