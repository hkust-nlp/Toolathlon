# Part 1: Account Registration
see `global_preparation/how2register_accounts.md`

# Part 2: Install the Envs
run 
```bash
bash global_preparation/install_env.sh true # if you have sudo
```
or
```bash
bash global_preparation/install_env.sh false # if you do not have sudo
```

# Part 3: Misc Configuration
run
```bash
bash global_preparation/misc_configuartion.sh
```

# Part 4: Launch the Containers
run
```bash
bash global_preparation/deploy_containers.sh true # if you need to configure Dovecot to allow plaintext auth in poste
```
or
```bash
bash global_preparation/deploy_containers.sh false # if you need to configure Dovecot to allow plaintext auth in poste
```

# Part 5: Run any Task You Want
TODO: complete this

run
```bash
bash scripts/temp_and_debug/debug_manual.sh
```

# Part 6: Run in Parallel
TODO: complete this

run
```bash
bash scripts/run_parallel_sequential.sh
```