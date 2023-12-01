from requests import Session
import requests as req
import time
import errors
import re
from errors import Error, TimeOut
import cv2
from httpclient import HttpClient
from flask import Flask, Response
import threading
from threadedCamera import ThreadedCamera


def generate_frames(threaded_camera, skip_frames):
    """
    Generate frames for streaming.
    """
    try:
        while True:
            frame_bytes = threaded_camera.get_frame()

            if not frame_bytes:
                # If frame is not available, yield an empty frame
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n\r\n\r\n')
                continue

            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n\r\n')

            time.sleep(skip_frames * threaded_camera.FPS)

    except Exception as e:
        # Log any exceptions that might occur during frame generation
        print(f"Error in generate_frames: {e}")


class TikTok:

    def __init__(self, httpclient, logger, room_id=None, user=None, url=None):
        self.camera = None
        self.logger = logger
        self.room_id = room_id
        self.user = user
        self.url = url
        if httpclient is not None:
            self.httpclient: Session = httpclient.req
        else:
            self.httpclient = req

        if self.room_id is None:
            self.room_id = self.get_room_id_from_user()

        self.logger.info(f"USERNAME: {self.user}")
        self.logger.info(f"ROOM_ID:  {self.room_id}")

        # I create a new httpclient without proxy
        self.httpclient = HttpClient(self.logger).req

    def run(self):
        """
        running the application
        checking if the user is live at the moment
            if yes starting to display the stream
            if no just print user is not live at the moment
        """
        if not self.is_user_in_live():
            self.logger.info(f"{self.user} is not live at the moment ")
        else:
            self.logger.info(f"{self.user} is live, we can get the stream this is the chanel if {self.room_id}")
            threading.Thread(target=self.start_flask_app).start()

    def start_flask_app(self):
        app = Flask(__name__)
        threaded_camera = ThreadedCamera(self.get_live_url())

        @app.route('/')
        def index():
            return Response(generate_frames(threaded_camera, 5),
                            mimetype='multipart/x-mixed-replace; boundary=frame')

        app.run(host='0.0.0.0', port=5000, debug=False)


    # def use_threaded_camera(self):
    #     live_url = self.get_live_url()
    #     threaded_camera = ThreadedCamera(live_url)
    #     while True:
    #         try:
    #             threaded_camera.show_frame()
    #         except AttributeError:
    #             pass
    #         except KeyboardInterrupt:
    #             break

    def start_display_stream(self, skip_frames=5):
        """
        Start displaying the live stream locally
        """
        live_url = self.get_live_url()
        if not live_url:
            raise ValueError(Error.URL_NOT_FOUND)

        self.logger.info("STARTED STREAMING...")

        try:
            self.camera = ThreadedCamera(live_url)

            frame_counter = 0
            while True:
                frame_bytes = self.camera.get_frame()

                if frame_counter % skip_frames == 0:
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n\r\n')

                frame_counter += 1

        except KeyboardInterrupt:
            pass
        finally:
            if self.httpclient:
                self.httpclient.close()
                self.logger.info("HTTP session closed")
            if self.camera:
                self.camera.capture.release()
                cv2.destroyAllWindows()

        self.logger.info("FINISHED STREAMING\n")

    def get_room_and_user_from_url(self):
        """
        Given a url, get user and room_id.
        """
        try:
            response = self.httpclient.get(self.url, allow_redirects=False)
            content = response.text

            if response.status_code == 302:
                raise errors.Blacklisted('Redirect')

            if response.status_code == 301:  # MOBILE URL
                regex = re.findall("com/@(.*?)/live", response.text)
                if len(regex) < 1:
                    raise errors.LiveNotFound(Error.LIVE_NOT_FOUND)
                self.user = regex[0]
                self.room_id = self.get_room_id_from_user()
                return self.user, self.room_id

            self.user = re.findall("com/@(.*?)/live", content)[0]
            self.room_id = re.findall("room_id=(.*?)\"/>", content)[0]
            return self.user, self.room_id

        except (req.HTTPError, errors.Blacklisted):
            raise errors.Blacklisted(Error.BLACKLIST_ERROR)
        except Exception as ex:
            self.logger.error(ex)
            exit(1)

    def get_room_id_from_user(self) -> str:
        """
        Given a username, I get the room_id
        """
        try:
            response = self.httpclient.get(f"https://www.tiktok.com/@{self.user}/live", allow_redirects=False)
            if response.status_code == 302:
                raise errors.Blacklisted('Redirect')

            content = response.text
            if "room_id" not in content:
                raise ValueError()

            return re.findall("room_id=(.*?)\"/>", content)[0]
        except (req.HTTPError, errors.Blacklisted) as e:
            raise errors.Blacklisted(Error.BLACKLIST_ERROR)
        except ValueError:
            self.logger.error(f"Unable to find room_id. I'll try again in {TimeOut.CONNECTION_CLOSED} minutes")
            time.sleep(TimeOut.CONNECTION_CLOSED * TimeOut.ONE_MINUTE)
            return self.get_room_id_from_user()
        except AttributeError:
            time.sleep(TimeOut.CONNECTION_CLOSED * TimeOut.ONE_MINUTE)
        except Exception as ex:
            self.logger.error(ex)
            exit(1)

    def get_live_url(self) -> str:
        """
        I get the cdn (flv or m3u8) of the streaming
        """
        try:
            url = f"https://webcast.tiktok.com/webcast/room/info/?aid=1988&room_id={self.room_id}"
            json = self.httpclient.get(url).json()

            if 'This account is private' in json:
                raise errors.AccountPrivate('Account is private, login required')

            live_url_flv = json['data']['stream_url']['rtmp_pull_url']
            self.logger.info(f"LIVE URL: {live_url_flv}")

            return live_url_flv
        except errors.AccountPrivate as ex:
            raise ex
        except Exception as ex:
            self.logger.error(ex)

    def is_user_in_live(self) -> bool:
        """
        Checking whether the user is live
        """
        self.logger.info(f"checking if {self.user} user is live")
        try:
            url = f"https://www.tiktok.com/api/live/detail/?aid=1988&roomID={self.room_id}"
            content = self.httpclient.get(url).text

            return '"status":4' not in content
        except ConnectionAbortedError:
            self.logger.error(Error.CONNECTION_CLOSED_AUTOMATIC)
            time.sleep(TimeOut.CONNECTION_CLOSED * TimeOut.ONE_MINUTE)
            return False
        except Exception as ex:
            self.logger.error(ex)
