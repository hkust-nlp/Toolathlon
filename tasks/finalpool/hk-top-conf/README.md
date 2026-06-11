HOW TO DO

To complete this task, the model needs to find papercopilot and use the hover tool on multiple pages, such as https://papercopilot.com/paper-list/icml-paper-list/icml-2024-paper-list/, to obtain the publication information of the three universities.

SOME CONCERNS

Currently, the model is not good at using the hover tool, and it is almost impossible to accomplish this task by other means.

DATA SNAPSHOT NOTE

The original ground truth was computed against Paper Copilot data from around 2025-08. A later Paper Copilot data commit changed the reproducible counts:

- Repository: https://github.com/papercopilot/paperlists
- Commit: d4c51fa4698b270690a237f03c3fc2901a1f4959
- Commit time: 2025-08-30 20:52:59 -0700
- Commit message: update iclr25
- Affected file: iclr/iclr2025.json

This commit changes ICLR 2025 affiliation indexing for several papers with empty first-author affiliation fields. It does not reduce the total number of accepted ICLR 2025 papers, and the relevant ICML 2024 and NeurIPS 2024 files had no later changes for this task. Under the task's first-author-affiliation counting setup, the later data reduces the ICLR 2025 contribution by 6 papers for HKUST and 4 papers for CUHK, with HKU unchanged. The checked-in ground truth accounts for this later Paper Copilot data change.
