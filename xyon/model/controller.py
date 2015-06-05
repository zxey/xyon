import model.qobjectlistmodel
import model.youtubeservice
import model.soundcloudservice
import model.player
import model.servicemanager
import model.downloadmanager
import model.downloadentry

import json
import urllib.parse
import pickle
import os

import pafy

from PyQt5.QtNetwork import *
from PyQt5.QtMultimedia import QMediaPlayer
from PyQt5.QtCore import \
    QObject, \
    pyqtSignal, \
    pyqtProperty, \
    pyqtSlot, \
    QUrl, \
    QPoint

from PyQt5.QtWidgets import QFileDialog, QWidget
from PyQt5.QtGui import QCursor

suffixes = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']


def humansize(nbytes):
    if nbytes == 0:
        return '0 B'
    i = 0
    while nbytes >= 1024 and i < len(suffixes) - 1:
        nbytes /= 1024.
        i += 1
    f = ('%.2f' % nbytes).rstrip('0').rstrip('.')
    return '%s %s' % (f, suffixes[i])


class Controller(QObject):

    def __init__(self, parent=None):
        super().__init__(parent)

        self._suggestionList = model.qobjectlistmodel.QObjectListModel([], self)

        self._serviceManager = model.servicemanager.ServiceManager(self)
        self._player = model.player.Player(self._serviceManager, self)

        self._network_manager = QNetworkAccessManager(self)
        self._network_manager.finished.connect(self.reply_finished)

        self._yPosition = 200
        self._xPosition = 200

        self._audioList = model.qobjectlistmodel.QObjectListModel([], self)
        self.downloader = model.downloadmanager.DownloadManager("tracks")
        self.downloader.start()

    # pyqtSignals
    xPositionChanged = pyqtSignal()
    yPositionChanged = pyqtSignal()

    @pyqtSlot()
    def tstarted(self):
        print("Thread started")

    @pyqtSlot(str)
    def print_completed(self, string):
        print("Completed:", string)

    @pyqtSlot(int)
    def print_progress(self, number):
        print("Progress:", number)

    @pyqtProperty(int, notify=xPositionChanged)
    def xPosition(self):
        return self._xPosition

    @xPosition.setter
    def xPosition(self, value):
        if self._xPosition != value:
            self._xPosition = value
            self.xPositionChanged.emit()

    @pyqtProperty(int, notify=yPositionChanged)
    def yPosition(self):
        return self._yPosition

    @yPosition.setter
    def yPosition(self, value):
        if self._yPosition != value:
            self._yPosition = value
            self.yPositionChanged.emit()

    @pyqtProperty(model.servicemanager.ServiceManager, constant=True)
    def serviceManager(self):
        return self._serviceManager

    @pyqtProperty(QMediaPlayer, constant=True)
    def player(self):
        return self._player

    @pyqtSlot(str, name="queryCompletion")
    def query_completion(self, text):
        if text is None or text == "":
            print("Empty query")
            self.reply_finished(None)
        else:
            print("Querying completion for", text)
            self._network_manager.get(QNetworkRequest(QUrl("http://suggestqueries.google.com/complete/search?client=firefox&ds=yt&"
                                                           + urllib.parse.urlencode({"q": text}))))

    @pyqtProperty(model.qobjectlistmodel.QObjectListModel, constant=True)
    def suggestionList(self):
        return self._suggestionList

    @pyqtSlot(QNetworkReply)
    def reply_finished(self, reply):
        if reply is None:
            self._suggestionList.clear()
        else:
            data_str = reply.readAll().data().decode("utf-8")
            obj = json.loads(data_str)
            if len(obj) == 2:
                self._suggestionList.setObjectList(obj[1])
            else:
                self._suggestionList.clear()

    @pyqtSlot(name="savePlaylist")
    def save_playlist(self):
        print("Saving playlist")

        file_name = QFileDialog.getSaveFileName(QWidget(), "Save playlist", "", "Xyon Playlist (*.xyp)")[0]
        print(file_name)

        serialized_entries = self.player.playlist.save()

        playlist_file = open(file_name, "wb+")
        pickle.dump(serialized_entries, playlist_file)
        playlist_file.close()

        print("Playlist saved")

    @pyqtSlot(name="openPlaylist")
    def open_playlist(self):
        print("Loading playlist")

        file_name = QFileDialog.getOpenFileName(QWidget(), "Open playlist", "", "Xyon Playlist (*.xyp)")[0]
        print(file_name)

        playlist_file = open(file_name, "rb")
        data = pickle.load(playlist_file)
        playlist_file.close()

        self.player.playlist.load(data)

        print("Playlist loaded")

    @pyqtSlot(QPoint, name="changePosition")
    def change_position(self, area_point):
        # print("before")
        if os.name == "nt":
            import win32con
            import win32gui
            hwnd = win32gui.GetForegroundWindow()
            if win32gui.GetWindowText(hwnd) == "Xyon":
                # print("is xyon")
                win32gui.SendMessage(hwnd, win32con.WM_SYSCOMMAND, 61458)
                win32gui.SendMessage(hwnd, win32con.WM_LBUTTONUP)
        else:
            point = QCursor.pos()
            self.xPosition = point.x() - area_point.x()
            self.yPosition = point.y() - area_point.y()
        # print("after")

    def remove_invalid_chars(self, value):
        for c in "<>:\"/\\|?*":
            value = value.replace(c, "")
        return value

    @pyqtSlot(model.audioentry.AudioEntry, name="downloadEntry")
    def download_entry(self, entry):
        print("fetching info for", entry.title)
        self.audioList.clear()
        video = pafy.new(entry.url)
        stream = video.getbestaudio()
        name = self.remove_invalid_chars(entry.title) + "." + stream.extension
        f = open("tracks" + os.sep + name, "w+")
        f.close()
        self.downloader.add(model.downloadentry.DownloadEntry(stream.url, name))

    @pyqtProperty(model.qobjectlistmodel.QObjectListModel, constant=True)
    def audioList(self):
        return self._audioList
