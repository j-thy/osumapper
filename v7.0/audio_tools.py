# -*- coding: utf-8 -*-

#
# For osu! file reading and analysis
#

import librosa;
import re, os, subprocess, json;
import numpy as np;
from os_tools import *;
from map_analyze import *;
from hitsound_tools import *;

# It will always fail. Soundfile doesn't support mp3
import warnings;
warnings.filterwarnings("ignore", message="PySoundFile failed. Trying audioread instead.");

workingdir = os.path.dirname(os.path.abspath(__file__));
os.chdir(workingdir);

# This ffmpeg path is unused
if(os.path.isfile('./FFmpeg/ffmpeg.exe')):
    FFMPEG_PATH = "FFmpeg\\ffmpeg.exe";
else:
    FFMPEG_PATH = "ffmpeg";

def read_osu_file(path, convert=False, wav_name="wavfile.wav", json_name="temp_json_file.json"):
    """
    Read .osu file to get audio path and JSON formatted map data
    "convert" will also read the music file (despite the name it doesn't convert)
    """
    file_dir = os.path.dirname(os.path.abspath(path));

    # ask node.js to convert the .osu file to .json format
    result = run_command(["node", "load_map.js", "jq", path, json_name]);
    if(len(result) > 1):
        print(result.decode("utf-8"));
        raise Exception("Map Convert Failure");

    with open(json_name, encoding="utf-8") as map_json:
        map_dict = json.load(map_json);

        if convert:
            mp3_file = os.path.join(file_dir, map_dict["general"]["AudioFilename"]);
            # result = run_command([FFMPEG_PATH, "-y", "-i", mp3_file, wav_name]);
            # if(len(result) > 1):
            #     print(result.decode("utf-8"));
            #     raise Exception("FFMPEG Failure");

    # delete the temp json later
    # if json_name == "temp_json_file.json":
    #     os.remove(json_name);

    return map_dict, mp3_file;

