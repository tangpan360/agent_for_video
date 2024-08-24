import re
import json
import os
import requests
import nls
import nls.speech_synthesizer

from moviepy.editor import (ImageClip, AudioFileClip, TextClip, concatenate_audioclips, CompositeVideoClip,
                            CompositeAudioClip, concatenate_videoclips, VideoFileClip, vfx)
from moviepy.config import change_settings

from typing import List
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv

_ = load_dotenv("../.env")
# 指定 ImageMagick 的路径
change_settings({"IMAGEMAGICK_BINARY": r"D:/Program Files/ImageMagick-7.1.1-Q16/magick.exe"})


def parse_json_from_response(rsp: str):
    pattern = r"```json(.*?)```"
    rsp_json = None
    try:
        match = re.search(pattern, rsp, re.DOTALL)
        if match is not None:
            try:
                rsp_json = json.loads(match.group(1).strip())
            except:
                pass
        else:
            rsp_json = json.loads(rsp)
        return rsp_json
    except json.JSONDecodeError as e:
        raise ("Json Decode Error: {error}".format(error=e))


def create_picture_prompt_text_files(sentences, save_folder):
    """
    创建一系列文本文件，文件名为递增数字，一位数前面加0，并命名为 picture_prompt 形式的文件名。

    参数:
    sentences : dict
        一个字典，键为描述性文本（如'sentence_1'），值为要写入文件的内容。
    """
    # 获取当前脚本所在目录
    current_file_path = os.path.abspath(__file__)
    current_dir = os.path.dirname(current_file_path)
    print("current_dir: ", current_dir)

    # 指定保存文件的目录
    dataset_dir = os.path.join(current_dir, '..', save_folder)

    # 如果目录不存在，则创建它
    if not os.path.exists(dataset_dir):
        os.makedirs(dataset_dir)

    # 创建文件并将内容写入
    for i, (key, value) in enumerate(sentences.items(), start=1):
        # 格式化文件名
        file_name = f"0{i:02d}_picture_prompt.txt"

        # 构建完整的文件路径
        file_path = os.path.join(dataset_dir, file_name)

        # 写入文件
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(value)

    print("所有 picture prompt 文件已创建并写入内容。")


# 定义一个自定义的 TTS 类，用于处理语音合成过程中的各种回调
class MyTTS:

    def __init__(self, url: str, token: str, appkey: str):
        self.URL = url
        self.TOKEN = token
        self.APPKEY = appkey

    def on_metainfo(self, message, *args):
        print("on_metainfo message=>{}".format(message))

    def on_error(self, message, *args):
        print("on_error args=>{}".format(args))

    def on_close(self, *args):
        print("on_close: args=>{}".format(args))
        try:
            # 关闭文件
            self.__file.close()
        except Exception as e:
            print("close failed:", e)

    def on_data(self, data, *args):
        try:
            # 将数据写入文件
            self.__file.write(data)
        except Exception as e:
            print("write data failed:", e)

    def on_completed(self, message, *args):
        print("on_completed:args=>{} message=>{}".format(args, message))

    def run(self, text, file, voice="zhiyuan", speech_rate=-456, pitch_rate=0, volume=50, aformat="mp3",
            sample_rate=16000):
        # 打开文件以二进制写模式
        self.__file = open(file, "wb")
        # 创建 NlsSpeechSynthesizer 实例
        tts = nls.NlsSpeechSynthesizer(
            url=self.URL,
            token=self.TOKEN,
            appkey=self.APPKEY,
            # 注册回调函数
            on_metainfo=self.on_metainfo,
            on_data=self.on_data,
            on_completed=self.on_completed,
            on_error=self.on_error,
            on_close=self.on_close
        )

        # 开始语音合成，使用指定的参数
        result = tts.start(
            text,
            voice=voice,
            aformat=aformat,
            sample_rate=sample_rate,
            speech_rate=speech_rate,
            pitch_rate=pitch_rate,
            volume=volume
        )
        # 输出合成结果的状态
        print("tts done with result:{}".format(result))


