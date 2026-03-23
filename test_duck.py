import numpy as np

def make_ducking_filter(t, transcriptions, ducking_volume=0.1):
    t_arr = np.array(t)
    vol = np.ones_like(t_arr, dtype=float)
    for seg in transcriptions:
        mask = (t_arr >= seg['start'] - 0.3) & (t_arr <= seg['end'] + 0.3)
        vol = np.where(mask, ducking_volume, vol)
    if np.isscalar(t):
        return float(vol)
    return vol[:, None]

t = np.array([0.0, 0.5, 1.0, 1.5, 2.0])
frames = np.ones((5, 2))
transcriptions = [{'start': 0.8, 'end': 1.2}]

print(make_ducking_filter(t, transcriptions) * frames)
print("Scalar test:", make_ducking_filter(1.0, transcriptions) * np.array([1, 1]))
