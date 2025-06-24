
import csv
import json
import pathlib
import random
import os 


SYSTEM_MESSAGES = [
 "你是一个专业的AI助手，任务是将小说文本转换为结构化的JSON数据。小说内容中包含了旁白描写和人物对话。你需要认真分析这些内容，从中识别出场景的视觉描述、人物的状态以及所有出现的对话。\n请将这些信息整理为如下格式的JSON：\n```json\n{\n  \"scene_description\": {\n    \"description\": \"string\" // 对场景环境、风格、氛围、人物姿态、重要动作等信息的综合描述，建议尽可能细致，可加入视觉风格提示。\n  },\n  \"dialogues\": [\n    {\n      \"sentence\": \"string\", // 人物说话的原句，去掉句尾的终结标点。\n      \"speaking_style\": \"string\" // 具体描写说话人的身份、性格、声音特征，以及此话的语气、情绪、肢体动作等。\n    }\n  ]\n```\n只输出合法的JSON，不要附加其他说明文字。所有信息需结合原文内容与合理推断得到。",
"你是一个负责文本结构化分析的AI助手。当前任务是从包含描述和对话的小说文本中提取关键信息，生成标准JSON。JSON应包含场景整体描述（包括风格与视觉细节），以及每句对话和其说话者特征。\n请确保JSON结构如下所示：\n```json\n{\n  \"scene_description\": {\n    \"description\": \"string\" // 包含环境、气氛、风格、关键物体、人物状态等综合描述。\n  },\n  \"dialogues\": [\n    {\n      \"sentence\": \"string\", // 去除末尾句号、问号等终止符号的对话原文。\n      \"speaking_style\": \"string\" // 细致描绘说话者的身份、性格、声音和说话时的语气、动作等。\n    }\n  ]\n```\n输出必须为纯JSON，不得包含解释或提示性文字。内容应尽可能从文本中还原或合理推断。",
"你是一个文本解析专家AI，负责将文学文本转换为结构化的视觉剧本信息。请从输入的小说段落中抽取场景细节和所有人物对话，将其整理为标准JSON格式：\n```json\n{\n  \"scene_description\": {\n    \"description\": \"string\" // 描述小说中呈现的场景氛围、视觉风格、角色行为、环境特征等。\n  },\n  \"dialogues\": [\n    {\n      \"sentence\": \"string\", // 原始对话文本，去掉句末的终止标点。\n      \"speaking_style\": \"string\" // 说话人的身份、性格、声音特征和说话时的情感、语调、动作等细节。\n    }\n  ]\n```\n请确保输出仅为上述JSON，不允许包含任何其他文字或解释。\n所有信息必须来源于输入文本，或基于文本内容合理推断。",
"你是一个用于辅助剧本创作的AI助手，专职从小说中提取视觉与对话信息。请根据输入小说段落，生成以下结构的JSON数据：\n```json\n{\n  \"scene_description\": {\n    \"description\": \"string\" // 对场景的整体描写，包括时间、地点、氛围、人物状态等，也可以建议视觉风格。\n  },\n  \"dialogues\": [\n    {\n      \"sentence\": \"string\", // 人物发言的文本，移除句末终结符。\n      \"speaking_style\": \"string\" // 说话者的背景、性格、语气、动作等综合描述，应尽量具体生动。\n    }\n  ]\n```\n输出内容必须是严格有效的JSON格式，不允许有附加说明文字。所有数据应基于原文或逻辑推断。",

]
# CSV 文件编码
CSV_ENCODING = 'gbk'
# JSON 文件编码
JSON_ENCODING = 'utf-8'


def convert_csv_row_to_sft_sample(text_content: str, speaking_style_content: str, system_messages: list) -> dict:
    """
    根据text和speaking_style内容，以及系统消息列表，创建一个Llama-Factory SFT的对话样本。

    Args:
        text_content: CSV行中的text内容。
        speaking_style_content: CSV行中的speaking_style内容。
        system_messages: 可选的系统消息列表，将从中随机选择一个。

    Returns:
        一个字典，表示一个SFT训练样本，格式为 {"conversation": [...]}.
        如果text或speaking_style内容为空，则返回 None。
    """
    if not text_content or not speaking_style_content:
        # 如果text或speaking_style内容为空，则不生成训练样本
        return None

    conversation_turns = []

    # 从系统消息列表中随机选择一个系统消息
    selected_system_message = random.choice(system_messages).strip('\n')
    conversation_turns.append({"from": "system", "value": selected_system_message})

    # text 内容作为 human 输入
    conversation_turns.append({"from": "human", "value": text_content})

    # speaking_style 内容作为 assistant 输出
    conversation_turns.append({"from": "assistant", "value": speaking_style_content})

    return {"conversations": conversation_turns}

