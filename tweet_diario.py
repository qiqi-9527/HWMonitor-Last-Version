import tweepy
import os
import time
import random  # 添加导入 random 模块

# --------------------------
# 1. 从环境变量读取Twitter API密钥
# --------------------------
API_KEY = os.getenv('API_KEY')
API_SECRET_KEY = os.getenv('API_SECRET_KEY')
ACCESS_TOKEN = os.getenv('ACCESS_TOKEN')
ACCESS_TOKEN_SECRET = os.getenv('ACCESS_TOKEN_SECRET')
BEARER_TOKEN = os.getenv('BEARER_TOKEN')

# 验证密钥是否存在，缺失则直接终止
if not all([API_KEY, API_SECRET_KEY, ACCESS_TOKEN, ACCESS_TOKEN_SECRET, BEARER_TOKEN]):
    print("Error: 缺少Twitter API密钥，请检查环境变量配置")
    exit(1)

# --------------------------
# 2. 初始化Twitter API连接
# --------------------------
try:
    # V1 API：用于图片上传（tweepy.Client不支持媒体上传）
    auth = tweepy.OAuthHandler(API_KEY, API_SECRET_KEY)
    auth.set_access_token(ACCESS_TOKEN, ACCESS_TOKEN_SECRET)
    api_v1 = tweepy.API(
        auth,
        wait_on_rate_limit=True,
    )
    
    # V2 API：用于发布带媒体的推文
    api_v2 = tweepy.Client(
        bearer_token=BEARER_TOKEN,
        consumer_key=API_KEY,
        consumer_secret=API_SECRET_KEY,
        access_token=ACCESS_TOKEN,
        access_token_secret=ACCESS_TOKEN_SECRET
    )
    print("✅ Twitter API V1（图片上传）与V2（推文发布）连接初始化成功")
except tweepy.TweepyException as e:
    print(f"Error: Twitter API连接失败 - {str(e)}")
    exit(1)

# --------------------------
# 3. 工具函数：按顺序读取下一条文案
# --------------------------
def leer_siguiente_linea(archivo="tweets.txt", indice_file="last_index.txt"):
    """
    从 tweets.txt 中读取下一条有效文案（按行顺序）
    使用 last_index.txt 记录上次发布的行号
    """
    if not os.path.exists(archivo):
        print(f"Error: 文案文件 '{archivo}' 不存在")
        exit(1)

    # 读取所有有效行（去重、去空）
    try:
        with open(archivo, 'r', encoding='utf-8') as file:
            lines = [line.strip() for line in file.readlines()]
            valid_lines = list(filter(None, lines))
        if not valid_lines:
            print(f"Error: 文案文件 '{archivo}' 中无有效内容")
            exit(1)
    except Exception as e:
        print(f"Error: 读取文案文件失败 - {str(e)}")
        exit(1)

    # 读取上次发布的索引
    index = 0
    if os.path.exists(indice_file):
        try:
            with open(indice_file, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if content.isdigit():
                    index = int(content)
        except Exception:
            pass  # 若读取失败则从0开始

    # 判断是否已发布完所有文案
    if index >= len(valid_lines):
        print(f"⚠️ 所有文案已发布完毕，即将循环回到第一条")
        print(f"📌 当前索引 {index}，已发布 {len(valid_lines)} 条")
        # 重置索引为 0，实现循环
        index = 0

    # 获取当前文案
    tweet_texto = valid_lines[index]

    # 更新索引：写入下一次要发布的行号
    try:
        with open(indice_file, 'w', encoding='utf-8') as f:
            f.write(str(index + 1))
    except Exception as e:
        print(f"Error: 无法更新索引文件 '{indice_file}' - {str(e)}")
        exit(1)

    return tweet_texto, index + 1  # 返回文案和下一个索引（用于提示）

def obtener_imagen_aleatoria(directorio="image"):
    """从指定目录随机选择有效图片（jpg/jpeg/png/gif），返回完整路径"""
    if not os.path.exists(directorio):
        print(f"Error: 图片目录 '{directorio}' 不存在")
        exit(1)
    
    image_extensiones = ('.jpg', '.jpeg', '.png', '.gif')
    imagenes = [
        os.path.join(directorio, f) 
        for f in os.listdir(directorio) 
        if os.path.isfile(os.path.join(directorio, f)) 
        and f.lower().endswith(image_extensiones)
    ]
    
    if not imagenes:
        print(f"Error: 图片目录 '{directorio}' 中无有效图片（支持格式：{image_extensiones}）")
        exit(1)
    
    return random.choice(imagenes)

# --------------------------
# 4. 核心函数：发布推文 + 输出图片路径（供工作流删除）
# --------------------------
def tweet_diario():
    # 步骤1：按顺序读取下一条文案
    tweet_texto, next_index = leer_siguiente_linea()
    print(f"\n📝 待发布文案（第 {next_index} 条）：{tweet_texto}")

    # 步骤2：随机选择一张图片并获取完整路径
    image_ruta = obtener_imagen_aleatoria()
    image_nombre = os.path.basename(image_ruta)
    print(f"🖼️  待上传图片：{image_ruta}（文件名：{image_nombre}）")

    # 步骤3：上传图片并发布推文
    try:
        print("\n🔄 开始上传图片到Twitter...")
        media_response = api_v1.media_upload(filename=image_ruta)
        if not media_response.media_id:
            print("Error: 图片上传失败，未获取到媒体ID")
            exit(1)
        print(f"✅ 图片上传成功，媒体ID：{media_response.media_id}")

        print("🔄 开始发布推文...")
        tweet_response = api_v2.create_tweet(
            text=tweet_texto,
            media_ids=[media_response.media_id]
        )
        if not tweet_response.data.get('id'):
            print("Error: 推文发布失败，未获取到推文ID")
            exit(1)
        
        tweet_id = tweet_response.data['id']
        tweet_url = f"https://twitter.com/i/web/status/{tweet_id}"
        print(f"✅ 推文发布成功！")
        print(f"📌 推文ID：{tweet_id}")
        print(f"🔗 推文链接：{tweet_url}")

        # 输出图片路径，供 GitHub Actions 删除
        print(f"\nPUBLISHED_IMAGE: {image_ruta}")

    except tweepy.TweepyException as e:
        print(f"Error: Twitter操作失败 - {str(e)}")
        exit(1)
    except Exception as e:
        print(f"Error: 推文发布流程异常 - {str(e)}")
        exit(1)

# --------------------------
# 5. 程序入口
# --------------------------
if __name__ == '__main__':
    print("=" * 50)
    print("        开始执行Twitter自动推文流程        ")
    print("=" * 50)
    tweet_diario()
    print("\n" + "=" * 50)
    print("        推文发布流程执行完成        ")
    print("=" * 50)