# Analyze the pitches/frequencies in the audio sample
def get_freqs(sig, fft_size):
    # Applies FFT to the input signal
    Lf = np.fft.fft(sig, fft_size);
    # Keep only the positive frequencies of the FFT
    Lc = Lf[0:fft_size//2];
    # Get the magnitude of the FFT
    La = np.abs(Lc[0:fft_size//2]);
    # Get the phase of the FFT
    Lg = np.angle(Lc[0:fft_size//2]);
    return La, Lg;

# Slices the wave at a given time in milliseconds
def slice_wave_at(ms, sig, samplerate, size):
    # Calculate the index corresponding to ms in the wave signal
    ind = (ms/1000 * samplerate)//1;
    # Take a slice of length size centered at that index
    return sig[max(0, int(ind - size//2)):int(ind + size - size//2)];

def lrmix(sig):
    """
    Get mono from stereo audio data. Unused in this version (already mono)
    """
    return (sig[:,0]+sig[:,1])/2;

def get_wav_data_at(ms, sig, samplerate, fft_size=2048, freq_low=0, freq_high=-1):
    # Default to half of the sampling rate if not specified
    if freq_high == -1:
        freq_high = samplerate//2;

    # Get a slice of the wave at the given time
    waveslice = slice_wave_at(ms, sig, samplerate, fft_size);

    # Find the frequencies in the wave slice
    La, Lg = get_freqs(waveslice, fft_size);

    # Only keep the frequencies in the specified range
    La = La[fft_size*freq_low//samplerate:fft_size*freq_high//samplerate];
    Lg = Lg[fft_size*freq_low//samplerate:fft_size*freq_high//samplerate];

    return La, Lg;

def read_wav_data(timestamps, wavfile, snapint=[-0.3, -0.2, -0.1, 0, 0.1, 0.2, 0.3], fft_size = 1024):
    """
    Read audio data based on timestamps.

    Snapint are percentages of difference between two timestamps.
    These are read to handle potential small offset differences between python and osu!.

    Resampling disabled for librosa because it is too slow.
    """
    # Read in WAV file as a mono signal and use native sampling
    # Sig is the audio signal as a 1D numpy array
    # Samplerate is the sampling rate of the audio signal
    sig, samplerate = librosa.load(wavfile, sr=None, mono=True);
    data = list();

    # Normalize sound wave and ensure the maximum absolute value of the signal is equal to 1
    sig = sig / np.max(np.abs(sig));

    # Calculate the time interval between each timestamp and append it to the end of the array.
    tmpts = np.array(timestamps);
    timestamp_interval = tmpts[1:] - tmpts[:-1];
    timestamp_interval = np.append(timestamp_interval, timestamp_interval[-1]);

    for sz in snapint:
        # For each timestamp, get the frequency/pitch data at that time and append it to the data array 
        data_r = np.array([get_wav_data_at(max(0, min(len(sig) - fft_size, coord + timestamp_interval[i] * sz)), sig, samplerate, fft_size=fft_size, freq_high=samplerate//4) for i, coord in enumerate(timestamps)]);
        data.append(data_r);

    raw_data = np.array(data);
    # Normalize the data
    norm_data = np.tile(np.expand_dims(np.mean(raw_data, axis=1), 1), (1, raw_data.shape[1], 1, 1));
    # Standardize the data
    std_data = np.tile(np.expand_dims(np.std(raw_data, axis=1), 1), (1, raw_data.shape[1], 1, 1));
    # Return the normalized and standardized data
    return (raw_data - norm_data) / std_data;

def get_transformed_lst_data(data):
    transformed_data = [];
    for d in data:
        if d[3] == 1:
            transformed_data.append([d[0], d[1], d[2], 1, 0, 0, 1, 0, d[4], d[5], d[6], d[7], d[8], d[9]]);
        elif d[3] == 2:
            transformed_data.append([d[0], d[1], d[2], 0, 1, 0, 0, 0, d[4], d[5], d[6], d[7], d[8], d[9]]);
        elif d[3] == 3:
            transformed_data.append([d[0], d[1], d[2], 0, 0, 1, 0, 0, d[4], d[5], d[6], d[7], d[8], d[9]]);
        elif d[3] == 4:
            transformed_data.append([d[0], d[1], d[2], 0, 0, 0, 1, 0, d[4], d[5], d[6], d[7], d[8], d[9]]);
        elif d[3] == 5:
            transformed_data.append([d[0], d[1], d[2], 0, 0, 0, 1, 0, d[4], d[5], d[6], d[7], d[8], d[9]]);
        else:
            transformed_data.append([d[0], d[1], d[2], 0, 0, 0, 0, 0, d[4], d[5], d[6], d[7], d[8], d[9]]);
    return transformed_data;

def read_and_save_osu_file(path, filename = "saved", divisor=4):
    """
    # Main function
    # Generated data shape:
    #     - "lst" array, length MAPTICKS
    #        table of [TICK, TIME, NOTE, IS_CIRCLE, IS_SLIDER, IS_SPINNER, IS_NOTE_END, UNUSED, SLIDING, SPINNING, MOMENTUM, EX1, EX2, EX3],
    #                     0,    1,    2,         3,         4,          5,           6,      7,        8,       9,       10
    #     - "wav" array, shape of [len(snapsize), MAPTICKS, 2, fft_size//4]
    #     - "flow" array, table of [TICK, TIME, TYPE, X, Y, IN_DX, IN_DY, OUT_DX, OUT_DY] notes only
    #     - "hs" array, shape [groups, metronome_count * divisor + 1]
    #
    # MAPTICKS = (Total map time + 3000) / tickLength / (divisor = 4) - EMPTY_TICKS
    # EMPTY_TICKS = ticks where no note around in 5 secs
    """
    osu_dict, wav_file = read_osu_file(path, convert = True);
    # Data is rhythm, flow data is placement
    data, flow_data = get_map_notes(osu_dict, divisor=divisor);
    # Get ticks/timestamps
    timestamps = [c[1] for c in data];
    # Get an array of frequencies/pitches at each timestamp
    wav_data = read_wav_data(timestamps, wav_file, snapint=[-0.3, -0.2, -0.1, 0, 0.1, 0.2, 0.3], fft_size = 128);
    # Make time the x-axis and frequency the y-axis
    wav_data = np.swapaxes(wav_data, 0, 1);

    # change the representation of note_type
    # a bit of copypaste code because I changed the data structure many times here
    transformed_data = get_transformed_lst_data(data);

    # read hitsounds from circles for taiko mode
    hs_data = get_circle_hitsounds(osu_dict, divisor=divisor);

    np.savez_compressed(filename, lst = transformed_data, wav = wav_data, flow = flow_data, hs = hs_data);

def read_and_save_timestamps(path, filename = "saved", divisor=4):
    """
    Only used in debugging
    """
    osu_dict, wav_file = read_osu_file(path, convert = True);
    data, flow_data = get_map_notes(osu_dict, divisor=divisor);
    timestamps = [c[1] for c in data];
    with open(filename + "_ts.json", "w") as json_file:
        json.dump(np.array(timestamps).tolist(), json_file);

def read_and_save_osu_file_using_json_wavdata(path, json_path, filename = "saved", divisor=4):
    """
    Only used in debugging
    """
    osu_dict, wav_file = read_osu_file(path, convert = True);
    data, flow_data = get_map_notes(osu_dict, divisor=divisor);
    with open(json_path) as wav_json:
        wav_data = json.load(wav_json)
    # in order to match first dimension
    # wav_data = np.swapaxes(wav_data, 0, 1);

    # change the representation of note_type
    # a bit of copypaste code because I changed the data structure many times here
    transformed_data = get_transformed_lst_data(data);

    # read hitsounds from circles for taiko mode
    hs_data = get_circle_hitsounds(osu_dict, divisor=divisor);

    np.savez_compressed(filename, lst = transformed_data, wav = wav_data, flow = flow_data, hs = hs_data);

def read_and_save_osu_tester_file(path, filename = "saved", json_name="mapthis.json", divisor=4):
    osu_dict, wav_file = read_osu_file(path, convert = True, json_name=json_name);
    sig, samplerate = librosa.load(wav_file, sr=None, mono=True);
    file_len = (sig.shape[0] / samplerate * 1000 - 3000);

    # ticks = ticks from each uninherited timing section
    ticks, timestamps, tick_lengths, slider_lengths = get_all_ticks_and_lengths_from_ts(osu_dict["timing"]["uts"], osu_dict["timing"]["ts"], file_len, divisor=divisor);

    # old version to determine ticks (all from start)
    # ticks = np.array([i for i,k in enumerate(timestamps)]);
    extra = np.array([60000 / tick_lengths, slider_lengths]);

    wav_data = read_wav_data(timestamps, wav_file, snapint=[-0.3, -0.2, -0.1, 0, 0.1, 0.2, 0.3], fft_size = 128);
    # in order to match first dimension
    wav_data = np.swapaxes(wav_data, 0, 1);

    np.savez_compressed(filename, ticks = ticks, timestamps = timestamps, wav = wav_data, extra = extra);

def read_and_return_osu_file(path, divisor=4):
    osu_dict, wav_file = read_osu_file(path, convert = True);
    data, flow_data = get_map_notes(osu_dict, divisor=divisor);
    timestamps = [c[1] for c in data];
    wav_data = read_wav_data(timestamps, wav_file, snapint=[-0.3, -0.2, -0.1, 0, 0.1, 0.2, 0.3], fft_size = 128);
    return data, wav_data, flow_data;

def test_process_path(path, version_var="--version"):
    """
    Use the version command to test if a dependency works
    """
    try:
        subprocess.call([path, version_var]);
        return True;
    except:
        print("Cannot find executable on {}".format(path));
        return False;
