# tiktok-restream-server

cd /mnt/c/workspace/TikTok-rnd/Tiktok-restream-server
conda activate tiktockenv
pip install -r requirements.txt

pyinstaller --name tiktok-restream-server --onedir --add-data "config.yaml;." main.py
