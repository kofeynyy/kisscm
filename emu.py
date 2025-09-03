vfs_name = "docker$ "
exit_cmd = 'exit'

while True:
    command = input(vfs_name)
    if command == exit_cmd: break
    print(command)