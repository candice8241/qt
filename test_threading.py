#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试线程是否正常工作的独立脚本
"""

import sys
import time
import threading
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QTextEdit, QLabel
from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from PyQt6.QtGui import QFont

class WorkerSignals(QObject):
    """信号对象"""
    finished = pyqtSignal(str)
    progress = pyqtSignal(str)
    error = pyqtSignal(str)

class TestWorker(threading.Thread):
    """测试工作线程"""
    def __init__(self, signals):
        super().__init__(daemon=True)
        self.signals = signals
    
    def run(self):
        """模拟长时间运行的任务"""
        try:
            self.signals.progress.emit("开始任务...")
            time.sleep(1)
            
            self.signals.progress.emit("处理中... 25%")
            time.sleep(1)
            
            self.signals.progress.emit("处理中... 50%")
            time.sleep(1)
            
            self.signals.progress.emit("处理中... 75%")
            time.sleep(1)
            
            self.signals.progress.emit("处理中... 100%")
            time.sleep(1)
            
            self.signals.finished.emit("任务完成！")
        except Exception as e:
            self.signals.error.emit(f"错误: {str(e)}")

class TestWindow(QWidget):
    """测试窗口"""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("线程测试")
        self.setGeometry(100, 100, 600, 400)
        
        layout = QVBoxLayout(self)
        
        # 标题
        title = QLabel("测试后台线程是否会卡住GUI")
        title.setFont(QFont('Arial', 14, QFont.Weight.Bold))
        layout.addWidget(title)
        
        # 说明
        info = QLabel("点击按钮后，如果能看到进度更新且窗口可以拖动，说明线程正常")
        info.setWordWrap(True)
        layout.addWidget(info)
        
        # 启动按钮
        self.start_btn = QPushButton("启动测试任务")
        self.start_btn.clicked.connect(self.start_task)
        layout.addWidget(self.start_btn)
        
        # 日志区域
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        layout.addWidget(self.log_text)
        
        self.worker = None
    
    def log(self, message):
        """添加日志"""
        self.log_text.append(message)
    
    def start_task(self):
        """启动任务"""
        self.log("=" * 50)
        self.log("启动后台任务...")
        self.start_btn.setEnabled(False)
        
        # 延迟启动
        QTimer.singleShot(100, self._start_worker)
    
    def _start_worker(self):
        """实际启动工作线程"""
        signals = WorkerSignals()
        signals.progress.connect(self.log)
        signals.finished.connect(self.on_finished)
        signals.error.connect(self.on_error)
        
        self.worker = TestWorker(signals)
        self.worker.start()
        self.log("✓ 线程已启动")
    
    def on_finished(self, message):
        """任务完成"""
        self.log(message)
        self.log("=" * 50)
        self.start_btn.setEnabled(True)
    
    def on_error(self, message):
        """任务出错"""
        self.log(f"❌ {message}")
        self.start_btn.setEnabled(True)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = TestWindow()
    window.show()
    sys.exit(app.exec())
