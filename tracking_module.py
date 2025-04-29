# tracking_module.py

import os
import imagej
import pandas as pd
import numpy as np
import cv2
from PIL import Image

# Constants (can be customized or passed to the function)
linking_max_distance = 50.0
gap_closing_max_distance = 50.0
max_frame_gap = 5
tracks_csv_name = "tracks.csv"
spots_csv_name = "spots.csv"

# Initialize Fiji / ImageJ once globally
ij = imagej.init('Fiji.app', headless=True)  # Start ImageJ instance (specifically, Fiji) for TrackMate plugin access.

def export_to_csv(data, headers, file_path):
    df = pd.DataFrame(data, columns=headers)
    df.to_csv(file_path, index=False)

def run_trackmate(sequence_dir, output_dir):
    if not os.path.isdir(sequence_dir):
        raise FileNotFoundError(f"Input directory not found: {sequence_dir}")

    folder_path = sequence_dir.replace("\\", "/")

    groovy_script = f"""
    import ij.plugin.FolderOpener;
    import fiji.plugin.trackmate.Model;
    import fiji.plugin.trackmate.Settings;
    import fiji.plugin.trackmate.TrackMate;
    import fiji.plugin.trackmate.detection.LabelImageDetectorFactory;
    import fiji.plugin.trackmate.Logger;
    import fiji.plugin.trackmate.providers.TrackerProvider;
    import fiji.plugin.trackmate.features.spot.SpotShapeAnalyzerFactory;
    import fiji.plugin.trackmate.features.spot.SpotFitEllipseAnalyzerFactory;
    import ij.ImagePlus;

    String folderPath = "{folder_path}";
    ImagePlus imp = FolderOpener.open(folderPath, "");
    if (imp == null) {{
        throw new IllegalArgumentException("Failed to load the image sequence.");
    }}

    if (imp.getNFrames() == 1 && imp.getNSlices() > 1) {{
        imp.setDimensions(1, 1, imp.getStackSize());
    }}

    Model model = new Model();
    model.setLogger(Logger.DEFAULT_LOGGER);
    Settings settings = new Settings().copyOn(imp);

    settings.detectorFactory = new LabelImageDetectorFactory();
    settings.detectorSettings.put("TARGET_CHANNEL", 1 as java.lang.Integer);
    settings.detectorSettings.put("SIMPLIFY_CONTOURS", true);

    settings.addSpotAnalyzerFactory(new SpotShapeAnalyzerFactory());
    settings.addSpotAnalyzerFactory(new SpotFitEllipseAnalyzerFactory());

    TrackerProvider trackerProvider = new TrackerProvider();
    settings.trackerFactory = trackerProvider.getFactory("SPARSE_LAP_TRACKER");
    settings.trackerSettings.put("LINKING_MAX_DISTANCE", {linking_max_distance} as java.lang.Double);
    settings.trackerSettings.put("GAP_CLOSING_MAX_DISTANCE", {gap_closing_max_distance} as java.lang.Double);
    settings.trackerSettings.put("ALLOW_GAP_CLOSING", true);
    settings.trackerSettings.put("MAX_FRAME_GAP", {max_frame_gap} as java.lang.Integer);
    settings.trackerSettings.put("ALLOW_TRACK_SPLITTING", true);
    settings.trackerSettings.put("SPLITTING_MAX_DISTANCE", 20.0 as java.lang.Double);
    settings.trackerSettings.put("ALLOW_TRACK_MERGING", true);
    settings.trackerSettings.put("MERGING_MAX_DISTANCE", 20.0 as java.lang.Double);
    settings.trackerSettings.put("ALTERNATIVE_LINKING_COST_FACTOR", 1.05 as java.lang.Double);
    settings.trackerSettings.put("CUTOFF_PERCENTILE", 0.9 as java.lang.Double);
    settings.trackerSettings.put("BLOCKING_VALUE", 10000.0 as java.lang.Double);

    TrackMate trackmate = new TrackMate(model, settings);
    if (!trackmate.checkInput()) {{
        throw new IllegalArgumentException("TrackMate input check failed: " + trackmate.getErrorMessage());
    }}
    if (!trackmate.process()) {{
        throw new IllegalArgumentException("TrackMate process failed: " + trackmate.getErrorMessage());
    }}

    def spotsData = [];
    for (trackID in model.getTrackModel().trackIDs(true)) {{
        for (spot in model.getTrackModel().trackSpots(trackID)) {{
            def spotMap = [:];
            spotMap['ID'] = spot.ID();
            spotMap['TRACK_ID'] = trackID;
            spotMap['POSITION_X'] = spot.getFeature('POSITION_X');
            spotMap['POSITION_Y'] = spot.getFeature('POSITION_Y');
            spotMap['POSITION_Z'] = spot.getFeature('POSITION_Z');
            spotMap['POSITION_T'] = spot.getFeature('POSITION_T');
            spotMap['FRAME'] = spot.getFeature('FRAME');
            spotMap['RADIUS'] = spot.getFeature('RADIUS');
            spotMap['AREA'] = spot.getFeature('AREA');
            spotMap['CIRCULARITY'] = spot.getFeature('CIRCULARITY');
            spotMap['SOLIDITY'] = spot.getFeature('SOLIDITY');
            spotMap['ELLIPSE_ASPECTRATIO'] = spot.getFeature('ELLIPSE_ASPECTRATIO');
            spotsData.add(spotMap);
        }}
    }}

    def tracksData = [];
    for (trackID in model.getTrackModel().trackIDs(true)) {{
        def trackMap = [:];
        trackMap['TRACK_ID'] = trackID;
        trackMap['NUMBER_SPOTS'] = model.getTrackModel().trackSpots(trackID).size();
        trackMap['NUMBER_SPLITS'] = model.getFeatureModel().getTrackFeature(trackID, 'NUMBER_SPLITS');
        trackMap['NUMBER_MERGES'] = model.getFeatureModel().getTrackFeature(trackID, 'NUMBER_MERGES');
        trackMap['TRACK_DISPLACEMENT'] = model.getFeatureModel().getTrackFeature(trackID, 'TRACK_DISPLACEMENT');
        tracksData.add(trackMap);
    }}

    return ['spots': spotsData, 'tracks': tracksData];
    """

    script_engine = ij.script().getLanguageByName("Groovy").getScriptEngine()
    results = script_engine.eval(groovy_script)

    spots = results.get("spots")
    tracks = results.get("tracks")

    export_to_csv(
        spots,
        ["ID", "TRACK_ID", "POSITION_X", "POSITION_Y", "POSITION_Z", "POSITION_T",
         "FRAME", "RADIUS", "CIRCULARITY", "SOLIDITY", "AREA", "ELLIPSE_ASPECTRATIO"],
        os.path.join(output_dir, spots_csv_name)
    )
    export_to_csv(
        tracks,
        ["TRACK_ID", "NUMBER_SPOTS", "NUMBER_SPLITS", "NUMBER_MERGES", "TRACK_DISPLACEMENT"],
        os.path.join(output_dir, tracks_csv_name)
    )

