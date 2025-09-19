因为 canvas的api无法完成上传file到canva 存储系统，所以使用playwright来操作。
其中在老工作区的excel中表示film课程的 2，4，6次assignment没完成。但是assign2 是有请假条的所以不用完成。
prompt 中明确表示，其他没有提交的作业不用她管，所以在check_local中，如果发现1，2，3，5的assignment有提交的内容，则直接判为失败。

根据junlong的要求，把工作区搞得复杂一些，增加很多无关的干扰文件，让agent自己搜索作业位置。 作业文件的名字也去掉assign—id ，只用主题来命名，agent需要根据assign的description来确定哪个才是真正的作业文件。   正确的作业文件在 /ssddata/xiaochen/workspace/mcpbench_dev/tasks/xiaochen/canvas_collect_work_data/initial_workspace/homeworks/temp 目录下。
 此外还有一个考察点放置了其他人的作业（id不一样，文件内容也包含名字），在/ssddata/xiaochen/workspace/mcpbench_dev/tasks/xiaochen/canvas_collect_work_data/initial_workspace/homeworks/films 路径下，看agent是否会混淆。

还有请假条，需要agent自行找到并发送给excel中提供的助教邮箱

9.19
initial_workspace 中把原有的多个文件压缩成包了，但是要注意git可能对此无法监控更改。