from conf import SAMPLE_INPUTS, SAMPLE_OUTPUTS
from moviepy.editor import *
from PIL import Image
from moviepy.video.fx.all import crop

source_path = os.path.join(SAMPLE_INPUTS, 'sample.mp4') 

GIF_DIR = os.path.join(SAMPLE_OUTPUTS, "gif")

os.makedirs(GIF_DIR, exist_ok=True)

output_path = os.path.join(GIF_DIR, 'sample1.gif')

clip = VideoFileClip(source_path)
fps = clip.reader.fps
subclip = clip.subclip(10,20)
subclip = subclip.resize(width=500) # will resize while maintaining aspect ratio
subclip.write_gif(output_path, fps=20, program='ffmpeg') # program by default is imageio. gifs created by ffmpeg are smaller in size and faster.


# Cropping the video

w, h = clip.size

subclip2 = clip.subclip(10, 20)

square_cropped_clip = crop(subclip, width=320, height=320, x_center=w/2, y_center=h/2)


square_cropped_clip.write_gif(output_path, fps=fps, program='ffmpeg')

 