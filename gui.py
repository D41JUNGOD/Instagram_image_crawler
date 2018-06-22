import logging as log  # 파이썬 로깅
import os
import sys
from time import *

from PyQt5 import uic
from PyQt5.QtCore import QSize
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

from HashTagSearchManager import HashTagSearchManager  # HashTagSearchManager.py 에서 HashTagSearchManager 함수를 import

appStyle="""
QMainWindow{
background-color: #d5d5d5;
}
"""

form_class = uic.loadUiType("ui/Main_window.ui")[0]
class Main_Window(QMainWindow, form_class):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.pushButton_1.clicked.connect(self.btn_clicked_1)
        self.pushButton_2.clicked.connect(self.btn_clicked_2)
        self.pushButton_3.clicked.connect(self.btn_clicked_3)
        self.setWindowIcon(QIcon('ui/image/instagram.png'))

        self.setStyleSheet(appStyle)
        self.pushButton_1.setIcon(QIcon('ui/image/camera.png'))
        self.pushButton_1.setIconSize(QSize(40, 40))
        layout = QVBoxLayout(self)
        layout.addWidget(self.pushButton_1)

        self.pushButton_2.setIcon(QIcon('ui/image/crawl.png'))
        self.pushButton_2.setIconSize(QSize(40, 40))
        layout = QVBoxLayout(self)
        layout.addWidget(self.pushButton_2)

        self.pushButton_3.setIcon(QIcon('ui/image/result.png'))
        self.pushButton_3.setIconSize(QSize(40, 40))
        layout = QVBoxLayout(self)
        layout.addWidget(self.pushButton_3)

        self.pushButton_4.setIcon(QIcon('ui/image/logout.png'))
        self.pushButton_4.setIconSize(QSize(40, 40))
        layout = QVBoxLayout(self)
        layout.addWidget(self.pushButton_4)

    def btn_clicked_1(self):
        up = Upload()
        up.exec()

    def btn_clicked_2(self):
        crawl = Crawling()
        crawl.exec()

    def btn_clicked_3(self):
        result = Result()
        result.exec()

form_class = uic.loadUiType("ui/Upload.ui")[0]
class Upload(QDialog, form_class):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.lineEdit.returnPressed.connect(self.lineEditInput)
        self.setWindowIcon(QIcon('ui/image/instagram.png'))

    def lineEditInput(self):
        path = str(self.lineEdit.text())
        print("경로 입력 받음")
        if not os.path.exists(path):
            print("파일을 찾을 수 없습니다")
            QMessageBox.warning(self, "알림", "파일을 찾을 수 없습니다.")
        else:
            manager.cur.execute(manager.source_image_insert_sql, (path,))
            manager.conn.commit()
            print("파일이 정상적으로 등록되었습니다")
            QMessageBox.information(self, "알림", "파일이 정상적으로 등록되었습니다.")
        self.close()

form_class = uic.loadUiType("ui/Crawling.ui")[0]
class Crawling(QDialog, form_class):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.lineEdit.returnPressed.connect(self.lineEditInput)
        self.setWindowIcon(QIcon('ui/image/instagram.png'))

    def lineEditInput(self):
        try:
            QMessageBox.information(self,"알림","크롤링 시작")
            keyword = str(self.lineEdit.text())
            start = time()
            total = manager.extract_recent_tag(keyword)
            end = time()
            print("탐색 시간 : " + str(int(end - start)) + "초\n총 탐색 개수 : " + str(total))
            QMessageBox.information(self, "알림", "탐색 시간 : "+str(int(end-start))+"초\n총 탐색 개수 : "+str(total))
            self.label.setText("크롤링 완료")
        except:
            QMessageBox.information(self, "알림", "크롤링 할 데이터 너무 적거나 없습니다.")
        finally:
            self.close()

form_class = uic.loadUiType("ui/Result.ui")[0]
class Result(QDialog, form_class):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.browser = QTextBrowser(self)
        self.browser.resize(650,550)
        self.browser.move(25,10)
        self.lineEdit.returnPressed.connect(self.lineEditInput)
        self.setWindowIcon(QIcon('ui/image/instagram.png'))

    def lineEditInput(self):
        try:
            i = 0
            self.browser.clear()
            threshold = (float(self.lineEdit.text()) - 0.001) / 100
            sql = "SELECT value, post_id, Post.display_src, Post.user, Post.code FROM Similarity LEFT JOIN Post ON Similarity.post_id = Post.id WHERE value > ? ORDER BY value DESC"
            manager.cur.execute(sql, (threshold,))
            result = manager.cur.fetchall()
            if len(result) > 0:
                for value, post_id, display_src, user_id, code in result:
                    self.browser.append("유사도 : " +str(round(value * 100, 2))+"%")
                    self.browser.append("포스트 URL : https://www.instagram.com/p/"+str(code)+"/")
                    self.browser.append("사진 링크 : "+str(display_src))
                    self.browser.append("userID : "+str(user_id))
                    self.browser.append("")
                    i += 1
                QMessageBox.information(self, "알림", "총 " + str(i) + "개의 결과가 나왔습니다.")
            else:
                print("결과가 없습니다")
                QMessageBox.information(self,"알림", "결과가 없습니다.")
        except:
            QMessageBox.about(self,"알림","잘못된 유사도가 입력되었습니다. 다시입력해 주세요.")

if __name__ == "__main__":
    log.basicConfig(level=log.INFO)
    manager = HashTagSearchManager()

    app = QApplication(sys.argv)
    Main_Window = Main_Window()

    Main_Window.show()
    app.exec_()
    print("종료합니다.")

    del manager                     # 프로그램 종료시 DB 초기화
    os.remove("database.sqlite3")
    print("DB를 초기화 했습니다.")