import pandas as pd
from openai import OpenAI
import os
import csv

# 配置 DeepSeek API
from config import API_KEY
client = OpenAI(api_key=API_KEY, base_url="https://api.deepseek.com")

# 路径配置
input_path = "../output/对话剧本_结构化数据_不含情绪动作.csv"
output_path = "../output_decoder/test_for_json.csv"
os.makedirs(os.path.dirname(output_path), exist_ok=True)

# 获取已处理的 ID 列表（如果输出文件存在）
processed_ids = set()
if os.path.isfile(output_path):
    with open(output_path, mode='r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            processed_ids.add(str(row["id"]))
else:
    # 写入表头
    with open(output_path, mode='w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow(['id', 'role', 'text', 'window_idx', 'emo_label', 'dialogue'])



# 读取数据
data = pd.read_csv(input_path)
print(data)
# 新建空列表用于写结果
results = []

# 遍历每一行，逐步处理
for idx, row in data.iterrows():
    row_id = str(row["id"])
    if row_id in processed_ids:
        print(f"⏭️ 跳过已处理的 ID: {row_id}")
        continue

    role = str(row["role"])
    text = str(row["emo_label"])
    # emo_label = str(row.get("emo_label", ""))
    # behaviour = str(row.get("behaviour", ""))

    # 获取前三句背景
    context_texts = data.iloc[max(0, idx - 3):idx]["text"].astype(str).tolist()
    background = "\n".join(context_texts)

    format = """
    {
    "scene_description": {},
    "dialogues": [
        {
        "sentence": "原文角色对白，",
        "speaking_style": "",
        },
        {
        "sentence": "原文角色对白2",
        "speaking_style": "",
        }
    ]
    }
    
    """

    # 构造prompt
    if role == "旁白":
        prompt = f"""你是一个场景描述器，现在需要将一段旁白生成相应的描述，要求如下：\n
                    1 在scene_description中，用一句话按照结构（“画风为xxx，整体为xxx风格” + “主体描述用完整句子描述包括（时间，地点，人物，并侧重描写画面细节，但不要使用比喻）” + “氛围”）描述一个符合内容的静态画面，人物动作表情尽量详细，描述画面内容即可；\n
                    2. 将内容分成多句对白，放入dialogues中，\n
                    3. 每句对白都需要包含speaking_style字段，用英文描述旁白的说话风格和语气，用一句话格式为（旁白（无性别、自然、音色）+此时场景下说这句话的情绪）；\n
                    请只输出合法 JSON 列表，并用 ```json ...``` 包裹，格式如下：\n
                    {format}\n
                    下面给出具体内容和背景信息，情节和背景信息为分析并处理待转化文本\n
                    背景信息：{background} \n;\n 
                    -----------------------------------------------------
                    当前内容（待转化文本）：{text}"""
    else:
        prompt = f"""你是一个场景描述器，现在需要带入角色{role}将一段对话总结相应的描述，要求如下：\n
                    1 在scene_description中，用一句话按照结构（“画风为xxx，整体为xxx风格” + “主体描述用完整句子描述包括（时间，地点，人物，并侧重描写画面细节，但不要使用比喻）” + “氛围”）描述一个符合内容的静态画面，人物动作表情尽量详细，描述画面内容即可；\n
                    2. 将内容分成多句对白，放入dialogues中\n
                    3. 每句对白都需要包含speaking_style字段，用英文描述角色的说话风格和语气，格式为（角色{role}人设（性别、年龄、音色、性格）+此时场景下说这句话的情绪）；\n
                    请只输出合法 JSON 列表，并用 ```json ...``` 包裹，格式如下：\n
                    {format}\n
                    下面给出具体内容和背景信息，情节和背景信息为分析并处理待转化文本\n
                    背景信息：{background} \n;\n 
                    -----------------------------------------------------
                    当前内容（待转化文本）：{text}"""

    # 调用 DeepSeek API
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": f"你是一个场景描述创作助手，擅长将结构化的角色描述转化为json格式的场景描述。"},
                {"role": "user", "content": prompt}
            ],
            stream=False,
            temperature=1.1,      # 人为空值随机性
            top_p=0.90,

        )
        dialogue = response.choices[0].message.content.strip().replace('\n', '\\n')

        print("当前角色为:", role, end='.')
        print("对话内容为:", dialogue)
        print("描述性文本为:", '(' + text + ')')
        print('*-'*30)
    except Exception as e:
        dialogue = f"(生成失败：{str(e)})"

    # 写入到文件
    with open(output_path, mode='a', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow(list(row) + [dialogue])


print(f"✅ 对话生成完成，保存到：{output_path}")