def generate_and_save_image(query: str, filename: str, image_size: str = "1024x1024", save_folder: str = "") -> None:
    """
    Generates an image based on the user's query or request using OpenAI's DALL-E model and saves it to disk.

    :param query: A natural language description of the image to be generated.
    :param filename: The name of the file to save the image as.
    :param image_size: The size of the image to be generated. (default is "1024x1024")
    :return: The filename of the saved image.
    """
    # 获取当前脚本所在目录
    current_file_path = os.path.abspath(__file__)
    current_dir = os.path.dirname(current_file_path)

    # 指定保存文件的目录
    dataset_dir = os.path.join(current_dir, '..', save_folder)
    # os.makedirs(dataset_dir, exist_ok=True)  # Create the directory if it doesn't exist

    client = OpenAI(
        api_key=os.getenv('OPENAI_API_KEY'),
        base_url=os.getenv('OPENAI_API_BASE'),
        timeout=60
    )  # Initialize the OpenAI client
    response = client.images.generate(model="dall-e-3", prompt=query, n=1, size=image_size)  # Generate images

    # Check if the response is successful
    if response.data:
        image_data = response.data[0]
        file_path = Path(os.path.join(dataset_dir, filename))

        img_url = image_data.url
        img_response = requests.get(img_url)
        if img_response.status_code == 200:
            # Write the binary content to a file
            with open(file_path, "wb") as img_file:
                img_file.write(img_response.content)
                return str(file_path)
        else:
            print(f"Failed to download the image from {img_url}")
    else:
        print("No image data found in the response!")


def process_and_write_text(file, text, base_file_name, output_dir):
    """
    处理文本并将其写入一系列新文件中。

    参数:
    file : file object
        已打开的文件对象，用于获取文件名信息。
    text : str
        要写入新文件的原始文本。
    base_file_name : str
        原始文件的基本名称。
    output_dir : str
        输出文件的目录。
    """
    # 去掉所有引号
    text = text.replace('"', '').replace("'", "").replace('”', '').replace("“", "").replace('’', '').replace("‘", "")

    # 使用正则表达式匹配所有标点符号
    punctuation_pattern = r'[，。！？,.;!?]'
    punctuations = re.findall(punctuation_pattern, text)

    # 分割文本
    start = 0
    line_number = 1
    while start < len(text):
        end = min(start + 21, len(text))
        line = text[start:end]

        # 查找最后一个标点符号的位置
        last_punctuation_pos = None
        for punc in punctuations:
            pos = line.rfind(punc)
            if pos != -1 and (last_punctuation_pos is None or pos > last_punctuation_pos):
                last_punctuation_pos = pos

        # 如果找到了合适的标点符号，替换为换行符
        if last_punctuation_pos is not None:
            line = line[:last_punctuation_pos]
            start += last_punctuation_pos + 1  # 跳过已处理的标点符号
        else:
            start = end

        # 构建新文件名
        new_file_name = f"{base_file_name}_{line_number:03d}.txt"
        new_file_path = os.path.join(output_dir, new_file_name)

        # 写入新文件
        with open(new_file_path, 'w', encoding='utf-8') as new_file:
            new_file.write(line + '\n')

        line_number += 1


def create_text_files(sentences, save_folder):
    """
    创建一系列文本文件，文件名为递增数字，一位数前面加0。
    每个文件中的每一行都会被写入一个新的文件中。

    参数:
    sentences : dict
        一个字典，键为描述性文本（如'sentence_1'），值为要写入文件的内容。
    """
    current_file_path = os.path.abspath(__file__)
    current_dir = os.path.dirname(current_file_path)
    file_path = os.path.join(current_dir, '..', save_folder)

    # 确保目标目录存在
    os.makedirs(file_path, exist_ok=True)

    # 创建文件并将内容写入
    for i, (key, value) in enumerate(sentences.items(), start=1):
        # 格式化文件名
        base_file_name = f"0{i:02d}_subtitle"

        # 处理文本并写入新文件
        with open(os.devnull, 'w', encoding='utf-8') as dummy_file:
            process_and_write_text(dummy_file, value, base_file_name, file_path)

    print("所有 subtitles 文件已创建并写入内容。")


