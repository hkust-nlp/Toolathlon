from argparse import ArgumentParser
import os
import shutil

if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--agent_workspace", required=True)
    args = parser.parse_args()

    # 烹饪任务的预处理很简单，只需要确保原材料文件存在
    initial_ingredients_file = os.path.join(
        os.path.dirname(__file__), 
        "..", 
        "initial_workspace", 
        "ingredients.csv"
    )
    
    target_ingredients_file = os.path.join(args.agent_workspace, "ingredients.csv")
    
    # 复制原材料文件到工作区
    if os.path.exists(initial_ingredients_file):
        shutil.copy2(initial_ingredients_file, target_ingredients_file)
        print(f"已复制原材料文件到工作区: {target_ingredients_file}")
    else:
        print(f"警告: 未找到原材料文件: {initial_ingredients_file}")
    
    print("烹饪任务预处理完成！")