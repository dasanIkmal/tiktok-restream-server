import sys
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


def generate_frames(cap):
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        _, jpeg = cv2.imencode('.jpg', frame)
        frame = jpeg.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')


class TikTok:

    def __init__(self, httpclient, logger, room_id=None, user=None, url=None):
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
            # threading.Thread(target=self.start_flask_app).start()
            self.start_display_stream()

    def start_display_stream(self):
        """
            Start displaying the live stream locally
        """
        live_url = self.get_live_url()

        if not live_url:
            raise ValueError(Error.URL_NOT_FOUND)

        self.logger.info("STARTED STREAMING...")

        try:
            cap = cv2.VideoCapture(live_url)

            if not cap.isOpened():
                self.logger.error("Error opening video stream.")
                sys.exit(1)

            cap.set(cv2.CAP_PROP_BUFFERSIZE, 3)

            frame_width = int(cap.get(3))  # Get the width of the frames
            frame_height = int(cap.get(4))  # Get the height of the frames

            cv2.namedWindow('TikTok Live Stream', cv2.WINDOW_NORMAL)
            cv2.resizeWindow('TikTok Live Stream', frame_width, frame_height)

            self.logger.info("[PRESS 'q' TO STOP STREAMING]")

            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                cv2.imshow('TikTok Live Stream', frame)

                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break

            cap.release()
            cv2.destroyAllWindows()

        except KeyboardInterrupt:
            pass
        finally:
            if self.httpclient:
                self.httpclient.close()
                self.logger.info("HTTP session closed")

        self.logger.info("FINISHED STREAMING\n")

    def generate_frames(self, cap):
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            _, jpeg = cv2.imencode('.jpg', frame)
            frame = jpeg.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')

    def start_flask_app(self):
        app = Flask(__name__)

        @app.route('/')
        def index():
            return Response(generate_frames(cv2.VideoCapture(self.get_live_url())),
                            mimetype='multipart/x-mixed-replace; boundary=frame')

        app.run(host='0.0.0.0', port=5000, debug=False)

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

            live_url_flv = json['data']['stream_url']['hls_pull_url']
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