def create_video_for_title(data_folder):
    # 加载第一个图像、字幕和音频文件
    first_image_path = os.path.join(data_folder, "001_picture_prompt.png")
    first_subtitle_path = os.path.join(data_folder, "title.txt")
    first_audio_path = os.path.join(data_folder, "title.mp3")
    bling_audio_path = os.path.join(data_folder, "../../music/bling.mp3")

    # 加载第一个图像
    first_image = ImageClip(first_image_path)

    # 加载第一个音频文件并获取其时长
    first_audio = AudioFileClip(first_audio_path)
    first_audio_duration = first_audio.duration

    # 加载 bling 音频文件并获取其时长
    bling_audio = AudioFileClip(bling_audio_path)
    bling_audio_duration = bling_audio.duration

    # 拼接音频文件
    combined_audio = concatenate_audioclips([first_audio, bling_audio])

    # 加载第一个字幕文件并创建TextClip
    try:
        with open(first_subtitle_path, 'r', encoding='utf-8') as file:
            first_subtitle_text = file.read().strip()  # 去除空白字符
            if not first_subtitle_text:  # 如果文件为空
                raise ValueError(f"No text found in subtitle file {first_subtitle_path}")

            # 设置字幕样式
            # 使用默认字体
            font_path = "C:/Windows/Fonts/HGY4_CNKI.TTF"
            first_subtitle = TextClip(first_subtitle_text, fontsize=100, color='black', bg_color='white', font=font_path, stroke_color='white', stroke_width=2)  # 改变颜色和字体

            # 设置字幕位置为屏幕中心
            video_width, video_height = first_image.size
            first_subtitle = first_subtitle.set_position(('center', 'center'))

            # 设置字幕持续时间
            # 注意：这里我们将字幕持续时间设置为两个音频文件的总和
            total_audio_duration = first_audio_duration + bling_audio_duration
            first_subtitle = first_subtitle.set_duration(total_audio_duration)

            # 设置第一个图像的持续时间与音频相同
            first_image = first_image.set_duration(total_audio_duration)

            # 合并图像片段和字幕
            first_clip = CompositeVideoClip([first_image, first_subtitle])

            # 设置第一个片段的音频
            first_clip = first_clip.set_audio(combined_audio)

            # 导出最终的视频，并在这里指定 fps
            output_file = f"./{data_folder}/title_video.mp4"
            first_clip.write_videofile(output_file, fps=24, codec='libx264', audio_codec='aac')
            print("title_video.mp4 has been generated!\n")
    except FileNotFoundError:
        print(f"Subtitle file {first_subtitle_path} or audio file {first_audio_path} not found.")


def create_video_from_images_audio(data_folder):
    # 获取所有图片文件名
    image_files = sorted([f for f in os.listdir(data_folder) if f.endswith("_picture_prompt.png")])

    # 创建一个列表来保存所有的图像片段
    clips = []
    # 创建一个列表来保存所有的音频片段
    audios = []

    for img_file in image_files:
        # 获取图片的基本名称(如: 001)
        base_name = img_file.split('_')[0]
        image_path = os.path.join(data_folder, img_file)

        # 获取所有与该图片对应的字幕和配音
        subtitle_files = sorted([f for f in os.listdir(data_folder) if f.startswith(base_name) and '_subtitle_' in f and f.endswith(".txt")])
        audio_files = sorted([f for f in os.listdir(data_folder) if f.startswith(base_name) and f.endswith(".mp3")])

        # 加载图片并初始化视频片段
        img_clip = ImageClip(image_path)
        img_clips = []

        for subtitle_file, audio_file in zip(subtitle_files, audio_files):
            # 加载音频
            audio_path = os.path.join(data_folder, audio_file)
            audio = AudioFileClip(audio_path)
            duration = audio.duration

            # 创建图像片段并设置其持续时间为音频的时长
            clip = img_clip.set_duration(duration)

            # 加载字幕文件并创建TextClip
            subtitle_path = os.path.join(data_folder, subtitle_file)
            try:
                with open(subtitle_path, 'r', encoding='utf-8') as file:
                    subtitle_text = file.read().strip()
                    if not subtitle_text:
                        raise ValueError(f"No text found in subtitle file {subtitle_file}")

                    # 设置字幕样式
                    font_path = "C:/Windows/Fonts/HGY4_CNKI.TTF"
                    subtitle = TextClip(subtitle_text, fontsize=50, color='yellow', font=font_path,
                                        stroke_color='black', stroke_width=2)
                    subtitle = subtitle.set_duration(duration)

                    # 设置字幕位置为距离顶部20%
                    video_height = clip.size[1]
                    subtitle = subtitle.set_position(('center', video_height * 0.9))

                    # 合并图像片段和字幕
                    clip = CompositeVideoClip([clip, subtitle])

                    img_clips.append(clip)
                    audios.append(audio)
            except FileNotFoundError:
                print(f"Subtitle file {subtitle_file} not found.")
                continue

        # 合并当前图片的所有字幕片段
        if img_clips:
            final_img_clip = concatenate_videoclips(img_clips)
            clips.append(final_img_clip)

    # 合并所有音频片段
    final_audio = concatenate_audioclips(audios)

    # 加载背景音乐
    bgm_path = os.path.join(data_folder, '../../music/background_music.mp3')
    bgm = AudioFileClip(bgm_path)

    # 调整背景音乐的长度以匹配视频长度
    bgm = bgm.subclip(0, final_audio.duration)

    # 将背景音乐与音频混合
    final_audio_with_bgm = CompositeAudioClip([final_audio, bgm.volumex(0.5)])  # 减小背景音乐音量

    # 合并所有图像片段到一个视频中
    final_clip = concatenate_videoclips(clips, method="compose")
    final_clip = final_clip.set_audio(final_audio_with_bgm)  # 设置音频

    # 导出最终的视频，并在这里指定 fps
    output_file = f"./{data_folder}/main_video.mp4"
    final_clip.write_videofile(output_file, fps=24, codec='libx264', audio_codec='aac')


