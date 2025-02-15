#  Copyright (c) 2021
#
#  This file, PocketSphinxAsr.py, is part of Project Alice.
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
#  Last modified: 2021.04.13 at 12:56:45 CEST

import shutil
import tarfile
from pathlib import Path
from typing import Optional

from core.asr.model.ASRResult import ASRResult
from core.asr.model.Asr import Asr
from core.asr.model.Recorder import Recorder
from core.commons import constants
from core.dialog.model.DialogSession import DialogSession
from core.util.Stopwatch import Stopwatch


try:
	from pocketsphinx import Decoder
except:
	pass


class PocketSphinxAsr(Asr):
	NAME = 'Pocketsphinx Asr'
	DEPENDENCIES = {
		'system': [
			'swig',
			'libpulse-dev'
		],
		'pip'   : [
			'pocketsphinx==0.1.15'
		]
	}

	LANGUAGE_PACK = {
		f'{constants.GITHUB_URL}/cmusphinx-models/blob/master/%lang%/%lang%.tar',
		f'{constants.GITHUB_URL}/cmusphinx-models/blob/master/%lang%/%lang%.lm.bin',
		f'{constants.GITHUB_URL}/cmusphinx-models/blob/master/%lang%/cmudict-%lang%.dict'
	}


	def __init__(self):
		super().__init__()
		self._capableOfArbitraryCapture = True
		self._isOnlineASR = False
		self._decoder: Optional[Decoder] = None
		self._config = None


	def onStart(self):
		super().onStart()

		if not self.checkLanguage():
			self.downloadLanguage()

		try:
			pocketSphinxPath = self.getPocketSphinxPath()
		except:
			raise

		self._config = Decoder.default_config()
		self._config.set_string('-hmm', f'{pocketSphinxPath}/model/{self.LanguageManager.activeLanguageAndCountryCode.lower()}')
		self._config.set_string('-lm', f'{pocketSphinxPath}/model/{self.LanguageManager.activeLanguageAndCountryCode.lower()}.lm.bin')
		self._config.set_string('-dict', f'{pocketSphinxPath}/model/cmudict-{self.LanguageManager.activeLanguageAndCountryCode.lower()}.dict')
		self._decoder = Decoder(self._config)


	def checkLanguage(self) -> bool:
		try:
			pocketSphinxPath = self.getPocketSphinxPath()
		except:
			raise

		if not Path(self.Commons.rootDir(), f'{pocketSphinxPath}/model/{self.LanguageManager.activeLanguageAndCountryCode.lower()}').exists():
			self.logInfo('Missing language model')
			return False

		return True


	def timeout(self):
		super().timeout()
		try:
			self._decoder.end_utt()
		except:
			# If this fails we don't care, at least we tried to close the utterance
			pass


	def downloadLanguage(self, forceLang: str = '') -> bool:
		lang = forceLang or self.LanguageManager.activeLanguageAndCountryCode
		self.logInfo(f'Downloading language model for "{lang}"')

		try:
			pocketSphinxPath = self.getPocketSphinxPath()
		except:
			raise

		for url in self.LANGUAGE_PACK:
			url = url.replace('%lang%', lang.lower())
			filename = Path(url).name
			download = Path(pocketSphinxPath, 'model', filename)
			result = self.Commons.downloadFile(url=f'{url}?raw=true', dest=str(download))
			if not result:
				if forceLang:
					return False
				else:
					# TODO be universal
					self.downloadLanguage(forceLang='en-US')
			else:
				if download.suffix == '.tar':
					dest = Path(pocketSphinxPath, 'model', lang.lower())

					if dest.exists():
						shutil.rmtree(dest)

					tar = tarfile.open(str(download))
					tar.extractall(str(dest))

					download.unlink()

		self.logInfo('Downloaded and installed')
		return True


	def decodeStream(self, session: DialogSession) -> Optional[ASRResult]:
		super().decodeStream(session)

		result = None
		counter = 0
		with Stopwatch() as processingTime:
			with Recorder(self._timeout, session.user, session.deviceUid) as recorder:
				self.ASRManager.addRecorder(session.deviceUid, recorder)
				self._recorder = recorder
				self._decoder.start_utt()
				inSpeech = False
				for chunk in recorder:
					if self._timeout.is_set():
						break

					self._decoder.process_raw(chunk, False, False)
					hypothesis = self._decoder.hyp()
					if hypothesis:
						counter += 1
						if counter == 10:
							self.partialTextCaptured(session, hypothesis.hypstr, hypothesis.prob, processingTime.time)
							counter = 0
					if self._decoder.get_in_speech() != inSpeech:
						inSpeech = self._decoder.get_in_speech()
						if not inSpeech:
							self._decoder.end_utt()
							result = self._decoder.hyp() if self._decoder.hyp() else None
							break

				self.end()

		return ASRResult(
			text=result.hypstr.strip(),
			session=session,
			likelihood=self._decoder.hyp().prob,
			processingTime=processingTime.time
		) if result else None


	def getPocketSphinxPath(self) -> Path:
		if Path(f'{self.Commons.rootDir()}/venv/lib/python3.7/').exists():
			return Path(f'{self.Commons.rootDir()}/venv/lib/python3.7/site-packages/pocketsphinx')
		elif Path(f'{self.Commons.rootDir()}/venv/lib/python3.9/').exists():
			return Path(f'{self.Commons.rootDir()}/venv/lib/python3.9/site-packages/pocketsphinx')
		else:
			raise Exception('Python 3.7 or 3.9 not found')