def process_single_csv_file(csv_input_path: pathlib.Path, json_output_path: pathlib.Path, system_messages: list, csv_encoding: str, json_encoding: str) -> bool:
    """
    处理单个CSV文件，将其转换为Llama-Factory SFT JSON格式。

    Args:
        csv_input_path: 输入的CSV文件路径 (pathlib.Path对象)。
        json_output_path: 输出的JSON文件路径 (pathlib.Path对象)。
        system_messages: 用于随机选择系统消息的列表。
        csv_encoding: CSV文件的编码。
        json_encoding: JSON文件的编码。

    Returns:
        处理成功返回 True，失败返回 False。
    """
    sft_data = []
    required_columns = ['text', 'speaking_style']

    print(f"  Processing: {csv_input_path.name}")

    try:
        with open(csv_input_path, mode='r', encoding=csv_encoding) as infile:
            reader = csv.DictReader(infile)

            # 检查必需的列
            if not all(col in reader.fieldnames for col in required_columns):
                print(f"    ❌ Error: Missing required columns in '{csv_input_path.name}'. Needs: {required_columns}")
                return False # 处理失败

            # 逐行处理 CSV 数据
            for i, row in enumerate(reader):
                text_content = row.get('text', '').strip()
                speaking_style_content = row.get('speaking_style', '').strip()

                sft_sample = convert_csv_row_to_sft_sample(text_content, speaking_style_content, system_messages)

                if sft_sample:
                    sft_data.append(sft_sample)
                else:
                    print(f"  Warning: Skipping row {i+2} in '{csv_input_path.name}' due to empty text or speaking_style.") # 行号+2是因为header和0-based index

            if sft_data:
                with open(json_output_path, mode='w', encoding=json_encoding) as outfile:
                    json.dump(sft_data, outfile, ensure_ascii=False, indent=2)
                print(f"  Successfully generated {len(sft_data)} records in '{json_output_path.name}'.")
                return True # 处理成功
            else:
                print(f" Warning: No valid training records generated from '{csv_input_path.name}'. No JSON file created.")
                return True # technically processed without error, just no data

    except FileNotFoundError:
        print(f"Error: Input CSV file not found: '{csv_input_path}'")
        return False 
    except Exception as e:
        print(f" Error processing file '{csv_input_path.name}': {e}")
        return False 


if __name__ == "__main__":

    input_directory = pathlib.Path('') 
    output_directory = pathlib.Path('') 

    print(f"--- Starting Batch CSV to SFT JSON Conversion ---")
    print(f"Input Directory: {input_directory}")
    print(f"Output Directory: {output_directory}")

    if not input_directory.is_dir():
        print(f"❌ Error: Input path is not a valid directory: '{input_directory}'")
        exit()

    try:
        output_directory.mkdir(parents=True, exist_ok=True)
        print(f"Ensured output directory exists.")
    except Exception as e:
        print(f"❌ Error creating output directory '{output_directory}': {e}")
        exit()

    total_csv_files = 0
    successful_conversions = 0
    failed_conversions = 0

    for item in input_directory.iterdir():
        if item.is_file() and item.suffix.lower() == '.csv':
            total_csv_files += 1
           
            json_output_filename = item.with_suffix('.json').name
            json_output_path = output_directory / json_output_filename

            # 调用函数处理单个文件
            success = process_single_csv_file(
                item,
                json_output_path,
                SYSTEM_MESSAGES,
                CSV_ENCODING,
                JSON_ENCODING
            )

            if success:
                successful_conversions += 1
            else:
                failed_conversions += 1

        elif item.is_dir():
            print(f"  ⏭️ Skipping directory: '{item.name}'")
        else:
            print(f"  ⏭️ Skipping non-CSV file: '{item.name}' (suffix: {item.suffix})")

    print(f"--- Batch Conversion Finished ---")
    print(f"Total .csv files found: {total_csv_files}")
    print(f"Successfully converted: {successful_conversions}")
    print(f"Failed conversions: {failed_conversions}")
    print(f"Output JSON files saved to: {output_directory}")