def merge_videos(video1_path, video2_path, output_path):
    # 加载第一个视频
    video1 = VideoFileClip(video1_path)

    # 加载第二个视频
    video2 = VideoFileClip(video2_path)

    # 合并两个视频片段
    final_video = concatenate_videoclips([video1, video2])

    # 导出最终的视频
    final_video.write_videofile(output_path, codec='libx264', audio_codec='aac')


if __name__ == '__main__':
#     sentences = """```json
# [
#     {
#         "sentence_1": "很久很久以前，在茂密的森林深处，住着一只凶猛的老虎和一只狡猾的狐狸。",
#         "sentence_2": "有一天，这只老虎在林间漫步时，突然发现了正在悠闲散步的狐狸，便猛地扑了过去，一把抓住了它。",
#         "sentence_3": "狐狸眼珠一转，心生一计，它假装镇定地说：“大王，您误会了！我是天帝派来的百兽之王，如果您吃了我，就是违抗天命！”",
#         "sentence_4": "老虎半信半疑，但又不敢轻易吃掉狐狸，怕真的得罪了天帝。",
#         "sentence_5": "狐狸见状，继续说道：“不信的话，咱们就在森林里走一圈，看看其他动物见到我是不是都害怕得逃走。”",
#         "sentence_6": "老虎想了想，决定跟着狐狸走一趟。",
#         "sentence_7": "于是，狐狸昂首挺胸地走在前面，老虎则紧跟其后。森林里的小动物们看到这一幕，都吓得四散奔逃。",
#         "sentence_8": "老虎见此情景，更加确信狐狸真的是百兽之王，于是灰溜溜地放走了狐狸。其实，小动物们逃跑并不是因为狐狸，而是因为它们害怕跟在后面的老虎。狐狸就这样利用老虎的威风，成功地逃过了一劫。。。"
#     }
# ]
# ```"""
#     sentences = parse_json_from_response(sentences)[0]
#     create_text_files(sentences=sentences)

    # # 定义 WebSocket 服务器的 URL 地址
    # URL = os.getenv('ALI_AUDIO_URL')
    #
    # # 设置访问令牌（Token）
    # TOKEN = os.getenv('ALI_AUDIO_TOKEN')
    #
    # # 设置 AppKey
    # APPKEY = os.getenv('ALI_AUDIO_APPKEY')
    #
    # # 创建 MyTTS 类的实例
    # synthesizer = MyTTS(url=URL, token=TOKEN, appkey=APPKEY)
    #
    # # 使用指定参数进行语音合成
    # synthesizer.run(
    #     text="很久很久以前，在茂密的森林深处，住着一只凶猛的老虎和一只狡猾的狐狸，你好呀。",
    #     file="../tests/zhiyuan.mp3",
    #     voice="zhiyuan",
    #     speech_rate=-456,
    #     pitch_rate=0,
    #     volume=50,
    #     sample_rate=16000
    # )

    generate_and_save_image(query="一片茂密的森林深处，老虎和狐狸各自在不同的地方，3D卡通风格", filename="001.png")

