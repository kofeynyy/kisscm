import shlex

vfs_name = "docker$ "
exit_cmd = 'exit'
while True:
    command = input(vfs_name)
    parts = shlex.split(command)
    if parts == exit_cmd:
        break
    if not parts:
        continue
    if parts[0] == 'ls':
        print(parts)
    elif parts[0] == 'cd':
        print(parts)
    else:
        print(f'{command}: command not found')
