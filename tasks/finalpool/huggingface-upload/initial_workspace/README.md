---
license: mit
library_name: transformers
---
# MyAwesomeModel
<!-- markdownlint-disable first-line-h1 -->
<!-- markdownlint-disable html -->
<!-- markdownlint-disable no-duplicate-header -->

<div align="center">
  <img src="figures/fig1.png" width="60%" alt="MyAwesomeModel" />
</div>
<hr>

<div align="center" style="line-height: 1;">
  <a href="LICENSE" style="margin: 2px;">
    <img alt="License" src="figures/fig2.png" style="display: inline-block; vertical-align: middle;"/>
  </a>
</div>

## 1. Introduction

The MyAwesomeModel has undergone a significant version upgrade. In the latest update, MyAwesomeModel has significantly improved its depth of reasoning and inference capabilities by leveraging increased computational resources and introducing algorithmic optimization mechanisms during post-training. The model has demonstrated outstanding performance across various benchmark evaluations, including mathematics, programming, and general logic. Its overall performance is now approaching that of other leading models.

<p align="center">
  <img width="80%" src="figures/fig3.png">
</p>

Compared to the previous version, the upgraded model shows significant improvements in handling complex reasoning tasks. For instance, in the AIME 2025 test, the model’s accuracy has increased from 70% in the previous version to 87.5% in the current version. This advancement stems from enhanced thinking depth during the reasoning process: in the AIME test set, the previous model used an average of 12K tokens per question, whereas the new version averages 23K tokens per question.

Beyond its improved reasoning capabilities, this version also offers a reduced hallucination rate and enhanced support for function calling.

## 2. Evaluation Results

### Comprehensive Benchmark Results

<div align="center">

| | Benchmark | Model1 | Model2 | Model1-v2 | MyAwesomeModel |
|---|---|---|---|---|---|
| **Core Reasoning Tasks** | Math Reasoning | 0.510 | 0.535 | 0.521 | {RESULT} |
| | Logical Reasoning | 0.789 | 0.801 | 0.810 | {RESULT} |
| | Common Sense | 0.716 | 0.702 | 0.725 | {RESULT} |
| **Language Understanding** | Reading Comprehension | 0.671 | 0.685 | 0.690 | {RESULT} |
| | Question Answering | 0.582 | 0.599 | 0.601 | {RESULT} |
| | Text Classification | 0.803 | 0.811 | 0.820 | {RESULT} |
| | Sentiment Analysis | 0.777 | 0.781 | 0.790 | {RESULT} |
| **Generation Tasks** | Code Generation | 0.615 | 0.631 | 0.640 | {RESULT} |
| | Creative Writing | 0.588 | 0.579 | 0.601 | {RESULT} |
| | Dialogue Generation | 0.621 | 0.635 | 0.639 | {RESULT} |
| | Summarization | 0.745 | 0.755 | 0.760 | {RESULT} |
| **Specialized Capabilities**| Translation | 0.782 | 0.799 | 0.801 | {RESULT} |
| | Knowledge Retrieval | 0.651 | 0.668 | 0.670 | {RESULT} |
| | Instruction Following | 0.733 | 0.749 | 0.751 | {RESULT} |
| | Safety Evaluation | 0.718 | 0.701 | 0.725 | {RESULT} |

</div>

### Overall Performance Summary
The MyAwesomeModel demonstrates strong performance across all evaluated benchmark categories, with particularly notable results in reasoning and generation tasks.

## 3. Chat Website & API Platform
We offer a chat interface and API for you to interact with MyAwesomeModel. Please check our official website for more details.

## 4. How to Run Locally

Please refer to our code repository for more information about running MyAwesomeModel locally.

Compared to previous versions, the usage recommendations for MyAwesomeModel have the following changes:

1. System prompt is supported.
2. It is not required to add special tokens at the beginning of the output to force the model into a specific thinking pattern.

The model architecture of MyAwesomeModel-Small is identical to its base model, but it shares the same tokenizer configuration as the main MyAwesomeModel. This model can be run in the same manner as its base model.

### System Prompt
We recommend using the following system prompt with a specific date.
```
You are MyAwesomeModel, a helpful AI assistant.
Today is {current date}.
```
For example,
```
You are MyAwesomeModel, a helpful AI assistant.
Today is May 28, 2025, Monday.
```
### Temperature
We recommend setting the temperature parameter $T_{model}$ to 0.6. 

### Prompts for File Uploading and Web Search
For file uploading, please follow the template to create prompts, where {file_name}, {file_content} and {question} are arguments.
```
file_template = \
"""[file name]: {file_name}
[file content begin]
{file_content}
[file content end]
{question}"""
```
For web search enhanced generation, we recommend the following prompt template where {search_results}, {cur_date}, and {question} are arguments.
```
search_answer_en_template = \
'''# The following contents are the search results related to the user's message:
{search_results}
In the search results I provide to you, each result is formatted as [webpage X begin]...[webpage X end], where X represents the numerical index of each article. Please cite the context at the end of the relevant sentence when appropriate. Use the citation format [citation:X] in the corresponding part of your answer. If a sentence is derived from multiple contexts, list all relevant citation numbers, such as [citation:3][citation:5]. Be sure not to cluster all citations at the end; instead, include them in the corresponding parts of the answer.
When responding, please keep the following points in mind:
- Today is {cur_date}.
- Not all content in the search results is closely related to the user's question. You need to evaluate and filter the search results based on the question.
- For listing-type questions (e.g., listing all flight information), try to limit the answer to 10 key points and inform the user that they can refer to the search sources for complete information. Prioritize providing the most complete and relevant items in the list. Avoid mentioning content not provided in the search results unless necessary.
- For creative tasks (e.g., writing an essay), ensure that references are cited within the body of the text, such as [citation:3][citation:5], rather than only at the end of the text. You need to interpret and summarize the user's requirements, choose an appropriate format, fully utilize the search results, extract key information, and generate an answer that is insightful, creative, and professional. Extend the length of your response as much as possible, addressing each point in detail and from multiple perspectives, ensuring the content is rich and thorough.
- If the response is lengthy, structure it well and summarize it in paragraphs. If a point-by-point format is needed, try to limit it to 5 points and merge related content.
- For objective Q&A, if the answer is very brief, you may add one or two related sentences to enrich the content.
- Choose an appropriate and visually appealing format for your response based on the user's requirements and the content of the answer, ensuring strong readability.
- Your answer should synthesize information from multiple relevant webpages and avoid repeatedly citing the same webpage.
- Unless the user requests otherwise, your response should be in the same language as the user's question.
# The user's message is:
{question}'''
```

## 5. License
This code repository is licensed under the [MIT License](LICENSE). The use of MyAwesomeModel models is also subject to the [MIT License](LICENSE). The model series supports commercial use and distillation.

## 6. Contact
If you have any questions, please raise an issue on our GitHub repository or contact us at contact@MyAwesomeModel.ai.
```
