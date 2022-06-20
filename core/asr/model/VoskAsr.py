#  Copyright (c) 2022
#
#  This file, VoskAsr.py, is part of Project Alice.
#
#  Project Alice is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <https://www.gnu.org/licenses/>
#
#  Last modified: 2022.06.20 at 13:00:00 CEST

import numpy as np
import json
from pathlib import Path
from typing import Generator, Optional

from core.asr.model.ASRResult import ASRResult
from core.asr.model.Asr import Asr
from core.asr.model.Recorder import Recorder
from core.dialog.model.DialogSession import DialogSession
from core.util.Stopwatch import Stopwatch

try:
	import vosk
except:
	pass


class VoskAsr(Asr):
	NAME = 'Vosk Asr'
	DEPENDENCIES = {
		'system': [],
		'pip'   : {
			'vosk'
		}
	}


	def __init__(self):
		super().__init__()
		self._capableOfArbitraryCapture = True
		self._isOnlineASR = False
		self._model: Optional[vosk.Model] = None

	def onStart(self):
		super().onStart()
		self.installDependencies()
		self.logInfo(f'Loading Model')
		self._model = vosk.Model(lang=self.LanguageManager.activeLanguage)
		self.logInfo(f'Model Loaded')

	def installDependencies(self) -> bool:
		self.Commons.runSystemCommand(['./venv/bin/pip', 'install', 'vosk'])

	def onVadUp(self):
		# Vosk uses internal VAD

	def onVadDown(self):
		# Vosk uses internal VAD

	def decodeStream(self, session: DialogSession) -> Optional[ASRResult]:
		super().decodeStream(session)
		result = None
		previous = ''

		with Stopwatch() as processingTime:
			with Recorder(self._timeout, session.user, session.deviceUid) as recorder:
				self.ASRManager.addRecorder(session.deviceUid, recorder)
				self._recorder = recorder
				recognizer = vosk.KaldiRecognizer(self._model, 16000.0)
				for chunk in recorder:

					if not chunk:
						break

					end_of_speech = recognizer.AcceptWavefrom(chunk)
					if end_of_speech:
						break

					result = json.loads(recognizer.PartialResult())
					if result['parial'] and result['partial'] != previous:
						previous = result
						self.partialTextCaptured(session=session, text=result['partial'], likelihood=1, seconds=0)

				result = json.loads(recognizer.FinalResult())['text']
				self.end()

		return ASRResult(
			text=result,
			session=session,
			likelihood=1.0,
			processingTime=processingTime.time
		) if result else None
