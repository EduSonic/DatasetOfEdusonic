import os
import json
import re
import pandas as pd
from openai import OpenAI
from multiprocessing import Process, Queue, current_process
from tqdm import tqdm  # 新增进度条
from config import API_KEY
import csv

# ———— 配置 ————

# —————————————————

def init_client():
    return OpenAI(api_key=API_KEY, base_url="https://api.deepseek.com")

def extract_turns_from_text(text: str, client) -> list[dict]:
    """
    调用 DeepSeek，从一段小说文本中抽取 [{local_id, role, text}, …]
    local_id 为该滑窗内部自增编号，从 1 开始。
    为提高鲁棒性，要求模型用 ```json ...``` 包裹输出，并严格输出合法 JSON。
    """
    prompt = (
        "你是一个剧本抽取器。\n"
        "请从下面这段小说中提取所有与“角色”相关的文本片段，\n"
        "可能是对白，也可能是场景/背景说明（旁白）。\n"
        "在旁白中，请注意环境和人物的描写，不要省略，也不要忽略对情景有推动作用的文字\n"
        "请只输出合法 JSON 列表，并用 ```json ...``` 包裹，格式如下：\n"
        "```json\n"
        "[\n"
        "  {\"id\": 1, \"role\": \"角色名\", \"text\": \"原文内容1\"},\n"
        "  {\"id\": 2, \"role\": \"旁白\", \"text\": \"背景介绍\"}\n"
        "]\n"
        "``` \n"
        "不要输出任何其他内容。\n\n"
        f"小说内容：\n{text}"
    )
    resp = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": "你是一个剧本抽取器。"},
            {"role": "user",   "content": prompt},
        ],
        stream=False
    )
    raw = resp.choices[0].message.content
    # 提取 ```json ... ``` 中的 JSON 部分
    m = re.search(r"```json\s*(\[[\s\S]*?\])\s*```", raw)
    json_str = m.group(1) if m else raw.strip()
    return json.loads(json_str)

def worker(input_queue: Queue, result_queue: Queue):
    client = init_client()
    while True:
        item = input_queue.get()
        if item is None:
            break
        window_idx, window_text = item
        print(f"[{current_process().name}] 处理滑窗 #{window_idx}")

        try:
            turns = extract_turns_from_text(window_text, client)
            for t in turns:
                t["window_idx"] = window_idx
            result_queue.put(turns)
        except Exception as e:
            print(f"[{current_process().name}] 错误 in window {window_idx}: {e}")
            result_queue.put([])

def rewrite_global(all_turns: list[dict]) -> list[dict]:
    # 1. 按 window_idx & local id 排序
    sorted_turns = sorted(all_turns, key=lambda t: (t["window_idx"], t["id"]))
    # 2. 全局去重
    seen = set(); unique = []
    for t in sorted_turns:
        txt = t["text"].strip()
        if txt not in seen:
            seen.add(txt)
            unique.append({"role": t["role"], "text": txt, "window_idx": t["window_idx"]})
    # 3. 重新编号
    for idx, t in enumerate(unique, start=1):
        t["id"] = idx
    return unique

def main_multiprocess_rr():
    # 1. 读取并排序前 NUM_WORKERS 个文件
    def num_key(fname):
        m = re.match(r"^(\d+)", fname)
        return int(m.group(1)) if m else float("inf")

    files = sorted(
        [f for f in os.listdir(INPUT_file) if f.lower().endswith(".txt")],
        key=num_key
    )[:FILE_NUMBERS]

    # 2. 合并所有行到内存
    all_lines = []
    for fname in files:
        with open(os.path.join(INPUT_file, fname), encoding="utf-8") as fr:
            all_lines.extend(fr.readlines())
    # print(all_lines)
    # 3. 构造滑窗：每次前进 WINDOW_SIZE*(1-OVERLAP_RATE) 行
    stride = int(WINDOW_SIZE * (1 - OVERLAP_RATE))
    if stride < 1: stride = 1
    tasks = []
    for start in range(0, len(all_lines), stride):
        window_lines = all_lines[start: start + WINDOW_SIZE]
        if not window_lines:
            break
        window_text = "".join(window_lines)
        window_idx  = start // stride + 1
        tasks.append((window_idx, window_text))

    # 4. 启动子进程 & 分发任务
    input_queues = [Queue() for _ in range(NUM_WORKERS)]
    result_queue = Queue()
    workers = [
        Process(target=worker, args=(input_queues[i], result_queue), name=f"Worker-{i+1}")
        for i in range(NUM_WORKERS)
    ]
    for p in workers: p.start()

    import itertools
    rr = itertools.cycle(range(NUM_WORKERS))
    # 分发进度条
    for task in tqdm(tasks, desc="Dispatching windows"):
        input_queues[next(rr)].put(task)
    for q in input_queues:
        q.put(None)

    # 5. 收集结果进度条
    all_turns = []
    for _ in tqdm(range(len(tasks)), desc="Collecting window results"):
        all_turns.extend(result_queue.get())
    for p in workers:
        p.join()

    # 6. Rewriter：全局去重＋重新编号
    final_turns = rewrite_global(all_turns)

    # 7. 保存 CSV
    df = pd.DataFrame(final_turns)[["id", "role", "text", "window_idx"]]
    df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")
    print(f"\n✅ 完成，结果已保存到 {OUTPUT_CSV}")