def visualize_spots(image_path, spots, output_path):
    img = Image.open(image_path)
    img_np = np.array(img)
    img_rgb = cv2.cvtColor(img_np, cv2.COLOR_GRAY2RGB).astype(np.uint8)

    for spot in spots:
        x = spot["POSITION_X"]
        y = spot["POSITION_Y"]
        radius = spot["RADIUS"]
        if x and y and radius:
            cv2.ellipse(
                img_rgb,
                center=(int(x), int(y)),
                axes=(int(radius), int(radius)),
                angle=0,
                startAngle=0,
                endAngle=360,
                color=(255, 0, 0),
                thickness=1,
            )

    output_img = Image.fromarray(img_rgb)
    output_img.save(output_path)

def add_spot_visualizations(sequence_dir, output_dir, spots_csv):
    spots_df = pd.read_csv(spots_csv)
    if "FRAME" in spots_df.columns:
        spots_df["FRAME"] = spots_df["FRAME"].fillna(0).astype(int)
    else:
        raise KeyError("Missing 'FRAME' column in spots CSV.")

    for frame in range(spots_df["FRAME"].min(), spots_df["FRAME"].max() + 1):
        frame_spots = spots_df[spots_df["FRAME"] == frame].to_dict(orient="records")
        frame_path = os.path.join(sequence_dir, f"frame_{frame+1}_mask.tif")
        output_path = os.path.join(output_dir, f"frame_{frame+1}_overlay.png")
        visualize_spots(frame_path, frame_spots, output_path)

def run_trackmate_and_visualize(segmented_dir, csv_dir, overlay_dir):
    os.makedirs(csv_dir, exist_ok=True)
    os.makedirs(overlay_dir, exist_ok=True)
    run_trackmate(segmented_dir, csv_dir)
    spots_csv_path = os.path.join(csv_dir, spots_csv_name)
    add_spot_visualizations(segmented_dir, overlay_dir, spots_csv_path)