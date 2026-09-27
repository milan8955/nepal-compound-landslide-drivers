# make data PROJECT=my-gcp-project  |  make analysis  |  make test
PROJECT ?= YOUR_GCP_PROJECT
data:
	python scripts/01_download_boundaries.py
	python scripts/02_download_bipad.py
	python scripts/03_download_coolr.py
	python scripts/04_download_forcing_gee.py --project $(PROJECT) --product era5l
	python scripts/04_download_forcing_gee.py --project $(PROJECT) --product imerg
analysis:
	python scripts/05_build_table.py
	python scripts/06_run_analysis.py
robustness:
	python scripts/07_robustness.py
test:
	pytest -q
.PHONY: data analysis robustness test
