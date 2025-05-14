import logging
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path


class FlushFileHandler(logging.FileHandler):
	def emit(self, record):
		super().emit(record)
		self.flush()


# 設定日誌
def setup_logging(name: str = None):
	# 建立 logs 目錄
	log_dir = Path('logs')
	log_dir.mkdir(exist_ok=True)

	# 設定日誌檔名（使用當前時間）
	current_time = datetime.now().strftime('%Y%m%d_%H%M%S')
	log_file = log_dir / f'{name}-{current_time}.log'

	# 設定日誌格式
	log_format = '%(asctime)s %(levelname)-8s [%(name)s] %(message)s'
	date_format = '%Y-%m-%d %H:%M:%S'

	file_handler = logging.TimedRotatingFileHandler(
		log_file,
		when='midnight',
		interval=1,
		backupCount=30,  # 符合30天保留策略
		encoding='utf-8',
	)

	# 設定根日誌記錄器
	logging.basicConfig(
		level=logging.INFO,
		format=log_format,
		datefmt=date_format,
		handlers=[
			# logging.FileHandler(log_file, encoding="utf-8"),
			# FlushFileHandler(log_file, encoding='utf-8'),
			file_handler,
			logging.StreamHandler(),  # 同時輸出到控制台
		],
		force=True,  # <--- 強制覆蓋所有 handler，確保生效
	)

	return logging.getLogger(__name__)


async def main():
	# 初始化日誌
	# logger = setup_logging()
	setup_logging()


if __name__ == '__main__':
	main()
