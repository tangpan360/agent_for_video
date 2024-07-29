import os
import autogen
from utils import MyTTS
from prompt import WRITER_PROMPT, MUSIC_PROMPT, SPLIT_PROMPT, PICTURE_PROMPT
from utils import parse_json_from_response
from utils import create_text_files
from utils import create_picture_prompt_text_files
from moviepy.editor import AudioFileClip, concatenate_audioclips
from utils import generate_and_save_image, create_video_for_title, create_video_from_images_audio, merge_videos

from dotenv import load_dotenv

_ = load_dotenv('./.env')

# 获取阿里云语音合成服务所需的 URL、TOKEN 和 APPKEY
URL = os.getenv("ALI_AUDIO_URL")
TOKEN = os.getenv("ALI_AUDIO_TOKEN")
APPKEY = os.getenv("ALI_AUDIO_APPKEY")


def concatenate_audio_files(data_folder, title_audio='title.mp3', bling_audio='bling.mp3', output_audio='first_image.mp3'):
    # 加载第一个音频文件
    title_audio_path = os.path.join(data_folder, title_audio)
    title_audio = AudioFileClip(title_audio_path)

    # 加载第二个音频文件
    bling_audio_path = os.path.join(data_folder, bling_audio)
    bling_audio = AudioFileClip(bling_audio_path)

    # 拼接两个音频文件
    concatenated_audio = concatenate_audioclips([title_audio, bling_audio])

    # 保存拼接后的音频文件
    output_path = os.path.join(data_folder, output_audio)
    concatenated_audio.write_audiofile(output_path)

# if __name__ == "__main__":
#     data_folder = "./dataset"
#     concatenate_audio_files(data_folder)


def check_and_generate_missing_images(prompts_dir, generated_images):
    while True:
        missing_images = set()

        for filename in os.listdir(prompts_dir):
            if filename.endswith("_picture_prompt.txt"):
                base_name = os.path.splitext(filename)[0]
                expected_image = f"{base_name}.png"

                if expected_image not in generated_images:
                    missing_images.add(expected_image)

        if not missing_images:
            print("All images have been generated successfully.")
            break

        for missing_image in missing_images:
            prompt_file = f"{os.path.splitext(missing_image)[0]}_picture_prompt.txt"
            prompt_path = os.path.join(prompts_dir, prompt_file)

            if os.path.exists(prompt_path):
                # 读取文件中的prompt
                with open(prompt_path, 'r', encoding='utf-8') as file:
                    prompt = file.read().strip()

                # 生成并保存图像
                generate_and_save_image(prompt, missing_image, prompts_dir)
                generated_images.add(missing_image)
                print(f"Re-generated image for '{prompt}' and saved as '{missing_image}'.")


def generate_images(prompts_dir):
    # 指定读取文件的目录
    generated_images = set()

    # 遍历目录中的所有文件生成图片
    for filename in os.listdir(prompts_dir):
        if filename.endswith("_picture_prompt.txt"):
            # 去掉文件扩展名，添加新的扩展名
            base_name = os.path.splitext(filename)[0]
            new_filename = f"{base_name}.png"
            new_filepath = os.path.join(prompts_dir, new_filename)

            if os.path.exists(new_filepath):
                generated_images.add(new_filename)
                continue

            # 读取文件中的prompt
            with open(os.path.join(prompts_dir, filename), 'r', encoding='utf-8') as file:
                prompt = file.read().strip()

            # 生成并保存图像
            generate_and_save_image(query=prompt, filename=new_filename, save_folder=prompts_dir)
            generated_images.add(new_filename)
            print(f"Generated image for '{prompt}' and saved as '{new_filename}'.")

    # 检查目录中的图片文件是否都生成成功
    check_and_generate_missing_images(prompts_dir, generated_images)


