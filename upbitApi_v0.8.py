# v0.7 코인 가격이 오를 때 red, 내릴 때 blue 색으로 출력되도록 변경
# v0.8 특정 가격이 되면 지정해 놓은 텔레그램으로 메시지 전송

import requests
import sys
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5 import uic
import pyupbit

import telegram
import asyncio

import time

form_class = uic.loadUiType("ui/bitcoin.ui")[0]  # 외부 ui 불러오기

class UpbitApi(QThread):  # 시그널 클래스->스레드 클래스

    coinDataSent = pyqtSignal(float, float)  # 시그널 함수->슬롯 함수에 데이터 전송
    
    def __init__(self, ticker):
    # 시그널 클래스로 객체가 선언될 때 메인윈도우 클래스에서 ticker를 받아오도록 설계
        super().__init__()
        self.ticker = ticker
        self.alive = True
    
    def run(self):
        while self.alive: # 무한루프(3초에 한번씩 실행)
            server_url = "https://api.upbit.com"
            params = {
                "markets": self.ticker
            }
            res = requests.get(server_url + "/v1/ticker", params=params)
            # print(res.json())
            coin_info = res.json()  # 리스트
            # print(btc_info[0]["trade_price"])  # 코인의 현재가격
            trade_price = coin_info[0]["trade_price"]  # 코인의 현재가격
            signed_change_rate = coin_info[0]["signed_change_rate"]  # 코인의 가격 변화율

            # trade_price = pyupbit.get_current_price(self.ticker)  # 입력된 코인의 가격 가져오기
            # print(trade_price)
            self.coinDataSent.emit(float(trade_price), float(signed_change_rate))  # 시그널 함수인 coinDataSent로 가져온 코인가격 데이터를 제출

            time.sleep(3)  # 업비트 호출하는 딜레이 3초로 설정

    def close(self):
        self.alive = False


class MainWindow(QMainWindow, form_class):  # 슬롯 클래스
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        
        self.upbitapi = UpbitApi("KRW-BTC")  # 시그널 클래스로 객체 생성
        
        self.comboBox_setting()  # 콤보박스 초기화 메소드 호출
        self.ticker_combobox.currentIndexChanged.connect(self.comboBox_active)
        # 콤보박스의 메뉴를 유저가 변경하면 발생하는 이벤트 처리
        self.upbitapi.coinDataSent.connect(self.printCoinData)  # 시그널 함수와 슬롯 함수를 연결
        self.upbitapi.start()
        # self.upbitapi.run()
        self.coinPrev = 0
        self.alarmFlag = 0
        
    def comboBox_setting(self):  # 콤보박스 초기값들 셋팅
        # 코인 종류(원화가격표시) ticker 리스트 가져오기(리스트 타입으로 반환)
        tickerList = pyupbit.get_tickers(fiat="KRW")

        tickerList2 = []
        for ticker in tickerList:
            tickerList2.append(ticker[4:])  # KRW- 제거

        tickerList2 = sorted(tickerList2)
        tickerList2.remove("BTC")  # 비트코인 ticker 삭제
        tickerList2 = ["BTC"] + tickerList2  # 비트코인 ticker를 제일 첫번째 순서로 고정
        self.ticker_combobox.addItems(tickerList2)  # 콤보박스 셋팅
    
    def comboBox_active(self):  # 콤보박스의 메뉴가 변경되었을 때 호출되는 메소드
        selected_ticker = self.ticker_combobox.currentText()  # 현재 콤보박스에서 선택된 메뉴 텍스트 가져오기
        self.ticker_label.setText(selected_ticker)
        self.upbitapi.close()  # 시그널 클래스의 while문 무한루프가 정지->시그널 클래스 객체가 삭제
        self.upbitapi = UpbitApi(f"KRW-{selected_ticker}")  # 시그널 클래스로 새로운 객체 생성
        self.upbitapi.coinDataSent.connect(self.printCoinData)  # 시그널 함수와 슬롯 함수를 연결
        self.upbitapi.start()

    def printCoinData(self, coinPrice, signed_change_rate):  # 슬롯 함수->시그널 함수에서 보내준 데이터를 받아주는 함수
        print(f"비트코인의 현재가격: {coinPrice}")

        if int(coinPrice) >= 134500000:
            self.telegram_message(f"지정 가격 도달! 현재 {coinPrice:,.0f}원 입니다.")

        if int(coinPrice) <= 134350000:
            if self.alarmFlag == 0:
                self.telegram_message(f"지정 가격 도달! 현재 {coinPrice:,.0f}원 입니다.")
                self.alarmFlag = 1

        self.price_label.setText(f"{coinPrice:,.0f}")

        print(f"비트코인의 이전 가격:{int(self.coinPrev)}")
        if self.coinPrev < int(coinPrice):  # 오름
            print("오름")
            self.price_label.setStyleSheet("color:red;")
        elif self.coinPrev == int(coinPrice):
            print("같음")
            self.price_label.setStyleSheet("color:green;")
        else:  # 내림
            print("내림")
            self.price_label.setStyleSheet("color:blue;")
        self.coinPrev = int(str(self.price_label.text()).replace(",",""))  
        # 이전 값 문자열에서 , 제거 후 interger 변환 추가
    
    # def up_style(self):  # 변화율이 +면 코인가격이 빨간색으로, -면 파란색으로 표시
    #     print(self.changeRate)
    #     if "-" in self.changeRate:
    #         self.price_label.setStyleSheet("color:blue;")
    #     else:
    #         self.price_label.setStyleSheet("color:red;")

    # 텔레그램에 메시지를 전송해주는 메소드(전송 텍스트 인수)
    def telegram_message(self, message):
        bot = telegram.Bot(token="")
        chat_id = ""

        asyncio.run(bot.sendMessage(chat_id=chat_id, text=message))


app = QApplication(sys.argv)
win = MainWindow()
win.show()
sys.exit(app.exec_())

