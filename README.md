
## 项目简介
***
* 该项目可以根据用户提供的内容和题目，自动生成简单的视频，视频效果可在demo文件夹中查看merged_video.mp4，或者[网页视频展示](https://gxlbvdk4ilp.feishu.cn/wiki/UV25wQNAViZn1wkiTWGcMjiNnxd#L2m2dvdFVoAYfkxaWOXcIGlJnec)。

## 配置内容

* 需要在.env文件配置阿里云智能语音交互平台的相关参数：[阿里云语音交互平台](https://nls-portal.console.aliyun.com/applist)
```python
# 设置阿里云智能语音交互相关参数
# 定义 WebSocket 服务器的 URL 地址
ALI_AUDIO_URL = "wss://nls-gateway.cn-shanghai.aliyuncs.com/ws/v1"
# 设置访问令牌（Token）
ALI_AUDIO_TOKEN = "******"
# 设置 AppKey
ALI_AUDIO_APPKEY = "******"
```

* 需要在.env文件中配置能够使用dalle-3作图和对话模型的api：
```python
# 设置 OpenAI url 和 key
OPENAI_API_KEY="sk-******"
OPENAI_API_BASE="https://api.openai.com/v1"
```

## 修改内容及运行
* 根据自己的需求修改create_video.py文件中的内容、题目、存储位置等信息，修改完成后直接运行该文件，待程序运行结束后，在save_folder文件夹中生成的 merged_video.mp4 即为最终合成的视频文件：
```python
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
```