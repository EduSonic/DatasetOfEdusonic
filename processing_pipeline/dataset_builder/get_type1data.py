import csv
import json
import pathlib
import random
import os 


# 系统消息列表（全局配置）
SYSTEM_MESSAGES = [
    "你是一个剧本创作助手，擅长根据简短的剧本描述（text），将其扩展成更生动、更详细的对话或旁白（dialogue）。你的任务是接收text内容，并输出对应的dialogue内容。",
    "请你扮演一个剧本扩写者的角色。我将给你一段简略的文本（text），请你将其转化为一段丰富的剧本对话或旁白（dialogue）。",
    "作为一名训练有素的AI，你的目标是将输入的text内容，高质量地扩写为对应的dialogue内容。",
    "请将以下提供的剧本大纲（text），改写为更具有表现力的剧本细节（dialogue）。",
    "这是一对用于训练的数据对，text是输入，dialogue是期望的输出，请你学习从text生成dialogue的模式。",
    "你的任务是根据给定的text，生成风格匹配且内容详实的dialogue。",
    "请将这个text描述转换为一个包含角色情感、动作和场景细节的dialogue片段。",
    "请根据text提示，创作出对应的dialogue内容。",
]

# CSV 文件编码
CSV_ENCODING = 'gbk'
# JSON 文件编码
JSON_ENCODING = 'utf-8'


def convert_csv_row_to_sft_sample(text_content: str, dialogue_content: str, system_messages: list) -> dict:
    """
    根据text和dialogue内容，以及系统消息列表，创建一个Llama-Factory SFT的对话样本。

    Args:
        text_content: CSV行中的text内容。
        dialogue_content: CSV行中的dialogue内容。
        system_messages: 可选的系统消息列表，将从中随机选择一个。

    Returns:
        一个字典，表示一个SFT训练样本，格式为 {"conversation": [...]}.
        如果text或dialogue内容为空，则返回 None。
    """
    if not text_content or not dialogue_content:
        # 如果text或dialogue内容为空，则不生成训练样本
        return None

    conversation_turns = []

    # 从系统消息列表中随机选择一个系统消息
    selected_system_message = random.choice(system_messages)
    conversation_turns.append({"from": "system", "value": selected_system_message})

    # 将 text 内容作为 human 输入
    conversation_turns.append({"from": "human", "value": text_content})

    # 将 dialogue 内容作为 assistant 输出
    conversation_turns.append({"from": "assistant", "value": dialogue_content})

    return {"conversation": conversation_turns}

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
    required_columns = ['text', 'dialogue']

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
                dialogue_content = row.get('dialogue', '').strip()

                sft_sample = convert_csv_row_to_sft_sample(text_content, dialogue_content, system_messages)

                if sft_sample:
                    sft_data.append(sft_sample)
                else:
                    print(f"  Warning: Skipping row {i+2} in '{csv_input_path.name}' due to empty text or dialogue.") # 行号+2是因为header和0-based index

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
        return False # 处理失败
    except Exception as e:
        print(f" Error processing file '{csv_input_path.name}': {e}")
        return False # 处理失败


if __name__ == "__main__":

    input_directory = pathlib.Path("") 
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