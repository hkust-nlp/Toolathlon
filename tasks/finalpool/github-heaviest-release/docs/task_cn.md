分析 GitHub 仓库 https://github.com/atom/atom 。在它所有的**稳定版 release**（排除 pre-release 和 draft）中，找出附件（assets）总大小（字节数）最大的那个 release；再在该 release 内部找出单个体积最大的 asset。将结果保存为工作目录下名为 `heaviest_release.csv` 的 CSV 文件，只含一行数据，列如下：

- `heaviest_release_tag`：附件总大小最大的稳定版 release 的 tag 名
- `total_assets_size`：该 release 所有附件的总大小（字节，整数）
- `largest_asset_name`：该 release 中最大单个附件的文件名
- `largest_asset_size`：该附件的大小（字节，整数）
