from conf import SAMPLE_INPUTS, SAMPLE_OUTPUTS
from moviepy.editor import *
from PIL import Image

source_path = os.path.join(SAMPLE_INPUTS, 'sample.mp4') 
source_audio_path = os.path.join(SAMPLE_INPUTS, 'audio.mp3') 

mix_audio_dir = os.path.join(SAMPLE_OUTPUTS, "mixed-audio-dir")
og_audio_path = os.path.join(mix_audio_dir,'og.mp3' )
final_audio_path = os.path.join(mix_audio_dir, 'overlay-audio.mp3')
final_video_path = os.path.join(mix_audio_dir, 'overlay-video.mp4')
os.makedirs(mix_audio_dir, exist_ok=True)

video_clip = VideoFileClip(source_path)
w, h = video_clip.size
fps = video_clip.fps

original_audio = video_clip.audio
original_audio.write_audiofile(og_audio_path)


background_audio_clip = AudioFileClip(source_audio_path)

bg_music = background_audio_clip.subclip(0, video_clip.duration)

# Decreasing the audio of the background music
bg_music = bg_music.volumex(0.10)

intro_duration = 5
intro_text = TextClip('Hello World!', fontsize=70, color='white', size=video_clip.size) # Default bg color is black, so text color is white.

intro_text = intro_text.set_duration(intro_duration)
intro_text = intro_text.set_fps(fps)

intro_text = intro_text.set_pos('center')

final_clip = concatenate_videoclips([intro_text, video_clip])

# intro_text.write_videofile(final_video_path)

# final_clip.write_videofile(final_video_path)


watermark_text = TextClip("Sourabh", fontsize=30, color="white", align='East', size = (w, 30))

watermark_text =  watermark_text.set_fps(fps)
watermark_text =  watermark_text.set_duration(video_clip.reader.duration)

watermark_text = watermark_text.set_position(("bottom"))


cvc = CompositeVideoClip([video_clip, watermark_text], size=video_clip.size)

cvc = cvc.set_duration(video_clip.reader.duration)

cvc = cvc.set_fps(fps)

cvc.write_videofile(final_video_path)