def convert_bg(input_path, output_path):
    # 获取已处理的 ID 列表（如果输出文件存在）
    client = OpenAI(api_key=API_KEY, base_url="https://api.deepseek.com")
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
            writer.writerow(['id', 'role', 'text', 'window_idx', 'dialogue'])


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
        text = str(row["text"])

        # 获取前三句背景
        context_texts = data.iloc[max(0, idx - 3):idx]["text"].astype(str).tolist()
        background = "\n".join(context_texts)

        # 构造prompt
        if role == "旁白":
            prompt = f"""你是剧本的旁白，请结合以下背景信息，以旁白的语气和神态描述当前内容：
                        背景信息：{background} \n;\n 
                        -----------------------------------------------------
                        当前内容（待转化文本）：{text}"""
        else:
            prompt = f"""你是角色“{role}”，请结合以下背景信息，以符合角色语气的方式表达：
                        背景信息：{background} ;
                        ------------------------------------------------------------------------
                        当前内容为（待转化文本）：{text}"""

        # 调用 DeepSeek API
        try:
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": "你是一个剧本创作助手，擅长将结构化的角色描述转化为自然对话文本。"},
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

def for_decoder(input_path, output_path):
    """
    读取 input_path 中的 CSV 文件，转换为适合 DeepSeek 解码器的格式，并保存到 output_path。
    """
    client = OpenAI(api_key=API_KEY, base_url="https://api.deepseek.com")
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
            writer.writerow(['id', 'role', 'text', 'window_idx','dialogue', 'speaking_style'])

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
        text = str(row["dialogue"])

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

if __name__ == "__main__":
    BASE_URL    = "https://api.deepseek.com/v1"
    INPUT_DIR   = "../A_get_novel/textbook/textbook/"
    OUTPUT_DIR  = "mid_output/"
    OUTPUT_script = "output/"
    OUTPUT_decoder = "output_decoder/"
    FILE_NUMBERS = 10 # 读取的章节数
    NUM_WORKERS = 5 # 同时的处理数
    WINDOW_SIZE = 40   # 每个滑窗的行数
    OVERLAP_RATE = 2/3  # 每个窗口与上一个窗口重叠2/3
    #遍历INPUT_DIR中的文件夹
    for folder in os.listdir(INPUT_DIR):
        if os.path.isdir(os.path.join(INPUT_DIR, folder)):
            INPUT_file = os.path.join(INPUT_DIR, folder)
            OUTPUT_CSV = os.path.join(OUTPUT_DIR, f"1_提取后结果_{folder}.csv")
            print(f"正在处理文件夹：{folder}")

            try:
                main_multiprocess_rr()
            except Exception as e:
                print(f"处理文件夹 {folder} 时出错：{str(e)}")
                continue
            # 重置INPUT_DIR和OUTPUT_CSV
            print(f"文件夹 {folder} 处理完成，结果已保存到 {OUTPUT_CSV}")


            output_path = os.path.join(OUTPUT_script, f"2_script_{folder}.csv")
            try:
                convert_bg(OUTPUT_CSV, output_path)
            except Exception as e:
                print(f"脚本转换失败：{str(e)}")
                continue
            print(f"脚本转换完成，保存到：{output_path}")


            output_path_deocoder = os.path.join(OUTPUT_decoder, f"3_decoder_{folder}.csv")
            try:
                for_decoder(output_path, output_path_deocoder)
            except Exception as e:
                print(f"解码器转换失败：{str(e)}")
                continue
            print(f"解码器转换完成，保存到：{output_path_deocoder}")




