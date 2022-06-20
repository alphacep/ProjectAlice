#  Copyright (c) 2021
#
#  This file, ASRManager.py, is part of Project Alice.
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
#  Last modified: 2021.07.31 at 15:54:28 CEST

from importlib import import_module, reload
from pathlib import Path
from typing import Dict

import paho.mqtt.client as mqtt
from googletrans import Translator
from langdetect import detect

from core.asr.model import Asr
from core.asr.model.ASRResult import ASRResult
from core.asr.model.Recorder import Recorder
from core.base.model.Manager import Manager
from core.commons import constants
from core.dialog.model.DialogSession import DialogSession


class ASRManager(Manager):
	NAME = 'ASRManager'


	def __init__(self):
		super().__init__(self.NAME)
		self._asr = None
		self._streams: Dict[str, Recorder] = dict()
		self._translator = Translator()
		self._usingFallback = False


	def onStart(self):
		super().onStart()
		self._startASREngine()


	def onStop(self):
		if self._asr:
			self._asr.onStop()


	def restartEngine(self):
		self._asr.onStop()
		self._startASREngine()


	def _startASREngine(self, forceAsr=None):
		self._usingFallback = False if forceAsr is None else True
		userASR = self.ConfigManager.getAliceConfigByName(configName='asr').lower() if forceAsr is None else forceAsr
		keepASROffline = self.ConfigManager.getAliceConfigByName('keepASROffline')
		stayOffline = self.ConfigManager.getAliceConfigByName('stayCompletelyOffline')
		online = self.InternetManager.online

		self._asr = None

		if userASR == 'google':
			package = 'core.asr.model.GoogleAsr'
		elif userASR == 'deepspeech':
			package = 'core.asr.model.DeepSpeechAsr'
		elif userASR == 'snips':
			package = 'core.asr.model.SnipsAsr'
		elif userASR == 'vosk':
			package = 'core.asr.model.VoskAsr'
		elif userASR == 'coqui':
			package = 'core.asr.model.CoquiAsr'
		else:
			package = 'core.asr.model.PocketSphinxAsr'

		module = import_module(package)
		asr = getattr(module, package.rsplit('.', 1)[-1])
		self._asr = asr()

		if not self._asr.checkDependencies():
			if not self._asr.installDependencies():
				self._asr = None
			else:
				module = reload(module)
				asr = getattr(module, package.rsplit('.', 1)[-1])
				self._asr = asr()

		if self._asr is None:
			self.logFatal("Couldn't install Asr, going down")
			return

		if self._asr.isOnlineASR and (not online or keepASROffline or stayOffline):
			self._asr = None

		if self._asr is None:
			if not forceAsr:
				fallback = self.ConfigManager.getAliceConfigByName('asrFallback')
				self.logWarning(f'Asr did not satisfy the user settings, falling back to **{fallback}**')
				self._startASREngine(forceAsr=fallback)
			else:
				self.logFatal('Fallback ASR failed, going down')
				return

		try:
			self._asr.onStart()
		except Exception as e:
			fallback = self.ConfigManager.getAliceConfigByName('asrFallback')
			if userASR == fallback:
				self.logFatal("Couldn't start any ASR, going down")
				return

			self.logWarning(f'Something went wrong starting user ASR, falling back to **{fallback}**: {e}', printStack=True)
			self._startASREngine(forceAsr=fallback)


	@property
	def asr(self) -> Asr:
		return self._asr


	def onInternetConnected(self):
		if not self._usingFallback or self.ConfigManager.getAliceConfigByName('stayCompletelyOffline') or self.ConfigManager.getAliceConfigByName('keepASROffline') or \
				self.ConfigManager.getAliceConfigByName('asrFallback') == self.ConfigManager.getAliceConfigByName('asr'):
			return

		if not self._asr.isOnlineASR:
			self.logInfo('Connected to internet, switching Asr')
			self.restartEngine()


	def onInternetLost(self):
		if self._asr.isOnlineASR:
			self.logInfo('Internet lost, switching to offline Asr')
			self.restartEngine()


	def onStartListening(self, session: DialogSession):
		self._asr.onStartListening(session)
		self.ThreadManager.newThread(name=f'streamdecode_{session.deviceUid}', target=self.decodeStream, args=[session])


	def onStopListening(self, session: DialogSession):
		if session.deviceUid not in self._streams:
			return

		self._streams[session.deviceUid].stopRecording()


	def onPartialTextCaptured(self, session: DialogSession, text: str, likelihood: float, seconds: float):
		self.logDebug(f'Capturing {text}')


	def decodeStream(self, session: DialogSession):
		result: ASRResult = self._asr.decodeStream(session)

		if result and result.text:
			if session.hasEnded:
				return

			self.logDebug(f'Asr captured: {result.text}')

			text = result.text
			if self.LanguageManager.overrideLanguage and not self.ConfigManager.getAliceConfigByName('stayCompletelyOffline') and not self.ConfigManager.getAliceConfigByName('keepASROffline'):
				language = detect(text)
				if language != 'en':
					text = self._translator.translate(text=text, src=language, dest='en').text
					self.logDebug(f'Asr translated to: {text}')

			self.MqttManager.publish(topic=constants.TOPIC_TEXT_CAPTURED, payload={'sessionId': session.sessionId, 'text': text, 'device': session.deviceUid, 'likelihood': result.likelihood, 'seconds': result.processingTime})
		else:
			self.MqttManager.playSound(
				soundFilename='error',
				location=Path(f'system/sounds/{self.LanguageManager.activeLanguage}'),
				deviceUid=session.deviceUid,
				sessionId=session.sessionId
			)
			self.MqttManager.endSession(sessionId=session.sessionId)


	def onAudioFrame(self, message: mqtt.MQTTMessage, deviceUid: str):
		if deviceUid not in self._streams or not self._streams[deviceUid].isRecording:
			return

		self._streams[deviceUid].onAudioFrame(message, deviceUid)


	def onSessionError(self, session: DialogSession):
		if session.deviceUid not in self._streams or not self._streams[session.deviceUid].isRecording:
			return

		self._streams[session.deviceUid].onSessionError(session)
		self._streams.pop(session.deviceUid, None)


	def onSessionEnded(self, session: DialogSession):
		if not self._asr or session.deviceUid not in self._streams or not self._streams[session.deviceUid].isRecording:
			return

		self._asr.end()
		self._streams.pop(session.deviceUid, None)


	def onVadUp(self, deviceUid: str):
		if not self._asr or deviceUid not in self._streams or not self._streams[deviceUid].isRecording:
			return

		self._asr.onVadUp()


	def onVadDown(self, deviceUid: str):
		if not self._asr or deviceUid not in self._streams or not self._streams[deviceUid].isRecording:
			return

		self._asr.onVadDown()


	def addRecorder(self, deviceUid: str, recorder: Recorder):
		self._streams[deviceUid] = recorder


	def updateASRCredentials(self, asr: str):
		# TODO this belongs in the ASR itself
		if asr == 'google':
			Path(self.Commons.rootDir(), 'credentials/googlecredentials.json').write_text(self.ConfigManager.getAliceConfigByName('googleASRCredentials'))

			self.ASRManager.onStop()
			self.ASRManager.onStart()
