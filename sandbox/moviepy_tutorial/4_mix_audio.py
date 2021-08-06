from conf import SAMPLE_INPUTS, SAMPLE_OUTPUTS
from moviepy.editor import *
from PIL import Image

source_path = os.path.join(SAMPLE_INPUTS, 'sample.mp4') 
source_audio_path = os.path.join(SAMPLE_INPUTS, 'audio.mp3') 

mix_audio_dir = os.path.join(SAMPLE_OUTPUTS, "mixed-audio-dir")
og_audio_path = os.path.join(mix_audio_dir,'og.mp3' )
final_audio_path = os.path.join(mix_audio_dir, 'final.mp3')
final_video_path = os.path.join(mix_audio_dir, 'final-video.mp4')
os.makedirs(mix_audio_dir, exist_ok=True)

video_clip = VideoFileClip(source_path)

original_audio = video_clip.audio
original_audio.write_audiofile(og_audio_path)


background_audio_clip = AudioFileClip(source_audio_path)

bg_music = background_audio_clip.subclip(0, video_clip.duration)

# Decreasing the audio of the background music
bg_music = bg_music.volumex(0.10)

final_audio = CompositeAudioClip([original_audio, bg_music], )

# same fps as the original audio
final_audio.write_audiofile(final_audio_path, fps=original_audio.fps)


final_clip = video_clip.set_audio(final_audio)

final_clip.write_videofile(final_video_path)
# The above should work if not run the below command 
# final_clip.write_videofile(final_video_path, codec='libx264', audio_codec="aac")