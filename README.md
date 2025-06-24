<h1 align="center">
  <img src="fig\logo.png" alt="Logo" width="400">
</h1>

❗ | **该项目为EduSonic的数据获取及预处理部分**
:---: | :---
⚠️ | 该项目仅供学习使用，请勿用于任何商业用途，若有侵权请联系删除。

# 项目简介

本项目旨在对小说文本进行多层次的自动化分析与处理，包括文本到剧本的转换、情感与动作识别、以及相关数据的生成与管理。项目采用模块化设计，便于扩展和维护，适用于自然语言处理、文本分析、剧本生成等相关研究与应用场景。

数据集总大小约107MB的文本语料，包括：1.文本剧本 2.对话剧本（生成声音）3.场景剧本（生成图片）4. 常识（防止微调时模型变傻）。不同类型的数据根据场景要求我们使用了不同数据形式（Alpaca/ShareGpt等）

<h1 align="center">
  <img src="fig\dataset.png" width="800">
</h1>

### 工作流


这项工作致力于实现一个从小说文本到多模态有声书内容的自动生成流程，整体流程主要分为三个阶段，分别为“脚本数据收集与过滤”、“模仿与微调”，以及“评论驱动的内容生成”。该项目主要为全流程的“脚本数据收集与过滤”的实现，具体内容如下：

<h1 align="center">
  <img src="fig\framework.png" width="800">
</h1>

在该阶段，首先从大量小说文本中提取原始数据，并借助通用大模型（如GPT-4o）进行结构化处理。为了提升文本结构的标准化程度，设计了特定的Interaction Template，包括任务说明（如“将输入小说文本整理成以下格式”）与格式要求（如分角色台词、情绪标注、叙述内容等），促使大模型根据输入小说自动生成符合预期结构的剧本格式。此过程还结合人工辅助与评价机制，引入“Critic 模块”对生成的脚本进行质量评分与筛选，确保最终存入数据库的台本具备可用性与一致性。

### 数据来源

我们通过网页爬虫与人工筛选相结合的方式，从互联网上采集了多种类型的中文文本资源作为语料基础（Metadata），包括外国小说（41.8%）、网络小说（28.5%）、童话故事（21.4%）以及课本内容（8.25%），以保证数据来源多样且结构均衡。
在此基础上，我们设计了多轮高质量Prompt，并结合人工规则进行文本拆分与结构化处理，将原始小说内容自动转化为三类特定格式的数据：全文转对话、对话转剧本、剧本转场景，为下游的监督微调（SFT）任务提供了高质量的训练样本。

<h1 align="center">
  <img src="fig\process.png" width="800">
</h1>

## 环境配置

为确保项目能够顺利运行，请按照以下步骤进行环境配置：
1. 克隆项目仓库
   ```bash
   git clone 
   cd yourproject
   ```

2. 创建虚拟环境
   ```bash
   conda create -n llm_director python=3.10
   conda activate llm_director
   ```

3. 安装依赖
   ```bash
   pip install -r requirements.txt
   ```    



## 目录结构

```
processing_pipeline/
├── utils/                    # 工具脚本（如动作生成、词语转换）
│   ├── generate_movement.py
│   └── transform_word.py
├── script_generate/          # 剧本生成模块及输出示例
│   ├── script_generate.py
│   └── *.docx
├── novel_analysis/           # 小说分析主模块
│   ├── main.py               # 主入口脚本
│   ├── config.py
│   ├── text_to_chat/         # 文本到对话转换
│   ├── script_for_decoder/   # 解码器输入格式转换
│   ├── mid_output/           # 中间输出（如csv结果）
│   ├── emotion_part/         # 情感识别
│   └── action_part/          # 动作识别
├── dataset_builder/          # json数据集构建模块
│   ├── get_type1data.py     
│   └── get_type2data.py
└── demo_data/                # 示例数据
    ├── type_one_data_demo.json
    ├── type_two_data_demo.json
    ├── type_three_data_demo.jsonl
    └── common_sense_demo.json
```
---


## 主要功能模块

> 1. utils 工具模块
- `generate_movement.py`：用于生成或处理文本中的动作信息。
- `transform_word.py`：实现词语的转换与处理。

> 2. script_generate 剧本生成
- `script_generate.py`：将分析后的文本自动生成剧本，支持.docx格式输出。
- 输出示例：多个.docx剧本文件。

