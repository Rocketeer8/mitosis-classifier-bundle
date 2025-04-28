# Mitosis Classifier Bundle

This project provides an easy-to-use pipeline for analyzing cell mitosis events from time-lapse images. It includes:

- **Stage 1**: Segmentation (using Cellpose)
- **Stage 2**: Tracking (using Fiji TrackMate)
- **Stage 3**: Post-tracking classification

All packed neatly into a **Docker** container for easy setup!

---

## Prerequisites

- **Docker Desktop** installed and running.
- **Windows**, **MacOS**, or **Linux** supported (any OS that runs Docker).
- Your data must be prepared inside an `/input` folder next to the project.

---

## Folder Structure

```
mitosis-classifier-bundle/
|-- Dockerfile
|-- run.bat (Windows helper)
|-- requirements.txt
|-- segmentation_module.py
|-- tracking_module.py
|-- post_tracking_module.py
|-- run_pipeline.py
|-- input/ (place your TIFF images here)
|-- output/ (results will be generated here)
```

---

## Quick Start

### 1. Download the repository

- Either clone it:
  ```bash
  git clone <repo_link>
  ```
- **OR** download as `.zip` and extract.

### 2. Place your images

- Put all your original `.tif` / `.tiff` files inside the `/input` folder.

### 3. Run the pipeline (Windows)

- Double-click `run.bat`
- It will:
  1. Build the Docker image
  2. Run the container
  3. Automatically execute the full pipeline

If successful, your output (segmented images, tracking data, overlays) will appear inside `/output/`.

### 4. Run manually (Mac/Linux)

```bash
# Build the docker image
docker build -t mitosis-classifier .

# Run the docker container
docker run -it --rm -v "$PWD/input:/app/input" -v "$PWD/output:/app/output" mitosis-classifier
```

---

## Notes

- **Java + Maven**: Installed inside Docker to allow Fiji (TrackMate) to run.
- **Cellpose**: Automatically installed.
- **Fiji**: Expected to be bundled inside `/app/Fiji.app` folder (already handled).
- **Output**: Classified mitosis events ("Success", "Failure", etc.) and overlays.

---

## Troubleshooting

- Make sure Docker Desktop is running!
- If Docker build fails, try rebuilding with:
  ```bash
  docker build --no-cache -t mitosis-classifier .
  ```
- If issues persist, please open an issue in the repo.

---

## License

MIT License

---

## Acknowledgements

- [Cellpose](https://github.com/MouseLand/cellpose)
- [Fiji/ImageJ](https://fiji.sc/)
- [TrackMate](https://imagej.net/plugins/trackmate/)

---

Enjoy your automated mitosis analysis! 👩‍🔬
