from argparse import ArgumentParser

if __name__=="__main__":
    parser = ArgumentParser()
    parser.add_argument("--agent_workspace", required=True)
    parser.add_argument("--launch_time", nargs='*', required=False, help="Launch time (can contain spaces)")
    args = parser.parse_args()

    # do not need to give model the hf token anymore as I have all switch three datasets to publib under my own account
    pass

    
