from conf import SAMPLE_INPUTS, SAMPLE_OUTPUTS
from moviepy.editor import *
from PIL import Image

source_path = os.path.join(SAMPLE_INPUTS, 'sample.mp4') 
thumbnail_dir = os.path.join(SAMPLE_OUTPUTS, 'thumbnails')
thumbnail_per_dir = os.path.join(SAMPLE_OUTPUTS, 'thumbnails_per_frame')

os.makedirs(thumbnail_dir, exist_ok=True)
os.makedirs(thumbnail_per_dir, exist_ok=True)


clip = VideoFileClip(source_path)

print(clip.reader.fps) # fps
print(clip.reader.nframes) #number of frames
print(clip.duration) # duration of the clip. Other way to call is clip.read.duration

duration = clip.duration

max_duration = int(duration) + 1 # Converting to int because the number of seconds in a clip can be a float value

for i in range(0, max_duration):
    frame = clip.get_frame(i) 
    # print(frame) # Prints numpy array of pixels of the image at that second. 
    new_img = Image.fromarray(frame)
    new_img_filepath = os.path.join(thumbnail_dir, f"{i}.jpg")
    # print(f"frame at {i} seconds saved at {new_img_filepath}")
    new_img.save(new_img_filepath)


fps = clip.reader.fps
nframes = clip.reader.nframes
seconds = nframes / (fps * 1.0)



# for i,frame in enumerate(clip.iter_frames()):  #To iterate from the first frame to the last of the clip.    
#     new_img = Image.fromarray(frame)
#     new_img_filepath = os.path.join(thumbnail_per_dir, f"{i}.jpg")
#     # print(f"frame at {i} seconds saved at {new_img_filepath}")
#     new_img.save(new_img_filepath)