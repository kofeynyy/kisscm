import zipfile
import base64
import os

def create_minimal_vfs():
    """Создает минимальный VFS с одним файлом"""
    with zipfile.ZipFile('minimal.vfs', 'w') as zf:
        zf.writestr('README.md', '# Minimal VFS\nThis is a minimal VFS with one file.')

def create_multifile_vfs():
    """Создает VFS с несколькими файлами"""
    with zipfile.ZipFile('multifile.vfs', 'w') as zf:
        zf.writestr('file1.txt', 'Content of file 1')
        zf.writestr('file2.txt', 'Content of file 2')
        zf.writestr('file3.txt', 'Content of file 3')
        zf.writestr('docs/readme.md', '# Documentation\nMultiple files VFS')
        zf.writestr('docs/help.txt', 'Help information')

def create_deep_vfs():
    """Создает VFS с глубокой структурой папок"""
    with zipfile.ZipFile('deep.vfs', 'w') as zf:
        # Уровень 1
        zf.writestr('root_file.txt', 'Root level file')
        
        # Уровень 2
        zf.writestr('folder1/file1.txt', 'File in folder1')
        zf.writestr('folder2/file2.txt', 'File in folder2')
        
        # Уровень 3
        zf.writestr('folder1/subfolder1/subfile1.txt', 'Deep file 1')
        zf.writestr('folder1/subfolder2/subfile2.txt', 'Deep file 2')
        zf.writestr('folder2/subfolder1/subfile3.txt', 'Deep file 3')
        
        # Уровень 4
        zf.writestr('folder1/subfolder1/deep/deep_file.txt', 'Very deep file')
        
        # Конфигурационные файлы
        zf.writestr('config/app.conf', 'app_config=value1')
        zf.writestr('config/db.conf', 'db_host=localhost')
        zf.writestr('config/logs/log.conf', 'log_level=debug')

def convert_to_base64(zip_filename, base64_filename):
    """Конвертирует ZIP файл в base64"""
    with open(zip_filename, 'rb') as f:
        zip_data = f.read()
    
    base64_data = base64.b64encode(zip_data).decode('utf-8')
    
    with open(base64_filename, 'w') as f:
        f.write(base64_data)

if __name__ == "__main__":
    # Создаем тестовые VFS
    create_minimal_vfs()
    create_multifile_vfs() 
    create_deep_vfs()
    
    # Конвертируем в base64
    convert_to_base64('minimal.vfs', 'minimal.vfs.base64')
    convert_to_base64('multifile.vfs', 'multifile.vfs.base64')
    convert_to_base64('deep.vfs', 'deep.vfs.base64')
    
    print("Test VFS files created:")
    print("- minimal.vfs / minimal.vfs.base64")
    print("- multifile.vfs / multifile.vfs.base64") 
    print("- deep.vfs / deep.vfs.base64")