def main(title: str, content: str, save_folder: str) -> None:

    if not os.path.exists(save_folder):
        os.makedirs(save_folder)

    llm_config = {
        'model': "gpt-4o-all",
        "api_key": os.getenv("OPENAI_API_KEY"),
        "base_url": os.getenv("OPENAI_API_BASE"),
    }
    print(os.getenv("OPENAI_API_KEY"))
    print(os.getenv("OPENAI_API_BASE"))
    print(llm_config['api_key'])
    print(llm_config['base_url'])
    print(llm_config['model'])

    # llm_config = {
    #     'model': "glm-4",
    #     "api_key": os.getenv("ZHIPU_API_KEY"),
    #     "base_url": os.getenv("ZHIPU_API_BASE"),
    # }
    # print(os.getenv("ZHIPU_API_KEY"))
    # print(os.getenv("ZHIPU_API_BASE"))
    # print(llm_config['api_key'])
    # print(llm_config['base_url'])
    # print(llm_config['model'])

    llm_config_music = {
        'model': "chirp-v2-xxl-alpha",
        "api_key": os.getenv("OPENAI_API_KEY"),
        "base_url": os.getenv("OPENAI_API_BASE"),
    }

    split_agent = autogen.ConversableAgent(
        name="split_agent",
        llm_config=llm_config,
        system_message=SPLIT_PROMPT,
    )

    # 对故事内容进行段落切分，切分成6-20段。
    reply_split_agent = split_agent.generate_reply(messages=[{"content": content, "role": "user"}])
    print(reply_split_agent)

    # 从生成的内容中提取处字典格式包裹的故事分段
    parse_result = parse_json_from_response(reply_split_agent)[0]

    # 将生成的sentence切割成字幕存入不同的txt中
    create_text_files(parse_result, save_folder)

    picture_prompt_agent = autogen.ConversableAgent(

        name="picture_prompt_agent",
        llm_config=llm_config,
        system_message=PICTURE_PROMPT,
    )

    # 生成每个段落的图片prompt
    reply_picture_prompt_agent = picture_prompt_agent.generate_reply(
        messages=[{"content": reply_split_agent, "role": "user"}])
    print(reply_picture_prompt_agent)

    # 从生成的内容中提取处字典格式包裹的图片prompt
    parse_result = parse_json_from_response(reply_picture_prompt_agent)[0]
    # 将生成的图片prompt存入不同的txt中
    create_picture_prompt_text_files(parse_result, save_folder)

    # 遍历目录中的所有文件生成图片
    generate_images(save_folder)

    # 创建 MyTTS 类的实例
    synthesizer = MyTTS(url=URL, token=TOKEN, appkey=APPKEY)

    # 遍历目录中的所有文件
    for filename in os.listdir(save_folder):
        # 检查文件名是否符合要求：以数字开头并包含"subtitle"
        if "_subtitle_" in filename and filename.endswith('.txt'):
            # 构建完整的文件路径
            filepath = os.path.join(save_folder, filename)

            # 读取文本文件
            with open(filepath, 'r', encoding='utf-8') as file:
                lines = file.readlines()

            # 针对每行文本生成语音文件
            for i, line in enumerate(lines):
                # 跳过空行
                if not line.strip():
                    continue

                # 构建输出文件名
                mp3_filename = f"{filename[:-4]}.mp3"
                output_path = os.path.join(save_folder, mp3_filename)

                # 使用指定参数进行语音合成
                synthesizer.run(
                    text=line.strip(),
                    file=output_path,
                    voice="zhiyuan",
                    speech_rate=-500,
                    pitch_rate=0,
                    volume=100,
                    sample_rate=16000
                )

    # 根据传入的title进行语音合成
    synthesizer.run(
        text=title,
        file=f"./{save_folder}/title.mp3",
        voice="zhiyuan",
        speech_rate=-500,
        pitch_rate=0,
        volume=100,
        sample_rate=16000
    )

    # 把title写入title.txt中
    # 指定文件路径
    file_path = os.path.join(f"./{save_folder}", "title.txt")
    # 使用 'w' 模式打开文件，这将创建新文件或覆盖现有文件
    with open(file_path, "w", encoding="utf-8") as file:
        # 写入标题
        file.write(title)

    # 利用图片，配音，title以及bling.mp3生成开头的视频
    create_video_for_title(save_folder)

    # 生成main_video.mp4
    create_video_from_images_audio(save_folder)

    # 合并视频
    video1_path = f"./{save_folder}/title_video.mp4"
    video2_path = f"./{save_folder}/main_video.mp4"
    output_path = f"./{save_folder}/merged_video.mp4"
    merge_videos(video1_path, video2_path, output_path)


if __name__ == '__main__':
    content = """
    从前，在一个阳光明媚的日子里，森林里的动物们聚集在一起，准备观看一场特别的比赛——龟兔赛跑。兔子因为跑得快而在动物中颇有名气，而乌龟则是出了名的慢吞吞。
    比赛一开始，兔子就像离弦的箭一样冲了出去，而乌龟则是一步一步慢慢地爬行。跑到半路，兔子回头一看，见乌龟远远落在后面，心想：“就算我睡一觉，乌龟也不可能追上来。”于是，兔子找了个舒服的地方躺下来打起了盹儿。
    乌龟虽然缓慢，但却一刻不停地向前爬。当兔子醒来时，发现乌龟已经快到终点了，它赶紧追赶，但最终还是乌龟赢得了比赛。
    这个故事告诉我们，骄傲使人失败，坚持不懈才是成功的秘诀。无论何时，我们都不能轻视对手，更不能因一时领先而放松警惕
    """
    title = "《龟兔赛跑》"
    save_folder = "day1"
    main(title=title, content=content, save_folder=save_folder)
