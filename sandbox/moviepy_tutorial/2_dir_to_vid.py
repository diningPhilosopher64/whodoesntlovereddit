from conf import SAMPLE_INPUTS, SAMPLE_OUTPUTS
from moviepy.editor import *
from PIL import Image

thumbnail_dir = os.path.join(SAMPLE_OUTPUTS, 'thumbnails')
thumbnail_per_dir = os.path.join(SAMPLE_OUTPUTS, 'thumbnails_per_frame')

unordered_output_video = os.path.join(SAMPLE_OUTPUTS, 'thumbs_unordered.mp4')
ordered_output_video = os.path.join(SAMPLE_OUTPUTS, 'thumbs_ordered.mp4')

this_dir = os.listdir(thumbnail_dir)


# The order in which these file_paths present in the array will lead to the same order in the video.
# Here when we iterate, os.listdir() will return in alphabetical order ie. 11.jpg is before 2.jpg.
# To avoid this, we use os.walk below
file_paths = [ os.path.join(thumbnail_dir, fname) for fname in this_dir if fname.endswith('.jpg')] 



os.makedirs(thumbnail_dir, exist_ok=True)
os.makedirs(thumbnail_per_dir, exist_ok=True)


clip = ImageSequenceClip(file_paths, fps=1)
clip.write_videofile(unordered_output_video)


# here we are storing the file path as the value and the file name as a key. The key has a float data type.
# This will enable us to sort the keys.
directory = {}
for root, dirs, files in os.walk(thumbnail_dir):
    for fname in files:
        file_path = os.path.join(root, fname)
        try:
            key = float(fname.replace(".jpg", ""))
        except:
            key = None    
		
        if key != None:
        	directory[key] = file_path
         
         
ordered_file_paths = []
for k in sorted(directory.keys()):
    file_path = directory[k]
    ordered_file_paths.append(file_path)
    
    
clip = ImageSequenceClip(ordered_file_paths, fps=1)
clip.write_videofile(ordered_output_video)
  
    
    