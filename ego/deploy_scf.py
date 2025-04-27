from pathlib import Path
import shutil
import subprocess
import zipfile


PROJECT_DIR = Path(__file__).parent
PACKAGE_DIR = PROJECT_DIR / "package"
ZIP_FILE = "django_scf_deploy.zip"

shutil.rmtree(PACKAGE_DIR)
PACKAGE_DIR.mkdir(parents=True, exist_ok=True)

# 授权 scf_bootstrap
subprocess.run(['chmod', '777', 'scf_bootstrap'], check=True)

# 复制项目文件到 package 目录
exclude_dirs = ['venv', '.git', '__pycache__', '.idea', 'package', 'logs', 'wallpaper/scripts']
exclude_files = ['*.log', '*.sqlite3', 'zappa_settings.json', 'deploy_scf.py', 'deploy_aws.py']

for f in PROJECT_DIR.rglob("*"):
    if f.is_file():
        if any(dir in str(f.parent) for dir in exclude_dirs):
            continue
        if any(str(f).endswith(ext) for ext in exclude_files):
            continue

        src_path = f
        dest_path = PACKAGE_DIR / f.relative_to(PROJECT_DIR)
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        # shutil.copytree(src_path, dest_path)
        shutil.copy2(src_path, dest_path)

# exclude = [
#     "package", "logs", "deploy_scf.py", "deploy_aws.py",
#     "zappa_settings.json", "backup_data.json", "db.sqlite3", "__init__.py"
# ]

# for f in PROJECT_DIR.iterdir():
#     if f.name in exclude:
#         continue
#     src_path = f
#     dest_path = PACKAGE_DIR / f.name
#     if f.is_dir():
#         shutil.copytree(src_path, dest_path)
#     else:
#         shutil.copy2(src_path, dest_path)


# 安装依赖到 package 目录
subprocess.run([
    'pip', 'install',
    '-r', 'requirements.txt',
    '-t', './package'
], check=True)


# 压缩成zip包
def create_zip():
    with zipfile.ZipFile(PACKAGE_DIR / ZIP_FILE, 'w') as zipf:
        for file_path in PACKAGE_DIR.rglob("*"):
            if file_path.is_file():
                # 只保留相对路径
                zip_path = str(file_path.relative_to(PACKAGE_DIR.parent))
                zipf.write(file_path, zip_path)

    for f in PACKAGE_DIR.iterdir():
        if f.name == ZIP_FILE:
            continue

        if f.is_dir():
            shutil.rmtree(f)
        else:
            f.unlink()

# create_zip()