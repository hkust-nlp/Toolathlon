# Annoy: This should be a paper Title

<p align="left">
    📑 <a href="https://huggingface.co/papers/xxxx.xxxxx" target="_blank">Paper</a> &nbsp&nbsp | &nbsp&nbsp 🌐 <a href="https://specx.github.io/" target="_blank">Project Page</a> &nbsp&nbsp | &nbsp&nbsp 💾 <a href="https://huggingface.co/collections/{hf_namespace}/specx-67a978e28fd926b56a4f55a2" target="_blank">Released Resources</a> &nbsp&nbsp | &nbsp&nbsp 📦 <a href="https://github.com/{github_namespace}/Annoy" target="_blank">Repo</a> 

This is the resource page of the our resources collection on Huggingface, we highlight your currect position with a blue block.

**Dataset**
<table>
      <tr>
        <th>Dataset</th>
        <th>Link</th>
    </tr>
      <tr>
        <td>Annoy-PythonEdu-Rs</td>
        <td style="background-color: #e6f3ff; text-align: center; vertical-align: middle;">
          <a href="https://huggingface.co/datasets/{hf_namespace}/Annoy-PyEdu-Rs">🤗</a>
        </td>
    </tr>
</table>
Please also check the raw data after our processing if you are interested: [{hf_namespace}/Annoy-PyEdu-Rs-Raw](https://huggingface.co/datasets/{hf_namespace}/Annoy-PyEdu-Rs-Raw).

**Models**
<table>
    <tr>
        <th rowspan="2">Base Model / Training</th>
        <th colspan="2">Annoy</th>
        <th colspan="2">Annoy++</th>
    </tr>
    <tr>
        <th>Stage 1</th>
        <th>Stage 2</th>
        <th>Stage 1</th>
        <th>Stage 2</th>
    </tr>
    <tr>
        <td>Qwen 2.5 7B Coder</td>
        <td style="text-align: center; vertical-align: middle;"><a href="https://huggingface.co/{hf_namespace}/qwen2.5-7b-coder_spec_stage1">🤗</a></td>
        <td style="text-align: center; vertical-align: middle;"><a href="https://huggingface.co/{hf_namespace}/qwen2.5-7b-coder_spec">🤗</a></td>
        <td style="text-align: center; vertical-align: middle;"><a href="https://huggingface.co/{hf_namespace}/qwen2.5-7b-coder_spec_pp_stage1">🤗</a></td>
        <td style="text-align: center; vertical-align: middle;"><a href="https://huggingface.co/{hf_namespace}/qwen2.5-7b-coder_spec_pp">🤗</a></td>
    </tr>
    <tr>
        <td>LLaMA 3.1 8B</td>
        <td style="text-align: center; vertical-align: middle;"><a href="https://huggingface.co/{hf_namespace}/llama3.1-8b_spec_stage1">🤗</a></td>
        <td style="text-align: center; vertical-align: middle;"><a href="https://huggingface.co/{hf_namespace}/llama3.1-8b_spec">🤗</a></td>
        <td style="text-align: center; vertical-align: middle;"><a href="https://huggingface.co/{hf_namespace}/llama3.1-8b_spec_pp_stage1">🤗</a></td>
        <td style="text-align: center; vertical-align: middle;"><a href="https://huggingface.co/{hf_namespace}/llama3.1-8b_spec_pp">🤗</a></td>
    </tr>
    <tr>
        <td>DeepSeek v2 Lite Coder</td>
        <td style="text-align: center; vertical-align: middle;"><a href="https://huggingface.co/{hf_namespace}/dsv2-lite-coder_spec_stage1">🤗</a></td>
        <td style="text-align: center; vertical-align: middle;"><a href="https://huggingface.co/{hf_namespace}/dsv2-lite-coder_spec">🤗</a></td>
        <td style="text-align: center; vertical-align: middle;"><a href="https://huggingface.co/{hf_namespace}/dsv2-lite-coder_spec_pp_stage1">🤗</a></td>
        <td style="text-align: center; vertical-align: middle;"><a href="https://huggingface.co/{hf_namespace}/dsv2-lite-coder_spec_pp">🤗</a></td>
    </tr>
</table>

**Introduction**

While having full executable code theoretically allows us to generate reliable execution trajectories as responses, two challenges arise: 1) Obtaining a deterministic reverse function for input prediction is impractical; 2) Automatically constructed trajectories are constrained by pre-designed templates and lack the expressiveness and generalizability of free-form natural language reasoning. Thus, we adopt a fully LLM-based approach for synthesizing all the desired responses using DeepSeek-V2.5, as it has top-tier performance but extremely low cost compared to other advanced LLMs.

*Due to our collaborators' compliance requirements, we only release the PythonEdu-Rs subset (this page) of full dataset.