> 3. novel_analysis 小说分析
- `main.py`：主入口，负责调度各子模块。
- `config.py`：配置api密钥。
- `text_to_chat/`：将小说文本转换为对话格式，便于后续处理。
- `script_for_decoder/`：将文本转换为适合解码器输入的格式。
- `mid_output/`：存放中间处理结果（如csv文件，包含不同小说的分析结果）。
- `emotion_part/`：情感识别模块，包含训练与评估脚本。
- `action_part/`：动作识别模块，包含训练、预测脚本及模型权重。

> 4. demo_data 示例数据
- `type_one_data_demo.json`：第一类数据示例。
- `type_two_data_demo.json`：第二类数据示例。
- `type_three_data_demo.jsonl`：第三类数据示例（每行为一个样本）。
- `common_sense_demo.json`：常识性数据示例。

---

## 快速开始

> **运行示例**
   - 在config.py中补全`API_KEY`。
     ```python
      API_KEY = '' # 替换为你自己的API密钥（Deepseek官网获取）
     ```
   - 进入`processing_pipeline/novel_analysis/`目录，运行主分析脚本：
     ```bash
     python main.py
     ```
   - 生成剧本：
     ```bash
     cd ../script_generate
     python script_generate.py
     ```
   - 数据集构建：
     ```bash
     cd ../dataset_builder
     python get_type1data.py
     python get_type2data.py
     ```
   这两个脚本用于将包含剧本大纲（text）和扩写结果（dialogue）的 CSV 文件，批量转换为符合 LLaMA-Factory 微调（SFT）要求的 JSON 格式数据。脚本通过随机注入系统提示（system prompt），模拟实际对话场景，构建出 system-human-assistant 三轮交互格式的训练样本。支持对多个 CSV 文件的自动遍历、字段校验与异常处理，便于大规模、高质量地准备指令微调数据集。在得到一类，二类数据后能够通过分类匹配合成三类数据，四类数据为常识
   

> **数据说明**
   - `demo_data/`文件夹下为各类数据的示例，可用于测试和功能演示。
   - 具体数据格式请参考对应的json/jsonl文件内容。

> **生成结果展示**
  
   本文以 《小红帽》和《九星霸体诀》前两章进行剧本的转换工作，因为笔者比较喜欢修仙类小说（doge），示例如下：
   [点击查看《九星霸体诀》剧本文档](processing_pipeline\script_generate\剧本输出_龙傲天版.docx)
   [点击查看《小红帽》剧本文档](processing_pipeline\script_generate\剧本输出_小红帽.docx)

---

> 完整原始数据下载：

[百度网盘链接](https://pan.baidu.com/s/10WwyOdOydzLLTbUl16T5rQ?pwd=fenv)



## 参考说明与鸣谢

本项目在构建中文剧本文本生成与微调数据集的过程中，参考和借鉴了以下资源与开源项目，在此一并致谢：

- 📄 论文：[FLAN Collection: Designing Better Instruction Datasets for Fine-tuning](https://arxiv.org/pdf/2204.05836)  
  本项目在构建 SFT 训练数据时借鉴了该论文中关于多样化系统提示语的设计思想，提升了模型对指令类型的泛化能力。

- 📁 GitHub：[instruction-finetune-datasets](https://github.com/A-baoYang/instruction-finetune-datasets?tab=readme-ov-file)  
  本项目参考了该仓库中多个任务格式（尤其是对话与摘要任务）的构建方法，受益良多，推荐给所有做 SFT 的开发者。

- 🎬 GitHub：[Novel-to-Script](https://github.com/ZhengDongHang/Novel-to-Script)  
  本项目的“对话转剧本”模块在设计 prompt 模板和处理格式时参考了该项目的剧本结构设定，非常感谢作者的公开资源。

- 📚 中文小说站：[笔趣阁](https://m.bqgl.cc/)  
  本项目中的部分原始小说文本数据来源于笔趣阁，仅用于科研用途，不做任何商业传播，如有侵权请联系删除 ~~其实是靠人工筛的，太肝了（x）~~

- 📦 GitHub：[nlp_chinese_corpus](https://github.com/brightmart/nlp_chinese_corpus?tab=readme-ov-file)  
  感谢该仓库提供的多种形式的中文文本数据，为本项目补充common sense对话，提供了常识语料的补充。

## TODO

- [ ] 提升场景分割准确性，实现更精准自动化分割
- [ ] 提供对应的视频生成数据
  
## License
本项目代码遵循 [MIT License](https://opensource.org/license/mit/)，数据集遵循 [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/) 协议。请在使用时遵守相关许可条款。
