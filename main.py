import atexit
import yaml
from httpclient import HttpClient
import logger_manager
from tiktok import TikTok

yaml_file_path = 'config.yaml'


def config_properties():
    with open(yaml_file_path, 'r') as yaml_file:
        data = yaml.safe_load(yaml_file)

    # Access values from the YAML data
    channel_name = data['channel']['name']
    channel_id = data['channel']['id']
    channel_url = data['channel']['url']
    proxy = data['proxy']
    return channel_name, channel_id, proxy, channel_url


def cleanup(httpclient, logger):
    if httpclient:
        httpclient.close_session()
        logger.info("HTTP session closed")


def main():
    url = None
    user = None
    mode = None
    room_id = None
    proxy = None
    use_ffmpeg = None
    httpclient = None

    print("Starting Stream")
    user, room_id, proxy, url = config_properties()

    # setup logging
    logger = logger_manager.LoggerManager()

    httpclient = HttpClient(logger)

    # Register the cleanup function to run when the program exits
    atexit.register(cleanup, httpclient, logger)

    try:
        bot = TikTok(
            httpclient=httpclient,
            logger=logger,
            room_id=room_id,
            user=user,
            url=url)
        bot.run()
    except Exception as ex:
        logger.error(f'Exception caught in main:\n{ex}')
    finally:
        httpclient.close_session()


if __name__ == "__main__":
    main()
